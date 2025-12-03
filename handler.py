"""AWS Lambda handler for 3-stage text generation pipeline."""

import json
import time

import requests

from monday_client import create_item, upload_file_to_column
from utils import to_slug
from pipeline import (
    GenerationInput,
    TextGenerationPipeline,
)
from placid.client import PlacidClient
from placid.config import (
    API_TOKEN,
    MONDAY_API_KEY,
    MONDAY_BOARD_ID,
    OPENAI_API_KEY,
    TEMPLATE_UUID,
    get_variant_by_index,
)


# Monday column IDs
CREATIVES_COLUMN_ID = "file_mky7b1ww"
TEST_FIELD_COLUMN_ID = "text_mky7650h"


def parse_input(body: dict) -> GenerationInput:
    """Parse request body into GenerationInput."""
    return GenerationInput(
        topic=body["topic"],
        event=body.get("event", "none"),
        discount=body.get("discount", "none"),
        page_type=body.get("page_type", "general"),
    )


def submit_all_images(client: PlacidClient, variations: list) -> dict:
    """
    Submit all 9 images at once. Returns {variation.index: image_id}.
    """
    image_ids = {}
    for variation in variations:
        variant = get_variant_by_index(variation.batch_num, variation.color_index)
        image_id = client.submit_job(variation.text, variant)
        if not image_id:
            raise Exception(f"Failed to submit image for variation {variation.index}")
        image_ids[variation.index] = image_id
        print(f"  Submitted variation {variation.index}", flush=True)
    return image_ids


def poll_all_images(client: PlacidClient, image_ids: dict, poll_interval: int = 20) -> dict:
    """
    Poll all images until all are done. Returns {variation.index: image_url}.
    """
    image_urls = {}
    pending = set(image_ids.keys())

    while pending:
        # Wait before polling
        print(f"  Waiting {poll_interval}s before polling {len(pending)} images...", flush=True)
        time.sleep(poll_interval)

        # Poll all pending images
        for index in list(pending):
            image_id = image_ids[index]
            status, url, error = client.poll_job(image_id)

            if status == "finished":
                image_urls[index] = url
                pending.remove(index)
                print(f"  Variation {index} done", flush=True)
            elif status == "error":
                raise Exception(f"Placid error for variation {index}: {error}")
            # else still pending, will retry next cycle

    return image_urls


def create_monday_row_for_batch(topic: str, batch_num: int) -> int:
    """Create a Monday row for one batch (3 images per row)."""
    item_name = to_slug(topic)
    column_values = {TEST_FIELD_COLUMN_ID: "auto-generated"}
    return create_item(MONDAY_API_KEY, MONDAY_BOARD_ID, item_name, column_values)


def upload_image_to_row(item_id: int, image_url: str, index: int):
    """Download and upload image to Monday row."""
    response = requests.get(image_url, stream=True, timeout=30)
    response.raise_for_status()
    filename = f"creative_{index}.jpg"
    upload_file_to_column(
        MONDAY_API_KEY, item_id, CREATIVES_COLUMN_ID, response.content, filename
    )


def lambda_handler(event, context):
    """
    AWS Lambda handler - triggered by SQS or HTTP.

    SQS event format: {"Records": [{"body": "{...}"}]}
    HTTP event format: {"body": "{...}"}

    Input payload:
    {
        "topic": "Girls Bracelet Making Kit",
        "event": "Black Friday",
        "discount": "up to 50%",
        "page_type": "category"
    }

    Output: 3 Monday rows with 9 images total (3 images per row, grouped by batch).
    """
    # Handle SQS event format
    if "Records" in event:
        # SQS trigger - body is in Records[0].body
        body = json.loads(event["Records"][0]["body"])
    else:
        # HTTP trigger (for local testing)
        body = json.loads(event.get("body", "{}"))

    # Validate required field
    if not body.get("topic"):
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing 'topic' field"}),
        }

    try:
        # Step 1: Parse input
        input_data = parse_input(body)
        print(f"Processing topic: {input_data.topic}", flush=True)

        # Step 2: Run 3-stage text pipeline
        pipeline = TextGenerationPipeline(OPENAI_API_KEY)
        result = pipeline.run(input_data)
        print(f"Generated {len(result.variations)} text variations", flush=True)

        # Step 3: Submit all 9 images at once
        placid_client = PlacidClient(API_TOKEN, TEMPLATE_UUID)

        print("Submitting all 9 images...", flush=True)
        image_ids = submit_all_images(placid_client, result.variations)

        # Step 4: Poll all images until done (20s intervals)
        print("Polling for completion...", flush=True)
        image_urls = poll_all_images(placid_client, image_ids, poll_interval=20)

        # Step 5: Create Monday rows and upload (grouped by batch)
        created_rows = []
        errors = []

        for batch_num in [1, 2, 3]:
            print(f"Creating Monday row for batch {batch_num}...", flush=True)

            batch_variations = [
                v for v in result.variations if v.batch_num == batch_num
            ]

            try:
                # Create 1 Monday row for this batch
                item_id = create_monday_row_for_batch(input_data.topic, batch_num)

                # Upload all 3 images to this row
                for variation in batch_variations:
                    upload_image_to_row(item_id, image_urls[variation.index], variation.index)

                created_rows.append({
                    "batch": batch_num,
                    "item_id": item_id,
                    "images_uploaded": len(batch_variations),
                    "texts": [v.text for v in batch_variations],
                })

            except Exception as e:
                errors.append({
                    "batch": batch_num,
                    "error": str(e),
                })
                print(f"  Error on batch {batch_num}: {e}", flush=True)

        # Determine response status
        if errors and not created_rows:
            status_code = 500
        elif errors:
            status_code = 207  # Multi-Status (partial success)
        else:
            status_code = 200

        return {
            "statusCode": status_code,
            "body": json.dumps({
                "topic": input_data.topic,
                "rows_created": len(created_rows),
                "rows": created_rows,
                "errors": errors if errors else None,
            }),
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }


# Local testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 5:
        print("Usage: python handler.py <topic> <event> <discount> <page_type>")
        print()
        print("Arguments:")
        print("  topic    - The topic/category name")
        print("  event    - e.g., 'Black Friday', 'Prime Day', 'none'")
        print("  discount - e.g., 'up to 50%', '50%', '24h', 'none'")
        print("  page_type - general | category")
        print()
        print("Example:")
        print('  python handler.py "Girls Bracelet Making Kit" "Black Friday" "up to 50%" category')
        sys.exit(1)

    test_input = {
        "topic": sys.argv[1],
        "event": sys.argv[2],
        "discount": sys.argv[3],
        "page_type": sys.argv[4],
    }

    print("Running with input:")
    print(json.dumps(test_input, indent=2))
    print()

    # Simulate Lambda event
    event = {"body": json.dumps(test_input)}

    result = lambda_handler(event, None)
    print("\nResult:")
    print(json.dumps(json.loads(result["body"]), indent=2))
