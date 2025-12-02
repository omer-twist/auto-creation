"""3-stage text generation pipeline for marketing copy."""

from .models import EventMode, DiscountMode, PageType, GenerationInput, TextVariation, PipelineResult
from .pipeline import TextGenerationPipeline

__all__ = [
    "EventMode",
    "DiscountMode",
    "PageType",
    "GenerationInput",
    "TextVariation",
    "PipelineResult",
    "TextGenerationPipeline",
]
