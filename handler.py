import json

import requests

from monday_client import create_item, upload_file_to_column
from openai_client import generate_text
from placid.client import PlacidClient
from placid.config import (
    API_TOKEN,
    MONDAY_API_KEY,
    MONDAY_BOARD_ID,
    TEMPLATE_UUID,
    get_variants_for_batch,
)
from placid.orchestrator import Orchestrator
from placid.tracker import JobTracker


# Monday column IDs
CREATIVES_COLUMN_ID = "file_mky7b1ww"
TEST_FIELD_COLUMN_ID = "text_mky7650h"


# Step 1: Create Monday row
def create_monday_row(item: str, column_values: dict) -> int:
    """Create a Monday row with all fields. Returns item_id."""
    # Add test field value
    column_values[TEST_FIELD_COLUMN_ID] = "omer-test"
    return create_item(MONDAY_API_KEY, MONDAY_BOARD_ID, item, column_values)


# Step 2: Generate creatives
def generate_creatives(item: str, batch_num: int) -> dict:
    """Generate marketing text + images."""
    text = generate_text(item)

    variants = get_variants_for_batch(batch_num)
    client = PlacidClient(API_TOKEN, TEMPLATE_UUID)
    tracker = JobTracker()
    orchestrator = Orchestrator(client, tracker, submit_delay=1.0, poll_interval=2.0)

    results = orchestrator.run(text, variants)
    urls = [job.image_url for job in results if job.image_url]

    return {"text": text, "urls": urls}


# Step 3: Upload images
def upload_images(item_id: int, urls: list[str]):
    """Download and upload images to Monday row's Creatives column."""
    for i, url in enumerate(urls):
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        file_bytes = response.content
        filename = f"creative_{i + 1}.jpg"
        upload_file_to_column(MONDAY_API_KEY, item_id, CREATIVES_COLUMN_ID, file_bytes, filename)


def lambda_handler(event, context):
    """AWS Lambda handler - orchestrates all steps."""
    body = json.loads(event.get("body", "{}"))
    item = body.get("item")
    batch_num = body.get("batch_num")
    column_values = body.get("column_values", {})  # Other Monday fields

    if not all([item, batch_num]):
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing item or batch_num"}),
        }

    try:
        # Step 1: Create Monday row (gets item_id)
        item_id = create_monday_row(item, column_values)

        # Step 2: Generate creatives
        creatives = generate_creatives(item, batch_num)

        # Step 3: Upload images to the Creatives column
        upload_images(item_id, creatives["urls"])

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "item_id": item_id,
                    "item": item,
                    "text": creatives["text"],
                    "images_uploaded": len(creatives["urls"]),
                }
            ),
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }


# Local testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python handler.py <item> <batch_num>")
        print("Example: python handler.py Nike 1")
        sys.exit(1)

    item = sys.argv[1]
    batch_num = int(sys.argv[2])

    # Simulate Lambda event
    event = {"body": json.dumps({"item": item, "batch_num": batch_num})}

    result = lambda_handler(event, None)
    print(json.dumps(json.loads(result["body"]), indent=2))
