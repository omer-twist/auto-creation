import time

from .client import PlacidClient
from .config import ImageVariant
from .tracker import Job, JobTracker


class Orchestrator:
    def __init__(
        self,
        client: PlacidClient,
        tracker: JobTracker,
        submit_delay: float = 1.0,
        poll_interval: float = 2.0,
    ):
        self.client = client
        self.tracker = tracker
        self.submit_delay = submit_delay
        self.poll_interval = poll_interval

    def submit_all(self):
        """Phase 1: Submit all pending jobs with fixed delay."""
        total = len(self.tracker.pending)
        for i, job in enumerate(list(self.tracker.pending), 1):
            bg = job.variant.color_scheme.background_color
            print(f"[{i}/{total}] Submitting {bg}...", flush=True)

            image_id = self.client.submit_job(job.text, job.variant)
            if image_id:
                self.tracker.mark_submitted(job, image_id)
                print(f"  -> ID: {image_id}", flush=True)
            else:
                self.tracker.mark_error(job, "Submit failed")
                print(f"  -> FAILED", flush=True)

            if i < total:
                time.sleep(self.submit_delay)

    def poll_all(self):
        """Phase 2: Poll all submitted jobs until all complete."""
        poll_round = 0
        while True:
            pending = self.tracker.get_submitted_jobs()
            if not pending:
                break

            poll_round += 1
            stats = self.tracker.get_stats()
            print(
                f"\n[Poll {poll_round}] {len(pending)} pending, "
                f"{stats['finished']} done, {stats['error']} errors",
                flush=True,
            )

            for job in pending:
                status, url, error = self.client.poll_job(job.image_id)

                if status == "finished":
                    self.tracker.mark_finished(job.image_id, url)
                    bg = job.variant.color_scheme.background_color
                    print(f"  [{bg}] DONE", flush=True)
                elif status == "error":
                    self.tracker.mark_error(job.image_id, error or "Unknown error")
                    bg = job.variant.color_scheme.background_color
                    print(f"  [{bg}] ERROR: {error}", flush=True)

            time.sleep(self.poll_interval)

    def run(self, text: str, variants: list[ImageVariant]) -> list[Job]:
        """Full pipeline: add jobs -> submit -> poll -> return results."""
        print(f"Adding {len(variants)} jobs...", flush=True)
        for variant in variants:
            self.tracker.add_job(text, variant)

        print(f"\n=== SUBMIT PHASE ===", flush=True)
        self.submit_all()

        print(f"\n=== POLL PHASE ===", flush=True)
        self.poll_all()

        return self.tracker.get_results()
