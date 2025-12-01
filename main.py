import sys

from placid.client import PlacidClient
from placid.config import API_TOKEN, TEMPLATE_UUID, get_all_variants
from placid.orchestrator import Orchestrator
from placid.tracker import JobStatus, JobTracker


def main(text: str):
    if not API_TOKEN or not TEMPLATE_UUID:
        print("Error: PLACID_API_TOKEN and PLACID_TEMPLATE_UUID must be set in .env")
        sys.exit(1)

    client = PlacidClient(API_TOKEN, TEMPLATE_UUID)
    tracker = JobTracker()
    orchestrator = Orchestrator(client, tracker, submit_delay=1.0, poll_interval=2.0)

    variants = get_all_variants()
    results = orchestrator.run(text, variants)

    print("\n=== RESULTS ===")
    for job in results:
        bg = job.variant.color_scheme.background_color
        if job.status == JobStatus.FINISHED:
            print(f"[{bg}] {job.image_url}")
        else:
            print(f"[{bg}] ERROR: {job.error}")

    stats = tracker.get_stats()
    print(f"\nTotal: {stats['finished']} success, {stats['error']} failed")


if __name__ == "__main__":
    text = sys.argv[1] if len(sys.argv) > 1 else "HELLO FROM PLACID"
    main(text)
