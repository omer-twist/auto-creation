"""Test scaling with 30 parallel Lambda invocations."""

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from handler import lambda_handler

# 6 topics for testing
TOPICS = [
    "Girls Bracelet Making Kit",
    "Scented Candles Set",
    "Wireless Earbuds",
    "Yoga Mat",
    "Coffee Maker",
    "Kitchen Knife Set",
]

def run_single_topic(topic: str, index: int) -> dict:
    """Run a single Lambda invocation for one topic."""
    start = time.time()

    event = {
        "body": json.dumps({
            "topic": topic,
            "event_mode": "BLACK_FRIDAY",
            "discount_mode": "UP_TO_PERCENT",
            "discount": "up to 50%",
            "page_type": "CATEGORY",
        })
    }

    try:
        result = lambda_handler(event, None)
        elapsed = time.time() - start
        body = json.loads(result["body"])

        return {
            "index": index,
            "topic": topic,
            "status": result["statusCode"],
            "rows_created": body.get("rows_created", 0),
            "elapsed": round(elapsed, 1),
            "success": result["statusCode"] == 200,
        }
    except Exception as e:
        elapsed = time.time() - start
        return {
            "index": index,
            "topic": topic,
            "status": 500,
            "error": str(e),
            "elapsed": round(elapsed, 1),
            "success": False,
        }


def main():
    print(f"Starting {len(TOPICS)} sequential Lambda invocations...")
    print(f"=" * 60)

    start_time = time.time()
    results = []

    # Run with concurrency of 3
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(run_single_topic, topic, i): topic
            for i, topic in enumerate(TOPICS, 1)
        }

        for future in as_completed(futures):
            result = future.result()
            results.append(result)

            status = "OK" if result["success"] else "FAIL"
            print(f"[{result['index']:2d}] {status} {result['topic'][:30]:<30} | {result['elapsed']}s | rows={result.get('rows_created', 'ERR')}")

    total_time = time.time() - start_time

    # Summary
    print(f"=" * 60)
    successful = sum(1 for r in results if r["success"])
    total_rows = sum(r.get("rows_created", 0) for r in results)

    print(f"Completed: {successful}/{len(TOPICS)} successful")
    print(f"Total rows created: {total_rows}")
    print(f"Total time: {round(total_time, 1)}s")
    print(f"Avg time per topic: {round(total_time/len(TOPICS), 1)}s")


if __name__ == "__main__":
    main()
