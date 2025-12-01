from dataclasses import dataclass, field
from enum import Enum

from .config import ImageVariant


class JobStatus(Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    FINISHED = "finished"
    ERROR = "error"


@dataclass
class Job:
    variant: ImageVariant
    text: str
    status: JobStatus = JobStatus.PENDING
    image_id: int | None = None
    image_url: str | None = None
    error: str | None = None


class JobTracker:
    def __init__(self):
        self.jobs: dict[int, Job] = {}  # image_id -> Job
        self.pending: list[Job] = []
        self.all_jobs: list[Job] = []  # All jobs in order

    def add_job(self, text: str, variant: ImageVariant) -> Job:
        """Add a new pending job."""
        job = Job(variant=variant, text=text)
        self.pending.append(job)
        self.all_jobs.append(job)
        return job

    def mark_submitted(self, job: Job, image_id: int):
        """Mark job as submitted, store image_id."""
        job.status = JobStatus.SUBMITTED
        job.image_id = image_id
        self.jobs[image_id] = job
        if job in self.pending:
            self.pending.remove(job)

    def mark_finished(self, image_id: int, image_url: str):
        """Mark job as finished with URL."""
        if image_id in self.jobs:
            job = self.jobs[image_id]
            job.status = JobStatus.FINISHED
            job.image_url = image_url

    def mark_error(self, job_or_id: Job | int, error: str):
        """Mark job as failed."""
        if isinstance(job_or_id, int):
            if job_or_id in self.jobs:
                job = self.jobs[job_or_id]
                job.status = JobStatus.ERROR
                job.error = error
        else:
            job_or_id.status = JobStatus.ERROR
            job_or_id.error = error
            if job_or_id in self.pending:
                self.pending.remove(job_or_id)

    def get_submitted_jobs(self) -> list[Job]:
        """Get all jobs that are submitted but not finished."""
        return [job for job in self.all_jobs if job.status == JobStatus.SUBMITTED]

    def get_results(self) -> list[Job]:
        """Get all jobs (for final output)."""
        return self.all_jobs

    def get_stats(self) -> dict[str, int]:
        """Get counts by status."""
        stats = {status.value: 0 for status in JobStatus}
        for job in self.all_jobs:
            stats[job.status.value] += 1
        return stats
