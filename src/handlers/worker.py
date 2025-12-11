"""AWS Lambda handler for creative generation."""

import json

import requests

from ..clients import LLMClient, CreativeClient, MondayClient
from ..models import Topic
from ..services import TopicService
from ..config import (
    PLACID_API_TOKEN,
    PLACID_TEMPLATE_UUID,
    OPENAI_API_KEY,
    MONDAY_API_KEY,
    MONDAY_BOARD_ID,
    MONDAY_COL_DATE,
    MONDAY_COL_SITE,
    MONDAY_COL_CREATIVES,
    MONDAY_COL_URL,
    MONDAY_GROUP_ID,
    MONDAY_SITE_VALUE,
)
from ..utils import to_slug, today_date


def handler(event, context):
    """
    AWS Lambda handler - triggered by SQS or HTTP.

    Input payload:
    {
        "topic": "Girls Bracelet Making Kit",
        "event": "Black Friday",
        "discount": "up to 50%",
        "page_type": "category"
    }

    Output: 4 Monday rows with 12 images total (3 images per row).
    """
    # Handle SQS event format
    if "Records" in event:
        body = json.loads(event["Records"][0]["body"])
    else:
        body = json.loads(event.get("body", "{}"))

    # Validate required field
    if not body.get("topic"):
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing 'topic' field"}),
        }

    try:
        # Create topic
        topic = Topic(
            name=body["topic"],
            event=body.get("event", "none"),
            discount=body.get("discount", "none"),
            page_type=body.get("page_type", "general"),
            url=body.get("url", ""),
        )
        print(f"Processing topic: {topic.name}", flush=True)

        # Generate creatives
        llm_client = LLMClient(api_key=OPENAI_API_KEY)
        creative_client = CreativeClient(PLACID_API_TOKEN, PLACID_TEMPLATE_UUID)
        monday_client = MondayClient(MONDAY_API_KEY, MONDAY_BOARD_ID)
        topic_service = TopicService(llm_client, creative_client)

        topic = topic_service.generate(topic)
        print(f"Generated {len(topic.campaigns)} campaigns", flush=True)

        # Upload each campaign to Monday
        created_rows = []
        errors = []

        for campaign_num, campaign in enumerate(topic.campaigns, start=1):
            print(f"Creating Monday row for campaign {campaign_num}...", flush=True)

            try:
                # Create row
                item_name = to_slug(topic.name)
                column_values = {
                    MONDAY_COL_DATE: {"date": today_date()},
                    MONDAY_COL_SITE: MONDAY_SITE_VALUE,
                    MONDAY_COL_URL: topic.url,
                }
                item_id = monday_client.create_item(item_name, column_values, MONDAY_GROUP_ID)
                campaign.monday_item_id = item_id

                # Upload images
                for i, creative in enumerate(campaign.creatives):
                    response = requests.get(creative.image_url, stream=True, timeout=30)
                    response.raise_for_status()
                    filename = f"creative_{campaign_num}_{i + 1}.jpg"
                    monday_client.upload_file(item_id, MONDAY_COL_CREATIVES, response.content, filename)

                created_rows.append({
                    "campaign": campaign_num,
                    "item_id": item_id,
                    "images_uploaded": len(campaign.creatives),
                    "texts": [c.text for c in campaign.creatives],
                })

            except Exception as e:
                errors.append({
                    "campaign": campaign_num,
                    "error": str(e),
                })
                print(f"  Error on campaign {campaign_num}: {e}", flush=True)

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
                "topic": topic.name,
                "campaigns_created": len(created_rows),
                "campaigns": created_rows,
                "errors": errors if errors else None,
            }),
        }

    except Exception as e:
        print(f"ERROR: {e}", flush=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }


# Local testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 5:
        print("Usage: python -m src.handlers.worker <topic> <event> <discount> <page_type>")
        print()
        print("Arguments:")
        print("  topic    - The topic/category name")
        print("  event    - e.g., 'Black Friday', 'Prime Day', 'none'")
        print("  discount - e.g., 'up to 50%', '50%', '24h', 'none'")
        print("  page_type - general | category")
        print()
        print("Example:")
        print('  python -m src.handlers.worker "Girls Bracelet Making Kit" "Black Friday" "up to 50%" category')
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

    event = {"body": json.dumps(test_input)}

    result = handler(event, None)
    print("\nResult:")
    print(json.dumps(json.loads(result["body"]), indent=2))
