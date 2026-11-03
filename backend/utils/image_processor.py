"""
ImageProcessor — End-to-end pipeline for single-frame parking analysis.

Pipeline:
  1. Load image (with optional EXIF-safe rotation)
  2. Run detector → list[Detection]
  3. Run estimator → EstimationResult
  4. Generate annotated image (bounding boxes)
  5. Generate heatmap overlay
  6. Serialize outputs to disk
  7. Return structured JSON-serializable dict
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Dict, Any

import cv2
import numpy as np

from models.detector import ParkingDetector
from models.space_estimator import SpaceEstimator
from utils.heatmap import HeatmapGenerator

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("outputs")


class ImageProcessor:
    """Processes a single parking lot image through the full CV pipeline."""

    def __init__(
        self,
        detector: ParkingDetector,
        estimator: SpaceEstimator,
        heatmap_gen: HeatmapGenerator,
        max_dim: int = 1280,
    ):
        self.detector = detector
        self.estimator = estimator
        self.heatmap_gen = heatmap_gen
        self.max_dim = max_dim

    # ──────────────────────────────────────────────────────────────────────────
    def process(self, file_path: Path, job_id: str) -> Dict[str, Any]:
        """
        Full processing pipeline for a single image.

        Returns
        -------
        dict
            JSON-serializable result dict matching the API contract.
        """
        # 1. Load & resize
        image = self._load_image(file_path)
        if image is None:
            raise ValueError(f"Cannot read image: {file_path}")

        H, W = image.shape[:2]
        logger.info("Processing image %s [%d×%d]", job_id[:8], W, H)

        # 2. Detect vehicles
        detections = self.detector.detect(image)
        logger.info("Detected %d vehicles", len(detections))

        # 2a. Create a sky-colour mask for high-confidence non-parking regions
        sky_mask = self._detect_sky_mask(image)

        # 3. Estimate spaces
        result = self.estimator.estimate(detections, (H, W), sky_mask=sky_mask)

        # 4. Generate annotated image
        annotated = self.detector.draw_detections(image, detections)
        annotated_path = OUTPUT_DIR / "annotated" / f"{job_id}_annotated.jpg"
        cv2.imwrite(str(annotated_path), annotated, [cv2.IMWRITE_JPEG_QUALITY, 88])

        # 5. Generate heatmap
        heatmap_img = self.heatmap_gen.generate(image, result)
        heatmap_path = OUTPUT_DIR / "heatmaps" / f"{job_id}_heatmap.jpg"
        self.heatmap_gen.save(heatmap_img, heatmap_path)

        # 6. Encode small thumbnails as base64 for inline display
        annotated_b64 = self._to_b64(annotated)
        heatmap_b64 = self._to_b64(heatmap_img)

        # 7. Build response
        return {
            "media_type": "image",
            "frame_shape": {"width": W, "height": H},
            "vehicles": {
                "cars": result.total_cars,
                "bikes": result.total_bikes,
                "trucks": sum(1 for d in detections if d.label == "truck"),
                "total": result.detected_vehicles,
            },
            "empty_spaces": len([r for r in result.free_regions if r.zone == "empty"]),
            "partial_spaces": len([r for r in result.free_regions if r.zone == "partial"]),
            "occupancy_ratio": result.occupancy_ratio,
            "estimated_capacity": {
                "cars": result.capacity_cars,
                "scooters": result.capacity_scooters,
                "equivalent_vehicles": result.capacity_equivalent,
            },
            "free_regions": [
                {
                    "bbox": list(r.bounding_box),
                    "area_px": r.pixel_area,
                    "zone": r.zone,
                    "capacity": {
                        "cars": r.cars_capacity,
                        "scooters": r.scooters_capacity,
                    },
                }
                for r in result.free_regions
            ],
            "annotated_media_url": f"/outputs/annotated/{job_id}_annotated.jpg",
            "heatmap_url": f"/outputs/heatmaps/{job_id}_heatmap.jpg",
            "annotated_b64": annotated_b64,
            "heatmap_b64": heatmap_b64,
        }

    # ──────────────────────────────────────────────────────────────────────────
    def _load_image(self, path: Path) -> np.ndarray | None:
        """Load image from disk and resize to max_dim while keeping aspect ratio."""
        img = cv2.imread(str(path))
        if img is None:
            return None

        H, W = img.shape[:2]
        if max(H, W) > self.max_dim:
            scale = self.max_dim / max(H, W)
            new_W = int(W * scale)
            new_H = int(H * scale)
            img = cv2.resize(img, (new_W, new_H), interpolation=cv2.INTER_AREA)

        return img

    # ──────────────────────────────────────────────────────────────────────────
    def _detect_sky_mask(self, image: np.ndarray, top_fraction: float = 0.35) -> np.ndarray:
        """Detect sky-like blue regions near top of image and mark as non-parkable."""
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)

        # Broad blue/sky hue range plus some white/near-white cloud margin
        blue_mask = cv2.inRange(hsv, (90, 30, 120), (140, 220, 255))
        white_mask = cv2.inRange(hsv, (0, 0, 180), (180, 70, 255))
        candidate = cv2.bitwise_or(blue_mask, white_mask)

        # Restrict to top area only to avoid mis-classifying blue cars.
        H, W = image.shape[:2]
        top_h = int(H * top_fraction)
        region_mask = np.zeros((H, W), dtype=np.uint8)
        region_mask[:top_h, :] = 255

        sky_mask = cv2.bitwise_and(candidate, candidate, mask=region_mask)
        sky_mask = cv2.morphologyEx(sky_mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
        sky_mask = cv2.erode(sky_mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)), iterations=2)

        return sky_mask.astype(bool)


    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _to_b64(image: np.ndarray, quality: int = 80) -> str:
        """Encode a BGR image as base64 JPEG string for inline API response."""
        _, buf = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, quality])
        return base64.b64encode(buf.tobytes()).decode("utf-8")
