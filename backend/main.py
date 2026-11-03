"""
Parking Space Detection API
FastAPI backend with YOLOv8 computer vision pipeline
"""

import os
import uuid
import time
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from models.detector import ParkingDetector
from models.space_estimator import SpaceEstimator
from utils.image_processor import ImageProcessor
from utils.video_processor import VideoProcessor
from utils.heatmap import HeatmapGenerator
from routers.results import router as results_router

# ─── Configuration ──────────────────────────────────────────────────────────────
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/bmp"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/avi", "video/quicktime", "video/x-msvideo"}

# In-memory job store (use Redis in production)
job_store: dict = {}

# ─── App Lifecycle ────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize models and directories on startup."""
    UPLOAD_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "annotated").mkdir(exist_ok=True)
    (OUTPUT_DIR / "heatmaps").mkdir(exist_ok=True)

    # Pre-load the YOLO model to avoid cold-start latency
    model_size = os.getenv("YOLO_MODEL_SIZE", "x")  # x, l, m, s, n
    conf = float(os.getenv("YOLO_CONF", "0.25"))
    iou = float(os.getenv("YOLO_IOU", "0.35"))

    print(f"🔧 Loading YOLOv8 model {model_size} (conf={conf}, iou={iou})...")
    app.state.detector = ParkingDetector(model_size=model_size, conf=conf, iou=iou)
    app.state.space_estimator = SpaceEstimator()
    app.state.heatmap_gen = HeatmapGenerator()
    app.state.image_proc = ImageProcessor(
        detector=app.state.detector,
        estimator=app.state.space_estimator,
        heatmap_gen=app.state.heatmap_gen,
    )
    app.state.video_proc = VideoProcessor(
        image_processor=app.state.image_proc,
        frame_interval=1.0,  # Process 1 frame per second
    )
    print("✅ Models loaded successfully")

    yield

    print("🛑 Shutting down...")


# ─── App Instance ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Parking Space Detection API",
    description="AI-powered parking lot analysis using YOLOv8",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve generated images/videos as static files
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

app.include_router(results_router, prefix="/results", tags=["results"])


# ─── Helpers ─────────────────────────────────────────────────────────────────────
def _validate_file(file: UploadFile) -> str:
    """Returns 'image' or 'video', raises on invalid type."""
    ct = file.content_type or ""
    if ct in ALLOWED_IMAGE_TYPES:
        return "image"
    if ct in ALLOWED_VIDEO_TYPES:
        return "video"
    raise HTTPException(
        status_code=415,
        detail=f"Unsupported file type: {ct}. Allowed: JPEG, PNG, WEBP, MP4, AVI, MOV",
    )


def _ext_for(content_type: str) -> str:
    mapping = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/bmp": ".bmp",
        "video/mp4": ".mp4",
        "video/avi": ".avi",
        "video/quicktime": ".mov",
        "video/x-msvideo": ".avi",
    }
    return mapping.get(content_type, ".bin")


# ─── Background Processing ────────────────────────────────────────────────────────
async def _process_job(job_id: str, file_path: Path, media_type: str):
    """Async background task: runs detection, estimation, heatmap generation."""
    try:
        job_store[job_id]["status"] = "processing"
        job_store[job_id]["progress"] = 10

        if media_type == "image":
            # Update progress in logical stages to avoid looking stuck at 10%
            result = await asyncio.to_thread(
                app.state.image_proc.process,
                file_path,
                job_id,
            )
            job_store[job_id]["progress"] = 90
        else:
            result = await asyncio.to_thread(
                app.state.video_proc.process,
                file_path,
                job_id,
                progress_callback=lambda p: job_store[job_id].update({"progress": p}),
            )

        job_store[job_id].update(
            {
                "status": "completed",
                "progress": 100,
                "result": result,
                "completed_at": time.time(),
            }
        )

    except Exception as exc:
        job_store[job_id].update(
            {
                "status": "failed",
                "error": str(exc),
                "completed_at": time.time(),
            }
        )
        raise


# ─── Endpoints ────────────────────────────────────────────────────────────────────
@app.post("/upload", summary="Upload parking lot image or video")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """
    Upload an image or video of a parking lot.
    Returns a job_id to poll for results via /analyze/{job_id}.
    """
    media_type = _validate_file(file)
    ext = _ext_for(file.content_type)
    job_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{job_id}{ext}"

    # Stream file to disk in chunks to handle large videos
    total_size = 0
    with open(file_path, "wb") as f:
        while chunk := await file.read(8192):
            total_size += len(chunk)
            if total_size > MAX_FILE_SIZE:
                file_path.unlink(missing_ok=True)
                raise HTTPException(413, "File too large (max 100 MB)")
            f.write(chunk)

    # Initialize job record
    job_store[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "progress": 0,
        "media_type": media_type,
        "filename": file.filename,
        "file_path": str(file_path),
        "created_at": time.time(),
        "result": None,
        "error": None,
    }

    # Kick off processing in background
    background_tasks.add_task(_process_job, job_id, file_path, media_type)

    return {"job_id": job_id, "status": "queued", "media_type": media_type}


@app.get("/analyze/{job_id}", summary="Poll job status and results")
async def analyze(job_id: str):
    """
    Poll the status of a processing job.
    Returns progress percentage and full results when completed.
    """
    if job_id not in job_store:
        raise HTTPException(404, f"Job {job_id} not found")

    job = job_store[job_id]

    # Build response payload
    response = {
        "job_id": job_id,
        "status": job["status"],
        "progress": job.get("progress", 0),
        "media_type": job.get("media_type"),
        "filename": job.get("filename"),
    }

    if job["status"] == "completed":
        response["result"] = job["result"]
    elif job["status"] == "failed":
        response["error"] = job.get("error", "Unknown error")

    return response


@app.get("/health", summary="Health check")
async def health():
    return {"status": "ok", "model_loaded": hasattr(app.state, "detector")}
