# Plan: Simplified Slot-Based Generation Model

## Summary

Replace smart indexing with a simple, explicit model:
- **Default**: 1 value per slot, broadcast to all creatives
- **`batch_creatives=True`**: N values per slot, one per creative

Generator contract stays the same: `generate(context) -> list[Any]`. Engine controls `context.count` based on config.

## Model

| Slot Config | Engine passes | Generator returns | Distribution |
|-------------|---------------|-------------------|--------------|
| default | `count=1` | `[value]` | `results[0]` → all creatives |
| `batch_creatives=True` | `count=12` | `[v0, ..., v11]` | `results[i]` → creative `i` |

No smart indexing. Just broadcast or direct index.

## Examples

### product_cluster
```python
slots=[
    Slot(name="header.text", source="text.header"),
    # → count=1, returns ["TOPIC"], all creatives get "TOPIC"

    Slot(name="main_text.text", source="text.main_text", batch_creatives=True),
    # → count=12, returns ["t0", ..., "t11"], creative[i] gets t[i]

    Slot(name="image.image", source="image.cluster"),
    # → count=1, returns ["url"], all creatives get "url"

    Slot(name="bg.background_color", source="style.background_color", batch_creatives=True),
    # → count=12, returns 12 colors from style_pool
]
```

### product_grid
```python
slots=[
    Slot(name="header.text", source="text.header"),
    Slot(name="main_text.text", source="text.main_text", batch_creatives=True),

    # 8 image slots - each gets count=1, uses slot_index for input
    Slot(name="image1.image", source="image.product"),  # slot_index=0 → urls[0]
    Slot(name="image2.image", source="image.product"),  # slot_index=1 → urls[1]
    Slot(name="image3.image", source="image.product"),  # slot_index=2 → urls[2]
    Slot(name="image4.image", source="image.product"),  # slot_index=3 → urls[3]
    Slot(name="image5.image", source="image.product"),  # slot_index=4 → urls[4]
    Slot(name="image6.image", source="image.product"),  # slot_index=5 → urls[5]
    Slot(name="image7.image", source="image.product"),  # slot_index=6 → urls[6]
    Slot(name="image8.image", source="image.product"),  # slot_index=7 → urls[7]
    # → 8 calls, each count=1, each returns [url], broadcast to all creatives

    Slot(name="bg.background_color", source="style.background_color", batch_creatives=True),
]
```

## Implementation

### 1. Update Slot Model

**File: `src/models/config.py`**

```python
@dataclass
class Slot:
    name: str
    source: str
    optional: bool = False
    generator_config: dict | None = None
    batch_creatives: bool = False       # NEW
```

### 2. Update GenerationContext

**File: `src/models/context.py`**

```python
@dataclass
class GenerationContext:
    topic: Topic
    inputs: dict[str, Any]
    options: dict[str, Any]
    count: int                          # how many values to generate
    slot_index: int | None = None       # NEW: index among slots with same source
```

### 3. Update Engine._resolve_sources

**File: `src/engine/engine.py`**

```python
def _resolve_sources(self, topic, config, inputs, options, creative_count):
    results = {}

    # Group slots by source
    slots_by_source = defaultdict(list)
    for slot in config.slots:
        slots_by_source[slot.source].append(slot)

    for source, slots in slots_by_source.items():
        if source.startswith("style."):
            results[source] = self._resolve_style_source(source, config)
            continue

        generator = self._create_generator(source)
        batch_creatives = any(s.batch_creatives for s in slots)

        if batch_creatives:
            # 1 call, count=creative_count
            context = GenerationContext(
                topic=topic,
                inputs=inputs,
                options=options,
                count=creative_count,
                slot_index=None,
            )
            results[source] = generator.generate(context)
        else:
            # 1 call per slot, count=1
            results[source] = []
            for slot_idx, slot in enumerate(slots):
                merged_inputs = {**inputs}
                if slot.generator_config:
                    merged_inputs.update(slot.generator_config)

                context = GenerationContext(
                    topic=topic,
                    inputs=merged_inputs,
                    options=options,
                    count=1,
                    slot_index=slot_idx,
                )
                value_list = generator.generate(context)  # returns [value]
                results[source].append(value_list[0])

    return results
```

### 4. Update Engine._build_layers

**File: `src/engine/engine.py`**

```python
def _build_layers(self, config, source_results, inputs, creative_idx, slot_indices):
    layers = {}

    for slot in config.slots:
        if slot.optional:
            toggle_name = f"include_{slot.name.split('.')[0]}"
            if not inputs.get(toggle_name, True):
                continue

        results = source_results[slot.source]

        if slot.batch_creatives or slot.source.startswith("style."):
            # Indexed by creative
            value = results[creative_idx]
        else:
            # Indexed by slot (same for all creatives)
            slot_idx = slot_indices[slot.source]["slots"][slot.name]
            value = results[slot_idx]

        layer_name, prop_name = slot.name.split(".")
        if layer_name not in layers:
            layers[layer_name] = {}
        layers[layer_name][prop_name] = value

    return layers
```

### 5. Generator Changes

Generators already return `list[Any]`. No signature change needed.

**text.header** - returns `[value]` (count=1):
```python
def generate(self, context) -> list[str]:
    header = context.topic.name.upper()
    return [header] * context.count  # works for count=1 or more
```

**text.main_text** - returns `[v0, ..., v11]` (count=12):
```python
def generate(self, context) -> list[str]:
    return self._generate_via_llm(context)  # returns count values
```

**image.product** - returns `[url]` (count=1), uses slot_index:
```python
def generate(self, context) -> list[str]:
    url = context.inputs["product_image_urls"][context.slot_index]
    processed = self._process(url)
    return [processed]
```

## Files to Modify

1. `src/models/config.py` - Add `batch_creatives` to Slot
2. `src/models/context.py` - Add `slot_index`
3. `src/engine/engine.py` - Rewrite `_resolve_sources` and `_build_layers`
4. `src/generators/text/header.py` - Use `context.count`
5. `src/generators/image/product.py` - Use `context.slot_index`
6. `src/creative_types/product_cluster.py` - Add `batch_creatives=True` where needed
7. `src/creative_types/product_grid.py` - Add `batch_creatives=True` where needed

## Future: group_id

For mixed aspect ratios (16:9 + 1:1 in same creative):

```python
Slot(name="hero.image", source="image.product", group_id="hero",
     generator_config={"aspect_ratio": "16:9"})
Slot(name="thumb1.image", source="image.product", group_id="thumbs",
     generator_config={"aspect_ratio": "1:1"})
Slot(name="thumb2.image", source="image.product", group_id="thumbs",
     generator_config={"aspect_ratio": "1:1"})
```

Engine groups by `(source, group_id)` instead of just `source`. Slots with different `group_id` get separate generator calls even if same source.

Not implementing now.

## Summary

- Generator contract unchanged: `generate(context) -> list[Any]`
- Engine controls `count`: 1 for default, N for batch_creatives
- Distribution is simple: broadcast `results[0]` or index `results[i]`
- `slot_index` tells generator which input to use (for multi-slot sources)
- No smart indexing formula
