"""AWS Lambda handler for creative generation."""

import json

import requests

from ..clients import LLMClient, CreativeClient, MondayClient
from ..clients.gemini import GeminiClient
from ..clients.removebg import RemoveBgClient
from ..models import Topic
from ..services import TopicService, ProductImageService
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

# v2 imports
from ..v2.engine import CreativeEngine
from ..v2.config.types import get_creative_type, list_creative_types
from ..v2.models import Topic as TopicV2
from ..v2.generators import get_generator_class


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

    # Route v2 creative types
    creative_type = body.get("creative_type", "standard")
    if creative_type in list_creative_types():
        return _handle_v2(body)

    try:
        # v1 path: Create topic
        topic = Topic(
            name=body["topic"],
            event=body.get("event", "none"),
            discount=body.get("discount", "none"),
            page_type=body.get("page_type", "general"),
            url=body.get("url", ""),
            product_urls=body.get("product_urls", []),
            creative_type=creative_type,
            product_image_urls=body.get("product_image_urls", []),
            main_lines=body.get("main_lines", []),
            is_people_mode=body.get("is_people_mode", False),
            include_header=body.get("include_header", True),
        )
        print(f"Processing topic: {topic.name} (creative_type={creative_type})", flush=True)

        # Initialize clients
        llm_client = LLMClient(api_key=OPENAI_API_KEY)
        creative_client = CreativeClient(PLACID_API_TOKEN, PLACID_TEMPLATE_UUID)
        monday_client = MondayClient(MONDAY_API_KEY, MONDAY_BOARD_ID)

        # Route by creative type
        if creative_type == "product_cluster":
            # Product cluster requires additional services
            gemini_client = GeminiClient(api_key=GEMINI_API_KEY)
            removebg_client = RemoveBgClient(api_key=REMOVEBG_API_KEY)
            product_image_service = ProductImageService(
                gemini_client=gemini_client,
                removebg_client=removebg_client,
                creative_client=creative_client,
            )
            topic_service = TopicService(llm_client, creative_client, product_image_service)
            topic = topic_service.generate_product_cluster(topic)
        else:
            # Standard creative generation
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
                    MONDAY_COL_CONTENT_MANAGER: MONDAY_CONTENT_MANAGER_VALUE,
                }
                item_id = monday_client.create_item(item_name, column_values, MONDAY_GROUP_ID)
                campaign.monday_item_id = item_id

                # Upload images
                for i, creative in enumerate(campaign.creatives):
                    response = requests.get(creative.image_url, stream=True, timeout=30)
                    response.raise_for_status()
                    filename = f"creative_{campaign_num}_{i + 1}.jpg"
                    monday_client.upload_file(item_id, MONDAY_COL_CREATIVES, response.content, filename)

                # Build texts response based on creative type
                if creative_type == "product_cluster":
                    texts = [
                        {"header": c.text, "main": c.text_secondary}
                        for c in campaign.creatives
                    ]
                else:
                    texts = [c.text for c in campaign.creatives]

                created_rows.append({
                    "campaign": campaign_num,
                    "item_id": item_id,
                    "images_uploaded": len(campaign.creatives),
                    "texts": texts,
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


# ===== v2 handlers =====


def _handle_v2(body: dict) -> dict:
    """Handle v2 creative type request."""
    creative_type = body["creative_type"]
    print(f"Processing v2 topic: {body['topic']} (creative_type={creative_type})", flush=True)

    try:
        # 1. Build v2 Topic (universal fields only)
        topic = TopicV2(
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
        return _upload_v2_creatives(topic, creatives)

    except Exception as e:
        print(f"ERROR: {e}", flush=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }


def _extract_inputs(body: dict, config) -> dict:
    """Extract inputs defined by config from request body."""
    inputs = {}
    for input_field in config.inputs:
        if input_field.name in body:
            inputs[input_field.name] = body[input_field.name]
        elif input_field.required:
            raise ValueError(f"Missing required input: {input_field.name}")
    return inputs


def _extract_options(body: dict, config) -> dict:
    """Extract options (toggles, generator options) from request body."""
    options = {}

    # Slot toggles (e.g., include_header)
    for slot in config.slots:
        if slot.ui and slot.ui.option_name:
            options[slot.ui.option_name] = body.get(
                slot.ui.option_name,
                slot.ui.toggle_default
            )

    # Generator options (e.g., is_people_mode)
    for source in {s.source for s in config.slots}:
        gen_class = get_generator_class(source)
        for opt in getattr(gen_class, "OPTIONS", []):
            options[opt.name] = body.get(opt.name, opt.default)

    return options


def _upload_v2_creatives(topic: TopicV2, creatives: list) -> dict:
    """Upload v2 creatives to Monday, return response."""
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
        print("Usage: python -m src.handlers.worker <topic> <event> <discount> <page_type> [creative_type] [extra_json]")
        print()
        print("Arguments:")
        print("  topic         - The topic/category name")
        print("  event         - e.g., 'Black Friday', 'Prime Day', 'none'")
        print("  discount      - e.g., 'up to 50%', '50%', '24h', 'none'")
        print("  page_type     - general | category")
        print("  creative_type - standard | product_cluster (default: standard)")
        print("  extra_json    - JSON object with additional fields:")
        print("                  Standard: {\"product_urls\": [...]}")
        print("                  Product Cluster: {\"product_image_urls\": [8 URLs]}")
        print()
        print("Example (standard):")
        print('  python -m src.handlers.worker "Girls Bracelet Making Kit" "Black Friday" "up to 50%" category')
        print()
        print("Example (product cluster):")
        print('  python -m src.handlers.worker "Girls Bracelet Making Kit" "Black Friday" "up to 50%" category product_cluster \'{"product_image_urls": ["url1", "url2", ..., "url8"]}\'')
        sys.exit(1)

    test_input = {
        "topic": sys.argv[1],
        "event": sys.argv[2],
        "discount": sys.argv[3],
        "page_type": sys.argv[4],
    }

    # Parse optional creative_type
    if len(sys.argv) > 5:
        test_input["creative_type"] = sys.argv[5]

    # Parse optional extra JSON (product_urls or product_image_urls)
    if len(sys.argv) > 6:
        extra = json.loads(sys.argv[6])
        test_input.update(extra)

    print("Running with input:")
    print(json.dumps(test_input, indent=2))
    print()

    event = {"body": json.dumps(test_input)}

    result = handler(event, None)
    print("\nResult:")
    print(json.dumps(json.loads(result["body"]), indent=2))
