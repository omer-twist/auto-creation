# Architecture Change: 1:1 Slot-to-Generator with Opt-in Batching

## Problem with Current Design

Current design defaults to batching: generator runs once per source, returns list, smart indexing distributes results. This leads to:

1. **Confusing mental model** - `(creative_idx * num_slots + slot_idx) % len(results)` is hard to reason about
2. **Input mapping is implicit** - no clear connection between `product_image_urls[3]` and which slot gets it
3. **Config sharing issues** - all slots with same source must share `generator_config`

Batching should be the **exception** (where it saves API calls), not the default.

## Proposed Design

### Default: 1:1 (One Generator Call Per Slot)

```python
# Engine assigns slot_index to each slot with same source
# Slot declaration order = index order

class ProductImageGenerator(Generator):
    def generate(self, context: GenerationContext) -> str:  # returns ONE result
        url = context.inputs["product_image_urls"][context.slot_index]
        return self.process_image(url, context.generator_config)
```

- Each slot triggers one generator call
- Generator receives `context.slot_index` (0, 1, 2... for slots sharing same source)
- Generator returns **single value**, not list
- Input array index = slot index (positional mapping)

### Opt-in: Batched Generators

```python
@register("text.main_text", batched=True)
class MainTextGenerator(Generator):
    def generate(self, context: GenerationContext) -> list[str]:  # returns N results
        return openai_generate_variations(context.topic, count=context.count)
```

- Explicitly declared with `batched=True`
- Called once for all slots with that source
- Returns list, engine distributes to slots (existing smart indexing)
- Use when batching saves API calls (e.g., one OpenAI call for 12 text variations)

## Benefits

| Aspect | Current (batch default) | Proposed (1:1 default) |
|--------|------------------------|------------------------|
| Mental model | Complex smart indexing | Slot N gets input N |
| Input mapping | Implicit, distributed | Explicit, positional |
| Per-slot config | Broken (all share) | Works naturally |
| API efficiency | Always batched | Batch only when helpful |

## Implementation

### GenerationContext Changes

```python
@dataclass
class GenerationContext:
    topic: Topic
    inputs: dict
    count: int  # total creatives (12)
    slot_index: int | None  # NEW - None for batched generators
    generator_config: dict  # slot-specific config
```

### Engine Changes

```python
def _resolve_sources(self, slots, context):
    results = {}

    for source in unique_sources(slots):
        generator = get_generator(source)

        if generator.batched:
            # Call once, get list
            ctx = context.with_slot_index(None)
            results[source] = generator.generate(ctx)
        else:
            # Call per slot
            results[source] = []
            for idx, slot in enumerate(slots_for_source(source)):
                ctx = context.with_slot_index(idx).with_config(slot.generator_config)
                results[source].append(generator.generate(ctx))

    return results
```

### Generator Registration

```python
def register(source: str, batched: bool = False):
    def decorator(cls):
        REGISTRY[source] = GeneratorEntry(cls, batched=batched)
        return cls
    return decorator
```

## Migration

### Generators to mark as `batched=True`:
- `text.main_text` - one OpenAI call for 12 variations
- `text.header` - could go either way (usually returns 1 value broadcast)

### Generators that stay 1:1 (default):
- `image.product` - already 1 API call per image
- `image.cluster` - 1 image total (only 1 slot uses it)

### Backward Compatibility

Existing generators return lists. Options:
1. **Require migration** - update all generators to new signature
2. **Auto-detect** - if returns list and not batched, treat as batched (deprecation warning)

Recommend option 1 - clean break, small codebase.

## Open Questions

1. **Slot ordering** - use declaration order in config? Alphabetical by slot name? Explicit `slot_order` field?

2. **Broadcasts** - for `text.header` that returns same value for all creatives, is it:
   - `batched=True`, returns `["HEADER"] * 12`
   - `batched=False`, each call returns `"HEADER"` (12 identical calls, wasteful?)
   - New mode: `broadcast=True`, called once, result copied to all?

3. **Mixed slot counts across creatives** - currently all creatives have same slots. Keep this assumption?

## Status

**IDEA** - written for tomorrow's experimentation.
