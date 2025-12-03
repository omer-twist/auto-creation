"""3-stage text generation pipeline for marketing copy."""

from .models import GenerationInput, TextVariation, PipelineResult
from .pipeline import TextGenerationPipeline

__all__ = [
    "GenerationInput",
    "TextVariation",
    "PipelineResult",
    "TextGenerationPipeline",
]
