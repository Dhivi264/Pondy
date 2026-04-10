"""
Model Exporter
==============
Exports a trained PyTorch checkpoint to ONNX format, validates the output
shape contract, runs a round-trip fidelity check, and deploys the model
for use by FaceRecognizer.
"""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ExportConfig:
    checkpoint_path: str                          # path to best.pt
    output_dir: str = "models/face_detection_trained"
    deploy_dir: str = "models/yolo_face"
    input_shape: tuple = (1, 3, 112, 112)
    expected_output_shape: tuple = (1, 128)
    rtol: float = 1e-4


@dataclass
class VerificationReport:
    input_shape: list
    output_shape: list
    max_abs_diff: float
    passed: bool


@dataclass
class ExportResult:
    onnx_path: str
    deployed_path: str
    verification: VerificationReport


class ModelExporter:
    """Converts a trained .pt checkpoint to ONNX and validates the result."""

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def export(self, config: ExportConfig) -> ExportResult:
        """
        Export *checkpoint_path* to ONNX, validate shape, run round-trip
        verification, copy to deploy_dir, and save a verification report.

        Args:
            config: Export configuration (paths, shapes, tolerance).

        Returns:
            ExportResult with paths and verification details.

        Raises:
            Any exception raised during export is logged and re-raised so
            that best.pt is never deleted on failure.
        """
        import onnxruntime
        from ultralytics import YOLO

        checkpoint_path = config.checkpoint_path
        output_dir = Path(config.output_dir)
        deploy_dir = Path(config.deploy_dir)

        try:
            logger.info(
                "[ModelExporter] Exporting %s to ONNX (imgsz=112).",
                checkpoint_path,
            )

            # Step 1: Export via Ultralytics — returns the path to the .onnx file
            onnx_path_raw = YOLO(checkpoint_path).export(
                format="onnx", imgsz=112
            )
            onnx_path = Path(str(onnx_path_raw))
            logger.info("[ModelExporter] ONNX written to %s.", onnx_path)

            # Step 2: Load the ONNX session and validate output shape
            session = onnxruntime.InferenceSession(
                str(onnx_path),
                providers=["CPUExecutionProvider"],
            )
            actual_shape = self._validate_output_shape(
                session, config.input_shape
            )
            logger.info(
                "[ModelExporter] Output shape validated: %s.", actual_shape
            )

            # Step 3: Round-trip verification against the PyTorch model
            import torch
            pt_model = YOLO(checkpoint_path).model
            pt_model.eval()

            report = self._round_trip_verify(
                pt_model, session, config.input_shape, config.rtol
            )
            if not report.passed:
                logger.warning(
                    "[ModelExporter] Round-trip verification FAILED "
                    "(max_abs_diff=%.6f > rtol=%.6f). "
                    "Saving report but continuing deployment.",
                    report.max_abs_diff,
                    config.rtol,
                )
            else:
                logger.info(
                    "[ModelExporter] Round-trip verification passed "
                    "(max_abs_diff=%.6f).",
                    report.max_abs_diff,
                )

            # Step 4: Copy ONNX to deploy directory
            deploy_dir.mkdir(parents=True, exist_ok=True)
            deployed_path = deploy_dir / "face_embed.onnx"
            shutil.copy2(str(onnx_path), str(deployed_path))
            logger.info(
                "[ModelExporter] Deployed ONNX to %s.", deployed_path
            )

            # Step 5: Save verification report
            self._save_report(report, str(output_dir))

            return ExportResult(
                onnx_path=str(onnx_path),
                deployed_path=str(deployed_path),
                verification=report,
            )

        except Exception as exc:
            logger.error(
                "[ModelExporter] Export failed: %s. "
                "Retaining checkpoint at %s.",
                exc,
                checkpoint_path,
                exc_info=True,
            )
            raise

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    def _validate_output_shape(self, session, input_shape: tuple) -> tuple:
        """
        Run one inference pass with a random float32 tensor of *input_shape*
        and assert the output shape is (1, 128).

        Args:
            session:     An onnxruntime.InferenceSession.
            input_shape: The input tensor shape, e.g. (1, 3, 112, 112).

        Returns:
            The actual output shape as a tuple.

        Raises:
            ValueError: If the output shape does not match (1, 128).
        """
        import numpy as np

        input_name = session.get_inputs()[0].name
        dummy = np.random.rand(*input_shape).astype(np.float32)
        outputs = session.run(None, {input_name: dummy})
        actual_shape = tuple(outputs[0].shape)

        if actual_shape != (1, 128):
            raise ValueError(
                f"ONNX output shape mismatch: expected (1, 128), "
                f"got {actual_shape}"
            )
        return actual_shape

    def _round_trip_verify(
        self,
        pt_model,
        onnx_session,
        input_shape: tuple,
        rtol: float,
    ) -> VerificationReport:
        """
        Compare PyTorch model output vs ONNX runtime output on the same
        random input tensor and compute the max absolute difference.

        Args:
            pt_model:     A PyTorch model in eval mode.
            onnx_session: An onnxruntime.InferenceSession.
            input_shape:  Input tensor shape, e.g. (1, 3, 112, 112).
            rtol:         Tolerance threshold; passed = max_abs_diff < rtol.

        Returns:
            VerificationReport with input_shape, output_shape,
            max_abs_diff, and passed.
        """
        import numpy as np
        import torch

        # Create a shared random input
        np_input = np.random.rand(*input_shape).astype(np.float32)
        torch_input = torch.from_numpy(np_input)

        # PyTorch inference
        with torch.no_grad():
            pt_output = pt_model(torch_input)
            # Handle models that return a tuple/list
            if isinstance(pt_output, (tuple, list)):
                pt_output = pt_output[0]
            pt_np = pt_output.cpu().numpy()

        # ONNX inference
        input_name = onnx_session.get_inputs()[0].name
        onnx_outputs = onnx_session.run(None, {input_name: np_input})
        onnx_np = onnx_outputs[0]

        max_abs_diff = float(np.max(np.abs(pt_np - onnx_np)))
        passed = max_abs_diff < rtol

        return VerificationReport(
            input_shape=list(input_shape),
            output_shape=list(onnx_np.shape),
            max_abs_diff=max_abs_diff,
            passed=passed,
        )

    def _save_report(self, report: VerificationReport, output_dir: str) -> None:
        """
        Serialise *report* to ``verification_report.json`` inside *output_dir*.

        Args:
            report:     The VerificationReport to serialise.
            output_dir: Directory where the JSON file will be written.
        """
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        report_path = out_dir / "verification_report.json"
        with report_path.open("w", encoding="utf-8") as fh:
            json.dump(asdict(report), fh, indent=2)
        logger.info("[ModelExporter] Verification report saved to %s.", report_path)
