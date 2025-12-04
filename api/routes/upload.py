"""Upload and indexing API routes.

Uses RagifyPipeline for consistent indexing with CLI.
Files stored in /tmp/collections/{collection}/ with 15-day retention.
"""

import os
import sys
import time
import uuid
import logging
import traceback
import zipfile
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

router = APIRouter()

# Collections storage directory
COLLECTIONS_DIR = Path(os.getenv('COLLECTIONS_DIR', '/tmp/collections'))
COLLECTIONS_DIR.mkdir(parents=True, exist_ok=True)

# File retention: 15 days in seconds
RETENTION_SECONDS = 15 * 24 * 3600

# Job tracking (in-memory)
jobs = {}


class JobStatus(BaseModel):
    """Job status response."""
    job_id: str
    status: str  # pending, running, completed, failed
    collection: str
    filename: str
    progress: float  # 0.0 to 1.0
    message: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None


class JobCreate(BaseModel):
    """Job creation response."""
    job_id: str
    status: str
    message: str


def cleanup_old_files():
    """
    Best-effort cleanup of files older than 15 days.
    Called during UI activity (list, upload).
    """
    if not COLLECTIONS_DIR.exists():
        return

    cutoff = time.time() - RETENTION_SECONDS
    cleaned_files = 0
    cleaned_dirs = 0

    try:
        for collection_dir in COLLECTIONS_DIR.iterdir():
            if not collection_dir.is_dir():
                continue

            # Clean old files in collection
            for f in list(collection_dir.iterdir()):
                try:
                    if f.is_file() and f.stat().st_mtime < cutoff:
                        f.unlink()
                        cleaned_files += 1
                except Exception:
                    pass

            # Remove empty directories
            try:
                if collection_dir.is_dir() and not any(collection_dir.iterdir()):
                    collection_dir.rmdir()
                    cleaned_dirs += 1
            except Exception:
                pass

        if cleaned_files or cleaned_dirs:
            logger.info(f"Cleanup: removed {cleaned_files} files, {cleaned_dirs} empty dirs")

    except Exception as e:
        logger.debug(f"Cleanup error (non-critical): {e}")


def run_indexing(job_id: str, collection_dir: Path, collection: str, filenames: List[str]):
    """
    Run indexing using RagifyPipeline.

    Args:
        job_id: Job identifier for tracking
        collection_dir: Directory containing uploaded files
        collection: Target collection name
        filenames: List of uploaded filenames for reporting
    """
    logger.info(f"[{job_id}] Starting indexing for {len(filenames)} file(s) -> collection '{collection}'")

    try:
        jobs[job_id]["status"] = "running"
        jobs[job_id]["message"] = "Initializing pipeline"
        jobs[job_id]["progress"] = 0.1

        # Import RagifyPipeline
        from ragify import RagifyPipeline
        from lib.config import RagifyConfig
        from lib.tika_check import is_tika_available, check_tika_available

        # Configure
        config = RagifyConfig.default()
        config.qdrant.collection = collection

        # Check Tika availability with diagnostic info
        tika_status = check_tika_available()
        use_tika = tika_status['can_use_tika']
        logger.info(f"[{job_id}] Tika status: java={tika_status['java_installed']}, "
                    f"jar={tika_status['tika_jar_available']}, path={tika_status.get('tika_jar_path')}")
        if tika_status['issues']:
            logger.warning(f"[{job_id}] Tika issues: {tika_status['issues']}")

        jobs[job_id]["progress"] = 0.2
        jobs[job_id]["message"] = f"Processing with {'Tika' if use_tika else 'text-only'} mode"
        jobs[job_id]["stage"] = "initializing"

        # Progress callback to update job stage
        def update_progress(stage: str, progress: float):
            jobs[job_id]["stage"] = stage
            jobs[job_id]["progress"] = progress

        # Create and run pipeline
        pipeline = RagifyPipeline(config, use_tika=use_tika)
        stats = pipeline.process_directory(collection_dir, progress_callback=update_progress)

        # Update job with results
        jobs[job_id]["progress"] = 1.0
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["stage"] = "completed"
        jobs[job_id]["message"] = (
            f"Indexed {stats['processed']}/{stats['processed'] + stats['failed']} files, "
            f"{stats['chunks']} chunks, {stats['skipped']} skipped"
        )
        jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()

        logger.info(
            f"[{job_id}] Indexing COMPLETED: "
            f"{stats['processed']} processed, {stats['chunks']} chunks, "
            f"{stats['failed']} failed, {stats['skipped']} skipped"
        )

    except Exception as e:
        error_msg = str(e)
        stack_trace = traceback.format_exc()
        logger.error(f"[{job_id}] Indexing FAILED: {error_msg}")
        logger.error(f"[{job_id}] Stack trace:\n{stack_trace}")

        jobs[job_id]["status"] = "failed"
        jobs[job_id]["stage"] = "failed"
        jobs[job_id]["message"] = error_msg
        jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()

    finally:
        # Cleanup: delete uploaded files after processing (success or failure)
        cleanup_count = 0
        for filename in filenames:
            file_path = collection_dir / filename
            try:
                if file_path.exists():
                    file_path.unlink()
                    cleanup_count += 1
            except Exception as cleanup_err:
                logger.warning(f"[{job_id}] Failed to cleanup {file_path}: {cleanup_err}")

        logger.info(f"[{job_id}] Cleanup: removed {cleanup_count}/{len(filenames)} uploaded files")


@router.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    collection: str = Form(default="documentation")
):
    """
    Upload a file for indexing.

    Files are saved to /tmp/collections/{collection}/ and processed
    by RagifyPipeline (same as CLI).

    Args:
        file: File to upload
        collection: Target collection name

    Returns:
        dict: Job information
    """
    # Trigger cleanup (best-effort, non-blocking)
    cleanup_old_files()

    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Create collection directory
    collection_dir = COLLECTIONS_DIR / collection
    collection_dir.mkdir(parents=True, exist_ok=True)

    # Save file
    file_path = collection_dir / file.filename
    try:
        content = await file.read()
        file_path.write_bytes(content)
        logger.info(f"Saved file: {file_path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    # Create job record
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "stage": "pending",
        "collection": collection,
        "filename": file.filename,
        "progress": 0.0,
        "message": "Job created, waiting to start",
        "created_at": datetime.utcnow().isoformat(),
        "completed_at": None
    }

    # Start background indexing
    background_tasks.add_task(
        run_indexing,
        job_id,
        collection_dir,
        collection,
        [file.filename]
    )

    return JobCreate(
        job_id=job_id,
        status="pending",
        message=f"File '{file.filename}' uploaded to collection '{collection}', indexing started"
    )


@router.post("/upload-multiple")
async def upload_multiple_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    collection: str = Form(default="documentation")
):
    """
    Upload multiple files for indexing.

    Args:
        files: List of files to upload
        collection: Target collection name

    Returns:
        dict: Job information
    """
    # Trigger cleanup
    cleanup_old_files()

    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    # Create collection directory
    collection_dir = COLLECTIONS_DIR / collection
    collection_dir.mkdir(parents=True, exist_ok=True)

    # Save all files
    saved_files = []
    for file in files:
        if not file.filename:
            continue

        file_path = collection_dir / file.filename
        try:
            content = await file.read()
            file_path.write_bytes(content)
            saved_files.append(file.filename)
            logger.info(f"Saved file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to save {file.filename}: {e}")

    if not saved_files:
        raise HTTPException(status_code=400, detail="No files could be saved")

    # Create job record
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "stage": "pending",
        "collection": collection,
        "filename": f"{len(saved_files)} files",
        "progress": 0.0,
        "message": f"Uploaded {len(saved_files)} files, waiting to start",
        "created_at": datetime.utcnow().isoformat(),
        "completed_at": None
    }

    # Start background indexing
    background_tasks.add_task(
        run_indexing,
        job_id,
        collection_dir,
        collection,
        saved_files
    )

    return JobCreate(
        job_id=job_id,
        status="pending",
        message=f"Uploaded {len(saved_files)} files to collection '{collection}', indexing started"
    )


def run_zip_indexing(job_id: str, zip_path: Path, collection_dir: Path, collection: str):
    """
    Extract ZIP and run indexing pipeline.

    Args:
        job_id: Job identifier for tracking
        zip_path: Path to uploaded ZIP file
        collection_dir: Target directory for extracted files
        collection: Target collection name
    """
    logger.info(f"[{job_id}] Starting ZIP extraction from {zip_path}")

    extracted_files = []  # Track files for cleanup in finally block

    try:
        jobs[job_id]["status"] = "running"
        jobs[job_id]["stage"] = "extracting_zip"
        jobs[job_id]["message"] = "Extracting ZIP archive"
        jobs[job_id]["progress"] = 0.05

        # Extract ZIP, filtering out macOS metadata and hidden files
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for name in zf.namelist():
                # Skip macOS metadata, hidden files, and directories
                if name.startswith('__MACOSX') or name.startswith('.') or name.endswith('/'):
                    continue
                # Skip nested hidden files (e.g., folder/.hidden)
                if '/.' in name:
                    continue

                zf.extract(name, collection_dir)
                extracted_files.append(name)

        # Remove ZIP after extraction
        zip_path.unlink()

        logger.info(f"[{job_id}] Extracted {len(extracted_files)} files from ZIP: {extracted_files}")
        jobs[job_id]["message"] = f"Extracted {len(extracted_files)} files"
        jobs[job_id]["progress"] = 0.15
        jobs[job_id]["filename"] = f"{len(extracted_files)} files"

        if not extracted_files:
            jobs[job_id]["status"] = "completed"
            jobs[job_id]["stage"] = "completed"
            jobs[job_id]["message"] = "ZIP was empty or contained only hidden files"
            jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
            return

        # Import RagifyPipeline
        from ragify import RagifyPipeline
        from lib.config import RagifyConfig
        from lib.tika_check import check_tika_available

        # Configure
        config = RagifyConfig.default()
        config.qdrant.collection = collection

        # Check Tika availability
        tika_status = check_tika_available()
        use_tika = tika_status['can_use_tika']
        logger.info(f"[{job_id}] Tika available: {use_tika}")

        # Progress callback
        def update_progress(stage: str, progress: float):
            # Scale progress: extraction was 0-0.15, pipeline is 0.15-1.0
            scaled_progress = 0.15 + (progress * 0.85)
            jobs[job_id]["stage"] = stage
            jobs[job_id]["progress"] = scaled_progress

        # Run pipeline
        pipeline = RagifyPipeline(config, use_tika=use_tika)
        stats = pipeline.process_directory(collection_dir, progress_callback=update_progress)

        # Update job with results
        jobs[job_id]["progress"] = 1.0
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["stage"] = "completed"
        jobs[job_id]["message"] = (
            f"Indexed {stats['processed']}/{stats['processed'] + stats['failed']} files, "
            f"{stats['chunks']} chunks"
        )
        jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()

        logger.info(f"[{job_id}] ZIP indexing COMPLETED: {stats['processed']} files, {stats['chunks']} chunks")

    except Exception as e:
        error_msg = str(e)
        logger.error(f"[{job_id}] ZIP indexing FAILED: {error_msg}")
        logger.error(f"[{job_id}] Stack trace:\n{traceback.format_exc()}")

        jobs[job_id]["status"] = "failed"
        jobs[job_id]["stage"] = "failed"
        jobs[job_id]["message"] = error_msg
        jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()

    finally:
        # Cleanup: delete ZIP if still exists
        if zip_path.exists():
            try:
                zip_path.unlink()
                logger.debug(f"[{job_id}] Cleanup: removed ZIP file")
            except Exception as cleanup_err:
                logger.warning(f"[{job_id}] Failed to cleanup ZIP {zip_path}: {cleanup_err}")

        # Cleanup: delete extracted files after processing (success or failure)
        cleanup_count = 0
        for filename in extracted_files:
            file_path = collection_dir / filename
            try:
                if file_path.exists():
                    file_path.unlink()
                    cleanup_count += 1
                    # Also try to remove parent dirs if empty (for nested paths)
                    parent = file_path.parent
                    while parent != collection_dir:
                        try:
                            parent.rmdir()  # Only removes if empty
                            parent = parent.parent
                        except OSError:
                            break
            except Exception as cleanup_err:
                logger.warning(f"[{job_id}] Failed to cleanup {file_path}: {cleanup_err}")

        if extracted_files:
            logger.info(f"[{job_id}] Cleanup: removed {cleanup_count}/{len(extracted_files)} extracted files")


@router.post("/upload-zip")
async def upload_zip(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    collection: str = Form(default="documentation")
):
    """
    Upload a ZIP file for extraction and indexing.

    The ZIP is extracted server-side, then all files are processed
    by RagifyPipeline as a single job.

    Args:
        file: ZIP file to upload
        collection: Target collection name

    Returns:
        dict: Job information
    """
    # Trigger cleanup
    cleanup_old_files()

    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="File must be a ZIP archive")

    # Create collection directory
    collection_dir = COLLECTIONS_DIR / collection
    collection_dir.mkdir(parents=True, exist_ok=True)

    # Save ZIP temporarily with unique name
    zip_path = collection_dir / f"_upload_{uuid.uuid4().hex}.zip"
    try:
        content = await file.read()
        zip_path.write_bytes(content)
        logger.info(f"Saved ZIP: {zip_path} ({len(content)} bytes)")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save ZIP: {e}")

    # Create job record
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "stage": "pending",
        "collection": collection,
        "filename": "ZIP archive",
        "progress": 0.0,
        "message": "ZIP uploaded, extraction starting",
        "created_at": datetime.utcnow().isoformat(),
        "completed_at": None
    }

    # Start background processing
    background_tasks.add_task(
        run_zip_indexing,
        job_id,
        zip_path,
        collection_dir,
        collection
    )

    return JobCreate(
        job_id=job_id,
        status="pending",
        message=f"ZIP uploaded to collection '{collection}', extraction and indexing started"
    )


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """
    Get job status.

    Args:
        job_id: Job identifier

    Returns:
        dict: Job status information
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    return JobStatus(**jobs[job_id])


@router.get("/jobs")
async def list_jobs(limit: int = 50):
    """
    List recent jobs.

    Args:
        limit: Maximum jobs to return

    Returns:
        dict: List of jobs
    """
    # Trigger cleanup on list (best-effort)
    cleanup_old_files()

    sorted_jobs = sorted(
        jobs.values(),
        key=lambda x: x["created_at"],
        reverse=True
    )[:limit]

    return {
        "jobs": sorted_jobs,
        "total": len(jobs)
    }


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """
    Delete a job record (does not cancel running jobs).

    Args:
        job_id: Job identifier

    Returns:
        dict: Deletion confirmation
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    if jobs[job_id]["status"] == "running":
        raise HTTPException(status_code=400, detail="Cannot delete running job")

    del jobs[job_id]
    return {"message": f"Job '{job_id}' deleted"}
