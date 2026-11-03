"""
VideoProcessor — Frame-sampling pipeline for parking lot videos.

Strategy:
  • Extract 1 frame per `frame_interval` seconds (default: 1.0 s)
  • Run ImageProcessor on each frame
  • Aggregate detections to find stable free zones (zones consistently
    empty across ≥ 70% of processed frames)
  • Output: summary dashboard stats + annotated video
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import cv2
import numpy as np

from utils.image_processor import ImageProcessor

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("outputs")


class VideoProcessor:
    """
    Processes a parking lot video by sampling frames and aggregating results.

    Parameters
    ----------
    image_processor : ImageProcessor
        Configured single-frame processor.
    frame_interval : float
        Seconds between sampled frames (1.0 = 1 fps analysis).
    max_frames : int
        Safety cap on frames to process (avoids OOM on long videos).
    """

    def __init__(
        self,
        image_processor: ImageProcessor,
        frame_interval: float = 1.0,
        max_frames: int = 120,
    ):
        self.image_processor = image_processor
        self.frame_interval = frame_interval
        self.max_frames = max_frames

    # ──────────────────────────────────────────────────────────────────────────
    def process(
        self,
        file_path: Path,
        job_id: str,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> Dict[str, Any]:
        """
        Process a video file and return aggregated parking analysis.

        Parameters
        ----------
        file_path : Path
            Path to the uploaded video.
        job_id : str
            Unique job identifier used for output file names.
        progress_callback : callable, optional
            Called with integer progress (0–100) during processing.
        """
        cap = cv2.VideoCapture(str(file_path))
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {file_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_s = total_frames / fps
        frame_step = max(1, int(fps * self.frame_interval))

        logger.info(
            "Video: %.1fs @ %.1ffps, step=%d frames", duration_s, fps, frame_step
        )

        # ── 1. Sample & process frames ────────────────────────────────────────
        frame_results: List[Dict[str, Any]] = []
        frame_idx = 0
        processed = 0

        while cap.isOpened() and processed < self.max_frames:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                break

            try:
                frame_result = self.image_processor.process(
                    _frame_to_temp(frame, job_id, processed),
                    f"{job_id}_f{processed:04d}",
                )
                frame_results.append(frame_result)
            except Exception as exc:
                logger.warning("Frame %d failed: %s", frame_idx, exc)

            frame_idx += frame_step
            processed += 1

            if progress_callback:
                pct = 15 + int((processed / min(self.max_frames, total_frames // frame_step + 1)) * 70)
                progress_callback(min(pct, 85))

        cap.release()

        if not frame_results:
            raise RuntimeError("No frames could be processed from the video")

        # ── 2. Aggregate ──────────────────────────────────────────────────────
        aggregated = self._aggregate(frame_results, duration_s)

        # ── 3. Write annotated output video ──────────────────────────────────
        annotated_video_url = self._write_annotated_video(
            file_path, job_id, frame_step, fps
        )

        if progress_callback:
            progress_callback(95)

        aggregated["annotated_media_url"] = annotated_video_url
        aggregated["heatmap_url"] = frame_results[-1].get("heatmap_url", "")
        aggregated["heatmap_b64"] = frame_results[-1].get("heatmap_b64", "")
        aggregated["annotated_b64"] = frame_results[-1].get("annotated_b64", "")

        return aggregated

    # ──────────────────────────────────────────────────────────────────────────
    def _aggregate(
        self, results: List[Dict[str, Any]], duration_s: float
    ) -> Dict[str, Any]:
        """
        Aggregate per-frame results into a stable summary.

        Stability rule: report median values across frames.
        """
        n = len(results)

        def med(key_path: List[str]) -> float:
            vals = []
            for r in results:
                v = r
                for k in key_path:
                    v = v.get(k, {}) if isinstance(v, dict) else 0
                if isinstance(v, (int, float)):
                    vals.append(v)
            return float(np.median(vals)) if vals else 0.0

        avg_cars = med(["vehicles", "cars"])
        avg_bikes = med(["vehicles", "bikes"])
        avg_total = med(["vehicles", "total"])
        avg_occ = med(["occupancy_ratio"])
        avg_cap_cars = med(["estimated_capacity", "cars"])
        avg_cap_scooters = med(["estimated_capacity", "scooters"])
        avg_empty = med(["empty_spaces"])

        # Peak / min across frames for trends
        occ_ratios = [r.get("occupancy_ratio", 0) for r in results]
        peak_occ = max(occ_ratios) if occ_ratios else 0
        min_occ = min(occ_ratios) if occ_ratios else 0

        return {
            "media_type": "video",
            "duration_seconds": round(duration_s, 1),
            "frames_analyzed": n,
            "frame_shape": results[0].get("frame_shape", {}),
            "vehicles": {
                "cars": round(avg_cars),
                "bikes": round(avg_bikes),
                "total": round(avg_total),
            },
            "empty_spaces": round(avg_empty),
            "occupancy_ratio": round(avg_occ, 3),
            "peak_occupancy_ratio": round(peak_occ, 3),
            "min_occupancy_ratio": round(min_occ, 3),
            "estimated_capacity": {
                "cars": round(avg_cap_cars),
                "scooters": round(avg_cap_scooters),
            },
            "timeline": [
                {
                    "frame": i,
                    "occupancy_ratio": r.get("occupancy_ratio", 0),
                    "vehicles": r.get("vehicles", {}).get("total", 0),
                }
                for i, r in enumerate(results)
            ],
        }

    # ──────────────────────────────────────────────────────────────────────────
    def _write_annotated_video(
        self,
        source_path: Path,
        job_id: str,
        frame_step: int,
        fps: float,
    ) -> str:
        """Write an annotated output video sampled at frame_step."""
        out_path = OUTPUT_DIR / "annotated" / f"{job_id}_annotated.mp4"
        cap = cv2.VideoCapture(str(source_path))
        W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out_fps = max(1.0, fps / frame_step)
        writer = cv2.VideoWriter(str(out_path), fourcc, out_fps, (W, H))

        frame_idx = 0
        while cap.isOpened():
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                break
            detections = self.image_processor.detector.detect(frame)
            annotated = self.image_processor.detector.draw_detections(frame, detections)
            writer.write(annotated)
            frame_idx += frame_step

        cap.release()
        writer.release()
        return f"/outputs/annotated/{job_id}_annotated.mp4"


# ──────────────────────────────────────────────────────────────────────────────
def _frame_to_temp(frame: np.ndarray, job_id: str, idx: int) -> Path:
    """Write a video frame to a temp file so ImageProcessor can load it."""
    tmp_dir = Path("uploads") / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    p = tmp_dir / f"{job_id}_f{idx:04d}.jpg"
    cv2.imwrite(str(p), frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return p
