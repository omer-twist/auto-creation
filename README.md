# AI Tools - Creative Generation

Generates marketing creatives for Amazon affiliate campaigns. Takes a topic and produces 12 styled images with copy, organized into 4 campaigns uploaded to Monday.com.

## How It Works

```
Topic → TextService (3-stage LLM) → CreativeService (Placid) → Monday.com
        └─ 12 text variations       └─ 12 styled images        └─ 4 rows
```

**Input:**
```json
{
  "topic": "Girls Bracelet Making Kit",
  "event": "Black Friday",
  "discount": "up to 50%",
  "page_type": "category"
}
```

**Output:** 4 Monday.com rows, each with 3 creative images.

## Setup

```bash
pip install -r requirements.txt
```

Required environment variables:
```
OPENAI_API_KEY
PLACID_API_TOKEN
PLACID_TEMPLATE_UUID
MONDAY_API_KEY
MONDAY_BOARD_ID
```

## Usage

### Local

```bash
python -m src.handlers.worker "<topic>" "<event>" "<discount>" "<page_type>"
```

### HTTP API

POST to the Lambda function URL:
```bash
curl -X POST https://<lambda-url>/ \
  -H "Content-Type: application/json" \
  -d '{"topic": "Wireless Earbuds", "event": "Prime Day", "discount": "30%", "page_type": "general"}'
```

## Deployment

```bash
# Build and push Docker image
docker build --provenance=false --platform linux/amd64 -t ai-tools .
docker tag ai-tools:latest <account>.dkr.ecr.us-east-1.amazonaws.com/campaigns-generator:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/campaigns-generator:latest

# Apply infrastructure
cd terraform && terraform apply
```

## Architecture

| Layer | Component | Purpose |
|-------|-----------|---------|
| Models | Topic, Campaign, Creative | Data structures |
| Services | TopicService, TextService, CreativeService | Business logic |
| Clients | LLMClient, CreativeClient, MondayClient | External APIs |
| Handlers | enqueue, worker | Lambda entrypoints |
