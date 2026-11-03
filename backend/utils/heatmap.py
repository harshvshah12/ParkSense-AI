"""
HeatmapGenerator — Generates a colour-coded overlay for parking lot images.

Colour scheme:
  🟢 Green  → Empty / available space
  🟡 Yellow → Partially usable (tight fit, restricted access)
  🔴 Red    → Occupied space

The heatmap is created on a per-pixel basis using the occupancy grid and
free-region metadata from SpaceEstimator.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np

from models.space_estimator import EstimationResult, FreeRegion

logger = logging.getLogger(__name__)

# BGR colour definitions
COLOR_OCCUPIED = (0, 0, 220)        # Red
COLOR_EMPTY = (0, 210, 80)          # Green
COLOR_PARTIAL = (0, 200, 255)       # Yellow (BGR)
COLOR_NO_PARKING = (130, 130, 130)  # Gray for unparkable regions (walkway/building)
COLOR_BACKGROUND = (40, 40, 40)     # Dark grey (unknown areas)

ALPHA_OVERLAY = 0.45                # Heatmap transparency over original image


class HeatmapGenerator:
    """
    Generates heatmap overlays from EstimationResult objects.

    Parameters
    ----------
    alpha : float
        Overlay transparency. 0 = invisible, 1 = opaque.
    blur_ksize : int
        Gaussian blur kernel size for smooth heatmap edges.
    """

    def __init__(self, alpha: float = ALPHA_OVERLAY, blur_ksize: int = 31):
        self.alpha = alpha
        self.blur_ksize = blur_ksize

    # ──────────────────────────────────────────────────────────────────────────
    def generate(
        self,
        image: np.ndarray,
        result: EstimationResult,
    ) -> np.ndarray:
        """
        Produce a heatmap-overlaid BGR image.

        Parameters
        ----------
        image : np.ndarray
            Source BGR image (H × W × 3).
        result : EstimationResult
            Output from SpaceEstimator.estimate().

        Returns
        -------
        np.ndarray
            Annotated BGR image with heatmap overlay.
        """
        H, W = image.shape[:2]
        heatmap = self._build_heatmap(result, H, W)

        # Blend heatmap with original image
        blended = cv2.addWeighted(image, 1 - self.alpha, heatmap, self.alpha, 0)

        # Draw region labels (capacity text)
        blended = self._annotate_regions(blended, result.free_regions)

        # Draw legend
        blended = self._draw_legend(blended)

        return blended

    # ──────────────────────────────────────────────────────────────────────────
    def _build_heatmap(self, result: EstimationResult, H: int, W: int) -> np.ndarray:
        """Create the raw colour heatmap (H × W × 3 BGR)."""
        canvas = np.zeros((H, W, 3), dtype=np.uint8)

        # Fill occupied regions in red
        occ_mask = result.occupancy_grid.astype(np.uint8) * 255
        occ_blurred = cv2.GaussianBlur(occ_mask, (self.blur_ksize, self.blur_ksize), 0)
        canvas[occ_blurred > 30] = COLOR_OCCUPIED

        # Fill free regions based on zone type
        for region in result.free_regions:
            if region.zone == "no_parking":
                color = COLOR_NO_PARKING
            elif region.zone == "partial":
                color = COLOR_PARTIAL
            else:
                color = COLOR_EMPTY
            rows, cols = region.mask_coords[:, 0], region.mask_coords[:, 1]
            canvas[rows, cols] = color

        # Smooth the transitions
        canvas = cv2.GaussianBlur(canvas, (self.blur_ksize, self.blur_ksize), 0)

        # Re-stamp hard colors over blurred canvas
        canvas[result.occupancy_grid] = COLOR_OCCUPIED
        for region in result.free_regions:
            color = COLOR_PARTIAL if region.zone == "partial" else COLOR_EMPTY
            rows, cols = region.mask_coords[:, 0], region.mask_coords[:, 1]
            canvas[rows, cols] = color

        return canvas

    # ──────────────────────────────────────────────────────────────────────────
    def _annotate_regions(
        self, image: np.ndarray, regions: List[FreeRegion]
    ) -> np.ndarray:
        """Draw capacity labels on each free region."""
        annotated = image.copy()
        for region in regions:
            if region.cars_capacity == 0 and region.scooters_capacity < 2:
                continue
            cx, cy = region.center
            label = f"🅿 {region.cars_capacity}c / {region.scooters_capacity}s"

            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            # Background pill
            cv2.rectangle(
                annotated,
                (cx - tw // 2 - 6, cy - th - 8),
                (cx + tw // 2 + 6, cy + 4),
                (20, 20, 20),
                -1,
            )
            cv2.putText(
                annotated,
                label,
                (cx - tw // 2, cy - 2),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )
        return annotated

    # ──────────────────────────────────────────────────────────────────────────
    def _draw_legend(self, image: np.ndarray) -> np.ndarray:
        """Add a colour legend to the bottom-left corner."""
        H, W = image.shape[:2]
        items = [
            (COLOR_EMPTY, "Empty space"),
            (COLOR_PARTIAL, "Partial space"),
            (COLOR_OCCUPIED, "Occupied"),
        ]
        x_start, y_start = 14, H - 20 - len(items) * 26
        box_w = 200

        # Semi-transparent background
        overlay = image.copy()
        cv2.rectangle(
            overlay,
            (x_start - 6, y_start - 10),
            (x_start + box_w, y_start + len(items) * 26 + 4),
            (20, 20, 20),
            -1,
        )
        image = cv2.addWeighted(image, 0.4, overlay, 0.6, 0)

        for i, (color, label) in enumerate(items):
            y = y_start + i * 26
            cv2.rectangle(image, (x_start, y), (x_start + 20, y + 16), color, -1)
            cv2.putText(
                image,
                label,
                (x_start + 28, y + 13),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.52,
                (230, 230, 230),
                1,
                cv2.LINE_AA,
            )

        return image

    # ──────────────────────────────────────────────────────────────────────────
    def save(
        self,
        image: np.ndarray,
        path: Path,
        quality: int = 90,
    ) -> Path:
        """Save the heatmap image to disk as JPEG."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(path), image, [cv2.IMWRITE_JPEG_QUALITY, quality])
        logger.debug("Heatmap saved → %s", path)
        return path
