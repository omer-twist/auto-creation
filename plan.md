# Architecture Change: Generator Grouping by (Source + Config)

## Problem

Currently, generators run **once per source**. All slots sharing a source share the same `generator_config`. This means you can't have:
- 4 image slots with `aspect_ratio: "1:1"`
- 4 image slots with `aspect_ratio: "16:9"`

...in the same creative type. The last config wins.

## Proposed Solution

Group slots by **(source + generator_config)** instead of just source.

### How It Works

```
Slot A: image.product, config={aspect_ratio: "1:1"}
Slot B: image.product, config={aspect_ratio: "1:1"}
Slot C: image.product, config={aspect_ratio: "16:9"}
Slot D: image.product, config={aspect_ratio: "16:9"}
```

→ Two generator runs:
1. Group `(image.product, 1:1)` → runs once for slots A, B
2. Group `(image.product, 16:9)` → runs once for slots C, D

### Smart Indexing Still Works

Formula: `(creative_index * num_slots_in_group + slot_idx_in_group) % len(results)`

| Scenario | num_slots | results | Behavior |
|----------|-----------|---------|----------|
| 1 text slot, 12 lines | 1 | 12 | Each creative gets unique line |
| 1 text slot, 1 line | 1 | 1 | All creatives get same line (broadcast) |
| 8 image slots (same config), 8 images | 8 | 8 | Each slot unique, all creatives same |
| 4+4 image slots (diff configs), 4+4 images | 4 per group | 4 per group | Each group distributed separately |

### Backward Compatible

Existing creative types (product_cluster, product_grid) work unchanged because:
- Slots with same source and NO config → group together (same as before)
- Slots with same source and SAME config → group together (same as before)

Only new behavior: slots with same source but DIFFERENT configs → separate groups.

## Implementation Changes

### 1. `_resolve_sources()`
- Group by `(source, frozen_config)` instead of just `source`
- Run generator once per unique group
- Store results keyed by `(source, config_key)`

### 2. `_compute_slot_indices()`
- Count slots per `(source, config)` group, not per source

### 3. `_build_layers()`
- Lookup results by `(source, config)` key
- Smart indexing uses group-specific slot count

## Open Questions

1. **How does generator know how many images to process per group?**
   - Currently gets all `product_image_urls`
   - Should we split inputs per group somehow?
   - Or should each slot specify which URL index it wants?

2. **Input structure for mixed aspect ratios:**
   ```python
   # Option A: Generator figures it out from slot count
   {"product_image_urls": ["url1", "url2", "url3", "url4", ...]}

   # Option B: Explicit per-group inputs
   {"product_image_urls_1x1": [...], "product_image_urls_16x9": [...]}

   # Option C: Slot specifies URL index
   Slot(..., generator_config={"aspect_ratio": "1:1", "url_index": 0})
   ```

3. **Is this over-engineering?**
   - Alternative: Just register generator twice (`image.product`, `image.product_wide`)
   - Simpler but duplicates code

## Files to Modify

- `src/engine/engine.py` - main changes
- `CLAUDE.md` - document new behavior

## Status

**Pending review** - discuss before implementing.
