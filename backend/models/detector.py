"""
ParkingDetector — YOLOv8-based vehicle detection for parking lots.

Detects cars, motorcycles, trucks, and buses using the COCO-pretrained
YOLOv8 model. Falls back to a stub implementation for CI/testing when
the ultralytics package is not installed.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# COCO class indices that represent vehicles
VEHICLE_CLASSES = {
    1: "bicycle",      # includes scooty/bike class from COCO
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}

# Default confidence threshold
DEFAULT_CONF = 0.25  # lower => more sensitive (more detections, may need NMS filtering)
DEFAULT_IOU = 0.35   # lower IoU to keep more overlapping boxes for small objects


@dataclass
class Detection:
    """Single vehicle detection result."""
    bbox: Tuple[int, int, int, int]   # x1, y1, x2, y2 (absolute pixels)
    confidence: float
    class_id: int
    label: str
    area: int = field(init=False)

    def __post_init__(self):
        x1, y1, x2, y2 = self.bbox
        self.area = max(0, (x2 - x1) * (y2 - y1))

    @property
    def center(self) -> Tuple[int, int]:
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) // 2, (y1 + y2) // 2)

    @property
    def width(self) -> int:
        return self.bbox[2] - self.bbox[0]

    @property
    def height(self) -> int:
        return self.bbox[3] - self.bbox[1]

    def is_car(self) -> bool:
        return self.label in ("car", "truck", "bus")

    def is_bike(self) -> bool:
        return self.label in ("motorcycle", "bicycle")


class ParkingDetector:
    """
    Wraps YOLOv8 for parking-lot vehicle detection.

    Parameters
    ----------
    model_size : str
        One of 'n' (nano), 's' (small), 'm' (medium), 'l' (large), 'x' (xlarge).
        Smaller models are faster; larger models are more accurate.
    conf : float
        Detection confidence threshold.
    iou : float
        Non-maximum suppression IoU threshold.
    device : str
        'cpu', 'cuda', or 'mps'. Defaults to auto-select.
    """

    def __init__(
        self,
        model_size: str = "x",  # xlarge for best accuracy; switch to m/l/s/n for speed
        conf: float = DEFAULT_CONF,
        iou: float = DEFAULT_IOU,
        device: Optional[str] = None,
    ):
        self.conf = conf
        self.iou = iou
        self.model = None
        self._load_model(model_size, device)

    # ──────────────────────────────────────────────────────────────────────────
    def _load_model(self, model_size: str, device: Optional[str]):
        """Load YOLOv8 from ultralytics (downloads weights on first run)."""
        try:
            from ultralytics import YOLO  # type: ignore
            import torch  # type: ignore

            # Workaround for PyTorch 2.6+ weights_only=True default 
            # Allow loading of checkpoint files with unsafe mode for trusted ultralytics weights
            import torch.serialization
            old_load = torch.load
            
            def safe_load(f, *args, weights_only=None, **kwargs):
                # Use weights_only=False for YOLOv8 checkpoint files (we trust ultralytics weights)
                if weights_only is None and isinstance(f, (str, Path)):
                    if str(f).endswith('.pt'):
                        weights_only = False
                return old_load(f, *args, weights_only=weights_only, **kwargs)
            
            torch.load = safe_load

            model_name = f"yolov8{model_size}.pt"
            self.model = YOLO(model_name)
            logger.info("✅ YOLOv8%s loaded", model_size)

            if device:
                self.model.to(device)
                
            # Restore original torch.load
            torch.load = old_load
        except ImportError:
            logger.warning(
                "ultralytics not installed — running in STUB mode. "
                "Install with: pip install ultralytics"
            )
            self.model = None

    # ──────────────────────────────────────────────────────────────────────────
    def detect(self, image: np.ndarray) -> List[Detection]:
        """
        Run vehicle detection on a BGR image (OpenCV format).

        Returns
        -------
        list[Detection]
            All detected vehicles above the confidence threshold.
        """
        if self.model is None:
            return self._stub_detect(image)

        results = self.model.predict(
            source=image,
            conf=self.conf,
            iou=self.iou,
            classes=list(VEHICLE_CLASSES.keys()),
            verbose=False,
        )

        detections: List[Detection] = []
        for r in results:
            if r.boxes is None:
                continue
            for box in r.boxes:
                cls_id = int(box.cls[0])
                if cls_id not in VEHICLE_CLASSES:
                    continue
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                detections.append(
                    Detection(
                        bbox=(x1, y1, x2, y2),
                        confidence=float(box.conf[0]),
                        class_id=cls_id,
                        label=VEHICLE_CLASSES[cls_id],
                    )
                )
        return detections

    # ──────────────────────────────────────────────────────────────────────────
    def _stub_detect(self, image: np.ndarray) -> List[Detection]:
        """
        Fallback stub: uses basic OpenCV background subtraction / blob analysis
        for a rough vehicle estimate when YOLO is unavailable.
        Note: Much lower accuracy — for development/testing only.
        """
        logger.warning("Using stub detector — results will be approximate")
        h, w = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (11, 11), 0)
        _, thresh = cv2.threshold(blurred, 80, 255, cv2.THRESH_BINARY_INV)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        detections = []
        min_area = (w * h) * 0.002   # at least 0.2% of frame
        max_area = (w * h) * 0.25    # at most 25% of frame

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if not (min_area < area < max_area):
                continue
            x, y, bw, bh = cv2.boundingRect(cnt)
            aspect = bw / max(bh, 1)
            if not (0.3 < aspect < 3.5):
                continue
            detections.append(
                Detection(
                    bbox=(x, y, x + bw, y + bh),
                    confidence=0.5,
                    class_id=2,
                    label="car",
                )
            )

        return detections

    # ──────────────────────────────────────────────────────────────────────────
    def draw_detections(
        self,
        image: np.ndarray,
        detections: List[Detection],
    ) -> np.ndarray:
        """Annotate image with bounding boxes and labels."""
        annotated = image.copy()
        colors = {
            "car": (0, 200, 80),
            "motorcycle": (255, 165, 0),
            "truck": (0, 100, 255),
            "bus": (200, 0, 200),
        }

        for det in detections:
            x1, y1, x2, y2 = det.bbox
            color = colors.get(det.label, (200, 200, 200))
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

            label_text = f"{det.label} {det.confidence:.0%}"
            (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
            cv2.rectangle(annotated, (x1, y1 - th - 6), (x1 + tw + 4, y1), color, -1)
            cv2.putText(
                annotated,
                label_text,
                (x1 + 2, y1 - 4),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 0, 0),
                1,
                cv2.LINE_AA,
            )

        return annotated
