"""
Unsaid FastAPI backend.
Endpoints:
  GET    /health               — system status & API key check
  GET    /filings/{ticker}     — query EDGAR for available 10-K fiscal years
  GET    /library              — list all analyzed / cached companies
  GET    /demos                — backward-compatible demo list
  GET    /diff/{ticker}        — return cached diff JSON (optional ?year1=&year2=)
  DELETE /cache/{ticker}       — delete cached analysis
  POST   /run                  — launch live ingest pipeline with rich progress
  GET    /run/{job_id}         — poll real-time ingest progress and logs
"""
import os
import uuid
import logging
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys_path_root = os.path.dirname(os.path.dirname(__file__))
import sys
sys.path.insert(0, sys_path_root)

from unsaid.cache import read_cache, list_cached_analyses, list_cached_demos, delete_cache
from unsaid.fetcher import list_available_10ks

logger = logging.getLogger(__name__)

app = FastAPI(title="Unsaid API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job store for live /run requests
_jobs: Dict[str, Dict[str, Any]] = {}


@app.get("/health")
def health():
    has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))
    has_azure = bool(os.environ.get("AZURE_AI_API_KEY") or os.environ.get("AZURE_OPENAI_API_KEY"))
    has_openai = bool(os.environ.get("OPENAI_API_KEY"))

    return {
        "status": "ok",
        "has_api_key": has_anthropic or has_azure or has_openai,
        "providers": {
            "anthropic": {"available": has_anthropic, "default_judge": "claude-opus-4-8", "default_segmenter": "claude-sonnet-4-6"},
            "azure_foundry": {"available": has_azure, "default_judge": "gpt-5.6-luna", "default_segmenter": "gpt-5.6-luna"},
            "openai": {"available": has_openai, "default_judge": "gpt-4o", "default_segmenter": "gpt-4o-mini"},
        },
        "version": "1.2.0",
        "embed_model": "all-mpnet-base-v2",
    }


class TestConnectionRequest(BaseModel):

    provider: str
    model: Optional[str] = None
    api_key: Optional[str] = None
    azure_endpoint: Optional[str] = None
    azure_api_version: Optional[str] = None


@app.post("/health/test-connection")
def test_connection(req: TestConnectionRequest):
    """Test connection and tool-calling capability for a given provider/model configuration."""
    import time
    from unsaid.llm import call_structured_tool, get_default_model

    provider = req.provider.lower()
    target_model = req.model or get_default_model(provider, "judge")
    start_time = time.time()

    try:
        data = call_structured_tool(
            provider=provider,
            model=target_model,
            system_prompt="You are a diagnostics tool evaluator. Return status='ok' and echo='ping_success'.",
            user_prompt="Run diagnostics ping test.",
            tool_name="ping_response",
            tool_description="Respond to health check.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "echo": {"type": "string"},
                },
                "required": ["status", "echo"],
            },
            api_key=req.api_key or None,
            azure_endpoint=req.azure_endpoint or None,
            azure_api_version=req.azure_api_version or None,
            max_tokens=128,
            retries=0,
        )
        latency = int((time.time() - start_time) * 1000)
        return {
            "success": True,
            "provider": provider,
            "model": target_model,
            "latency_ms": latency,
            "message": f"Connected to {provider} ({target_model}) in {latency}ms.",
            "data": data,
        }
    except Exception as e:
        latency = int((time.time() - start_time) * 1000)
        logger.warning("Diagnostics ping failed for %s/%s: %s", provider, target_model, e)
        return {
            "success": False,
            "provider": provider,
            "model": target_model,
            "latency_ms": latency,
            "error": str(e),
        }



@app.get("/filings/{ticker}")
def get_filings(ticker: str, cik: Optional[str] = None):
    """Query SEC EDGAR for available 10-K filings for any ticker or CIK."""
    try:
        company_name, resolved_cik, filings = list_available_10ks(ticker=ticker, cik=cik)
        return {
            "ticker": ticker.upper(),
            "company_name": company_name,
            "cik": resolved_cik,
            "filings": filings,
            "total_available": len(filings),
        }
    except Exception as e:
        logger.exception("Failed to fetch filings for %s", ticker)
        raise HTTPException(
            status_code=400,
            detail=f"Could not retrieve 10-Ks for '{ticker.upper()}': {str(e)}"
        )


@app.get("/library")
def get_library():
    """List all cached analyses with enriched summary metadata."""
    return list_cached_analyses()


@app.get("/demos")
def get_demos():
    """Backward-compatible endpoint for demo listings."""
    return list_cached_demos()


@app.get("/diff/{ticker}")
def get_diff(
    ticker: str,
    year1: Optional[int] = Query(None, description="First fiscal year"),
    year2: Optional[int] = Query(None, description="Second fiscal year"),
):
    """Return cached diff JSON for a ticker. 404 if not cached."""
    data = read_cache(ticker.upper(), year1=year1, year2=year2)
    if data is None:
        years_msg = f" (FY{year1}→FY{year2})" if year1 and year2 else ""
        raise HTTPException(
            status_code=404,
            detail=f"No cached analysis found for ticker '{ticker.upper()}'{years_msg}. "
                   f"Launch an analysis run to generate it."
        )
    return data


@app.delete("/cache/{ticker}")
def delete_cached_analysis(
    ticker: str,
    year1: Optional[int] = None,
    year2: Optional[int] = None,
):
    """Delete a cached analysis from disk."""
    success = delete_cache(ticker.upper(), year1=year1, year2=year2)
    if not success:
        raise HTTPException(status_code=404, detail="No matching cache file found to delete.")
    return {"deleted": True, "ticker": ticker.upper(), "year1": year1, "year2": year2}


class RunRequest(BaseModel):
    ticker: str
    year1: int
    year2: int
    cik: Optional[str] = None
    provider: Optional[str] = "anthropic"
    model_judge: Optional[str] = None
    model_segmenter: Optional[str] = None
    api_key: Optional[str] = None
    azure_endpoint: Optional[str] = None
    azure_api_version: Optional[str] = None
    force: bool = False


@app.post("/run")
def start_run(req: RunRequest):
    """
    Launch the ingest pipeline in a background thread with real-time progress callbacks.
    Returns a job_id to poll at GET /run/{job_id}.
    """
    job_id = str(uuid.uuid4())[:8]
    now_iso = datetime.now(timezone.utc).isoformat()
    provider = req.provider or "anthropic"

    _jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "step": "queued",
        "pct": 0,
        "ticker": req.ticker.upper(),
        "year1": req.year1,
        "year2": req.year2,
        "provider": provider,
        "model_judge": req.model_judge,
        "model_segmenter": req.model_segmenter,
        "message": f"Queued analysis for {req.ticker.upper()} (FY{req.year1} → FY{req.year2}) via {provider}",
        "details": None,
        "logs": [
            {"time": now_iso, "step": "queued", "pct": 0, "msg": f"Job queued for {req.ticker.upper()} ({provider})"}
        ],
        "started_at": now_iso,
        "finished_at": None,
        "result_url": f"/diff/{req.ticker.upper()}?year1={req.year1}&year2={req.year2}",
    }

    def _progress_callback(step: str, pct: int, msg: str, details: Optional[str] = None):
        t_iso = datetime.now(timezone.utc).isoformat()
        job = _jobs.get(job_id)
        if job:
            job["step"] = step
            job["pct"] = pct
            job["message"] = msg
            job["details"] = details
            job["logs"].append({"time": t_iso, "step": step, "pct": pct, "msg": msg})

    def _run():
        job = _jobs[job_id]
        job["status"] = "running"
        job["step"] = "initializing"
        job["pct"] = 5
        job["message"] = f"Initializing pipeline for {req.ticker.upper()}…"

        try:
            from unsaid.ingest import run_pipeline
            cache_path = run_pipeline(
                ticker=req.ticker or None,
                cik=req.cik or None,
                year1=req.year1,
                year2=req.year2,
                force=req.force,
                provider=provider,
                model_judge=req.model_judge,
                model_segmenter=req.model_segmenter,
                api_key=req.api_key or None,
                azure_endpoint=req.azure_endpoint or None,
                azure_api_version=req.azure_api_version or None,
                progress_callback=_progress_callback,
            )
            job["status"] = "done"
            job["step"] = "completed"
            job["pct"] = 100
            job["message"] = f"Complete — analysis saved to cache"
            job["finished_at"] = datetime.now(timezone.utc).isoformat()
            job["result_path"] = cache_path
        except Exception as e:
            job["status"] = "error"
            job["step"] = "error"
            job["message"] = str(e)
            job["finished_at"] = datetime.now(timezone.utc).isoformat()
            _progress_callback("error", job.get("pct", 0), f"Error: {str(e)}")
            logger.exception("Live run failed for ticker %s", req.ticker)

    t = threading.Thread(target=_run, daemon=True)
    t.start()

    return {"job_id": job_id, "status": "queued", "ticker": req.ticker.upper(), "provider": provider}


@app.get("/run/{job_id}")
def get_run_status(job_id: str):
    """Poll the real-time progress of a live ingest job."""
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job


