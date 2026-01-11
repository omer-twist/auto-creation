# Auto-Creation

Generates marketing creatives for affiliate campaigns. Takes a topic and produces 12 styled images with copy, organized into 4 campaigns uploaded to Monday.com.

## How It Works

```
Topic + Config → CreativeEngine → Placid → Monday.com
                     │
                     ├── text.header → "TOPIC NAME"
                     ├── text.main_text → 12 variations (LLM)
                     ├── image.cluster → product cluster (Gemini)
                     └── style.* → colors from style_pool
```

**Input:**
```json
{
  "topic": "Girls Bracelet Making Kit",
  "event": "Black Friday",
  "discount": "up to 50%",
  "page_type": "category",
  "creative_type": "product_cluster",
  "product_image_urls": ["url1", "url2", "url3"]
}
```

**Output:** 4 Monday.com rows, each with 3 creative images.

## Setup

```bash
pip install -r requirements.txt
```

Required environment variables (see `.env.example`):
```
OPENAI_API_KEY
GEMINI_API_KEY
REMOVEBG_API_KEY
PLACID_API_TOKEN
PLACID_PRODUCT_CLUSTER_TEMPLATE_UUID
PLACID_PRODUCT_CLUSTER_TEMPLATE_UUID_WHITE
MONDAY_API_KEY
MONDAY_BOARD_ID
```

## Usage

### Local

```bash
python -m src.handlers.worker "<topic>" "<event>" "<discount>" "<page_type>" [creative_type] [inputs_json]

# Example
python -m src.handlers.worker "Girls Bracelet Kit" "Black Friday" "50%" category product_cluster '{"product_image_urls": ["url1", "url2", "url3"]}'
```

### HTTP API

POST to the Lambda function URL:
```bash
curl -X POST https://<lambda-url>/ \
  -H "Content-Type: application/json" \
  -d '{"topic": "Wireless Earbuds", "event": "Prime Day", "discount": "30%", "page_type": "general", "creative_type": "product_cluster", "product_image_urls": ["url1", "url2"]}'
```

GET config for frontend form:
```bash
curl https://<lambda-url>/config
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
| Models | Topic, Creative, Slot, CreativeTypeConfig | Data structures |
| Engine | CreativeEngine | Config-driven orchestration |
| Generators | text.header, text.main_text, image.cluster | Independent content producers |
| Creative Types | product_cluster | Declarative configs (slots, variants, style_pool) |
| Clients | LLMClient, GeminiClient, CreativeClient, MondayClient | External APIs |
| Handlers | enqueue, worker | Lambda entrypoints |
