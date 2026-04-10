"""
Adaptive Frame Processor
========================
Handles two key concerns for real-world camera deployments:

1. FRAME SKIPPING
   High-resolution cameras can overwhelm a CPU/GPU if every frame is processed.
   This processor applies adaptive skipping (process every Nth frame) based on:
     - Configured skip_rate (static) OR
     - Measured system load (dynamic / auto mode)

2. EDGE-HARDWARE YOLO MODEL SELECTION
   Automatically selects the right YOLO model variant based on the detected
   or declared hardware profile:
     ┌─────────────────────────────┬──────────────────┬────────────────┐
     │ Hardware                    │ YOLO Variant     │ Skip Rate      │
     ├─────────────────────────────┼──────────────────┼────────────────┤
     │ Server GPU (CUDA)           │ YOLOv8x / v8l    │ 1 (no skip)    │
     │ Workstation CPU             │ YOLOv8m          │ 2              │
     │ Raspberry Pi 4/5            │ YOLOv8n (Nano)   │ 5              │
     │ Intel NCS2 / OpenVINO       │ YOLOv8n-openvino │ 5              │
     │ Jetson Nano                 │ YOLOv8s (TRT)    │ 3              │
     └─────────────────────────────┴──────────────────┴────────────────┘

3. LMP-TX INTEGRATION
   Processed frames feed directly into the multi-modal fusion engine,
   enriching face detection events with spatial and temporal context.
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Generator, TYPE_CHECKING
from collections import deque

if TYPE_CHECKING:
    from app.lmp_tx.event_manager import EventManager

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────
# Hardware Profiles
# ─────────────────────────────────────────────────────────────────


class HardwareProfile(str, Enum):
    SERVER_GPU = "server_gpu"  # NVIDIA CUDA server
    WORKSTATION = "workstation"  # Desktop CPU / iGPU
    JETSON_NANO = "jetson_nano"  # NVIDIA Jetson Nano (TensorRT)
    INTEL_NCS = "intel_ncs"  # Intel Neural Compute Stick 2 (OpenVINO)
    RASPBERRY_PI = "raspberry_pi"  # Raspberry Pi 4 / 5
    AUTO = "auto"  # Detect at runtime


@dataclass
class HardwareConfig:
    profile: HardwareProfile
    yolo_variant: str  # e.g. "yolov8n", "yolov8x"
    yolo_backend: str  # "pytorch" | "openvino" | "tensorrt"
    default_skip: int  # frames to skip between inferences
    max_resolution: tuple[int, int]  # (width, height) cap for this hw
    notes: str = ""


# Hardware → config mapping
HARDWARE_CONFIGS: dict[HardwareProfile, HardwareConfig] = {
    HardwareProfile.SERVER_GPU: HardwareConfig(
        profile=HardwareProfile.SERVER_GPU,
        yolo_variant="yolov8x",
        yolo_backend="pytorch",
        default_skip=1,
        max_resolution=(1920, 1080),
        notes="Full YOLOv8-XL — highest accuracy, CUDA required.",
    ),
    HardwareProfile.WORKSTATION: HardwareConfig(
        profile=HardwareProfile.WORKSTATION,
        yolo_variant="yolov8m",
        yolo_backend="pytorch",
        default_skip=2,
        max_resolution=(1280, 720),
        notes="Medium model. Process every 2nd frame to stay real-time.",
    ),
    HardwareProfile.JETSON_NANO: HardwareConfig(
        profile=HardwareProfile.JETSON_NANO,
        yolo_variant="yolov8s",
        yolo_backend="tensorrt",
        default_skip=3,
        max_resolution=(960, 540),
        notes="TensorRT-optimised small model. Every 3rd frame.",
    ),
    HardwareProfile.INTEL_NCS: HardwareConfig(
        profile=HardwareProfile.INTEL_NCS,
        yolo_variant="yolov8n",
        yolo_backend="openvino",
        default_skip=5,
        max_resolution=(640, 480),
        notes="Nano YOLO via OpenVINO IR. Every 5th frame on NCS2.",
    ),
    HardwareProfile.RASPBERRY_PI: HardwareConfig(
        profile=HardwareProfile.RASPBERRY_PI,
        yolo_variant="yolov8n",
        yolo_backend="pytorch",  # or "tflite" when converted
        default_skip=5,
        max_resolution=(640, 480),
        notes="Nano YOLO — use every 5th frame on Pi 4/5 for smooth throughput.",
    ),
}


# ─────────────────────────────────────────────────────────────────
# Runtime Hardware Detector
# ─────────────────────────────────────────────────────────────────


def detect_hardware() -> HardwareProfile:
    """
    Auto-detect the best hardware profile at startup.
    Falls back gracefully through the hierarchy.
    """
    # 1. CUDA GPU?
    try:
        import torch  # type: ignore

        if torch.cuda.is_available():
            logger.info("[HW] CUDA GPU detected → SERVER_GPU profile")
            return HardwareProfile.SERVER_GPU
    except ImportError:
        pass

    # 2. Intel OpenVINO / NCS?
    try:
        from openvino.runtime import Core  # type: ignore

        devices = Core().available_devices
        if any("MYRIAD" in d or "NCS" in d for d in devices):
            logger.info("[HW] Intel NCS detected → INTEL_NCS profile")
            return HardwareProfile.INTEL_NCS
    except Exception:
        pass

    # 3. Raspberry Pi? (check /proc/cpuinfo)
    try:
        with open("/proc/cpuinfo") as f:
            cpuinfo = f.read()
        if "BCM2" in cpuinfo or "Raspberry" in cpuinfo:
            logger.info("[HW] Raspberry Pi detected → RASPBERRY_PI profile")
            return HardwareProfile.RASPBERRY_PI
    except FileNotFoundError:
        pass

    # 4. Jetson? (check /proc/device-tree/model)
    try:
        with open("/proc/device-tree/model") as f:
            model = f.read()
        if "Jetson" in model:
            logger.info("[HW] NVIDIA Jetson detected → JETSON_NANO profile")
            return HardwareProfile.JETSON_NANO
    except FileNotFoundError:
        pass

    logger.info("[HW] No specialised hardware detected → WORKSTATION profile")
    return HardwareProfile.WORKSTATION


# ─────────────────────────────────────────────────────────────────
# Adaptive Frame Skip Controller
# ─────────────────────────────────────────────────────────────────


@dataclass
class FrameSkipStats:
    """Rolling statistics for a single camera stream."""

    camera_id: str
    total_frames_received: int = 0
    total_frames_processed: int = 0
    current_skip_rate: int = 1
    avg_inference_ms: float = 0.0
    _recent_times: deque = field(default_factory=lambda: deque(maxlen=30))

    def update_inference_time(self, ms: float) -> None:
        self._recent_times.append(ms)
        self.avg_inference_ms = sum(self._recent_times) / len(self._recent_times)

    @property
    def effective_fps(self) -> float:
        if self.avg_inference_ms <= 0:
            return 0.0
        return 1000.0 / (self.avg_inference_ms * self.current_skip_rate)


class AdaptiveFrameSkipController:
    """
    Per-camera adaptive frame skip controller.

    Static mode:  Always process every Nth frame (N = skip_rate).
    Dynamic mode: Adjusts N automatically to keep inference within the
                  target latency budget. Useful when load varies.

    Example (Raspberry Pi, static):
        ctrl = AdaptiveFrameSkipController(skip_rate=5)
        for i, frame in enumerate(stream):
            if ctrl.should_process(camera_id, i):
                run_yolo(frame)
    """

    def __init__(
        self,
        skip_rate: int = 1,
        dynamic: bool = False,
        target_latency_ms: float = 100.0,
        min_skip: int = 1,
        max_skip: int = 10,
    ):
        self.base_skip_rate = max(1, skip_rate)
        self.dynamic = dynamic
        self.target_latency_ms = target_latency_ms
        self.min_skip = min_skip
        self.max_skip = max_skip
        self._stats: dict[str, FrameSkipStats] = {}

    # ── Core decision ─────────────────────────────────────────────

    def should_process(self, camera_id: str, frame_index: int) -> bool:
        """Return True if this frame should be sent to inference."""
        stats = self._get_or_create(camera_id)
        stats.total_frames_received += 1
        process = (frame_index % stats.current_skip_rate) == 0
        if process:
            stats.total_frames_processed += 1
        return process

    def record_inference(self, camera_id: str, elapsed_ms: float) -> None:
        """
        Call after each inference. In dynamic mode, adjusts the skip rate
        automatically to stay within the target latency budget.
        """
        stats = self._get_or_create(camera_id)
        stats.update_inference_time(elapsed_ms)

        if not self.dynamic:
            return

        avg = stats.avg_inference_ms
        if (
            avg > self.target_latency_ms * 1.1
            and stats.current_skip_rate < self.max_skip
        ):
            stats.current_skip_rate += 1
            logger.debug(
                f"[FrameSkip] {camera_id}: latency {avg:.1f}ms > target, "
                f"skip_rate → {stats.current_skip_rate}"
            )
        elif (
            avg < self.target_latency_ms * 0.75
            and stats.current_skip_rate > self.min_skip
        ):
            stats.current_skip_rate -= 1
            logger.debug(
                f"[FrameSkip] {camera_id}: latency {avg:.1f}ms < 75% target, "
                f"skip_rate → {stats.current_skip_rate}"
            )

    def get_stats(self, camera_id: str) -> Optional[FrameSkipStats]:
        return self._stats.get(camera_id)

    def all_stats(self) -> list[FrameSkipStats]:
        return list(self._stats.values())

    def _get_or_create(self, camera_id: str) -> FrameSkipStats:
        if camera_id not in self._stats:
            self._stats[camera_id] = FrameSkipStats(
                camera_id=camera_id,
                current_skip_rate=self.base_skip_rate,
            )
        return self._stats[camera_id]


# ─────────────────────────────────────────────────────────────────
# YOLO Model Loader (hardware-aware)
# ─────────────────────────────────────────────────────────────────


class YOLOModelLoader:
    """
    Selects and loads the appropriate YOLO model for the detected hardware.

    Keeps a singleton model instance per config so multiple camera streams
    share a single loaded model (memory-efficient).
    """

    _instance: Optional["YOLOModelLoader"] = None
    _loaded_model = None

    def __init__(self, profile: HardwareProfile = HardwareProfile.AUTO):
        if profile == HardwareProfile.AUTO:
            profile = detect_hardware()
        self.profile = profile
        self.config = HARDWARE_CONFIGS[profile]
        logger.info(
            f"[YOLO] Profile={profile.value} | "
            f"Model={self.config.yolo_variant} | "
            f"Backend={self.config.yolo_backend} | "
            f"DefaultSkip={self.config.default_skip} | "
            f"Notes: {self.config.notes}"
        )

    @classmethod
    def get_instance(
        cls, profile: HardwareProfile = HardwareProfile.AUTO
    ) -> "YOLOModelLoader":
        if cls._instance is None:
            cls._instance = cls(profile)
        return cls._instance

    def load(self, model_path: Optional[str] = None):
        """
        Load the YOLO model. Falls back gracefully if ultralytics
        is not installed (returns a no-op stub).
        """
        if self._loaded_model is not None:
            return self._loaded_model

        try:
            from ultralytics import YOLO  # type: ignore

            path = model_path or f"{self.config.yolo_variant}.pt"
            self._loaded_model = YOLO(path)

            if self.config.yolo_backend == "openvino":
                # Export to OpenVINO IR format for NCS2 acceleration
                self._loaded_model = self._loaded_model.export(format="openvino")
                logger.info("[YOLO] Exported to OpenVINO IR for NCS2")
            elif self.config.yolo_backend == "tensorrt":
                self._loaded_model = self._loaded_model.export(format="engine")
                logger.info("[YOLO] Exported to TensorRT engine for Jetson")

            logger.info(f"[YOLO] Loaded: {path}")
        except ImportError:
            logger.warning("[YOLO] ultralytics not installed — using stub model.")
            self._loaded_model = _StubYOLO(self.config.yolo_variant)

        return self._loaded_model

    @property
    def recommended_skip_rate(self) -> int:
        return self.config.default_skip

    @property
    def max_resolution(self) -> tuple[int, int]:
        return self.config.max_resolution


class _StubYOLO:
    """
    Lightweight stub used when ultralytics is not installed.
    Returns empty detections — allows the pipeline to boot without crashing.
    """

    def __init__(self, variant: str):
        self.variant = variant

    def predict(self, frame, **kwargs):
        return []

    def __repr__(self):
        return f"<StubYOLO variant={self.variant}>"


# ─────────────────────────────────────────────────────────────────
# Integrated Stream Processor  (all 5 config params applied)
# ─────────────────────────────────────────────────────────────────


class StreamProcessor:
    """
    Full pipeline: RTSP capture → FrameBuffer → FrameSkip → YOLO →
    conf_filter → class_filter → roi_filter → LMP-TX fusion.

    All five CameraConfig parameters are respected:
        conf_threshold  → ghost suppression
        roi / polygon   → spatial mask
        queue_size      → FrameBuffer cap (lag prevention)
        classes         → class-ID whitelist
        retries         → auto-reconnect with exponential back-off

    Usage:
        from app.lmp_tx.camera_config import config_registry, CameraConfig
        cfg = CameraConfig(camera_id="cam_01", url="rtsp://...",
                           conf_threshold=0.5, classes=[0,2],
                           roi=[100,100,500,500], queue_size=30, retries=5)
        config_registry.set(cfg)

        proc = StreamProcessor.from_hardware_profile()
        for result in proc.process_stream_with_config("cam_01"):
            send_to_lmp_tx_fusion(result)
    """

    def __init__(
        self,
        loader: YOLOModelLoader,
        skip_ctrl: AdaptiveFrameSkipController,
        event_mgr: Optional["EventManager"] = None,
    ):
        self.loader = loader
        self.skip_ctrl = skip_ctrl
        self.model = loader.load()
        self.event_mgr = event_mgr
        self._clip_buffer: dict[str, list] = {}

    @classmethod
    def from_hardware_profile(
        cls,
        profile: HardwareProfile = HardwareProfile.AUTO,
        dynamic_skip: bool = True,
        target_latency_ms: float = 80.0,
        event_mgr: Optional["EventManager"] = None,
    ) -> "StreamProcessor":
        loader = YOLOModelLoader.get_instance(profile)
        ctrl = AdaptiveFrameSkipController(
            skip_rate=loader.recommended_skip_rate,
            dynamic=dynamic_skip,
            target_latency_ms=target_latency_ms,
        )
        return cls(loader=loader, skip_ctrl=ctrl, event_mgr=event_mgr)

    # ── Primary entry-point: uses CameraConfig ────────────────────

    def process_stream_with_config(
        self,
        camera_id: str,
    ) -> Generator[dict, None, None]:
        """
        Config-driven stream processor.  Reads all parameters from the
        CameraConfigRegistry and wires them into each pipeline stage.
        Call config_registry.set(cfg) before using this method.
        """
        # Late import to avoid circular dependency at module load time
        from app.lmp_tx.camera_config import config_registry
        from app.lmp_tx.frame_buffer import buffer_registry
        from app.lmp_tx.reconnect import reconnect_registry

        cfg = config_registry.get(camera_id)
        if cfg is None:
            logger.error(
                f"[StreamProcessor] No config found for {camera_id}. "
                "Register it first with config_registry.set(CameraConfig(...))"
            )
            return

        buf = buffer_registry.get_or_create(camera_id, maxsize=cfg.queue_size)
        ctrl = reconnect_registry.get_or_create(camera_id, retries=cfg.retries)

        def _one_stream_pass():
            yield from self._capture_loop(camera_id, cfg.url, cfg, buf)

        # Wrap in reconnect logic if auto_reconnect is enabled
        if cfg.auto_reconnect:
            collected: list[dict] = []

            def _stream_fn():
                for result in self._capture_loop(camera_id, cfg.url, cfg, buf):
                    collected.append(result)

            try:
                ctrl.run_with_reconnect(
                    stream_fn=_stream_fn,
                    on_reconnect=lambda _: buf.drain(),
                )
            except Exception as exc:  # StreamGaveUpError or other
                logger.error(f"[StreamProcessor] {camera_id}: {exc}")

            yield from collected
        else:
            yield from self._capture_loop(camera_id, cfg.url, cfg, buf)

    # ── Internal capture loop ─────────────────────────────────────

    def _capture_loop(
        self,
        camera_id: str,
        rtsp_url: str,
        cfg,  # CameraConfig
        buf,  # FrameBuffer
    ) -> Generator[dict, None, None]:
        """
        Single-pass RTSP capture with frame skip, filtering, and buffering.
        Raises on stream drop (ReconnectController handles the retry).
        """
        from app.lmp_tx.detection_filters import apply_all_filters
        from app.lmp_tx.clip_recorder import ClipRecorder  # Late import

        recorder = ClipRecorder()

        try:
            import cv2  # type: ignore
        except ImportError:
            logger.error("[StreamProcessor] opencv-python not installed.")
            return

        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        if not cap.isOpened():
            raise ConnectionError(f"Cannot open RTSP stream: {rtsp_url}")

        w, h = self.loader.max_resolution
        frame_idx = 0

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    raise ConnectionError(
                        f"{camera_id}: stream dropped (no frame returned)"
                    )

                # ── 3. Buffer: put every incoming frame into the queue ──
                buf.put(frame)

                # ── 1. Frame skip: only pull + infer every Nth frame ───
                if not self.skip_ctrl.should_process(camera_id, frame_idx):
                    frame_idx += 1
                    continue

                # Pull from buffer (gets the most recent, drops stale)
                proc_frame = buf.get_nowait() or frame
                proc_frame = cv2.resize(proc_frame, (w, h))

                # Run YOLO
                t0 = time.perf_counter()
                raw_out = self.model.predict(
                    proc_frame,
                    verbose=False,
                    conf=cfg.conf_threshold,  # pre-filter at model level
                    classes=cfg.classes,  # pre-filter at model level
                )
                elapsed_ms = (time.perf_counter() - t0) * 1000
                self.skip_ctrl.record_inference(camera_id, elapsed_ms)

                # ── 1. conf_filter  2. class_filter  4. roi_filter ─────
                detections = apply_all_filters(
                    raw_results=raw_out,
                    conf_threshold=cfg.conf_threshold,
                    classes=cfg.classes,
                    roi=cfg.roi,
                    roi_polygon=cfg.roi_polygon,
                )

                # ── Track Person Events ───────────────────────────────
                if self.event_mgr:
                    self.event_mgr.process_detections(camera_id, proc_frame, detections)

                    # Manage clip buffer if detections occurred
                    if detections:
                        if camera_id not in self._clip_buffer:
                            self._clip_buffer[camera_id] = []

                        self._clip_buffer[camera_id].append(proc_frame)

                        # Once we have 30 frames (approx 2s at real-time), save it
                        if len(self._clip_buffer[camera_id]) >= 30:
                            recorder.record_clip(
                                camera_id, self._clip_buffer[camera_id]
                            )
                            self._clip_buffer[camera_id] = []

                skip_stats = self.skip_ctrl.get_stats(camera_id)
                yield {
                    "camera_id": camera_id,
                    "frame_index": frame_idx,
                    "detections": detections,
                    "detection_count": len(detections),
                    "inference_ms": round(elapsed_ms, 2),
                    "skip_rate": skip_stats.current_skip_rate
                    if skip_stats
                    else cfg.frame_skip,
                    "effective_fps": round(skip_stats.effective_fps, 1)
                    if skip_stats
                    else 0,
                    "resolution": (w, h),
                    "buffer_depth": buf.depth,
                    "buffer_dropped": buf.stats.total_dropped,
                    "roi_active": cfg.roi is not None or cfg.roi_polygon is not None,
                    "classes_active": cfg.classes,
                    "conf_threshold": cfg.conf_threshold,
                }
                frame_idx += 1
        finally:
            cap.release()

    # ── Legacy entry-point (no config, kept for compatibility) ────

    def process_stream(
        self,
        camera_id: str,
        rtsp_url: str,
        max_width: Optional[int] = None,
        max_height: Optional[int] = None,
    ) -> Generator[dict, None, None]:
        """
        Bare stream processor without CameraConfig.
        Kept for backward compatibility; prefer process_stream_with_config().
        """
        try:
            import cv2  # type: ignore
        except ImportError:
            logger.error("[StreamProcessor] opencv-python not installed.")
            return

        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        if not cap.isOpened():
            logger.error(f"[StreamProcessor] Cannot open RTSP: {rtsp_url}")
            return

        w = int(max_width or self.loader.max_resolution[0])
        h = int(max_height or self.loader.max_resolution[1])
        frame_idx = 0

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    logger.warning(f"[StreamProcessor] {camera_id}: stream dropped.")
                    break

                if not self.skip_ctrl.should_process(camera_id, frame_idx):
                    frame_idx += 1
                    continue

                frame = cv2.resize(frame, (w, h))
                t0 = time.perf_counter()
                raw_out = self.model.predict(frame, verbose=False)
                elapsed_ms = (time.perf_counter() - t0) * 1000

                self.skip_ctrl.record_inference(camera_id, elapsed_ms)
                stats = self.skip_ctrl.get_stats(camera_id)

                yield {
                    "camera_id": camera_id,
                    "frame_index": frame_idx,
                    "detections": raw_out,
                    "inference_ms": round(elapsed_ms, 2),
                    "skip_rate": stats.current_skip_rate if stats else 1,
                    "effective_fps": round(stats.effective_fps, 1) if stats else 0,
                    "resolution": (w, h),
                }
                frame_idx += 1
        finally:
            cap.release()
            logger.info(f"[StreamProcessor] {camera_id}: stream closed.")
