"""
Embedding Runtime Module

Provides text, image, video, audio, and multimodal embedding generation,
vector operations, similarity search, and embedding model management.
"""

from runtime.embedding.module import (
    EmbeddingModule,
    EmbeddingModel,
    EmbeddingType,
    DistanceMetric,
    PoolingStrategy,
    EmbeddingInput,
    EmbeddingResult,
    SimilarityResult,
    VectorSearchResult,
    EmbeddingModelInfo,
    EmbeddingBackend,
    TextEmbeddingBackend,
    ImageEmbeddingBackend,
    VideoEmbeddingBackend,
    AudioEmbeddingBackend,
    MultimodalEmbeddingBackend,
    CodeEmbeddingBackend,
    VectorOperationsBackend,
    VectorStoreBackend,
)

__all__ = [
    "EmbeddingModule",
    "EmbeddingModel",
    "EmbeddingType",
    "DistanceMetric",
    "PoolingStrategy",
    "EmbeddingInput",
    "EmbeddingResult",
    "SimilarityResult",
    "VectorSearchResult",
    "EmbeddingModelInfo",
    "EmbeddingBackend",
    "TextEmbeddingBackend",
    "ImageEmbeddingBackend",
    "VideoEmbeddingBackend",
    "AudioEmbeddingBackend",
    "MultimodalEmbeddingBackend",
    "CodeEmbeddingBackend",
    "VectorOperationsBackend",
    "VectorStoreBackend",
]