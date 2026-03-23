"""
FastAPI worker service for the Compile ML pipeline.
Runs evolution jobs and streams progress via SSE.
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from worker.jobs import job_manager, JobStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _check_data_available() -> bool:
    """Check if FlyWire data files exist."""
    data_dir = os.environ.get("COMPILE_DATA_DIR", "data")
    required = [
        "2025_Connectivity_783.parquet",
        "2025_Completeness_783.csv",
        "flywire_annotations.tsv",
    ]
    if not os.path.isdir(data_dir):
        return False
    for f in required:
        if not os.path.exists(os.path.join(data_dir, f)):
            return False
    return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    has_data = _check_data_available()
    if has_data:
        logger.info("FlyWire data found. Worker ready for jobs.")
    else:
        logger.warning(
            "FlyWire data NOT found at %s. "
            "Jobs will fail. Set COMPILE_DATA_DIR to the directory containing FlyWire files.",
            os.environ.get("COMPILE_DATA_DIR", "data"),
        )
    yield


app = FastAPI(
    title="Compile ML Worker",
    description="Evolution pipeline worker for compile.now",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Models ---

class EvolutionRequest(BaseModel):
    fitness_function: str
    seed: int = 0
    generations: int = 50
    mutations_per_gen: int = 5
    architecture: str = "hub_and_spoke"
    use_biological_reference: bool = False


class JobResponse(BaseModel):
    id: str
    status: str
    fitness_function: str
    seed: int


# --- Endpoints ---

class RegressionRequest(BaseModel):
    fitness_function: str  # the newly compiled behavior
    job_id: str  # reference to the completed evolution job
    test_against: list[str] = []  # behaviors to regression-test; empty = auto-select


@app.post("/jobs/regression-test", status_code=202)
async def create_regression_test(req: RegressionRequest):
    """Run regression testing: re-evaluate existing behaviors on the mutated brain."""
    if not _check_data_available():
        raise HTTPException(status_code=503, detail="FlyWire data not available.")

    # Auto-select if not specified: test against navigation (fastest, most common)
    targets = req.test_against
    if not targets:
        try:
            from compile.fitness import FITNESS_FUNCTIONS
            available = sorted(FITNESS_FUNCTIONS.keys())
            # Default: test the 2 most important behaviors (navigation + escape)
            defaults = ["navigation", "escape"]
            targets = [b for b in defaults if b in available and b != req.fitness_function]
        except ImportError:
            targets = []

    if not targets:
        return {"job_id": req.job_id, "regressions": [], "message": "No targets to test"}

    # Run regression synchronously (each test is ~30s, not worth async for 2 behaviors)
    from worker.regression import run_regression_tests
    results = run_regression_tests(req.fitness_function, targets)

    return {
        "job_id": req.job_id,
        "compiled_behavior": req.fitness_function,
        "regressions": results,
    }


@app.get("/health")
async def health():
    has_data = _check_data_available()
    available = []
    if has_data:
        try:
            from compile.fitness import FITNESS_FUNCTIONS
            available = sorted(FITNESS_FUNCTIONS.keys())
        except ImportError:
            available = []
    return {
        "status": "ok",
        "has_data": has_data,
        "data_dir": os.environ.get("COMPILE_DATA_DIR", "data"),
        "available_behaviors": available,
    }


@app.post("/jobs/evolution", status_code=202)
async def create_evolution_job(req: EvolutionRequest):
    if not _check_data_available():
        raise HTTPException(
            status_code=503,
            detail="FlyWire data not available. Download from flywire.ai and set COMPILE_DATA_DIR.",
        )

    # Validate against the compile package's actual fitness functions
    try:
        from compile.fitness import FITNESS_FUNCTIONS
        valid_behaviors = set(FITNESS_FUNCTIONS.keys())
    except ImportError:
        valid_behaviors = {"navigation", "escape", "turning", "arousal", "circles", "rhythm"}

    if req.fitness_function not in valid_behaviors:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown fitness function: {req.fitness_function}. Available: {sorted(valid_behaviors)}",
        )

    job = job_manager.create_job(
        fitness_function=req.fitness_function,
        seed=req.seed,
        generations=req.generations,
        mutations_per_gen=req.mutations_per_gen,
        architecture=req.architecture,
        use_biological_reference=req.use_biological_reference,
    )

    # Start the job in the background
    asyncio.create_task(job_manager.run_job(job))

    return JobResponse(
        id=job.id,
        status=job.status.value,
        fitness_function=job.fitness_function,
        seed=job.seed,
    )


@app.get("/jobs/{job_id}")
async def get_job(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "id": job.id,
        "status": job.status.value,
        "fitness_function": job.fitness_function,
        "seed": job.seed,
        "progress": job.progress,
        "current_fitness": job.current_fitness,
        "accepted_count": job.accepted_count,
        "result": job.result,
        "error": job.error,
    }


@app.get("/jobs/{job_id}/stream")
async def stream_job(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        yield {"event": "connected", "data": f'{{"job_id": "{job_id}"}}'}

        while True:
            try:
                msg = await asyncio.wait_for(job.queue.get(), timeout=30.0)
            except asyncio.TimeoutError:
                # Send keepalive
                yield {"event": "ping", "data": "{}"}
                continue

            event_type = msg.get("type", "unknown")

            if event_type == "progress":
                import json
                yield {
                    "event": "progress",
                    "data": json.dumps({
                        "generation": msg["generation"],
                        "total": msg["total"],
                        "progress": msg["progress"],
                        "current_fitness": msg.get("current_fitness", 0),
                        "accepted_count": msg.get("accepted_count", 0),
                    }),
                }
            elif event_type == "done":
                import json
                yield {
                    "event": "done",
                    "data": json.dumps({
                        "job_id": job_id,
                        "status": "completed",
                        "result": msg.get("result"),
                    }),
                }
                break
            elif event_type == "error":
                import json
                yield {
                    "event": "error",
                    "data": json.dumps({
                        "job_id": job_id,
                        "message": msg.get("message", "Unknown error"),
                    }),
                }
                break
            elif event_type == "started":
                import json
                yield {
                    "event": "started",
                    "data": json.dumps({"job_id": job_id}),
                }

    return EventSourceResponse(event_generator())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
