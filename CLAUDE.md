# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Marketing creative generation system for affiliate campaigns. Takes a topic (e.g., "Girls Bracelet Making Kit") and generates 12 creatives (text + styled images) organized into 4 campaigns, then uploads to Monday.com.

## Commands

```bash
# Run locally
python -m src.handlers.worker "<topic>" "<event>" "<discount>" "<page_type>" [creative_type] [inputs_json]

# product_cluster - combines products into single image
python -m src.handlers.worker "Girls Bracelet Kit" "Black Friday" "50%" category product_cluster '{"product_image_urls": ["url1", "url2", "url3"]}'

# product_grid - 8 individual product images in grid layout
python -m src.handlers.worker "Girls Bracelet Kit" "Black Friday" "50%" category product_grid '{"product_image_urls": ["url1", "url2", "url3", "url4", "url5", "url6", "url7", "url8"]}'

# Deploy (builds, pushes to ECR, updates both lambdas)
./deploy.sh

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
    def _generate_raw(self, context) -> bytes:
        # Download products → Gemini cluster → bytes
```

Generator inputs are declared in `src/generators/inputs.py` (kept separate to avoid heavy imports in enqueue Lambda).

### Adding a New Creative Type

#### Questions to Ask User

**1. Placid Template Info:**
- What is the Placid template UUID(s)?
- What are all the layer names? (e.g., `header`, `main_text`, `image`, `bg-left`)
- For each layer, what type? (`text`, `image`, `background_color`)
- For image layers: what dimensions/aspect ratio? (e.g., 16:9, 1:1, 270x270)

**2. Image Generation:**
- How many product images as input?
- Combined into one (cluster) or separate (grid)?
- What aspect ratio for generated images?
  - `image.cluster` default: **16:9**
  - `image.product` default: **1:1**
- Override via `generator_config={"aspect_ratio": "16:9"}` on slot

**3. Color/Style Variants:**
- How many color variants? (e.g., 4 variants × 3 = 12 creatives)
- For each variant, what are the hex colors for each background layer?
- Any text color changes? (usually handled by Placid template variants)

**4. Template Variants:**
- Single template or multiple? (e.g., dark text vs white text)
- If multiple, what's the sequence? (e.g., 6 dark + 6 light)

**5. Text:**
- Has header? Optional or required?
- Has main_text? (usually yes, uses `text.main_text`)

#### Implementation Steps

1. **Create config** in `src/creative_types/new_type.py`:
   ```python
   CreativeTypeConfig(
       name="new_type",
       display_name="New Type",
       variants={"default": "PLACID_UUID"},
       variant_sequence=["default"] * 12,
       style_pool=[...],  # 12 entries for colors
       slots=[
           Slot(name="layer.property", source="generator.name"),
           # For images with non-default aspect ratio:
           Slot(name="image.image", source="image.cluster",
                generator_config={"aspect_ratio": "16:9"}),
       ],
   )
   ```

2. **Register** in `src/creative_types/__init__.py`

3. **Add inputs** to `src/generators/inputs.py` if using new generator

4. **Create generator** if needed (or reuse `image.cluster`, `image.product`, etc.)

#### Generator Aspect Ratios

| Generator | Default | Override via |
|-----------|---------|--------------|
| `image.cluster` | 16:9 | `generator_config={"aspect_ratio": "X:Y"}` |
| `image.product` | 1:1 | `generator_config={"aspect_ratio": "X:Y"}` |

#### Slot-to-Source Mapping

- **Text layers**: `source="text.header"` or `source="text.main_text"`
- **Image layers**: `source="image.cluster"` (combined) or `source="image.product"` (individual)
- **Background colors**: `source="style.field_name"` (from style_pool)

No handler changes required - the engine routes based on config.

### Key Concepts

- **Slot**: Maps a Placid layer (e.g., `header.text`) to a source (`text.header` or `style.background_color`)
- **Smart slot indexing**: `results[(creative_idx * num_slots + slot_idx) % len(results)]`
  - Distributes values across slots first, then creatives
  - 1 result → broadcasts to all slots/creatives
  - N results matching N slots → each slot gets unique value, all creatives same
  - N×M results → each slot in each creative gets unique value
- **style_pool**: Pre-defined values for `style.*` sources (colors, fonts)
- **variant_sequence**: Which Placid template to use for each creative index

### Available Generators

| Generator | Source | Returns | Use Case |
|-----------|--------|---------|----------|
| `text.header` | `text.header` | 1 or N strings | Header text (broadcasts) |
| `text.main_text` | `text.main_text` | 12 strings | Main ad copy (1 per creative) |
| `image.cluster` | `image.cluster` | 1 URL | Combined product cluster image |
| `image.product` | `image.product` | N URLs | Individual product images (1 per slot) |

### Creative Types

| Type | Description | Image Source |
|------|-------------|--------------|
| `product_cluster` | Single combined product image | `image.cluster` (1 image) |
| `product_grid` | 8 individual product images in grid | `image.product` (8 images) |

### Infrastructure

Two Lambdas (both use same Docker image):
- **enqueue** - HTTP endpoint: GET /config (returns field definitions), POST / (queues to SQS)
- **worker** - Processes SQS messages, generates creatives

Frontend hosted on Cloudflare Pages (`creatives-dealogic.pages.dev`), protected by Cloudflare Access.

External services: OpenAI (text), Gemini (images), remove.bg (background removal), Placid (rendering), Monday.com (output)
