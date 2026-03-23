"""Job manager for evolution jobs with progress streaming."""

import asyncio
import uuid
import logging
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    QUEUED = "queued"


@dataclass
class Job:
    id: str
    fitness_function: str
    seed: int
    generations: int
    mutations_per_gen: int
    architecture: str = "hub_and_spoke"
    use_biological_reference: bool = False
    status: JobStatus = JobStatus.PENDING
    progress: int = 0
    current_fitness: float = 0.0
    accepted_count: int = 0
    result: dict | None = None
    error: str | None = None
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)


class JobManager:
    """Manages evolution jobs with a single-worker process pool."""

    def __init__(self, max_workers: int = 1):
        self.jobs: dict[str, Job] = {}
        self.max_workers = max_workers
        self._executor: ProcessPoolExecutor | None = None
        self._running_count = 0

    def create_job(
        self,
        fitness_function: str,
        seed: int,
        generations: int = 50,
        mutations_per_gen: int = 5,
        architecture: str = "hub_and_spoke",
        use_biological_reference: bool = False,
    ) -> Job:
        job_id = str(uuid.uuid4())
        job = Job(
            id=job_id,
            fitness_function=fitness_function,
            seed=seed,
            generations=generations,
            mutations_per_gen=mutations_per_gen,
            architecture=architecture,
            use_biological_reference=use_biological_reference,
        )
        self.jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> Job | None:
        return self.jobs.get(job_id)

    async def run_job(self, job: Job) -> None:
        """Run evolution job and push progress events to the job's queue."""
        job.status = JobStatus.RUNNING
        self._running_count += 1

        try:
            await job.queue.put({
                "type": "started",
                "job_id": job.id,
            })

            # Import here to avoid loading torch at module level
            from worker.runner import run_evolution_with_progress

            # Run in process pool to avoid GIL blocking the event loop
            loop = asyncio.get_event_loop()

            if self._executor is None:
                self._executor = ProcessPoolExecutor(max_workers=self.max_workers)

            # We use a thread-safe callback bridge: the subprocess writes to a
            # multiprocessing Queue, and we poll it from the async event loop.
            import multiprocessing
            progress_queue: multiprocessing.Queue = multiprocessing.Queue()

            future = loop.run_in_executor(
                self._executor,
                run_evolution_with_progress,
                job.fitness_function,
                job.seed,
                job.generations,
                job.mutations_per_gen,
                progress_queue,
                job.architecture,
                job.use_biological_reference,
            )

            # Poll the progress queue while the job is running
            done = False
            while not done:
                # Check if the future completed (with or without sending "done")
                if future.done():
                    # Drain any remaining messages
                    while not progress_queue.empty():
                        try:
                            msg = progress_queue.get_nowait()
                            if msg["type"] == "progress":
                                job.progress = msg["progress"]
                                job.current_fitness = msg.get("current_fitness", 0.0)
                                job.accepted_count = msg.get("accepted_count", 0)
                                await job.queue.put(msg)
                        except Exception:
                            break
                    done = True
                    break

                try:
                    msg = await asyncio.wait_for(
                        loop.run_in_executor(None, lambda: progress_queue.get(timeout=0.5)),
                        timeout=1.5,
                    )
                    if msg["type"] == "progress":
                        job.progress = msg["progress"]
                        job.current_fitness = msg.get("current_fitness", 0.0)
                        job.accepted_count = msg.get("accepted_count", 0)
                        await job.queue.put(msg)
                    elif msg["type"] == "done":
                        done = True
                    elif msg["type"] == "error":
                        raise Exception(msg.get("message", "Worker error"))
                except asyncio.TimeoutError:
                    continue
                except Exception as poll_err:
                    if future.done():
                        break
                    # Only re-raise if it's a real error, not a queue timeout
                    if "Worker error" in str(poll_err):
                        raise
                    continue

            # Get the final result
            result = future.result()
            job.result = result
            job.status = JobStatus.COMPLETED
            job.progress = 100

            await job.queue.put({
                "type": "done",
                "job_id": job.id,
                "result": result,
            })

        except Exception as e:
            logger.exception("Job %s failed", job.id)
            job.status = JobStatus.FAILED
            job.error = str(e)
            await job.queue.put({
                "type": "error",
                "job_id": job.id,
                "message": str(e),
            })
        finally:
            self._running_count -= 1


# Global singleton
job_manager = JobManager(max_workers=1)
