# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Marketing creative generation system for Amazon affiliate campaigns. Takes a topic (e.g., "Girls Bracelet Making Kit") and generates 12 creatives (text + styled images) organized into 4 campaigns, then uploads to Monday.com.

## Commands

```bash
# Run locally
python -m src.handlers.worker "<topic>" "<event>" "<discount>" "<page_type>"
python -m src.handlers.worker "Girls Bracelet Making Kit" "Black Friday" "up to 50%" category

# Deploy
docker build --provenance=false --platform linux/amd64 -t ai-tools .
docker tag ai-tools:latest <account>.dkr.ecr.us-east-1.amazonaws.com/campaigns-generator:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/campaigns-generator:latest

# Infrastructure
cd terraform && terraform apply
```

## Architecture

### Entity Hierarchy

- **Topic** → 4 Campaigns → 3 Creatives each (12 total)
- **Campaign** = batch that becomes one Monday.com row
- **Creative** = atomic unit: text + image_url + styling

### Service Design Pattern

**Every entity service can be both a pipeline step AND an orchestrator. Leaf providers (TextService, styles) enable any service to become an orchestrator.**

```
TopicService.generate(topic)           # orchestrator
    ├── TextService.generate_for_topic()   # leaf (LLM, 3-stage pipeline)
    ├── get_styles_for_count()             # leaf (style pool)
    ├── CreativeService.generate_batch()   # step (Placid images)
    └── _group_into_campaigns()
```

Leaves:
- **TextService** - generates texts via LLM prompts
- **styles.py** - provides styles from predefined pool (`get_styles_for_count()`)

No service is inherently "top-level" - it depends on what's calling it. Future services (CampaignService, BatchService) can make current orchestrators into steps.

### Text Generation Pipeline

TextService runs 3 LLM stages, each with its own prompt in `src/prompts/`:
1. `creator.txt` - generates initial 12 variations
2. `editor.txt` - refines the variations
3. `final_toucher.txt` - final polish

Each stage outputs TSV format (index + text), parsed and passed to the next stage.

### Infrastructure

Two Lambdas:
- **enqueue** - HTTP endpoint, queues to SQS
- **worker** - Docker image, processes SQS messages, generates creatives

External services: OpenAI (text), Placid (images), Monday.com (output)
