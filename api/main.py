"""
Unsaid FastAPI backend.
Endpoints:
  GET  /diff/{ticker}         — return cached diff JSON
  GET  /demos                 — list all pre-cached demos
  POST /run                   — launch live ingest (bonus)
  GET  /run/{job_id}          — poll live ingest status
"""
import os
import uuid
import logging
import threading
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys_path_root = os.path.dirname(os.path.dirname(__file__))
import sys
sys.path.insert(0, sys_path_root)

from unsaid.cache import read_cache, list_cached_demos

logger = logging.getLogger(__name__)

app = FastAPI(title="Unsaid API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job store for live /run requests
_jobs: Dict[str, Dict[str, Any]] = {}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/demos")
def get_demos():
    """List all pre-cached demo companies."""
    return list_cached_demos()


@app.get("/diff/{ticker}")
def get_diff(ticker: str):
    """Return cached diff JSON for a ticker. 404 if not cached."""
    data = read_cache(ticker.upper())
    if data is None:
        raise HTTPException(
            status_code=404,
            detail=f"No cached analysis for ticker '{ticker.upper()}'. "
                   f"Run the ingest pipeline first."
        )
    return data


class RunRequest(BaseModel):
    ticker: str
    year1: int
    year2: int
    cik: str | None = None


@app.post("/run")
def start_run(req: RunRequest):
    """
    Launch the ingest pipeline in a background thread.
    Returns a job_id to poll at GET /run/{job_id}.
    """
    job_id = str(uuid.uuid4())[:8]
    _jobs[job_id] = {"status": "queued", "ticker": req.ticker, "message": "Pipeline queued"}

    def _run():
        _jobs[job_id]["status"] = "running"
        _jobs[job_id]["message"] = "Fetching EDGAR filings…"
        try:
            from unsaid.ingest import run_pipeline
            cache_path = run_pipeline(
                ticker=req.ticker or None,
                cik=req.cik or None,
                year1=req.year1,
                year2=req.year2,
            )
            _jobs[job_id]["status"] = "done"
            _jobs[job_id]["message"] = f"Complete — cache written to {cache_path}"
            _jobs[job_id]["ticker"] = req.ticker.upper()
        except Exception as e:
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["message"] = str(e)
            logger.exception("Live run failed for ticker %s", req.ticker)

    t = threading.Thread(target=_run, daemon=True)
    t.start()

    return {"job_id": job_id, "status": "queued"}


@app.get("/run/{job_id}")
def get_run_status(job_id: str):
    """Poll the status of a live ingest job."""
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job
