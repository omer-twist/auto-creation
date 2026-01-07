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
├── text/product_cluster    → knows how to make header+main text
├── image/cluster           → knows how to make cluster images
└── ... future generators

Configs (thin, just wiring):
└── product_cluster         → "slot X uses text/product_cluster.header"
                            → "slot Y uses image/cluster"

Engine:
└── generate(topic, config, inputs, options, count) → list[Creative]
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
│     config = CREATIVE_TYPES["product_cluster"]              │
│                                                             │
│  2. Build v2.Topic (UNIVERSAL ONLY)                         │
│     Topic(name, event, discount, page_type, url)            │
│                                                             │
│  3. Extract inputs & options from request                   │
│     inputs = {"product_image_urls": [...]}                  │
│     options = {"is_people_mode": True}                      │
│                                                             │
│  4. Call engine.generate(topic, config, inputs, options, 12)│
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                         ENGINE                              │
├─────────────────────────────────────────────────────────────┤
│  1. Build GenerationContext(topic, inputs, options, count)  │
│                                                             │
│  2. For each slot in config.slots:                          │
│     - "text/product_cluster" → TextGenerator.generate()     │
│     - "image/cluster" → ImageGenerator.generate()           │
│     - "style" → pull from style pool                        │
│                                                             │
│  3. Render via Placid → list[Creative] ← CREATED HERE       │
│                                                             │
│  4. Return creatives (NO CAMPAIGN GROUPING)                 │
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
│   │   ├── __init__.py              # Registry
│   │   ├── base.py                  # Generator base class
│   │   ├── text/
│   │   │   ├── __init__.py
│   │   │   └── product_cluster.py
│   │   └── image/
│   │       ├── __init__.py
│   │       └── cluster.py
│   │
│   ├── config/
│   │   ├── types/
│   │   │   ├── __init__.py          # CREATIVE_TYPES registry
│   │   │   └── product_cluster.py
│   │   └── styles/
│   │       ├── __init__.py
│   │       └── product_cluster.py
│   │
│   └── engine/
│       ├── __init__.py
│       └── engine.py                # CreativeEngine
│
├── models/                          # OLD - untouched until migration
├── services/                        # OLD - untouched until migration
├── handlers/                        # OLD - untouched until migration
├── clients/                         # Shared - minimal changes
└── prompts/                         # Shared - unchanged
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
"""Creative output model - field names match Placid layers for optimization traceability."""

from dataclasses import dataclass


@dataclass
class Creative:
    """Field names match Placid layers for optimization traceability."""
    # Placid layer values (what we sent)
    main_text: str                        # main_text.text
    background_color: str                 # bg.background_color
    main_text_color: str                  # main_text.text_color
    font: str                             # main_text.font
    header_text: str | None = None        # header.text
    header_text_color: str | None = None  # header.text_color
    cluster_image_url: str | None = None  # image.image (input to Placid)

    # Output (what Placid returns)
    image_url: str = ""                   # The generated creative image

    # Future: id, campaign_id, parent_id (for variations), metadata
```

#### 4. `src/v2/models/slot.py`

```python
"""Slot definitions for Placid templates."""

from dataclasses import dataclass
from typing import Any


@dataclass
class SlotUI:
    """UI behavior for a slot."""
    toggleable: bool = False
    toggle_label: str | None = None
    toggle_default: bool = True


@dataclass
class Slot:
    """A slot in a Placid template that needs to be filled."""
    name: str                    # Placid layer name
    source: str                  # "text/product_cluster", "image/cluster", "style", "topic", "static"
    field: str | None = None     # For multi-output generators or style/topic field
    value: Any = None            # For static source
    ui: SlotUI | None = None
    # Note: Removed transform - uppercase for headers is internal engine logic
```

#### 5. `src/v2/models/config.py`

```python
"""Creative type configuration."""

from dataclasses import dataclass, field

from .slot import Slot


@dataclass
class InputField:
    """A user-provided input for a creative type."""
    name: str
    type: str                    # "text" | "url_list" | "number" | "select"
    label: str
    required: bool = True


@dataclass
class CreativeTypeConfig:
    """Configuration for a creative type. THIN - just wiring."""
    name: str
    display_name: str
    template_uuid: str
    slots: list[Slot]
    inputs: list[InputField] = field(default_factory=list)
    style_pool: str = "default"
```

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


def register(path: str):
    """Decorator to register a generator."""
    def decorator(cls):
        _GENERATORS[path] = cls
        return cls
    return decorator


def get_generator_class(path: str) -> Type[Generator]:
    """Get generator class by path."""
    if path not in _GENERATORS:
        raise ValueError(f"Unknown generator: {path}")
    return _GENERATORS[path]


def list_generators() -> list[str]:
    """List all registered generators."""
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
creatives = [Creative(text=f"text{i}", image_url=f"url{i}", background_color="#000", text_color="#FFF", font="Arial") for i in range(12)]
campaigns = group_into_campaigns(creatives, size=3)
assert len(campaigns) == 4
assert len(campaigns[0].creatives) == 3

# Verify flexible count
campaigns_5 = group_into_campaigns(creatives[:10], size=2)
assert len(campaigns_5) == 5

print("Phase 1 complete - all imports and basic tests pass")
```

---

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
| 4. Config | Create product_cluster config | `src/v2/config/types/product_cluster.py` |
| 5. Engine | Wire everything together | `src/v2/engine/engine.py` |
| 6. Integration | New API endpoints | `src/handlers/worker.py` (v2 routes) |
| 7. Frontend | Config-driven UI | `frontend/` |
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

### Deferred Decisions (Refine in Phase 4/5)

- **Upload location:** Currently inside generator. May extract to engine later for flexibility.
- **aspect_ratio source:** Currently from `context.inputs`. May move to slot/template config.
- **Post-processing options:** `remove_bg` and `crop` read from `context.options`, defaults True.

### Key Decisions

- Generators return `list[str]` (single-element list with URL, engine broadcasts)
- Flexible aspect ratio - any Gemini-supported ratio works
- Uses existing clients directly: `GeminiClient`, `RemoveBgClient`, `CreativeClient`

---

## Key Differences from Current System

| Aspect | Current | V2 |
|--------|---------|-----|
| Topic | Has everything | Universal only |
| Type-specific data | In Topic | In `inputs` dict |
| Toggles/options | In Topic | In `options` dict |
| Routing | `if creative_type == ...` | Config lookup |
| Text generation | TextService methods | text/ generators |
| Image generation | ProductImageService | image/ generators |
| Output | Topic.campaigns (mutates) | Returns `list[Creative]` |
| Campaign grouping | Inside TopicService | Caller utility |
| Count | Hardcoded 12 | Flexible parameter |
| Adding new type | Touch 4+ files | Add config + maybe generator |
