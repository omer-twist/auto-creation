"""AWS Lambda handler for creative generation."""

import json

import requests

from ..clients import LLMClient, CreativeClient, MondayClient
from ..clients.gemini import GeminiClient
from ..clients.removebg import RemoveBgClient
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
    MONDAY_COL_CONTENT_MANAGER,
    MONDAY_GROUP_ID,
    MONDAY_SITE_VALUE,
    MONDAY_CONTENT_MANAGER_VALUE,
    GEMINI_API_KEY,
    REMOVEBG_API_KEY,
)
from ..utils import to_slug, today_date

from ..engine import CreativeEngine
from ..creative_types import get_creative_type, list_creative_types
from ..models import Topic
from ..generators import get_generator_class


def handler(event, context):
    """
    AWS Lambda handler - triggered by SQS or HTTP.

    Input payload:
    {
        "topic": "Girls Bracelet Making Kit",
        "event": "Black Friday",
        "discount": "up to 50%",
        "page_type": "category",
        "creative_type": "product_cluster",
        "product_image_urls": ["url1", "url2", ...]
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

    # Route to config-driven engine
    creative_type = body.get("creative_type", "product_cluster")
    if creative_type not in list_creative_types():
        return {
            "statusCode": 400,
            "body": json.dumps({"error": f"Unknown creative_type: {creative_type}"}),
        }

    return _handle_creative(body)


def _handle_creative(body: dict) -> dict:
    """Handle creative type request."""
    creative_type = body["creative_type"]
    print(f"Processing topic: {body['topic']} (creative_type={creative_type})", flush=True)

    try:
        # 1. Build Topic (universal fields only)
        topic = Topic(
            name=body["topic"],
            event=body.get("event", "none"),
            discount=body.get("discount", "none"),
            page_type=body.get("page_type", "general"),
            url=body.get("url", ""),
        )

        # 2. Get config
        config = get_creative_type(creative_type)

        # 3. Extract inputs and options
        inputs = _extract_inputs(body, config)
        options = _extract_options(body, config)

        # 4. Initialize clients
        llm_client = LLMClient(api_key=OPENAI_API_KEY)
        gemini_client = GeminiClient(api_key=GEMINI_API_KEY)
        removebg_client = RemoveBgClient(api_key=REMOVEBG_API_KEY)
        creative_client = CreativeClient(PLACID_API_TOKEN, PLACID_TEMPLATE_UUID)

        # 5. Create engine and generate
        engine = CreativeEngine(
            llm=llm_client,
            gemini=gemini_client,
            removebg=removebg_client,
            creative=creative_client,
        )

        creatives = engine.generate(topic, config, inputs, options, count=12)
        print(f"Generated {len(creatives)} creatives", flush=True)

        # 6. Upload to Monday
        return _upload_creatives(topic, creatives)

    except Exception as e:
        print(f"ERROR: {e}", flush=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }


def _extract_inputs(body: dict, config) -> dict:
    """Extract all inputs from request body based on generator INPUTS and slot options."""
    inputs = {}

    # Collect from generator INPUTS
    for slot in config.slots:
        # Skip style sources (they don't have generator classes)
        if slot.source.startswith("style."):
            continue
        gen_class = get_generator_class(slot.source)
        for field in getattr(gen_class, "INPUTS", []):
            if field.name in body:
                inputs[field.name] = body[field.name]
            elif field.required:
                raise ValueError(f"Missing required input: {field.name}")
            elif field.default is not None:
                inputs[field.name] = field.default

    # Collect slot toggles (e.g., include_header)
    for slot in config.slots:
        if slot.optional:
            toggle_name = f"include_{slot.name.split('.')[0]}"
            inputs[toggle_name] = body.get(toggle_name, True)  # Default to included

    return inputs


def _extract_options(body: dict, config) -> dict:
    """Extract internal processing options (not user-facing)."""
    # Options now only contains internal settings, not user inputs
    # User inputs (including toggles) go in inputs dict
    return {}


def _upload_creatives(topic: Topic, creatives: list) -> dict:
    """Upload creatives to Monday, return response."""
    monday_client = MondayClient(MONDAY_API_KEY, MONDAY_BOARD_ID)

    # Group into campaigns of 3
    campaigns = [creatives[i:i+3] for i in range(0, len(creatives), 3)]

    created_rows = []
    errors = []

    for campaign_num, campaign_creatives in enumerate(campaigns, start=1):
        print(f"Creating Monday row for campaign {campaign_num}...", flush=True)

        try:
            # Create Monday row
            item_name = to_slug(topic.name)
            column_values = {
                MONDAY_COL_DATE: {"date": today_date()},
                MONDAY_COL_SITE: MONDAY_SITE_VALUE,
                MONDAY_COL_URL: topic.url,
                MONDAY_COL_CONTENT_MANAGER: MONDAY_CONTENT_MANAGER_VALUE,
            }
            item_id = monday_client.create_item(item_name, column_values, MONDAY_GROUP_ID)

            # Upload images
            for i, creative in enumerate(campaign_creatives):
                response = requests.get(creative.creative_url, stream=True, timeout=30)
                response.raise_for_status()
                filename = f"creative_{campaign_num}_{i + 1}.jpg"
                monday_client.upload_file(item_id, MONDAY_COL_CREATIVES, response.content, filename)

            created_rows.append({
                "campaign": campaign_num,
                "item_id": item_id,
                "images_uploaded": len(campaign_creatives),
            })

        except Exception as e:
            errors.append({"campaign": campaign_num, "error": str(e)})
            print(f"  Error on campaign {campaign_num}: {e}", flush=True)

    # Build response
    status_code = 500 if errors and not created_rows else (207 if errors else 200)

    return {
        "statusCode": status_code,
        "body": json.dumps({
            "topic": topic.name,
            "campaigns_created": len(created_rows),
            "campaigns": created_rows,
            "errors": errors if errors else None,
        }),
    }


# Local testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 5:
        print("Usage: python -m src.handlers.worker <topic> <event> <discount> <page_type> [creative_type] [inputs_json]")
        print()
        print("Arguments:")
        print("  topic         - The topic/category name")
        print("  event         - e.g., 'Black Friday', 'Prime Day', 'none'")
        print("  discount      - e.g., 'up to 50%', '50%', '24h', 'none'")
        print("  page_type     - general | category")
        print("  creative_type - product_cluster (default)")
        print("  inputs_json   - JSON object with inputs: {\"product_image_urls\": [...]}")
        print()
        print("Example:")
        print('  python -m src.handlers.worker "Girls Bracelet Making Kit" "Black Friday" "up to 50%" category product_cluster \'{"product_image_urls": ["url1", "url2", "url3"]}\'')
        sys.exit(1)

    test_input = {
        "topic": sys.argv[1],
        "event": sys.argv[2],
        "discount": sys.argv[3],
        "page_type": sys.argv[4],
        "creative_type": sys.argv[5] if len(sys.argv) > 5 else "product_cluster",
    }

    # Parse optional inputs JSON
    if len(sys.argv) > 6:
        inputs = json.loads(sys.argv[6])
        test_input.update(inputs)

    print("Running with input:")
    print(json.dumps(test_input, indent=2))
    print()

    event = {"body": json.dumps(test_input)}

    result = handler(event, None)
    print("\nResult:")
    print(json.dumps(json.loads(result["body"]), indent=2))
