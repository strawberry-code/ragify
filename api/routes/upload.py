"""Upload and indexing API routes."""

import os
import uuid
import shutil
import asyncio
from pathlib import Path
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel

router = APIRouter()

# Upload configuration
UPLOAD_DIR = Path(os.getenv('UPLOAD_DIR', '/tmp/ragify_uploads'))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Job tracking (in-memory for simplicity, could use Redis in production)
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


def run_indexing(job_id: str, file_path: Path, collection: str):
    """
    Run indexing in background.

    This function is called as a background task and runs the ragify
    indexing pipeline on the uploaded file.
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    try:
        jobs[job_id]["status"] = "running"
        jobs[job_id]["message"] = "Indexing started"

        # Import ragify components
        from lib.config import RagifyConfig
        from lib.embedding import get_embedding
        from lib.qdrant_operations import upload_points, check_qdrant_connection
        from lib.chunking import create_chunks
        from lib.file_utils import compute_file_hash
        from lib.text_cleaning import clean_text

        # Check services
        if not check_qdrant_connection():
            raise Exception("Cannot connect to Qdrant")

        # Load config
        config = RagifyConfig.load()
        config.qdrant.collection = collection

        # Process file
        jobs[job_id]["progress"] = 0.1
        jobs[job_id]["message"] = "Reading file"

        # Read file content
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        file_hash = compute_file_hash(str(file_path))

        jobs[job_id]["progress"] = 0.2
        jobs[job_id]["message"] = "Cleaning text"

        # Clean text
        cleaned = clean_text(content)

        jobs[job_id]["progress"] = 0.3
        jobs[job_id]["message"] = "Creating chunks"

        # Create chunks
        chunks = create_chunks(cleaned, chunk_size=config.chunking.chunk_size)

        if not chunks:
            raise Exception("No chunks created from file")

        jobs[job_id]["progress"] = 0.5
        jobs[job_id]["message"] = f"Generating embeddings for {len(chunks)} chunks"

        # Generate embeddings
        embedded_chunks = []
        for i, chunk in enumerate(chunks):
            embedding = get_embedding(chunk["text"])
            if embedding:
                embedded_chunks.append({
                    **chunk,
                    "embedding": embedding
                })
            jobs[job_id]["progress"] = 0.5 + (0.4 * (i + 1) / len(chunks))

        jobs[job_id]["progress"] = 0.9
        jobs[job_id]["message"] = "Uploading to Qdrant"

        # Create points and upload
        from lib.qdrant_operations import batch_upload_chunks

        title = file_path.stem
        url = str(file_path.name)

        uploaded = batch_upload_chunks(
            embedded_chunks,
            url=url,
            title=title,
            collection_name=collection,
            batch_size=10
        )

        jobs[job_id]["progress"] = 1.0
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["message"] = f"Indexed {uploaded} chunks from {file_path.name}"
        jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()

    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["message"] = str(e)
        jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()

    finally:
        # Cleanup uploaded file
        try:
            if file_path.exists():
                file_path.unlink()
            if file_path.parent.exists() and file_path.parent != UPLOAD_DIR:
                shutil.rmtree(file_path.parent, ignore_errors=True)
        except Exception:
            pass


@router.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    collection: str = Form(default="documentation")
):
    """
    Upload a file for indexing.

    Args:
        file: File to upload
        collection: Target collection name

    Returns:
        dict: Job information
    """
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Create job directory
    job_id = str(uuid.uuid4())
    job_dir = UPLOAD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # Save file
    file_path = job_dir / file.filename
    try:
        content = await file.read()
        file_path.write_bytes(content)
    except Exception as e:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    # Create job record
    jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "collection": collection,
        "filename": file.filename,
        "progress": 0.0,
        "message": "Job created, waiting to start",
        "created_at": datetime.utcnow().isoformat(),
        "completed_at": None
    }

    # Start background indexing
    background_tasks.add_task(run_indexing, job_id, file_path, collection)

    return JobCreate(
        job_id=job_id,
        status="pending",
        message=f"File '{file.filename}' uploaded, indexing job created"
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

    # Don't allow deleting running jobs
    if jobs[job_id]["status"] == "running":
        raise HTTPException(status_code=400, detail="Cannot delete running job")

    del jobs[job_id]
    return {"message": f"Job '{job_id}' deleted"}
