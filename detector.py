"""
detector.py
===========
Real-time YOLO11m object detector with BoT-SORT tracking.
Single responsibility: inference + box rendering.

Key changes from v1:
  - Double confidence filter removed (conf already applied in .track() call)
  - Colour-coded bounding boxes: green=default, orange=verified, yellow=new
  - Frame pre-resize before passing to YOLO (saves internal copy)
  - Clean model loading with proper fallback
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

import config

log = logging.getLogger(__name__)


@dataclass
class Detection:
    """A single object detection result with optional track assignment."""
    label: str
    confidence: float
    bbox: Tuple[int, int, int, int]   # x1, y1, x2, y2  (original frame coords)
    track_id: Optional[int] = None


class ObjectDetector:
    """Wrapper around Ultralytics YOLO11m with BoT-SORT tracking."""

    def __init__(self) -> None:
        self._model = None
        self._class_names: List[str] = []
        self._load_model()

    # ──────────────────────────────────────────────────────────────────────────
    # Model Loading
    # ──────────────────────────────────────────────────────────────────────────

    def _load_model(self) -> None:
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError(
                "ultralytics is not installed. Run: pip install ultralytics"
            ) from exc

        models_dir = Path(config.MODELS_DIR)
        models_dir.mkdir(parents=True, exist_ok=True)

        # Priority: models/ dir → project root → auto-download
        candidates = [
            models_dir / config.YOLO_MODEL,
            Path(config.YOLO_MODEL),
        ]
        model_path = next((p for p in candidates if p.exists()), None)

        try:
            if model_path:
                log.info("Loading YOLO model from: %s", model_path)
                self._model = YOLO(str(model_path))
            else:
                log.info("Model %s not found locally — downloading...", config.YOLO_MODEL)
                self._model = YOLO(config.YOLO_MODEL)
                # Cache to models/ for future offline use
                self._cache_model(models_dir / config.YOLO_MODEL)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load YOLO model '{config.YOLO_MODEL}': {exc}\n"
                "Ensure internet access on first run, or place the .pt file in models/"
            ) from exc

        if hasattr(self._model, "names"):
            raw = self._model.names
            self._class_names = list(raw.values()) if isinstance(raw, dict) else list(raw)

        log.info(
            "YOLO11m loaded. Classes: %d | Inference size: %dpx | Tracker: %s",
            len(self._class_names), config.INFERENCE_SIZE, config.TRACKER_TYPE,
        )

    def _cache_model(self, target: Path) -> None:
        """Copy downloaded model weights to models/ for offline future use."""
        import shutil
        candidates = [
            Path(config.YOLO_MODEL),
            Path.home() / ".ultralytics" / "assets" / config.YOLO_MODEL,
        ]
        for src in candidates:
            if src.exists() and src != target:
                shutil.copy2(str(src), str(target))
                log.info("Cached model to %s for offline use.", target)
                return

    # ──────────────────────────────────────────────────────────────────────────
    # Inference
    # ──────────────────────────────────────────────────────────────────────────

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """
        Run YOLO11m + BoT-SORT on one frame.
        Returns a list of Detection objects with track IDs assigned.
        """
        if self._model is None or frame is None or frame.size == 0:
            return []

        try:
            results = self._model.track(
                source=frame,
                conf=config.CONFIDENCE_THRESHOLD,   # applied internally — not repeated
                iou=config.NMS_IOU_THRESHOLD,
                max_det=config.MAX_DETECTIONS,
                imgsz=config.INFERENCE_SIZE,
                verbose=False,
                stream=False,
                persist=True,                        # BoT-SORT state persists across frames
                tracker=config.TRACKER_TYPE,
            )
        except Exception as exc:
            log.warning("YOLO inference error: %s", exc)
            return []

        detections: List[Detection] = []
        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                label = (
                    self._class_names[cls_id]
                    if cls_id < len(self._class_names)
                    else str(cls_id)
                )
                x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
                track_id = int(box.id[0]) if box.id is not None else None

                detections.append(
                    Detection(label=label, confidence=conf,
                              bbox=(x1, y1, x2, y2), track_id=track_id)
                )

        return detections

    # ──────────────────────────────────────────────────────────────────────────
    # Rendering
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def draw_detections(
        frame: np.ndarray,
        detections: List[Detection],
        scene_memory=None,           # SceneMemory instance (optional)
        verification_cache: Dict = None,
    ) -> None:
        """
        Draw colour-coded bounding boxes onto the frame in-place.
          - Yellow  : newly appeared object
          - Orange  : Gemini-verified label
          - Green   : standard YOLO detection
        """
        verification_cache = verification_cache or {}

        for det in detections:
            x1, y1, x2, y2 = det.bbox
            tid = det.track_id

            # Determine label to display
            display_label = det.label
            if verification_cache and tid in verification_cache:
                display_label = verification_cache[tid].get("label", det.label)

            id_str = f"#{tid}" if tid is not None else "#?"
            label_txt = f"{display_label} {id_str} {det.confidence:.0%}"

            # Colour selection
            is_verified = tid is not None and verification_cache and tid in verification_cache and bool(verification_cache[tid].get("label"))
            is_new = False
            if scene_memory is not None and tid is not None:
                rec = scene_memory.get_record(tid)
                is_new = rec.is_new if rec else False

            if is_new:
                colour = config.COLOUR_BOX_NEW
            elif is_verified:
                colour = config.COLOUR_BOX_VERIFIED
            else:
                colour = config.COLOUR_BOX_DEFAULT

            # Bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), colour, 2)

            # Label background + text
            (tw, th), baseline = cv2.getTextSize(
                label_txt, cv2.FONT_HERSHEY_SIMPLEX, config.FONT_SCALE, 1
            )
            label_y = max(y1 - 5, th + 5)
            cv2.rectangle(
                frame,
                (x1, label_y - th - 4),
                (x1 + tw + 6, label_y + baseline),
                colour, cv2.FILLED,
            )
            cv2.putText(
                frame, label_txt, (x1 + 3, label_y),
                cv2.FONT_HERSHEY_SIMPLEX, config.FONT_SCALE,
                config.COLOUR_TEXT, 1, cv2.LINE_AA,
            )
