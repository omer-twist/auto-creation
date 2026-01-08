"""Serializers for creative type configs."""

from ..config.types import CREATIVE_TYPES
from ..models.config import CreativeTypeConfig, Field
from ..generators import get_generator_class


def serialize_all() -> dict:
    """Serialize all creative types for API response."""
    return {
        name: serialize_type(config)
        for name, config in CREATIVE_TYPES.items()
    }


def serialize_type(config: CreativeTypeConfig) -> dict:
    """Serialize a single creative type config."""
    fields = collect_fields_for_type(config)
    sorted_fields = sort_fields(fields)
    return {
        "displayName": config.display_name,
        "fields": [serialize_field(f) for f in sorted_fields],
    }


def collect_fields_for_type(config: CreativeTypeConfig) -> list[Field]:
    """Collect all unique fields from generators used by this creative type."""
    seen = set()
    fields = []

    # Collect INPUTS from generators
    for slot in config.slots:
        try:
            generator_cls = get_generator_class(slot.source)
            for field in getattr(generator_cls, 'INPUTS', []):
                if field.name not in seen:
                    seen.add(field.name)
                    fields.append(field)
        except ValueError:
            # Generator not found, skip
            pass

    # Create toggle fields for optional slots
    for slot in config.slots:
        if slot.optional:
            name = f"include_{slot.name.split('.')[0]}"  # "header.text" -> "include_header"
            if name not in seen:
                seen.add(name)
                fields.append(Field(
                    name=name,
                    type="toggle",
                    label=slot.label or slot.name.split('.')[0].title(),
                    default=True,
                ))

    return fields


def sort_fields(fields: list[Field]) -> list[Field]:
    """Sort fields by type for consistent UI ordering."""
    def get_order(field: Field) -> int:
        has_condition = field.condition is not None
        cond_type = field.condition.type if field.condition else None

        # Inline conditionals first
        if field.type == 'text' and cond_type == 'select':
            return 1
        # Standalone toggles
        if field.type == 'toggle' and not has_condition:
            return 2
        # Block fields (no condition)
        if field.type == 'list' and not has_condition:
            return 3
        if field.type == 'textarea' and not has_condition:
            return 4
        # Block conditionals (toggle → section)
        if field.type == 'list' and cond_type == 'toggle':
            return 5
        if field.type == 'textarea' and cond_type == 'toggle':
            return 6
        return 99

    return sorted(fields, key=get_order)


def serialize_field(field: Field) -> dict:
    """Serialize a field for API response."""
    result = {
        "name": field.name,
        "type": field.type,
        "label": field.label,
        "required": field.required,
    }
    if field.default is not None:
        result["default"] = field.default
    if field.options:
        result["options"] = field.options
    if field.condition:
        result["condition"] = {
            "type": field.condition.type,
            "label": field.condition.label,
            "default": field.condition.default,
        }
        if field.condition.options:
            result["condition"]["options"] = field.condition.options
        if field.condition.show_when:
            result["condition"]["showWhen"] = field.condition.show_when
    return result
