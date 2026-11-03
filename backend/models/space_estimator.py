"""
SpaceEstimator — Geometric reasoning to find empty parking spaces.

Algorithm:
1. Build an occupancy grid from detected vehicle bounding boxes.
2. Identify contiguous free regions using connected-component analysis.
3. Apply perspective-aware scaling (vehicles near the top of frame are
   farther away, so free regions near the top accommodate fewer slots).
4. Estimate how many standard cars and scooters fit in each free region.

Vehicle size references (ground-plane, approximate):
  Car:      ~4.8 m × 2.0 m  → 9.6 m²
  Scooter:  ~1.8 m × 0.8 m  → 1.4 m²
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import cv2
import numpy as np

from models.detector import Detection

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Reference real-world sizes (in pixel-area units, calibrated per image)
# We derive a pixel-per-meter ratio from median detected vehicle size.
CAR_REAL_AREA_M2 = 9.6       # 4.8 m × 2.0 m
SCOOTER_REAL_AREA_M2 = 1.44  # 1.8 m × 0.8 m

# Packing efficiency (vehicles don't tile perfectly)
CAR_PACKING_EFF = 0.70
SCOOTER_PACKING_EFF = 0.80

# Parameters for sky/non-parking exclusion; this ensures the top region
# (horizon/sky) does not count as free parking space.
DEFAULT_SKY_CUTOFF_RATIO = 0.22  # assume top 22% is non-parking by default
MIN_SKY_CUTOFF_RATIO = 0.08
# Regional characteristics for non-parking path/building filtering.
MAX_PARKABLE_ASPECT = 4.0
MIN_PARKABLE_WIDTH_RATIO = 0.08
MIN_PARKABLE_HEIGHT_RATIO = 0.10
MIN_PARKABLE_AREA_M2 = 1.8  # avoid thin corridor-style free regions
# Equal-weight vehicle capacity uses average of car+scooter footprint
# so one 'vehicle slot' counts similarly for both types.
AVERAGE_VEHICLE_AREA_M2 = (CAR_REAL_AREA_M2 + SCOOTER_REAL_AREA_M2) / 2.0


@dataclass
class FreeRegion:
    """A contiguous empty area in the parking lot."""
    mask_coords: np.ndarray        # (N,2) pixel coordinates belonging to this region
    bounding_box: Tuple[int, int, int, int]  # x1,y1,x2,y2
    pixel_area: int
    cars_capacity: int
    scooters_capacity: int
    equivalent_capacity: int
    y_center: float                # used for perspective bucketing
    zone: str = "empty"            # 'empty' | 'partial' | 'no_parking'

    @property
    def center(self) -> Tuple[int, int]:
        x1, y1, x2, y2 = self.bounding_box
        return ((x1 + x2) // 2, (y1 + y2) // 2)
        return ((x1 + x2) // 2, (y1 + y2) // 2)


@dataclass
class EstimationResult:
    """Full output of the space estimator."""
    free_regions: List[FreeRegion]
    total_cars: int
    total_bikes: int
    detected_vehicles: int
    empty_pixel_area: int
    occupied_pixel_area: int
    total_parking_pixel_area: int
    unparkable_pixel_area: int
    occupancy_ratio: float              # 0.0 → 1.0
    capacity_cars: int
    capacity_scooters: int
    capacity_equivalent: int
    pixel_per_m2: float                 # calibration scale
    frame_shape: Tuple[int, int]        # (H, W)
    occupancy_grid: np.ndarray = field(repr=False)   # boolean H×W
    parking_mask: np.ndarray = field(repr=False)    # bool H×W


class SpaceEstimator:
    """
    Estimates available parking capacity from a list of detections
    and the image dimensions.

    Parameters
    ----------
    grid_scale : float
        Downscale factor for the occupancy grid (speed/accuracy trade-off).
        1.0 = full resolution, 0.25 = quarter resolution (default).
    min_region_pixels : int
        Minimum pixel area for a free region to be considered usable.
    perspective_strength : float
        How strongly to apply perspective correction.
        0.0 = no correction, 1.0 = full correction.
    """

    def __init__(
        self,
        grid_scale: float = 0.25,
        min_region_pixels: int = 500,
        perspective_strength: float = 0.6,
    ):
        self.grid_scale = grid_scale
        self.min_region_pixels = min_region_pixels
        self.perspective_strength = perspective_strength

    # ──────────────────────────────────────────────────────────────────────────
    def estimate(
        self,
        detections: List[Detection],
        frame_shape: Tuple[int, int],
        sky_mask: Optional[np.ndarray] = None,
    ) -> EstimationResult:
        """
        Main entry point.

        Parameters
        ----------
        detections : list[Detection]
            Vehicles detected by the detector.
        frame_shape : (H, W)
            Pixel dimensions of the source frame.
        """
        H, W = frame_shape

        # 1. Calibrate pixel-to-meter scale from median vehicle size
        pixel_per_m2 = self._calibrate_scale(detections, H, W)

        # 2. Determine parking area mask (exclude sky/horizon and sky-colour regions)
        parking_mask = self._compute_parking_mask(detections, H, W, sky_mask=sky_mask)

        # 3. Build occupancy grid
        occ_grid = self._build_occupancy_grid(detections, H, W, parking_mask)

        # 4. Find free regions via connected components
        free_regions, unparkable_px = self._find_free_regions(
            occ_grid, parking_mask, pixel_per_m2, H, W
        )

        # 5. Aggregate stats
        cars = sum(1 for d in detections if d.is_car())
        bikes = sum(1 for d in detections if d.is_bike())

        occupied_px = int(np.sum(occ_grid & parking_mask)) + unparkable_px
        empty_px = int(np.sum((~occ_grid) & parking_mask)) - unparkable_px
        total_parking_px = int(np.sum(parking_mask))

        # safety clamp to [0, total_parking_px]
        empty_px = max(0, min(empty_px, total_parking_px))

        occupancy = occupied_px / max(total_parking_px, 1)

        cap_cars = sum(r.cars_capacity for r in free_regions)
        cap_scooters = sum(r.scooters_capacity for r in free_regions)
        cap_equivalent = sum(r.equivalent_capacity for r in free_regions)

        return EstimationResult(
            free_regions=free_regions,
            total_cars=cars,
            total_bikes=bikes,
            detected_vehicles=len(detections),
            empty_pixel_area=empty_px,
            occupied_pixel_area=occupied_px,
            total_parking_pixel_area=total_parking_px,
            unparkable_pixel_area=unparkable_px,
            occupancy_ratio=round(occupancy, 3),
            capacity_cars=cap_cars,
            capacity_scooters=cap_scooters,
            capacity_equivalent=cap_equivalent,
            pixel_per_m2=pixel_per_m2,
            frame_shape=(H, W),
            occupancy_grid=occ_grid,
            parking_mask=parking_mask,
        )

    # ──────────────────────────────────────────────────────────────────────────
    def _calibrate_scale(
        self, detections: List[Detection], H: int, W: int
    ) -> float:
        """
        Estimate pixels-per-square-meter from detected car sizes.
        Falls back to a heuristic if no cars detected.
        """
        car_areas = [d.area for d in detections if d.is_car() and d.area > 100]
        if car_areas:
            median_px = float(np.median(car_areas))
            px_per_m2 = median_px / CAR_REAL_AREA_M2
        else:
            # Heuristic: assume a car takes ~2% of frame area
            frame_area = H * W
            px_per_m2 = (frame_area * 0.02) / CAR_REAL_AREA_M2

        return max(px_per_m2, 1.0)

    # ──────────────────────────────────────────────────────────────────────────
    def _compute_parking_mask(
        self,
        detections: List[Detection],
        H: int,
        W: int,
        sky_mask: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """Return boolean mask for parkable area (exclude sky/horizon)."""
        mask = np.ones((H, W), dtype=bool)

        if detections:
            top_vehicle_y = min(d.bbox[1] for d in detections)
            sky_cut = min(
                int(H * DEFAULT_SKY_CUTOFF_RATIO),
                max(int(H * MIN_SKY_CUTOFF_RATIO), top_vehicle_y - int(H * 0.08)),
            )
        else:
            sky_cut = int(H * DEFAULT_SKY_CUTOFF_RATIO)

        # Enforce reasonable limits to avoid including sky as parking
        sky_cut = max(0, min(sky_cut, int(H * 0.35)))
        mask[:sky_cut, :] = False

        if sky_mask is not None and sky_mask.shape == mask.shape:
            # If explicit sky-colour mask is provided, exclude it too.
            mask &= ~sky_mask

        return mask

    # ──────────────────────────────────────────────────────────────────────────
    def _build_occupancy_grid(
        self, detections: List[Detection], H: int, W: int, parking_mask: np.ndarray
    ) -> np.ndarray:
        """
        Build a boolean H×W occupancy grid.
        Detected bounding boxes are marked as occupied with a dilation margin
        (accounts for doors opening, driver space, etc.).
        """
        grid = np.zeros((H, W), dtype=bool)

        for det in detections:
            x1, y1, x2, y2 = det.bbox

            # Add margin proportional to vehicle size
            margin_x = max(10, int((x2 - x1) * 0.12))
            margin_y = max(10, int((y2 - y1) * 0.15))

            gx1 = max(0, x1 - margin_x)
            gy1 = max(0, y1 - margin_y)
            gx2 = min(W, x2 + margin_x)
            gy2 = min(H, y2 + margin_y)

            grid[gy1:gy2, gx1:gx2] = True

        # Exclude non-parkable area (sky/horizon) from being treated as free space
        grid[~parking_mask] = True

        return grid

    # ──────────────────────────────────────────────────────────────────────────
    def _find_free_regions(
        self,
        occ_grid: np.ndarray,
        parking_mask: np.ndarray,
        pixel_per_m2: float,
        H: int,
        W: int,
    ) -> tuple[List[FreeRegion], int]:
        """
        Connected-component analysis on the free (not occupied) grid.
        Applies perspective scaling: regions higher in the frame (farther away)
        are scaled to account for foreshortening.
        """
        free_mask = ((~occ_grid) & parking_mask).astype(np.uint8)

        # Morphological opening to remove tiny noise slivers
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
        free_mask = cv2.morphologyEx(free_mask, cv2.MORPH_OPEN, kernel)

        # Connected components
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            free_mask, connectivity=8
        )

        regions = []
        unparkable_px = 0
        for lbl in range(1, num_labels):  # skip background label 0
            px_area = int(stats[lbl, cv2.CC_STAT_AREA])
            if px_area < self.min_region_pixels:
                continue

            x = int(stats[lbl, cv2.CC_STAT_LEFT])
            y = int(stats[lbl, cv2.CC_STAT_TOP])
            bw = int(stats[lbl, cv2.CC_STAT_WIDTH])
            bh = int(stats[lbl, cv2.CC_STAT_HEIGHT])
            cy = float(centroids[lbl][1])

            # Perspective scale: 1.0 at bottom, < 1.0 at top
            # Vehicles near top appear smaller → each px represents more real area
            norm_y = cy / max(H, 1)   # 0 = top, 1 = bottom
            # perspective_factor > 1 when viewing from above (top = farther)
            perspective_factor = 1.0 + self.perspective_strength * (1.0 - norm_y)

            effective_px = px_area * perspective_factor
            real_area_m2 = effective_px / pixel_per_m2

            cars = max(0, int(real_area_m2 * CAR_PACKING_EFF / CAR_REAL_AREA_M2))
            scooters = max(0, int(real_area_m2 * SCOOTER_PACKING_EFF / SCOOTER_REAL_AREA_M2))

            # Equal-weight vehicle capacity for mixed lot estimation.
            # This assumes one unit per vehicle regardless of class (car/scooter),
            # while preserving overall usable area capacity.
            equivalent = max(0, int(real_area_m2 * ((CAR_PACKING_EFF + SCOOTER_PACKING_EFF) / 2.0) / AVERAGE_VEHICLE_AREA_M2))

            # Decide if this region is realistically parkable.
            width_ratio = bw / max(W, 1)
            height_ratio = bh / max(H, 1)
            is_narrow = (width_ratio < MIN_PARKABLE_WIDTH_RATIO) or (height_ratio < MIN_PARKABLE_HEIGHT_RATIO)
            is_elongated = (bw / max(bh, 1) > MAX_PARKABLE_ASPECT) or (bh / max(bw, 1) > MAX_PARKABLE_ASPECT)
            insufficient_area = real_area_m2 < MIN_PARKABLE_AREA_M2

            if is_narrow or is_elongated or insufficient_area:
                zone = "no_parking"
                # Mark as no-parking so final stats do not count it as empty.
                # Keep it for visualization and diagnostics.
            else:
                zone = "partial" if real_area_m2 < CAR_REAL_AREA_M2 * 1.5 else "empty"

            if zone == "no_parking":
                # Do not include extremely narrow/long walkway-like segments as parking slots.
                # Mark them as occupied for occupancy ratio reduction to avoid false open areas.
                unparkable_px += px_area
                occ_grid[labels == lbl] = True
                continue

            mask_coords = np.column_stack(np.where(labels == lbl))

            regions.append(
                FreeRegion(
                    mask_coords=mask_coords,
                    bounding_box=(x, y, x + bw, y + bh),
                    pixel_area=px_area,
                    cars_capacity=cars,
                    scooters_capacity=scooters,
                    equivalent_capacity=equivalent,
                    y_center=cy,
                    zone=zone,
                )
            )

        # Sort by capacity (largest first)
        regions.sort(key=lambda r: r.cars_capacity, reverse=True)
        return regions, unparkable_px
