# Creative Engine Refactor Plan (Generators Architecture)

## Overview

### The Problem

Current architecture couples creative types with generation logic:

```
TopicService.generate()                    → standard path
TopicService.generate_product_cluster()    → product cluster path
TextService.generate_for_topic()           → standard
TextService.generate_for_product_cluster() → product cluster
CreativeService.generate_batch()           → standard
CreativeService.generate_product_cluster_batch() → product cluster
```

Adding a new creative type means adding parallel methods to 4+ files.

### The Solution

**Generators** are independent modules that know HOW to create things.
**Configs** are thin wiring that says WHAT generator to use for WHAT slot.
**Engine** returns `list[Creative]`, caller decides how to group.

```
Generators (independent, reusable, evolvable):
├── text.header             → topic name uppercased
├── text.main_text          → LLM-generated marketing text
├── image.cluster           → Gemini cluster images + post-processing
└── ... future generators

Configs (thin, just wiring):
└── product_cluster         → variants: {dark: UUID, light: UUID}
                            → variant_sequence: ["dark", "light"] * 6
                            → slots: header.text ← text.header
                                     main_text.text ← text.main_text
                                     image.image ← image.cluster

Engine:
└── generate(topic, config, inputs, options, count) → list[Creative]
    Creative = {creative_type, variant, layers, creative_url}
```

---

## Key Design Decisions

### 1. Separate `src/v2/` Folder

All new code lives in `src/v2/`. Old code in `src/services/`, `src/models/` stays untouched until migration is complete.

### 2. Fresh Models (No Baggage)

New Topic, Campaign, Creative models in v2 - no imports from old `src/models/`.

**Old Topic** (has everything):
```python
Topic(name, event, discount, page_type, url,
      product_urls, creative_type, product_image_urls,  # type-specific
      main_lines, is_people_mode, include_header,       # type-specific
      campaigns)                                         # output
```

**New Topic** (universal only):
```python
Topic(name, event, discount, page_type, url)
```

### 3. Engine Returns `list[Creative]`

Engine just generates creatives. Caller decides if/how to group into campaigns.

```python
# Engine
def generate(topic, config, inputs, options, count) -> list[Creative]

# Caller decides grouping
creatives = engine.generate(..., count=12)
campaigns = group_into_campaigns(creatives, size=3)  # Optional
```

### 4. Flexible Count

`count` is passed by caller, not hardcoded. Could be 12, 10, 6, etc.

---

## Data Flow Comparison

### Old Flow

```
┌─────────────────────────────────────────────────────────────┐
│                         WORKER                              │
├─────────────────────────────────────────────────────────────┤
│  1. Build OLD Topic (has EVERYTHING)                        │
│     Topic(name, event, ..., product_image_urls,             │
│           is_people_mode, campaigns=[])                     │
│  2. Call TopicService.generate_product_cluster(topic)       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                     TOPIC SERVICE                           │
├─────────────────────────────────────────────────────────────┤
│  1. ProductImageService → cluster_url                       │
│  2. TextService.generate_for_product_cluster() → texts      │
│  3. get_product_cluster_styles_for_count() → styles         │
│  4. CreativeService.generate_product_cluster_batch()        │
│     → list[Creative]  ← CREATED HERE                        │
│  5. _group_into_campaigns() → list[Campaign] ← CREATED HERE │
│  6. topic.campaigns = campaigns (MUTATES Topic)             │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                         WORKER                              │
├─────────────────────────────────────────────────────────────┤
│  3. topic.campaigns → Upload to Monday                      │
└─────────────────────────────────────────────────────────────┘
```

### New Flow (v2)

```
┌─────────────────────────────────────────────────────────────┐
│                         WORKER                              │
├─────────────────────────────────────────────────────────────┤
│  1. Load config                                             │
│     config = get_creative_type("product_cluster")           │
│                                                             │
│  2. Build v2.Topic (UNIVERSAL ONLY)                         │
│     Topic(name, event, discount, page_type, url)            │
│                                                             │
│  3. Extract inputs & options from request                   │
│     inputs = {"product_image_urls": [...]}                  │
│     options = {"is_people_mode": True, "include_header": True}
│                                                             │
│  4. Call engine.generate(topic, config, inputs, options, 12)│
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                         ENGINE                              │
├─────────────────────────────────────────────────────────────┤
│  1. _resolve_sources() - run generators once each:          │
│     - "text.header" → HeaderGenerator.generate() → list     │
│     - "text.main_text" → MainTextGenerator.generate() → list│
│     - "image.cluster" → ClusterImageGenerator.generate()    │
│                                                             │
│  2. _build_creatives() - for each creative i:               │
│     a. Get variant: config.variant_sequence[i]              │
│     b. Get UUID: config.variants[variant]                   │
│     c. _build_layers() with modulo indexing                 │
│     d. submit_generic_job(uuid, layers)                     │
│                                                             │
│  3. Poll jobs → Creative(creative_type, variant, layers,    │
│                          creative_url)                      │
│                                                             │
│  4. Return list[Creative] (NO CAMPAIGN GROUPING)            │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                         WORKER                              │
├─────────────────────────────────────────────────────────────┤
│  5. CALLER DECIDES: group_into_campaigns(creatives, size=3) │
│     → list[Campaign] ← CREATED HERE (optional)              │
│                                                             │
│  6. Upload to Monday                                        │
└─────────────────────────────────────────────────────────────┘
```

---

## File Structure

```
src/
├── v2/                              # ALL NEW CODE HERE
│   ├── __init__.py
│   │
│   ├── models/                      # Fresh models (no old imports)
│   │   ├── __init__.py
│   │   ├── topic.py                 # Simplified Topic
│   │   ├── campaign.py              # Campaign + group_into_campaigns()
│   │   ├── creative.py              # Creative output
│   │   ├── slot.py                  # Slot, SlotUI
│   │   ├── config.py                # CreativeTypeConfig, InputField
│   │   └── context.py               # GenerationContext
│   │
│   ├── generators/                  # Independent generation modules
│   │   ├── __init__.py              # Registry + auto-loading
│   │   ├── base.py                  # Generator base class
│   │   ├── text/
│   │   │   ├── __init__.py
│   │   │   ├── header.py            # text/header - topic name uppercased
│   │   │   └── main_text.py         # text/main_text - LLM-generated
│   │   └── image/
│   │       ├── __init__.py
│   │       ├── base.py              # ImageGenerator base (remove.bg, crop, upload)
│   │       └── cluster.py           # image/cluster - Gemini product clusters
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   └── types/
│   │       ├── __init__.py          # CREATIVE_TYPES registry
│   │       └── product_cluster.py   # product_cluster config (templates, style_pool, slots)
│   │
│   ├── prompts/
│   │   └── main_text.txt            # Main text generation prompt
│   │
│   └── engine/                      # Phase 5
│       ├── __init__.py
│       └── engine.py                # CreativeEngine
│
├── models/                          # OLD - untouched until migration
├── services/                        # OLD - untouched until migration
├── handlers/                        # OLD - untouched until migration
├── clients/                         # Shared - GeminiClient, RemoveBgClient, etc.
└── prompts/                         # OLD prompts - v2 has its own
```

---

## Phase 1: Foundation

Create the foundational models and structures.

### Files to Create

#### 1. `src/v2/models/topic.py`

```python
"""Simplified Topic - universal fields only."""

from dataclasses import dataclass


@dataclass
class Topic:
    """Universal fields for all creative types."""
    name: str
    event: str
    discount: str
    page_type: str
    url: str = ""
```

#### 2. `src/v2/models/campaign.py`

```python
"""Campaign - optional grouping utility."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .creative import Creative


@dataclass
class Campaign:
    """A group of creatives. Optional - caller decides if/how to group."""
    creatives: list["Creative"] = field(default_factory=list)
    monday_item_id: str | None = None
    # Future: id, topic_id, created_at, metadata


def group_into_campaigns(creatives: list["Creative"], size: int = 3) -> list[Campaign]:
    """
    Utility to group creatives into campaigns.

    Caller decides if/when to use this.
    Engine does NOT call this - it just returns creatives.
    """
    return [
        Campaign(creatives=creatives[i:i + size])
        for i in range(0, len(creatives), size)
    ]
```

#### 3. `src/v2/models/creative.py`

```python
"""Creative output model - generic, DB-friendly, works for any creative type."""

from dataclasses import dataclass
from typing import Any


@dataclass
class Creative:
    """Generic creative - stores layers dict for any creative type."""
    creative_type: str       # "product_cluster", "banner", etc.
    variant: str             # "dark", "light", "default"
    layers: dict[str, Any]   # Inputs sent to Placid (layer_name -> {prop: value})
    creative_url: str        # Final rendered output from Placid
```

**Note**: Updated in Phase 5 to be generic. `layers` stores what we sent to Placid,
`creative_url` is the final rendered creative. DB-friendly for future optimization.

#### 4. `src/v2/models/slot.py`

```python
"""Slot definitions for Placid templates."""

from dataclasses import dataclass
from typing import Any


@dataclass
class SlotUI:
    """UI behavior for a slot."""
    toggleable: bool = False
    toggle_label: str | None = None   # UI display text
    toggle_default: bool = True
    option_name: str | None = None    # Key in options dict (e.g., "include_header")


@dataclass
class Slot:
    """A slot in a Placid template that needs to be filled."""
    name: str                    # Placid layer name (e.g., "header.text", "image.image")
    source: str                  # "text.header", "image.cluster" (dot notation)
    ui: SlotUI | None = None
    generator_config: dict[str, Any] | None = None  # Generator-specific settings
```

**Note**: Updated in Phase 5 - added `option_name` to SlotUI, sources use dot notation.

#### 5. `src/v2/models/config.py`

```python
"""Creative type configuration."""

from dataclasses import dataclass, field
from typing import Any

from .slot import Slot


@dataclass
class InputField:
    """User-provided input - validation handled by frontend/internal code."""
    name: str
    type: str                    # "text" | "url_list" | "number" | "select"
    label: str                   # UI display text
    required: bool = True


@dataclass
class CreativeTypeConfig:
    """Configuration for a creative type. CreativeType IS the template."""
    name: str                            # Template identifier
    display_name: str
    variants: dict[str, str]             # {"dark": UUID, "light": UUID} - physical Placid files
    variant_sequence: list[str] | None   # ["dark", "light"] * 6, or None for single variant
    slots: list[Slot]
    inputs: list[InputField] = field(default_factory=list)
```

**Note**: Updated in Phase 5 - `templates` → `variants`, `style_pool` → `variant_sequence`.

#### 6. `src/v2/models/context.py`

```python
"""Generation context passed to generators."""

from dataclasses import dataclass
from typing import Any

from .topic import Topic


@dataclass
class GenerationContext:
    """Context passed to generators."""
    topic: Topic
    inputs: dict[str, Any]       # Type-specific inputs (e.g., product_image_urls)
    options: dict[str, Any]      # Runtime options (e.g., is_people_mode)
    count: int                   # How many creatives (flexible, not hardcoded)
```

#### 7. `src/v2/models/__init__.py`

```python
"""V2 Models."""

from .topic import Topic
from .campaign import Campaign, group_into_campaigns
from .creative import Creative
from .slot import Slot, SlotUI
from .config import CreativeTypeConfig, InputField
from .context import GenerationContext

__all__ = [
    "Topic",
    "Campaign",
    "group_into_campaigns",
    "Creative",
    "Slot",
    "SlotUI",
    "CreativeTypeConfig",
    "InputField",
    "GenerationContext",
]
```

#### 8. `src/v2/generators/base.py`

```python
"""Generator base class and option definition."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from ..models.context import GenerationContext


@dataclass
class GeneratorOption:
    """Simplified - just toggles for now (is_people_mode, include_header)."""
    name: str
    type: str       # "toggle" for now
    label: str      # UI display text
    default: Any


class Generator(ABC):
    """Base class for generators."""

    OPTIONS: list[GeneratorOption] = []

    @abstractmethod
    def generate(self, context: GenerationContext) -> list[Any]:
        """Generate values for all creatives."""
        pass

    @classmethod
    def get_options(cls) -> list[GeneratorOption]:
        """Get options this generator accepts."""
        return cls.OPTIONS
```

#### 9. `src/v2/generators/__init__.py`

```python
"""Generator registry."""

from typing import Type
from .base import Generator, GeneratorOption

_GENERATORS: dict[str, Type[Generator]] = {}


def _ensure_generators_loaded():
    """Import all generator modules to trigger registration."""
    from . import text  # noqa: F401
    from . import image  # noqa: F401


def register(path: str):
    """Decorator to register a generator."""
    def decorator(cls):
        _GENERATORS[path] = cls
        return cls
    return decorator


def get_generator_class(path: str) -> Type[Generator]:
    """Get generator class by path."""
    _ensure_generators_loaded()
    if path not in _GENERATORS:
        raise ValueError(f"Unknown generator: {path}")
    return _GENERATORS[path]


def list_generators() -> list[str]:
    """List all registered generators."""
    _ensure_generators_loaded()
    return list(_GENERATORS.keys())


__all__ = [
    "Generator",
    "GeneratorOption",
    "register",
    "get_generator_class",
    "list_generators",
]
```

#### 10. `src/v2/config/types/__init__.py`

```python
"""Creative types registry."""

from ...models.config import CreativeTypeConfig

CREATIVE_TYPES: dict[str, CreativeTypeConfig] = {}


def get_creative_type(name: str) -> CreativeTypeConfig:
    """Get creative type config by name."""
    if name not in CREATIVE_TYPES:
        raise ValueError(f"Unknown creative type: {name}")
    return CREATIVE_TYPES[name]


def list_creative_types() -> list[str]:
    """List all registered creative types."""
    return list(CREATIVE_TYPES.keys())


__all__ = [
    "CREATIVE_TYPES",
    "get_creative_type",
    "list_creative_types",
]
```

#### 11. `src/v2/__init__.py`

```python
"""V2 Creative Engine."""

from . import models
from . import generators
from . import config

__all__ = ["models", "generators", "config"]
```

---

## Validation (Phase 1)

After creating all files, run:

```python
# test_phase1.py
from src.v2.models import (
    Topic, Campaign, Creative, group_into_campaigns,
    Slot, SlotUI, CreativeTypeConfig, InputField, GenerationContext
)
from src.v2.generators import Generator, GeneratorOption
from src.v2.config.types import CREATIVE_TYPES

# Verify Topic is simplified
topic = Topic(name="Test", event="Black Friday", discount="50%", page_type="category", url="")
assert hasattr(topic, 'name')
assert not hasattr(topic, 'product_image_urls')  # Type-specific removed
assert not hasattr(topic, 'campaigns')           # Output removed

# Verify group_into_campaigns works
creatives = [
    Creative(
        main_text=f"text{i}",
        background_color="#000",
        main_text_color="#FFF",
        font="Arial",
        image_url=f"url{i}"
    )
    for i in range(12)
]
campaigns = group_into_campaigns(creatives, size=3)
assert len(campaigns) == 4
assert len(campaigns[0].creatives) == 3

print("Phase 1 complete - all imports and basic tests pass")
```

---

## V2 Separation Principle

**v2 is completely self-contained.** Regular `src/` continues working unchanged - team can keep shipping features.

**What v2 has:**
- `src/v2/models/` - fresh models (no imports from old `src/models/`)
- `src/v2/generators/` - generator classes
- `src/v2/prompts/` - v2's own prompts (doesn't touch `src/prompts/`)
- `src/v2/config/` - creative type configs

**Shared utilities (imported from regular src):**
- `src/clients/llm.py` - LLMClient (pure utility, no business logic)

When v2 is complete and tested, we switch over and delete old code.

---

## Migration Phases Summary

| Phase | Goal | Key Files |
|-------|------|-----------|
| 1. Foundation ✅ | Models and registries | `src/v2/models/`, `src/v2/generators/base.py` |
| 2. Text Generator ✅ | Main text generation | `src/v2/generators/text/main_text.py`, `src/v2/prompts/main_text.txt` |
| 3. Image Generator ✅ | Extract image generation | `src/v2/generators/image/cluster.py` |
| 4. Config ✅ | Create product_cluster config | `src/v2/config/types/product_cluster.py` |
| 5. Engine ✅ | Wire everything together | `src/v2/engine/engine.py` |
| 6. Integration ✅ | v2 API endpoints | `src/handlers/worker.py` (v2 routes) |
| 7. Frontend & Style Pool ✅ | Config-driven UI + style_pool | `frontend/`, `src/v2/engine/engine.py` |
| 8. Cleanup | Remove old code | Delete `src/services/`, old models |

---

## Phase 2: Main Text Generator ✅

### Files Created

1. **`src/v2/prompts/main_text.txt`** - single prompt (replaces 3-stage pipeline)
2. **`src/v2/generators/text/__init__.py`** - exports MainTextGenerator
3. **`src/v2/generators/text/main_text.py`** - MainTextGenerator class

### Key Decisions

- **Header** = always `topic.name.upper()` (not LLM-generated)
- **Main Text** = LLM-generated via single prompt
- **Override** = if `main_lines` provided, skip LLM
- **Prompt** = simplified, just topic name (EVENT/DISCOUNT rules removed for now)

---

## Phase 3: Image Generator ✅

### Files Created

1. **`src/v2/generators/image/__init__.py`** - exports ImageGenerator, ClusterImageGenerator
2. **`src/v2/generators/image/base.py`** - ImageGenerator base class
3. **`src/v2/generators/image/cluster.py`** - ClusterImageGenerator

### Architecture

- **ImageGenerator** base class with shared post-processing (remove.bg, crop, upload)
- **ClusterImageGenerator** extends base, adds product cluster logic (download, Gemini)
- Template method pattern: `generate()` → `_generate_raw()` → `_post_process()` → `_upload()`

### Key Decisions

- Generators return `list[str]` (single-element list with URL, engine broadcasts)
- `aspect_ratio` comes from `slot.generator_config` (resolved in Phase 4)
- Post-processing options (`remove_bg`, `crop`) read from `context.options`, defaults True
- Uses existing clients directly: `GeminiClient`, `RemoveBgClient`, `CreativeClient`

---

## Phase 4: Config ✅

### Key Concepts

**Slots = Structure** (what properties, where values come from)
**Style Pool = Data** (values for style_pool-sourced slots + template selection)
**Templates = Just UUIDs**

```python
# ONE slot defines the mapping
Slot(name="bg.background_color", source="style_pool", field="background_color")

# Style pool has VALUES (one per creative)
style_pool = [{"background_color": "#FFF"}, {"background_color": "#000"}, ...]
```

### Files Created/Updated

1. **`src/v2/generators/text/header.py`** - HeaderGenerator (topic name uppercased)
2. **`src/v2/generators/text/__init__.py`** - exports HeaderGenerator
3. **`src/v2/generators/text/main_text.py`** - updated to return `list[str]` (not tuples)
4. **`src/v2/models/slot.py`** - added `generator_config` field
5. **`src/v2/models/config.py`** - added `templates`, changed `style_pool` to list
6. **`src/v2/config/types/product_cluster.py`** - main config
7. **`src/v2/config/types/__init__.py`** - register product_cluster config

### Key Decisions

- **Separate HeaderGenerator** - returns `list[str]` (topic name uppercased)
- **MainTextGenerator simplified** - returns `list[str]` (main texts only, no header)
- **Slot.generator_config** - generator-specific settings (e.g., aspect_ratio)
- **Product cluster uses 2 templates** (dark/light) with hardcoded styles (no style_pool slots needed)
- **Source naming**: `source="style_pool"` for style-sourced slots, generator paths for generators

### Product Cluster Config

```python
CreativeTypeConfig(
    name="product_cluster",
    variants={"dark": DARK_UUID, "light": LIGHT_UUID},
    variant_sequence=["dark", "light"] * 6,  # 12 alternating
    slots=[
        Slot(
            name="header.text",
            source="text.header",
            ui=SlotUI(toggleable=True, toggle_label="Include Header",
                      toggle_default=True, option_name="include_header"),
        ),
        Slot(name="main_text.text", source="text.main_text"),
        Slot(name="image.image", source="image.cluster", generator_config={"aspect_ratio": "16:9"}),
    ],
)
```

---

## Phase 5: Engine ✅

### Goal

Wire everything together: config → generators → Placid → creatives.

### Files Created/Updated

| File | Action |
|------|--------|
| `src/v2/engine/__init__.py` | Created - exports CreativeEngine |
| `src/v2/engine/engine.py` | Created - main engine class |
| `src/clients/creative.py` | Updated - added `submit_generic_job()` |
| `src/v2/models/slot.py` | Updated - added `option_name` to SlotUI |
| `src/v2/models/config.py` | Updated - `variants` + `variant_sequence` |
| `src/v2/models/creative.py` | Updated - generic Creative with layers dict |
| `src/v2/config/types/product_cluster.py` | Updated - dot notation + variants |
| `src/v2/generators/text/header.py` | Updated - `@register("text.header")` |
| `src/v2/generators/text/main_text.py` | Updated - `@register("text.main_text")` |
| `src/v2/generators/image/cluster.py` | Updated - `@register("image.cluster")` |

### Key Design Decisions

#### 1. CreativeType = Template

The creative type IS the template. Variants are color themes (physically different Placid files).

```python
CreativeTypeConfig(
    name="product_cluster",              # THIS is the template
    variants={"dark": UUID1, "light": UUID2},  # physical Placid files
    variant_sequence=["dark", "light"] * 6,    # which variant per creative
)

# Single variant case:
CreativeTypeConfig(
    name="banner",
    variants={"default": UUID},
    variant_sequence=None,  # uses "default" for all
)
```

#### 2. Generic Creative (DB-Friendly)

Creative stores `layers` dict + `creative_url`. Works for any creative type.

```python
@dataclass
class Creative:
    creative_type: str       # "product_cluster", "banner", etc.
    variant: str             # "dark", "light", "default"
    layers: dict[str, Any]   # inputs sent to Placid
    creative_url: str        # final rendered output from Placid
```

- `layers` = what we send TO Placid (inputs)
- `creative_url` = what Placid RETURNS (the complete rendered creative)

#### 3. Uniform Sources (Dot Notation)

All slot sources use dot notation (`text.header`, `image.cluster`).

```python
slots=[
    Slot(name="header.text", source="text.header", ...),
    Slot(name="main_text.text", source="text.main_text"),
    Slot(name="image.image", source="image.cluster", ...),
]
```

#### 4. Explicit Client Injection

Engine receives individual clients in constructor:

```python
class CreativeEngine:
    def __init__(
        self,
        llm: LLMClient,
        gemini: GeminiClient,
        removebg: RemoveBgClient,
        creative: CreativeClient,
    ):
```

#### 5. Modulo Indexing

`results[i % len(results)]` cycles through any number of generator results:
- 1 result → broadcasts to all creatives
- 2 results → alternates
- 12 results → 1:1 mapping

#### 6. Toggleable Slots with Explicit option_name

```python
Slot(
    name="header.text",
    source="text.header",
    ui=SlotUI(
        toggleable=True,
        toggle_label="Include Header",
        toggle_default=True,
        option_name="include_header",  # explicit key in options dict
    ),
)
```

#### 7. Submit-Then-Poll

Submit all Placid jobs first (parallel processing on Placid side), then poll for results.

### Engine Implementation

```python
class CreativeEngine:
    def generate(self, topic, config, inputs, options, count=12) -> list[Creative]:
        # 1. Resolve all sources (generators)
        source_results = self._resolve_sources(topic, config, inputs, options, count)

        # 2. Build and submit Placid jobs
        creatives = self._build_creatives(config, source_results, options, count)

        return creatives

    def _resolve_sources(self, ...) -> dict[str, list[Any]]:
        # Run each unique generator once, cache results
        for source in generator_sources:
            generator = self._create_generator(source)
            results[source] = generator.generate(context)
        return results

    def _build_creatives(self, ...) -> list[Creative]:
        for i in range(count):
            variant = config.variant_sequence[i] if config.variant_sequence else "default"
            layers = self._build_layers(config, source_results, options, i)
            job_id = self.creative.submit_generic_job(variant_uuid, layers)

        # Poll and build Creative objects
        for job_id, layers, variant in job_ids:
            creative_url = self._poll_job(job_id)
            creatives.append(Creative(
                creative_type=config.name,
                variant=variant,
                layers=layers,
                creative_url=creative_url,
            ))
        return creatives

    def _build_layers(self, ...) -> dict[str, dict[str, Any]]:
        # Uniform value lookup with modulo indexing
        for slot in config.slots:
            if slot.ui and slot.ui.toggleable:
                if not options.get(slot.ui.option_name, slot.ui.toggle_default):
                    continue  # Skip toggled-off slot

            results = source_results[slot.source]
            value = results[index % len(results)]

            layer_name, prop_name = slot.name.split(".")
            layers[layer_name][prop_name] = value
        return layers
```

### Validation

```python
from src.v2.engine import CreativeEngine
from src.v2.config.types import get_creative_type
from src.v2.models import Topic

# Setup
engine = CreativeEngine(
    llm=llm_client,
    gemini=gemini_client,
    removebg=removebg_client,
    creative=creative_client,
)

config = get_creative_type("product_cluster")
topic = Topic(name="Girls Bracelet Kit", event="Black Friday", discount="50%", page_type="category")
inputs = {"product_image_urls": ["url1", "url2", "url3"]}
options = {"is_people_mode": False, "include_header": True}

creatives = engine.generate(topic, config, inputs, options, count=12)

assert len(creatives) == 12
assert all(c.creative_url for c in creatives)
assert creatives[0].creative_type == "product_cluster"
assert creatives[0].variant in ["dark", "light"]
```

### Open Questions (Future)

**1. style.* sources**: When we need style values (colors, fonts) as slot sources, add `style_pool: list[dict] | None` to config and pre-compute `style.*` sources in `_resolve_sources`. Not needed yet.

**2. Client naming and injection is messy**:

Current reality:
- `LLMClient` → OpenAI → **text** generation
- `GeminiClient` → Google Gemini → **image** generation

Problems:
- "LLM" is generic but it's OpenAI-specific and only for text
- "Gemini" is a provider name, but Gemini can do both text AND image (we only use it for image)
- The name doesn't tell you what it's FOR (text vs image)
- Engine hardcodes which clients go to which generator type:
```python
if source.startswith("text."):
    return generator_class(llm=self.llm)
elif source.startswith("image."):
    return generator_class(gemini=self.gemini, ...)
```

Consider:
- Rename by PURPOSE: `TextClient`, `ImageGenerationClient`
- Or by PROVIDER consistently: `OpenAIClient`, `GeminiClient`
- Generators declare what clients they need
- Registry-based client injection

---

## Key Differences from Current System

| Aspect | Current | V2 |
|--------|---------|-----|
| Topic | Has everything | Universal only |
| Type-specific data | In Topic | In `inputs` dict |
| Toggles/options | In Topic | In `options` dict |
| Routing | `if creative_type == ...` | Config lookup |
| Text generation | TextService methods | `text.header`, `text.main_text` generators |
| Image generation | ProductImageService | `image.cluster` generator |
| Output | Topic.campaigns (mutates) | Returns `list[Creative]` |
| Creative model | Type-specific fields | Generic: `layers` dict + `creative_url` |
| Template selection | `templates` + `style_pool` | `variants` + `variant_sequence` |
| Campaign grouping | Inside TopicService | Caller utility |
| Count | Hardcoded 12 | Flexible parameter |
| Adding new type | Touch 4+ files | Add config + maybe generator |

---

## Phase 6: Integration ✅

### Goal

Wire v2 CreativeEngine into worker.py for safe testing alongside v1.

### Routing Strategy

| creative_type | Path | Notes |
|---------------|------|-------|
| `standard` | v1 | unchanged |
| `product_cluster` | v1 | unchanged |
| `product_cluster_v2` | **v2** | new, for testing |

Using `product_cluster_v2` allows safe A/B testing - both paths produce equivalent Monday.com output.

### Files Modified

| File | Changes |
|------|---------|
| `src/v2/config/types/__init__.py` | Register as `product_cluster_v2` (not `product_cluster`) |
| `src/handlers/worker.py` | Add v2 imports, routing, and handler functions |

### Implementation

#### 1. Early Routing in handler()

```python
# Route v2 creative types
creative_type = body.get("creative_type", "standard")
if creative_type in list_creative_types():
    return _handle_v2(body)

# v1 path continues below...
```

#### 2. v2 Handler Functions

```python
def _handle_v2(body: dict) -> dict:
    """Handle v2 creative type request."""
    # 1. Build v2 Topic (universal fields only)
    topic = TopicV2(name=..., event=..., discount=..., page_type=..., url=...)

    # 2. Get config
    config = get_creative_type(creative_type)

    # 3. Extract inputs and options (config-driven)
    inputs = _extract_inputs(body, config)
    options = _extract_options(body, config)

    # 4. Initialize clients & engine
    engine = CreativeEngine(llm=..., gemini=..., removebg=..., creative=...)

    # 5. Generate creatives
    creatives = engine.generate(topic, config, inputs, options, count=12)

    # 6. Upload to Monday
    return _upload_v2_creatives(topic, creatives)


def _extract_inputs(body: dict, config) -> dict:
    """Extract inputs defined by config from request body."""
    # Iterates config.inputs, validates required fields

def _extract_options(body: dict, config) -> dict:
    """Extract options (toggles, generator options) from request body."""
    # 1. Slot toggles (e.g., include_header from slot.ui.option_name)
    # 2. Generator options (e.g., is_people_mode from generator.OPTIONS)

def _upload_v2_creatives(topic, creatives) -> dict:
    """Upload v2 creatives to Monday, return response."""
    # Groups into campaigns of 3, uploads images, returns response
    # Note: No 'texts' in response - nobody consumes it
```

### Key Decisions

1. **Safe testing** - `product_cluster_v2` routes to v2, `product_cluster` stays v1
2. **Separate upload function** - `_upload_v2_creatives()` separate from v1 for clean deletion later
3. **No texts in response** - Investigation showed nobody consumes the `texts` field in Lambda response (SQS discards it)
4. **Config-driven extraction** - Inputs/options extracted based on config definitions, not hardcoded

### Testing

```bash
# v1 path (unchanged)
python -m src.handlers.worker "Girls Bracelet Kit" "Black Friday" "50%" category product_cluster '{"product_image_urls": ["url1", "url2", "url3"]}'

# v2 path (new)
python -m src.handlers.worker "Girls Bracelet Kit" "Black Friday" "50%" category product_cluster_v2 '{"product_image_urls": ["url1", "url2", "url3"]}'
```

Both should produce equivalent Monday.com output. Compare results to validate v2.

---

## Phase 7: Frontend & Style Pool ✅

### Goal

Config-driven UI that fetches field definitions from API and renders dynamic forms.

### Architecture

```
Frontend                    Backend
   │                          │
   │  GET /config             │
   │ ───────────────────────► │
   │                          │  serialize_all() collects:
   │                          │  - INPUTS from generators
   │                          │  - toggle fields from optional slots
   │  {product_cluster_v2:    │
   │    fields: [...]}        │
   │ ◄─────────────────────── │
   │                          │
   │  Render dynamic fields   │
   │  based on field.type     │
   │                          │
   │  POST / (submit)         │
   │ ───────────────────────► │  → SQS → Worker → Monday
```

### Files Created/Modified

| File | Changes |
|------|---------|
| `src/v2/api/serializers.py` | `serialize_all()` - collects fields from generators, creates toggle fields for optional slots |
| `src/v2/models/config.py` | Added `Field` and `Condition` dataclasses for generic UI primitives |
| `src/v2/generators/*.py` | Generators declare `INPUTS` (list of Field) |
| `src/handlers/enqueue.py` | Added `GET /config` route, fixed import to `from src.v2.api.serializers` |
| `frontend/app.js` | Generic field renderer - fetches config, renders fields by type |
| `frontend/index.html` | Base HTML with creative-type dropdown and dynamic-fields container |
| `frontend/styles.css` | Styles for all field types |

### Field Types

| Type | Renders As | Value Type |
|------|-----------|------------|
| `text` | Single-line input | string |
| `textarea` | Multi-line input | string[] (lines) |
| `list` | Add button + items list | string[] |
| `toggle` | Toggle switch | boolean |
| `select` | Dropdown | string |

### API Response Shape

```json
{
  "product_cluster_v2": {
    "displayName": "Product Cluster",
    "fields": [
      {"name": "is_people_mode", "type": "toggle", "label": "People Mode", "default": false},
      {"name": "include_header", "type": "toggle", "label": "Header", "default": true},
      {"name": "product_image_urls", "type": "list", "label": "Product Image URLs", "required": true},
      {"name": "main_lines", "type": "textarea", "label": "Main Text Lines", "required": false}
    ]
  }
}
```

### Infrastructure Changes

Significant infrastructure changes were made to support the frontend:

#### 1. Enqueue Lambda: Zip → Docker

Converted enqueue from zip-based to Docker-based deployment:

**Before:**
```hcl
resource "aws_lambda_function" "enqueue" {
  handler       = "handlers.enqueue.handler"
  runtime       = "python3.11"
  filename      = data.archive_file.enqueue.output_path
  # ... complex zip creation with archive_file
}
```

**After:**
```hcl
resource "aws_lambda_function" "enqueue" {
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.worker.repository_url}:latest"
  image_config {
    command = ["src.handlers.enqueue.handler"]
  }
  # ... shares same Docker image as worker
}
```

**Benefits:**
- Both lambdas use same Docker image (simpler deployment)
- No zip packaging complexity (`archive_file`, `null_resource` removed)
- Consistent import paths (`from src.v2...` works everywhere)

**Trade-off:**
- Heavier cold starts (~5-7s) due to loading all dependencies
- Increased timeout from 10s → 30s to accommodate

#### 2. Worker Memory Increase

```hcl
memory_size = 256  # Before: 93-97% usage, risk of OOM
memory_size = 512  # After: ~50% usage, faster image processing
```

#### 3. CORS Fix

Removed duplicate CORS header from handler (terraform's Lambda Function URL config already sets it):

```python
# Before: Double header "*, *" caused CORS error
"Access-Control-Allow-Origin": "*"  # REMOVED

# After: Only terraform sets CORS
```

### Background Color Fix (style_pool)

**Problem:** v2 creatives all had the same background color because:
1. v2 wasn't sending `bg.background_color` to Placid (v1 sends it dynamically)
2. v2 used alternating variant_sequence (`["dark", "light"] * 6`) instead of v1's 6+6 pattern

**Solution:** Added `style_pool` support to the engine.

**Files Modified:**

| File | Changes |
|------|---------|
| `src/v2/models/config.py` | Added `style_pool: list[dict[str, Any]] \| None` field to `CreativeTypeConfig` |
| `src/v2/engine/engine.py` | Added `_resolve_style_source()` method, modified `_resolve_sources()` to handle `style.*` sources |
| `src/v2/config/types/product_cluster.py` | Added `style_pool` with 12 background colors, added `bg.background_color` slot, changed `variant_sequence` to 6+6 |
| `src/handlers/worker.py` | Modified `_extract_inputs()` to skip `style.*` sources (they don't have generator classes) |

**Implementation:**

```python
# CreativeTypeConfig now has style_pool
style_pool: list[dict[str, Any]] | None = None

# product_cluster config
style_pool=[
    # Light backgrounds (for dark text template) - first 6
    {"background_color": "#FDEDD4"},
    {"background_color": "#D4D2D6"},
    ...
    # Dark backgrounds (for white text template) - last 6
    {"background_color": "#855E89"},
    {"background_color": "#559B82"},
    ...
],
variant_sequence=["dark"] * 6 + ["light"] * 6,  # 6+6 pattern (matching v1)
slots=[
    ...
    Slot(name="bg.background_color", source="style.background_color"),  # NEW
],

# Engine resolves style.* sources from style_pool
def _resolve_style_source(self, source: str, config) -> list[Any]:
    field = source.split(".", 1)[1]  # "style.background_color" → "background_color"
    return [style[field] for style in config.style_pool]
```

**Result:**
- Creatives 0-5: dark template + light backgrounds (#FDEDD4, #D4D2D6, #E8AAAC, #B5D7E6, #DBD4FD, #FDD4D4)
- Creatives 6-11: light template + dark backgrounds (#855E89, #559B82, #A69A87, #597A9A, #827171, #5B6E82)

### TODO: Audit Unused Abstractions

Check if these are actually needed:

- [ ] `Condition` class - defined in config.py but never instantiated
- [ ] `GeneratorOption` class - defined in base.py but never used

If not used by the 10 creative types, delete them.

### Testing

Full flow tested and working:
1. ✅ Frontend loads config from `/config` API
2. ✅ Dynamic fields render based on field types
3. ✅ Form submission sends to enqueue
4. ✅ SQS triggers worker
5. ✅ Worker processes via v2 engine
6. ✅ Creatives uploaded to Monday.com
7. ✅ Background colors working (12 unique colors, matching v1)

---

## Local Development Setup

Before Phase 8, set up local development to reduce reliance on production Lambda for testing.

### Option 1: Simple Flask Dev Server (Recommended)

Minimal setup - serves frontend and calls handlers directly without SQS.

**Create `dev_server.py`:**

```python
"""Local dev server - serves frontend and calls handlers directly."""

from flask import Flask, request, jsonify, send_from_directory
from src.v2.api.serializers import serialize_all
from src.handlers.worker import handler as worker_handler

app = Flask(__name__)

@app.route('/config')
def config():
    """Serve creative type configs (same as enqueue Lambda)."""
    return jsonify(serialize_all())

@app.route('/', methods=['POST'])
def enqueue():
    """Call worker directly (bypasses SQS)."""
    event = {"Records": [{"body": request.data.decode()}]}
    result = worker_handler(event, None)
    return jsonify(result)

@app.route('/')
def index():
    return send_from_directory('frontend', 'index.html')

@app.route('/<path:path>')
def frontend(path):
    return send_from_directory('frontend', path)

if __name__ == '__main__':
    app.run(port=3000, debug=True)
```

**Setup:**

```bash
pip install flask
python dev_server.py
# Open http://localhost:3000
```

**Pros:**
- ~20 lines of code
- No AWS emulation needed
- Fast iteration (debug=True auto-reloads)
- Same code paths as production (just skips SQS)

**Cons:**
- No SQS queue behavior (batching, retries, DLQ)
- Synchronous (blocks until worker completes)

### Option 2: LocalStack

Full AWS emulation - Lambda, SQS, everything local.

**Setup:**

```bash
pip install localstack awscli-local
localstack start

# Create resources
awslocal sqs create-queue --queue-name campaigns
awslocal lambda create-function \
  --function-name worker \
  --runtime python3.11 \
  --handler src.handlers.worker.handler \
  --zip-file fileb://lambda.zip

# Wire SQS trigger
awslocal lambda create-event-source-mapping \
  --function-name worker \
  --event-source-arn arn:aws:sqs:us-east-1:000000000000:campaigns
```

**Pros:**
- Full AWS parity (SQS batching, Lambda concurrency, DLQ)
- Test infrastructure changes locally
- Terraform can target LocalStack

**Cons:**
- Heavier setup
- Docker required
- Slower than Flask approach

### Option 3: SAM Local

Official AWS tool - runs Lambda locally with Docker.

**Setup:**

```bash
pip install aws-sam-cli

# Create template.yaml (SAM format) or use existing terraform
sam local start-api  # HTTP API
sam local invoke worker --event test_event.json  # Direct invoke
```

**Pros:**
- Official AWS tool
- Good Lambda debugging
- Supports layers and container images

**Cons:**
- Requires SAM template (parallel to terraform)
- Docker required
- Less flexible than Flask for rapid iteration

### Recommendation

Start with **Option 1 (Flask)** for daily development:
- Fastest setup and iteration
- Good enough for 90% of development work
- Add LocalStack later if you need to test SQS-specific behavior

---

## Current Status

**Phases 1-7 Complete:**
- Models: Topic, Creative, Slot, CreativeTypeConfig, Field, Condition
- Generators: text.header, text.main_text, image.cluster (with INPUTS declarations)
- Config: product_cluster_v2 with variants/variant_sequence/style_pool
- Engine: CreativeEngine with full pipeline + style_pool support
- Integration: worker.py routes `product_cluster_v2` to v2 engine
- API: `/config` endpoint serves field definitions
- Frontend: Generic field renderer, dynamic forms
- Infrastructure: Both lambdas on Docker, increased memory/timeout
- Style support: `style.*` sources resolve from `config.style_pool`

**v2 product_cluster is fully working and matches v1 output.**

**Next - Phase 8 (Cleanup):**
1. Validate v2 output matches v1 in production
2. Rename `product_cluster_v2` → `product_cluster` (replace v1)
3. Delete v1 code:
   - `src/services/topic.py` (generate_product_cluster method)
   - `src/services/creative.py` (product_cluster methods)
   - `src/services/text.py` (generate_for_product_cluster method)
   - `src/models/styles.py` (PRODUCT_CLUSTER_STYLES - now in v2 config)
4. Audit and delete unused abstractions (Condition, GeneratorOption)

---

## Phase 9: Production Deployment (S3 + CloudFront + Auth)

### Goal

Deploy frontend to S3, serve via CloudFront, add Basic Auth at edge layer.

### Architecture

```
User → CloudFront (Lambda@Edge auth) → S3 (frontend static files)
                                     → Lambda Function URL (API)
```

### Components

1. **S3 Bucket** - hosts frontend static files (index.html, app.js, styles.css)
2. **CloudFront Distribution** - CDN with two origins:
   - Default: S3 bucket (frontend)
   - `/api/*`: Lambda Function URL (backend)
3. **Lambda@Edge** - Basic Auth on viewer-request
4. **Route53** (optional) - custom domain

### Files to Create

#### 1. `edge_auth.py` - Lambda@Edge function

```python
import base64

CREDENTIALS = "admin:your-password"  # Move to parameter store later

def handler(event, context):
    request = event["Records"][0]["cf"]["request"]
    headers = request.get("headers", {})

    auth = headers.get("authorization", [{}])[0].get("value", "")

    if auth.startswith("Basic "):
        decoded = base64.b64decode(auth[6:]).decode()
        if decoded == CREDENTIALS:
            return request  # Allow through

    return {
        "status": "401",
        "headers": {
            "www-authenticate": [{"value": 'Basic realm="Login"'}]
        },
        "body": "Login required"
    }
```

#### 2. Terraform resources

```hcl
# S3 bucket for frontend
resource "aws_s3_bucket" "frontend" {
  bucket = "campaigns-frontend-${var.environment}"
}

resource "aws_s3_bucket_policy" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "cloudfront.amazonaws.com" }
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.frontend.arn}/*"
      Condition = {
        StringEquals = {
          "AWS:SourceArn" = aws_cloudfront_distribution.main.arn
        }
      }
    }]
  })
}

# Lambda@Edge for auth (must be in us-east-1)
resource "aws_lambda_function" "edge_auth" {
  provider      = aws.us_east_1
  function_name = "campaigns-edge-auth"
  role          = aws_iam_role.edge_auth.arn
  handler       = "edge_auth.handler"
  runtime       = "python3.11"
  publish       = true  # Required for Lambda@Edge

  filename         = data.archive_file.edge_auth.output_path
  source_code_hash = data.archive_file.edge_auth.output_base64sha256
}

# CloudFront distribution
resource "aws_cloudfront_distribution" "main" {
  enabled             = true
  default_root_object = "index.html"

  # Frontend origin (S3)
  origin {
    domain_name              = aws_s3_bucket.frontend.bucket_regional_domain_name
    origin_id                = "s3"
    origin_access_control_id = aws_cloudfront_origin_access_control.main.id
  }

  # API origin (Lambda Function URL)
  origin {
    domain_name = replace(aws_lambda_function_url.enqueue.function_url, "https://", "")
    origin_id   = "api"
    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  # Default behavior (S3 frontend)
  default_cache_behavior {
    target_origin_id       = "s3"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]

    lambda_function_association {
      event_type   = "viewer-request"
      lambda_arn   = aws_lambda_function.edge_auth.qualified_arn
      include_body = false
    }

    forwarding_values {
      query_string = false
      cookies { forward = "none" }
    }
  }

  # API behavior
  ordered_cache_behavior {
    path_pattern           = "/api/*"
    target_origin_id       = "api"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
    cached_methods         = ["GET", "HEAD"]

    lambda_function_association {
      event_type   = "viewer-request"
      lambda_arn   = aws_lambda_function.edge_auth.qualified_arn
      include_body = true
    }

    forwarding_values {
      query_string = true
      headers      = ["Authorization", "Content-Type"]
      cookies { forward = "none" }
    }

    min_ttl     = 0
    default_ttl = 0
    max_ttl     = 0
  }

  restrictions {
    geo_restriction { restriction_type = "none" }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}
```

### Frontend Changes

Update API calls to use `/api/` prefix:

```javascript
// Before
fetch('/config')
fetch('/', { method: 'POST', ... })

// After
fetch('/api/config')
fetch('/api/', { method: 'POST', ... })
```

### Deployment Steps

1. Create S3 bucket and CloudFront via terraform
2. Upload frontend files to S3: `aws s3 sync frontend/ s3://bucket-name/`
3. Update frontend to use `/api/` prefix
4. Test via CloudFront URL

### Security Notes

- Lambda@Edge credentials hardcoded initially - move to SSM Parameter Store later
- S3 bucket is private, only accessible via CloudFront OAC
- All traffic forced to HTTPS
