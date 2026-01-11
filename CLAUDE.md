# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Marketing creative generation system for affiliate campaigns. Takes a topic (e.g., "Girls Bracelet Making Kit") and generates 12 creatives (text + styled images) organized into 4 campaigns, then uploads to Monday.com.

## Commands

```bash
# Run locally (product_cluster is the default creative type)
python -m src.handlers.worker "<topic>" "<event>" "<discount>" "<page_type>" [creative_type] [inputs_json]
python -m src.handlers.worker "Girls Bracelet Kit" "Black Friday" "50%" category product_cluster '{"product_image_urls": ["url1", "url2", "url3"]}'

# Deploy
docker build --provenance=false --platform linux/amd64 -t ai-tools .
docker tag ai-tools:latest <account>.dkr.ecr.us-east-1.amazonaws.com/campaigns-generator:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/campaigns-generator:latest

# Infrastructure
cd terraform && terraform apply
```

## Architecture

### Config-Driven Engine

The system uses a config-driven architecture where creative types are defined declaratively:

```
CreativeTypeConfig (src/creative_types/)
    ├── variants: {"dark": UUID, "light": UUID}     # Placid template UUIDs
    ├── variant_sequence: ["dark"] * 6 + ["light"] * 6
    ├── style_pool: [{background_color: "#FFF"}, ...]
    └── slots: [
            Slot(name="header.text", source="text.header"),
            Slot(name="main_text.text", source="text.main_text"),
            Slot(name="image.image", source="image.cluster"),
            Slot(name="bg.background_color", source="style.background_color"),
        ]
```

### Data Flow

```
Worker Handler
    │
    ├── Topic (universal: name, event, discount, page_type, url)
    ├── inputs (type-specific: product_image_urls, include_header)
    └── options (runtime settings)
    │
    ▼
CreativeEngine.generate(topic, config, inputs, options, count=12)
    │
    ├── _resolve_sources() → runs each generator once, caches results
    │       text.header    → ["TOPIC NAME"] (broadcasts to all 12)
    │       text.main_text → ["line1", "line2", ...] (12 variations)
    │       image.cluster  → ["https://..."] (1 image, broadcasts)
    │       style.*        → values from config.style_pool
    │
    └── _build_creatives() → for each of 12 creatives:
            1. Select variant (dark/light) from variant_sequence
            2. Build layers dict using modulo indexing
            3. Submit to Placid via submit_generic_job()
            4. Poll for result → Creative(creative_url)
    │
    ▼
Upload to Monday.com (4 rows × 3 images each)
```

### Generators

Generators are independent modules registered via decorator:

```python
@register("text.header")
class HeaderGenerator(Generator):
    def generate(self, context: GenerationContext) -> list[str]:
        return [context.topic.name.upper()] * context.count

@register("image.cluster")
class ClusterImageGenerator(ImageGenerator):
    INPUTS = [Field(name="product_image_urls", type="list", required=True)]
    def _generate_raw(self, context) -> bytes:
        # Download products → Gemini cluster → bytes
```

Generators declare `INPUTS` (user-provided fields) which the frontend serializer collects automatically.

### Adding a New Creative Type

1. Create config in `src/creative_types/new_type.py`
2. Register in `src/creative_types/__init__.py`
3. Create generators if needed (or reuse existing ones)

No handler changes required - the engine routes based on config.

### Key Concepts

- **Slot**: Maps a Placid layer (e.g., `header.text`) to a source (`text.header` or `style.background_color`)
- **Modulo indexing**: `results[i % len(results)]` - 1 result broadcasts to all, 12 results map 1:1
- **style_pool**: Pre-defined values for `style.*` sources (colors, fonts)
- **variant_sequence**: Which Placid template to use for each creative index

### Infrastructure

Two Lambdas (both use same Docker image):
- **enqueue** - HTTP endpoint: GET /config (returns field definitions), POST / (queues to SQS)
- **worker** - Processes SQS messages, generates creatives

External services: OpenAI (text), Gemini (images), remove.bg (background removal), Placid (rendering), Monday.com (output)
