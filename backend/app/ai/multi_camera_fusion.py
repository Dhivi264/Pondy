import logging
import time
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass

from app.config import settings
from app.ai.face_recognizer import FaceRecognizer

logger = logging.getLogger(__name__)


@dataclass
class GlobalTrack:
    global_id: int
    local_track_id: int
    camera_id: str
    first_seen: datetime
    last_seen: datetime
    embedding: Optional[np.ndarray] = None  # 128-d or 512-d normalized embedding
    position_history: Optional[deque] = None  # For velocity / trajectory
    confidence: float = 0.0
    employee_id: Optional[int] = None


class MultiCameraFusion:
    """
    Production Multi-Camera Tracking Fusion with ReID.
    - Assigns consistent GLOBAL IDs across all cameras.
    - Combines appearance (ReID embeddings), spatio-temporal, and face match cues.
    - Handles overlapping + non-overlapping camera topologies.
    - Feeds unified tracks to EventEngine / AttendanceEngine.
    """

    def __init__(self, face_recognizer: Optional[FaceRecognizer] = None):
        self.face_rec = face_recognizer or FaceRecognizer()  # Reuse your existing face ReID

        self.global_tracks: Dict[int, GlobalTrack] = {}          # global_id → track
        self.camera_to_global: Dict[str, Dict[int, int]] = defaultdict(dict)  # cam_id → local_id → global_id

        self.next_global_id = 1
        self.max_inactive_time = timedelta(seconds=getattr(settings, 'MULTI_CAM_INACTIVE_SECONDS', 45))

        # Embedding gallery for fast matching (global_id → embedding)
        self.global_embeddings: Dict[int, np.ndarray] = {}

        # Camera topology (optional: define adjacency or overlap matrix)
        self.camera_topology: Dict[str, List[str]] = {}  # cam_id → list of likely next cameras

        # Stats for Watchdog
        self.stats = {
            "fusion_events": 0,
            "id_assignments": 0,
            "id_merges": 0,
            "reid_matches": 0,
            "last_fusion": time.time()
        }

        logger.info("🚀 MultiCameraFusion initialized – Global person tracking across cameras enabled.")

    def register_camera_topology(self, topology: Dict[str, List[str]]):
        """Define camera adjacency for better spatio-temporal priors (e.g., "Cam1" → ["Cam2", "Cam3"])."""
        self.camera_topology = topology
        logger.info(f"[Fusion] Camera topology registered with {len(topology)} cameras.")

    def process_tracks(
        self,
        camera_id: str,
        local_tracks: List[Dict],          # From Detector.tracker.update()
        frame_np: Optional[np.ndarray] = None,
        timestamp: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Fuse local tracks into global tracks.
        Returns enriched tracks with 'global_id' and optional 'employee_id'.
        """
        if timestamp is None:
            timestamp = datetime.now()

        fused_tracks = []

        for track in local_tracks:
            local_id = track["track_id"]
            box = track["box"]
            conf = track["confidence"]

            # 1. Extract embedding (use face crop if possible, else full person crop)
            embedding = None
            if frame_np is not None:
                x1, y1, x2, y2 = map(int, box)
                crop = frame_np[max(0, y1):min(frame_np.shape[0], y2),
                                max(0, x1):min(frame_np.shape[1], x2)]
                if crop.size > 0:
                    embedding = self.face_rec.get_embedding(crop)  # Your existing 128-d normalized embedding

            # 2. Try to match with existing global tracks
            global_id = self._match_global_track(camera_id, local_id, embedding, timestamp, box)

            if global_id is None:
                # Create new global identity
                global_id = self.next_global_id
                self.next_global_id += 1

                self.global_tracks[global_id] = GlobalTrack(
                    global_id=global_id,
                    local_track_id=local_id,
                    camera_id=camera_id,
                    first_seen=timestamp,
                    last_seen=timestamp,
                    embedding=embedding,
                    position_history=deque(maxlen=30),  # last 30 positions for velocity
                    confidence=conf
                )
                self.stats["id_assignments"] += 1

            # Update existing global track
            gtrack = self.global_tracks[global_id]
            gtrack.last_seen = timestamp
            gtrack.camera_id = camera_id
            gtrack.local_track_id = local_id
            gtrack.confidence = max(gtrack.confidence, conf)

            if embedding is not None:
                gtrack.embedding = embedding
                self.global_embeddings[global_id] = embedding

            # Add position (center) for trajectory
            center_x = (box[0] + box[2]) / 2
            center_y = (box[1] + box[3]) / 2
            if gtrack.position_history is not None:
                gtrack.position_history.append((center_x, center_y, timestamp))

            # Optional: Try face match for employee linkage
            if embedding is not None and hasattr(self.face_rec, 'known_embeddings') and self.face_rec.known_embeddings:
                emp_id, match_conf = self.face_rec.match(embedding)
                if emp_id and match_conf > getattr(settings, 'FACE_MATCH_THRESHOLD', 0.5) * 0.9:
                    gtrack.employee_id = emp_id

            # Enrich original track with global info
            track["global_id"] = global_id
            track["employee_id"] = gtrack.employee_id
            fused_tracks.append(track)

            # Register mapping
            self.camera_to_global[camera_id][local_id] = global_id

        self.stats["fusion_events"] += len(local_tracks)
        self.stats["last_fusion"] = time.time()

        # Cleanup inactive global tracks
        self._cleanup_inactive_tracks(timestamp)

        return fused_tracks

    def _match_global_track(
        self,
        camera_id: str,
        local_id: int,
        embedding: Optional[np.ndarray],
        timestamp: datetime,
        box: List[float]
    ) -> Optional[int]:
        """Hierarchical matching: spatial/temporal → ReID appearance."""
        candidates = []

        # Fast filter: recent tracks from same or adjacent cameras
        for gid, gtrack in self.global_tracks.items():
            if (timestamp - gtrack.last_seen) > self.max_inactive_time:
                continue

            # Spatio-temporal bonus (same camera or adjacent)
            if gtrack.camera_id == camera_id or camera_id in self.camera_topology.get(gtrack.camera_id, []):
                candidates.append((gid, 1.0))  # high prior
            else:
                candidates.append((gid, 0.6))

        if not candidates:
            return None

        # ReID appearance matching (if embedding available)
        if embedding is not None:
            best_gid = None
            best_score = -1.0

            for gid, prior in candidates:
                known_emb = self.global_embeddings.get(gid)
                if known_emb is None:
                    continue

                # Cosine similarity
                sim = float(np.dot(embedding, known_emb))
                final_score = sim * 0.7 + prior * 0.3

                if final_score > best_score and final_score > getattr(settings, 'REID_MATCH_THRESHOLD', 0.75):
                    best_score = final_score
                    best_gid = gid

            if best_gid is not None:
                self.stats["reid_matches"] += 1
                # Merge if strong match (optional conflict resolution)
                return best_gid

        # Fallback: return most recent candidate from same/adjacent camera
        candidates.sort(key=lambda x: self.global_tracks[x[0]].last_seen, reverse=True)
        return candidates[0][0] if candidates else None

    def _cleanup_inactive_tracks(self, now: datetime):
        """Remove stale global tracks to prevent memory growth."""
        to_remove = []
        for gid, gtrack in self.global_tracks.items():
            if now - gtrack.last_seen > self.max_inactive_time * 2:
                to_remove.append(gid)

        for gid in to_remove:
            self.global_tracks.pop(gid, None)
            self.global_embeddings.pop(gid, None)

    def get_global_track(self, global_id: int) -> Optional[GlobalTrack]:
        """Retrieve a global track by ID."""
        return self.global_tracks.get(global_id)

    def get_fusion_stats(self) -> Dict:
        """For Watchdog monitoring."""
        return {
            **self.stats,
            "active_global_tracks": len(self.global_tracks),
            "total_global_ids_ever": self.next_global_id - 1,
            "avg_fusion_rate": self.stats["fusion_events"] / max(1, (time.time() - self.stats.get("init_time", time.time())) / 60)
        }


# Singleton / Global instance
multi_camera_fusion = MultiCameraFusion()
