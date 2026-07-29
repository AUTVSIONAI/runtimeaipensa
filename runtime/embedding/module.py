"""
Embedding Runtime Module

Provides text, image, video, audio, and multimodal embedding generation,
vector operations, similarity search, and embedding model management.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple, Union, TYPE_CHECKING
import asyncio
import logging
import uuid
from pathlib import Path

import numpy as np

from runtime.base.module import (
    RuntimeModule,
    ModuleMetadata,
    ModuleState,
)

if TYPE_CHECKING:
    from runtime.runtime import Runtime

logger = logging.getLogger(__name__)


class EmbeddingModel(Enum):
    """Embedding model types."""
    # Text Embeddings
    OPENAI_ADA_002 = "text-embedding-ada-002"
    OPENAI_3_SMALL = "text-embedding-3-small"
    OPENAI_3_LARGE = "text-embedding-3-large"
    COHERE_EMBED_V3 = "cohere_embed_v3"
    COHERE_EMBED_MULTILINGUAL = "cohere_embed_multilingual_v3"
    GOOGLE_GEODESIC = "google_geodesic"
    GOOGLE_GEMINI_EMBEDDING = "google_gemini_embedding"
    SENTENCE_TRANSFORMERS_MINILM = "sentence_transformers_minilm"
    SENTENCE_TRANSFORMERS_MPNET = "sentence_transformers_mpnet"
    SENTENCE_TRANSFORMERS_E5 = "sentence_transformers_e5"
    SENTENCE_TRANSFORMERS_BGE = "sentence_transformers_bge"
    INSTRUCTOR_XL = "instructor_xl"
    E5_MISTRAL = "e5_mistral"
    GTE = "gte"
    BGE = "bge"
    JINA_EMBEDDINGS = "jina_embeddings"
    NOMIC_EMBED = "nomic_embed"
    MXBAI = "mxbai"

    # Multimodal Embeddings
    CLIP_VIT_B32 = "clip_vit_b32"
    CLIP_VIT_L14 = "clip_vit_l14"
    CLIP_VIT_H14 = "clip_vit_h14"
    ALIGN = "align"
    FLAVA = "flava"
    IMAGE_BIND = "imagebind"
    BEIT = "beit"
    BLIP2 = "blip2"
    BRIDGE = "bridge"

    # Image Embeddings
    DINO_V2 = "dino_v2"
    DINO_V2_LARGE = "dino_v2_large"
    MAE = "mae"
    BEIT_V2 = "beit_v2"
    CONVNEAT_XL = "convnext_xl"
    SWIN_V2 = "swin_v2"
    EVA = "eva"
    EVA_V2 = "eva_v2"
    SAM = "sam"
    SAM_V2 = "sam_v2"

    # Video Embeddings
    VIDEO_MA_E = "video_mae"
    TIMESFORMER = "timesformer"
    VIVIT = "vivit"
    MViT = "mvit"
    X3D = "x3d"
    SLOWFAST = "slowfast"
    OMNIVORE = "omnivore"

    # Audio Embeddings
    WAV2VEC2 = "wav2vec2"
    HUBERT = "hubert"
    WAVLM = "wavlm"
    CLAP = "clap"
    AUDIO_CLAP = "audio_clap"
    PANNS = "panns"
    AST = "ast"
    BEATS = "beats"

    # Code Embeddings
    CODEBERT = "codebert"
    GRAPHCODEBERT = "graphcodebert"
    UNIXCODER = "unixcoder"
    CODET5 = "codet5"
    STARCODER_EMBED = "starcoder_embed"

    # Custom
    CUSTOM = "custom"


class EmbeddingType(Enum):
    """Type of input for embedding."""
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    CODE = "code"
    MULTIMODAL = "multimodal"


class DistanceMetric(Enum):
    """Distance metrics for similarity."""
    COSINE = "cosine"
    EUCLIDEAN = "euclidean"
    DOT_PRODUCT = "dot_product"
    MANHATTAN = "manhattan"
    CHEBYSHEV = "chebyshev"
    MINKOWSKI = "minkowski"
    HAMMING = "hamming"
    JACCARD = "jaccard"


class PoolingStrategy(Enum):
    """Pooling strategies for token embeddings."""
    MEAN = "mean"
    MAX = "max"
    CLS = "cls"
    FIRST = "first"
    LAST = "last"
    WEIGHTED_MEAN = "weighted_mean"
    ATTENTION = "attention"


@dataclass
class EmbeddingInput:
    """Input for embedding generation."""
    input_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    texts: List[str] = field(default_factory=list)
    images: List[Any] = field(default_factory=list)  # np.ndarray, PIL Image, path, bytes
    videos: List[Any] = field(default_factory=list)
    audios: List[Any] = field(default_factory=list)
    code_snippets: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding_type: EmbeddingType = EmbeddingType.TEXT


@dataclass
class EmbeddingResult:
    """Embedding generation result."""
    result_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    embeddings: List[List[float]] = field(default_factory=list)
    dimensions: int = 0
    model: EmbeddingModel = EmbeddingModel.OPENAI_ADA_002
    input_type: EmbeddingType = EmbeddingType.TEXT
    token_counts: List[int] = field(default_factory=list)
    processing_time: float = 0.0
    pooling_strategy: Optional[PoolingStrategy] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_numpy(self) -> np.ndarray:
        """Convert embeddings to numpy array."""
        return np.array(self.embeddings, dtype=np.float32)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "embeddings": self.embeddings,
            "dimensions": self.dimensions,
            "model": self.model.value,
            "input_type": self.input_type.value,
            "token_counts": self.token_counts,
            "processing_time": self.processing_time,
            "pooling_strategy": self.pooling_strategy.value if self.pooling_strategy else None,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class SimilarityResult:
    """Similarity computation result."""
    result_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    query_embedding: List[float] = field(default_factory=list)
    candidates: List[Dict[str, Any]] = field(default_factory=list)
    scores: List[float] = field(default_factory=list)
    indices: List[int] = field(default_factory=list)
    metric: DistanceMetric = DistanceMetric.COSINE
    top_k: int = 10
    processing_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "candidates": self.candidates,
            "scores": self.scores,
            "indices": self.indices,
            "metric": self.metric.value,
            "top_k": self.top_k,
            "processing_time": self.processing_time,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class VectorSearchResult:
    """Vector search result."""
    result_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    query_vector: Optional[List[float]] = None
    hits: List[Dict[str, Any]] = field(default_factory=list)
    total_hits: int = 0
    search_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "hits": self.hits,
            "total_hits": self.total_hits,
            "search_time": self.search_time,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class EmbeddingModelInfo:
    """Information about an embedding model."""
    model_id: str
    name: str
    provider: str
    dimensions: int
    max_sequence_length: int
    supported_types: List[EmbeddingType]
    supported_pooling: List[PoolingStrategy]
    supports_batching: bool = True
    supports_streaming: bool = False
    is_multilingual: bool = False
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class EmbeddingBackend(ABC):
    """Abstract base class for embedding backends."""

    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def get_model_info(self) -> EmbeddingModelInfo:
        pass


class TextEmbeddingBackend(EmbeddingBackend):
    """Text embedding backend interface."""

    @abstractmethod
    async def embed_texts(
        self,
        texts: List[str],
        model: Optional[EmbeddingModel] = None,
        pooling: Optional[PoolingStrategy] = None,
        normalize: bool = True,
        **kwargs
    ) -> EmbeddingResult:
        pass

    @abstractmethod
    async def embed_query(
        self,
        query: str,
        model: Optional[EmbeddingModel] = None,
        pooling: Optional[PoolingStrategy] = None,
        normalize: bool = True,
        **kwargs
    ) -> EmbeddingResult:
        pass

    @abstractmethod
    async def embed_documents(
        self,
        documents: List[str],
        model: Optional[EmbeddingModel] = None,
        pooling: Optional[PoolingStrategy] = None,
        normalize: bool = True,
        **kwargs
    ) -> EmbeddingResult:
        pass


class ImageEmbeddingBackend(EmbeddingBackend):
    """Image embedding backend interface."""

    @abstractmethod
    async def embed_images(
        self,
        images: List[Any],  # paths, URLs, arrays, PIL Images
        model: Optional[EmbeddingModel] = None,
        normalize: bool = True,
        **kwargs
    ) -> EmbeddingResult:
        pass


class VideoEmbeddingBackend(EmbeddingBackend):
    """Video embedding backend interface."""

    @abstractmethod
    async def embed_videos(
        self,
        videos: List[Any],  # paths, VideoData objects
        model: Optional[EmbeddingModel] = None,
        normalize: bool = True,
        **kwargs
    ) -> EmbeddingResult:
        pass


class AudioEmbeddingBackend(EmbeddingBackend):
    """Audio embedding backend interface."""

    @abstractmethod
    async def embed_audio(
        self,
        audios: List[Any],  # paths, AudioData objects
        model: Optional[EmbeddingModel] = None,
        normalize: bool = True,
        **kwargs
    ) -> EmbeddingResult:
        pass


class MultimodalEmbeddingBackend(EmbeddingBackend):
    """Multimodal embedding backend interface."""

    @abstractmethod
    async def embed_multimodal(
        self,
        texts: Optional[List[str]] = None,
        images: Optional[List[Any]] = None,
        model: Optional[EmbeddingModel] = None,
        normalize: bool = True,
        **kwargs
    ) -> EmbeddingResult:
        pass

    @abstractmethod
    async def embed_text_image_pairs(
        self,
        pairs: List[Tuple[str, Any]],  # (text, image)
        model: Optional[EmbeddingModel] = None,
        normalize: bool = True,
        **kwargs
    ) -> EmbeddingResult:
        pass


class CodeEmbeddingBackend(EmbeddingBackend):
    """Code embedding backend interface."""

    @abstractmethod
    async def embed_code(
        self,
        code_snippets: List[str],
        language: Optional[str] = None,
        model: Optional[EmbeddingModel] = None,
        normalize: bool = True,
        **kwargs
    ) -> EmbeddingResult:
        pass


class VectorOperationsBackend(ABC):
    """Vector operations backend interface."""

    @abstractmethod
    async def compute_similarity(
        self,
        query: List[float],
        candidates: List[List[float]],
        metric: DistanceMetric = DistanceMetric.COSINE,
        top_k: int = 10,
        **kwargs
    ) -> SimilarityResult:
        pass

    @abstractmethod
    async def compute_pairwise_similarity(
        self,
        vectors_a: List[List[float]],
        vectors_b: List[List[float]],
        metric: DistanceMetric = DistanceMetric.COSINE,
        **kwargs
    ) -> np.ndarray:
        pass

    @abstractmethod
    async def normalize_vectors(
        self,
        vectors: List[List[float]],
        norm: str = "l2",
        **kwargs
    ) -> List[List[float]]:
        pass

    @abstractmethod
    async def reduce_dimensions(
        self,
        vectors: List[List[float]],
        target_dim: int,
        method: str = "pca",
        **kwargs
    ) -> List[List[float]]:
        pass

    @abstractmethod
    async def cluster_vectors(
        self,
        vectors: List[List[float]],
        n_clusters: int,
        algorithm: str = "kmeans",
        **kwargs
    ) -> Dict[str, Any]:
        pass


class VectorStoreBackend(ABC):
    """Vector store backend interface."""

    @abstractmethod
    async def add_vectors(
        self,
        vectors: List[List[float]],
        ids: List[str],
        metadata: Optional[List[Dict[str, Any]]] = None,
        namespace: str = "default",
        **kwargs
    ) -> bool:
        pass

    @abstractmethod
    async def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        namespace: str = "default",
        filter: Optional[Dict[str, Any]] = None,
        metric: DistanceMetric = DistanceMetric.COSINE,
        **kwargs
    ) -> VectorSearchResult:
        pass

    @abstractmethod
    async def search_by_id(
        self,
        vector_id: str,
        namespace: str = "default",
        **kwargs
    ) -> Optional[List[float]]:
        pass

    @abstractmethod
    async def delete_vectors(
        self,
        ids: List[str],
        namespace: str = "default",
        **kwargs
    ) -> bool:
        pass

    @abstractmethod
    async def update_metadata(
        self,
        ids: List[str],
        metadata: List[Dict[str, Any]],
        namespace: str = "default",
        **kwargs
    ) -> bool:
        pass

    @abstractmethod
    async def count_vectors(
        self,
        namespace: str = "default",
        **kwargs
    ) -> int:
        pass


class EmbeddingModule(RuntimeModule):
    """
    Embedding Runtime Module

    Provides comprehensive embedding capabilities:
    - Text embeddings (multiple models and providers)
    - Image embeddings (CLIP, DINOv2, MAE, etc.)
    - Video embeddings (VideoMAE, TimeSformer, etc.)
    - Audio embeddings (Wav2Vec2, HuBERT, CLAP, etc.)
    - Code embeddings (CodeBERT, GraphCodeBERT, etc.)
    - Multimodal embeddings (CLIP, ALIGN, ImageBind, etc.)
    - Vector operations (similarity, clustering, dimensionality reduction)
    - Vector storage and search (integration with vector databases)
    """

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="embedding",
            version="1.0.0",
            description="Embedding generation for text, image, video, audio, code, and multimodal content with vector operations and storage",
            author="AIPENSA",
            dependencies=["numpy"],
            provides=["text_embedding", "image_embedding", "video_embedding", "audio_embedding", "code_embedding", "multimodal_embedding", "vector_operations", "vector_store"],
            tags={"embedding", "vector", "embeddings", "similarity", "search"}
        )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        # Embedding backends by type
        self._text_backend: Optional[TextEmbeddingBackend] = None
        self._image_backend: Optional[ImageEmbeddingBackend] = None
        self._video_backend: Optional[VideoEmbeddingBackend] = None
        self._audio_backend: Optional[AudioEmbeddingBackend] = None
        self._multimodal_backend: Optional[MultimodalEmbeddingBackend] = None
        self._code_backend: Optional[CodeEmbeddingBackend] = None

        # Operations backends
        self._vector_ops_backend: Optional[VectorOperationsBackend] = None
        self._vector_store_backend: Optional[VectorStoreBackend] = None

        # Model cache
        self._model_cache: Dict[str, Any] = {}

    async def initialize(self, runtime: "Runtime", config: Dict[str, Any]) -> None:
        """Initialize embedding backends."""
        await super().initialize(runtime, config)

        config = self.config

        # Text embedding backend
        text_config = config.get("text", {})
        backend_type = text_config.get("backend", "mock")
        if backend_type == "mock":
            self._text_backend = MockTextEmbeddingBackend()
        await self._text_backend.initialize(text_config)

        # Image embedding backend
        image_config = config.get("image", {})
        backend_type = image_config.get("backend", "mock")
        if backend_type == "mock":
            self._image_backend = MockImageEmbeddingBackend()
        await self._image_backend.initialize(image_config)

        # Video embedding backend
        video_config = config.get("video", {})
        backend_type = video_config.get("backend", "mock")
        if backend_type == "mock":
            self._video_backend = MockVideoEmbeddingBackend()
        await self._video_backend.initialize(video_config)

        # Audio embedding backend
        audio_config = config.get("audio", {})
        backend_type = audio_config.get("backend", "mock")
        if backend_type == "mock":
            self._audio_backend = MockAudioEmbeddingBackend()
        await self._audio_backend.initialize(audio_config)

        # Multimodal embedding backend
        multi_config = config.get("multimodal", {})
        backend_type = multi_config.get("backend", "mock")
        if backend_type == "mock":
            self._multimodal_backend = MockMultimodalEmbeddingBackend()
        await self._multimodal_backend.initialize(multi_config)

        # Code embedding backend
        code_config = config.get("code", {})
        backend_type = code_config.get("backend", "mock")
        if backend_type == "mock":
            self._code_backend = MockCodeEmbeddingBackend()
        await self._code_backend.initialize(code_config)

        # Vector operations backend
        vec_ops_config = config.get("vector_operations", {})
        backend_type = vec_ops_config.get("backend", "mock")
        if backend_type == "mock":
            self._vector_ops_backend = MockVectorOperationsBackend()
        await self._vector_ops_backend.initialize(vec_ops_config)

        # Vector store backend
        vec_store_config = config.get("vector_store", {})
        backend_type = vec_store_config.get("backend", "mock")
        if backend_type == "mock":
            self._vector_store_backend = MockVectorStoreBackend()
        await self._vector_store_backend.initialize(vec_store_config)

        logger.info("Embedding module initialized with all backends")

    async def start(self) -> None:
        """Start embedding module."""
        await super().start()
        logger.info("Embedding module started")

    async def stop(self) -> None:
        """Stop embedding module and cleanup backends."""
        backends = [
            self._text_backend, self._image_backend, self._video_backend,
            self._audio_backend, self._multimodal_backend, self._code_backend,
            self._vector_ops_backend, self._vector_store_backend
        ]
        for backend in backends:
            if backend:
                await backend.cleanup()

        await super().stop()
        logger.info("Embedding module stopped")

    async def cleanup(self) -> None:
        """Clean up all resources."""
        # Cleanup backends
        backends = [
            self._text_backend, self._image_backend, self._video_backend,
            self._audio_backend, self._multimodal_backend, self._code_backend,
            self._vector_ops_backend, self._vector_store_backend
        ]
        for backend in backends:
            if backend:
                await backend.cleanup()

        self._model_cache.clear()
        await super().cleanup()
        logger.info("Embedding module cleaned up")

    async def health_check(self) -> Dict[str, Any]:
        """Check health of all backends."""
        health = await super().health_check()
        health["backends"] = {}

        for name, backend in [
            ("text", self._text_backend),
            ("image", self._image_backend),
            ("video", self._video_backend),
            ("audio", self._audio_backend),
            ("multimodal", self._multimodal_backend),
            ("code", self._code_backend),
            ("vector_operations", self._vector_ops_backend),
            ("vector_store", self._vector_store_backend)
        ]:
            if backend:
                health["backends"][name] = await backend.health_check()
            else:
                health["backends"][name] = {"status": "not_initialized"}

        all_healthy = all(
            b.get("status") == "healthy"
            for b in health["backends"].values()
        )
        health["status"] = "healthy" if all_healthy else "degraded"
        return health

    # Text Embedding Operations
    async def embed_texts(
        self,
        texts: List[str],
        model: Optional[EmbeddingModel] = None,
        pooling: Optional[PoolingStrategy] = None,
        normalize: bool = True,
        **kwargs
    ) -> EmbeddingResult:
        """Embed a list of texts."""
        if not self._text_backend:
            raise RuntimeError("Text embedding backend not initialized")
        return await self._text_backend.embed_texts(texts, model, pooling, normalize, **kwargs)

    async def embed_query(
        self,
        query: str,
        model: Optional[EmbeddingModel] = None,
        pooling: Optional[PoolingStrategy] = None,
        normalize: bool = True,
        **kwargs
    ) -> EmbeddingResult:
        """Embed a single query text."""
        if not self._text_backend:
            raise RuntimeError("Text embedding backend not initialized")
        return await self._text_backend.embed_query(query, model, pooling, normalize, **kwargs)

    async def embed_documents(
        self,
        documents: List[str],
        model: Optional[EmbeddingModel] = None,
        pooling: Optional[PoolingStrategy] = None,
        normalize: bool = True,
        **kwargs
    ) -> EmbeddingResult:
        """Embed a list of documents."""
        if not self._text_backend:
            raise RuntimeError("Text embedding backend not initialized")
        return await self._text_backend.embed_documents(documents, model, pooling, normalize, **kwargs)

    # Image Embedding Operations
    async def embed_images(
        self,
        images: List[Any],
        model: Optional[EmbeddingModel] = None,
        normalize: bool = True,
        **kwargs
    ) -> EmbeddingResult:
        """Embed a list of images."""
        if not self._image_backend:
            raise RuntimeError("Image embedding backend not initialized")
        return await self._image_backend.embed_images(images, model, normalize, **kwargs)

    # Video Embedding Operations
    async def embed_videos(
        self,
        videos: List[Any],
        model: Optional[EmbeddingModel] = None,
        normalize: bool = True,
        **kwargs
    ) -> EmbeddingResult:
        """Embed a list of videos."""
        if not self._video_backend:
            raise RuntimeError("Video embedding backend not initialized")
        return await self._video_backend.embed_videos(videos, model, normalize, **kwargs)

    # Audio Embedding Operations
    async def embed_audio(
        self,
        audios: List[Any],
        model: Optional[EmbeddingModel] = None,
        normalize: bool = True,
        **kwargs
    ) -> EmbeddingResult:
        """Embed a list of audio files."""
        if not self._audio_backend:
            raise RuntimeError("Audio embedding backend not initialized")
        return await self._audio_backend.embed_audio(audios, model, normalize, **kwargs)

    # Multimodal Embedding Operations
    async def embed_multimodal(
        self,
        texts: Optional[List[str]] = None,
        images: Optional[List[Any]] = None,
        model: Optional[EmbeddingModel] = None,
        normalize: bool = True,
        **kwargs
    ) -> EmbeddingResult:
        """Embed multimodal inputs."""
        if not self._multimodal_backend:
            raise RuntimeError("Multimodal embedding backend not initialized")
        return await self._multimodal_backend.embed_multimodal(texts, images, model, normalize, **kwargs)

    async def embed_text_image_pairs(
        self,
        pairs: List[Tuple[str, Any]],
        model: Optional[EmbeddingModel] = None,
        normalize: bool = True,
        **kwargs
    ) -> EmbeddingResult:
        """Embed text-image pairs."""
        if not self._multimodal_backend:
            raise RuntimeError("Multimodal embedding backend not initialized")
        return await self._multimodal_backend.embed_text_image_pairs(pairs, model, normalize, **kwargs)

    # Code Embedding Operations
    async def embed_code(
        self,
        code_snippets: List[str],
        language: Optional[str] = None,
        model: Optional[EmbeddingModel] = None,
        normalize: bool = True,
        **kwargs
    ) -> EmbeddingResult:
        """Embed code snippets."""
        if not self._code_backend:
            raise RuntimeError("Code embedding backend not initialized")
        return await self._code_backend.embed_code(code_snippets, language, model, normalize, **kwargs)

    # Vector Operations
    async def compute_similarity(
        self,
        query: List[float],
        candidates: List[List[float]],
        metric: DistanceMetric = DistanceMetric.COSINE,
        top_k: int = 10,
        **kwargs
    ) -> SimilarityResult:
        """Compute similarity between query and candidates."""
        if not self._vector_ops_backend:
            raise RuntimeError("Vector operations backend not initialized")
        return await self._vector_ops_backend.compute_similarity(query, candidates, metric, top_k, **kwargs)

    async def compute_pairwise_similarity(
        self,
        vectors_a: List[List[float]],
        vectors_b: List[List[float]],
        metric: DistanceMetric = DistanceMetric.COSINE,
        **kwargs
    ) -> np.ndarray:
        """Compute pairwise similarity matrix."""
        if not self._vector_ops_backend:
            raise RuntimeError("Vector operations backend not initialized")
        return await self._vector_ops_backend.compute_pairwise_similarity(vectors_a, vectors_b, metric, **kwargs)

    async def normalize_vectors(
        self,
        vectors: List[List[float]],
        norm: str = "l2",
        **kwargs
    ) -> List[List[float]]:
        """Normalize vectors."""
        if not self._vector_ops_backend:
            raise RuntimeError("Vector operations backend not initialized")
        return await self._vector_ops_backend.normalize_vectors(vectors, norm, **kwargs)

    async def reduce_dimensions(
        self,
        vectors: List[List[float]],
        target_dim: int,
        method: str = "pca",
        **kwargs
    ) -> List[List[float]]:
        """Reduce vector dimensions."""
        if not self._vector_ops_backend:
            raise RuntimeError("Vector operations backend not initialized")
        return await self._vector_ops_backend.reduce_dimensions(vectors, target_dim, method, **kwargs)

    async def cluster_vectors(
        self,
        vectors: List[List[float]],
        n_clusters: int,
        algorithm: str = "kmeans",
        **kwargs
    ) -> Dict[str, Any]:
        """Cluster vectors."""
        if not self._vector_ops_backend:
            raise RuntimeError("Vector operations backend not initialized")
        return await self._vector_ops_backend.cluster_vectors(vectors, n_clusters, algorithm, **kwargs)

    # Vector Store Operations
    async def add_vectors(
        self,
        vectors: List[List[float]],
        ids: List[str],
        metadata: Optional[List[Dict[str, Any]]] = None,
        namespace: str = "default",
        **kwargs
    ) -> bool:
        """Add vectors to vector store."""
        if not self._vector_store_backend:
            raise RuntimeError("Vector store backend not initialized")
        return await self._vector_store_backend.add_vectors(vectors, ids, metadata, namespace, **kwargs)

    async def search_vectors(
        self,
        query_vector: List[float],
        top_k: int = 10,
        namespace: str = "default",
        filter: Optional[Dict[str, Any]] = None,
        metric: DistanceMetric = DistanceMetric.COSINE,
        **kwargs
    ) -> VectorSearchResult:
        """Search for similar vectors."""
        if not self._vector_store_backend:
            raise RuntimeError("Vector store backend not initialized")
        return await self._vector_store_backend.search(query_vector, top_k, namespace, filter, metric, **kwargs)

    async def search_by_text(
        self,
        query_text: str,
        top_k: int = 10,
        namespace: str = "default",
        filter: Optional[Dict[str, Any]] = None,
        model: Optional[EmbeddingModel] = None,
        **kwargs
    ) -> VectorSearchResult:
        """Search by embedding a text query."""
        query_result = await self.embed_query(query_text, model=model)
        if not query_result.embeddings:
            raise ValueError("Failed to generate query embedding")
        return await self.search_vectors(query_result.embeddings[0], top_k, namespace, filter, **kwargs)

    async def get_vector(
        self,
        vector_id: str,
        namespace: str = "default",
        **kwargs
    ) -> Optional[List[float]]:
        """Get vector by ID."""
        if not self._vector_store_backend:
            raise RuntimeError("Vector store backend not initialized")
        return await self._vector_store_backend.search_by_id(vector_id, namespace, **kwargs)

    async def delete_vectors(
        self,
        ids: List[str],
        namespace: str = "default",
        **kwargs
    ) -> bool:
        """Delete vectors from store."""
        if not self._vector_store_backend:
            raise RuntimeError("Vector store backend not initialized")
        return await self._vector_store_backend.delete_vectors(ids, namespace, **kwargs)

    async def update_metadata(
        self,
        ids: List[str],
        metadata: List[Dict[str, Any]],
        namespace: str = "default",
        **kwargs
    ) -> bool:
        """Update vector metadata."""
        if not self._vector_store_backend:
            raise RuntimeError("Vector store backend not initialized")
        return await self._vector_store_backend.update_metadata(ids, metadata, namespace, **kwargs)

    async def count_vectors(
        self,
        namespace: str = "default",
        **kwargs
    ) -> int:
        """Count vectors in namespace."""
        if not self._vector_store_backend:
            raise RuntimeError("Vector store backend not initialized")
        return await self._vector_store_backend.count_vectors(namespace, **kwargs)

    # Convenience methods for batch processing
    async def embed_and_store(
        self,
        texts: List[str],
        ids: List[str],
        metadata: Optional[List[Dict[str, Any]]] = None,
        namespace: str = "default",
        model: Optional[EmbeddingModel] = None,
        **kwargs
    ) -> bool:
        """Embed texts and store in vector database."""
        result = await self.embed_texts(texts, model=model, **kwargs)
        return await self.add_vectors(result.embeddings, ids, metadata, namespace, **kwargs)

    async def find_similar_texts(
        self,
        query_text: str,
        top_k: int = 10,
        namespace: str = "default",
        filter: Optional[Dict[str, Any]] = None,
        model: Optional[EmbeddingModel] = None,
        **kwargs
    ) -> VectorSearchResult:
        """Find similar texts to query."""
        return await self.search_by_text(query_text, top_k, namespace, filter, model, **kwargs)

    async def execute(self, operation: str, **kwargs) -> Any:
        """Execute embedding module operation."""
        operations = {
            # Text embeddings
            "embed_texts": self.embed_texts,
            "embed_query": self.embed_query,
            "embed_documents": self.embed_documents,
            # Image embeddings
            "embed_images": self.embed_images,
            # Video embeddings
            "embed_videos": self.embed_videos,
            # Audio embeddings
            "embed_audio": self.embed_audio,
            # Multimodal embeddings
            "embed_multimodal": self.embed_multimodal,
            "embed_text_image_pairs": self.embed_text_image_pairs,
            # Code embeddings
            "embed_code": self.embed_code,
            # Vector operations
            "compute_similarity": self.compute_similarity,
            "compute_pairwise_similarity": self.compute_pairwise_similarity,
            "normalize_vectors": self.normalize_vectors,
            "reduce_dimensions": self.reduce_dimensions,
            "cluster_vectors": self.cluster_vectors,
            # Vector store
            "add_vectors": self.add_vectors,
            "search_vectors": self.search_vectors,
            "search_by_text": self.search_by_text,
            "get_vector": self.get_vector,
            "delete_vectors": self.delete_vectors,
            "update_metadata": self.update_metadata,
            "count_vectors": self.count_vectors,
            # Convenience
            "embed_and_store": self.embed_and_store,
            "find_similar_texts": self.find_similar_texts,
        }
        if operation in operations:
            return await operations[operation](**kwargs)
        raise NotImplementedError(f"Operation '{operation}' not supported")


# Mock backend implementations
class MockTextEmbeddingBackend(TextEmbeddingBackend):
    async def initialize(self, config: Dict[str, Any]) -> None:
        pass
    async def cleanup(self) -> None:
        pass
    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy", "backend": "mock_text_embedding"}
    async def get_model_info(self) -> EmbeddingModelInfo:
        return EmbeddingModelInfo(
            model_id="mock", name="Mock Text Embedding", provider="mock",
            dimensions=768, max_sequence_length=512,
            supported_types=[EmbeddingType.TEXT],
            supported_pooling=[PoolingStrategy.MEAN, PoolingStrategy.CLS]
        )
    async def embed_texts(self, texts: List[str], model: Optional[EmbeddingModel] = None, pooling: Optional[PoolingStrategy] = None, normalize: bool = True, **kwargs) -> EmbeddingResult:
        import random, time
        start = time.time()
        embeddings = [[random.random() for _ in range(768)] for _ in texts]
        if normalize:
            embeddings = [self._normalize(e) for e in embeddings]
        return EmbeddingResult(
            embeddings=embeddings, dimensions=768,
            model=model or EmbeddingModel.SENTENCE_TRANSFORMERS_MINILM,
            input_type=EmbeddingType.TEXT,
            token_counts=[len(t.split()) for t in texts],
            processing_time=time.time() - start,
            pooling_strategy=pooling
        )
    async def embed_query(self, query: str, model: Optional[EmbeddingModel] = None, pooling: Optional[PoolingStrategy] = None, normalize: bool = True, **kwargs) -> EmbeddingResult:
        return await self.embed_texts([query], model, pooling, normalize, **kwargs)
    async def embed_documents(self, documents: List[str], model: Optional[EmbeddingModel] = None, pooling: Optional[PoolingStrategy] = None, normalize: bool = True, **kwargs) -> EmbeddingResult:
        return await self.embed_texts(documents, model, pooling, normalize, **kwargs)
    def _normalize(self, vec: List[float]) -> List[float]:
        import math
        norm = math.sqrt(sum(x*x for x in vec))
        return [x/norm for x in vec] if norm > 0 else vec


class MockImageEmbeddingBackend(ImageEmbeddingBackend):
    async def initialize(self, config: Dict[str, Any]) -> None:
        pass
    async def cleanup(self) -> None:
        pass
    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy", "backend": "mock_image_embedding"}
    async def get_model_info(self) -> EmbeddingModelInfo:
        return EmbeddingModelInfo(
            model_id="mock", name="Mock Image Embedding", provider="mock",
            dimensions=512, max_sequence_length=0,
            supported_types=[EmbeddingType.IMAGE],
            supported_pooling=[PoolingStrategy.MEAN]
        )
    async def embed_images(self, images: List[Any], model: Optional[EmbeddingModel] = None, normalize: bool = True, **kwargs) -> EmbeddingResult:
        import random, time
        start = time.time()
        embeddings = [[random.random() for _ in range(512)] for _ in images]
        return EmbeddingResult(
            embeddings=embeddings, dimensions=512,
            model=model or EmbeddingModel.CLIP_VIT_B32,
            input_type=EmbeddingType.IMAGE,
            processing_time=time.time() - start
        )


class MockVideoEmbeddingBackend(VideoEmbeddingBackend):
    async def initialize(self, config: Dict[str, Any]) -> None:
        pass
    async def cleanup(self) -> None:
        pass
    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy", "backend": "mock_video_embedding"}
    async def get_model_info(self) -> EmbeddingModelInfo:
        return EmbeddingModelInfo(
            model_id="mock", name="Mock Video Embedding", provider="mock",
            dimensions=768, max_sequence_length=0,
            supported_types=[EmbeddingType.VIDEO],
            supported_pooling=[PoolingStrategy.MEAN]
        )
    async def embed_videos(self, videos: List[Any], model: Optional[EmbeddingModel] = None, normalize: bool = True, **kwargs) -> EmbeddingResult:
        import random, time
        start = time.time()
        embeddings = [[random.random() for _ in range(768)] for _ in videos]
        return EmbeddingResult(
            embeddings=embeddings, dimensions=768,
            model=model or EmbeddingModel.VIDEO_MAE,
            input_type=EmbeddingType.VIDEO,
            processing_time=time.time() - start
        )


class MockAudioEmbeddingBackend(AudioEmbeddingBackend):
    async def initialize(self, config: Dict[str, Any]) -> None:
        pass
    async def cleanup(self) -> None:
        pass
    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy", "backend": "mock_audio_embedding"}
    async def get_model_info(self) -> EmbeddingModelInfo:
        return EmbeddingModelInfo(
            model_id="mock", name="Mock Audio Embedding", provider="mock",
            dimensions=768, max_sequence_length=0,
            supported_types=[EmbeddingType.AUDIO],
            supported_pooling=[PoolingStrategy.MEAN]
        )
    async def embed_audio(self, audios: List[Any], model: Optional[EmbeddingModel] = None, normalize: bool = True, **kwargs) -> EmbeddingResult:
        import random, time
        start = time.time()
        embeddings = [[random.random() for _ in range(768)] for _ in audios]
        return EmbeddingResult(
            embeddings=embeddings, dimensions=768,
            model=model or EmbeddingModel.CLAP,
            input_type=EmbeddingType.AUDIO,
            processing_time=time.time() - start
        )


class MockMultimodalEmbeddingBackend(MultimodalEmbeddingBackend):
    async def initialize(self, config: Dict[str, Any]) -> None:
        pass
    async def cleanup(self) -> None:
        pass
    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy", "backend": "mock_multimodal_embedding"}
    async def get_model_info(self) -> EmbeddingModelInfo:
        return EmbeddingModelInfo(
            model_id="mock", name="Mock Multimodal Embedding", provider="mock",
            dimensions=512, max_sequence_length=77,
            supported_types=[EmbeddingType.TEXT, EmbeddingType.IMAGE, EmbeddingType.MULTIMODAL],
            supported_pooling=[PoolingStrategy.MEAN, PoolingStrategy.CLS]
        )
    async def embed_multimodal(self, texts: Optional[List[str]] = None, images: Optional[List[Any]] = None, model: Optional[EmbeddingModel] = None, normalize: bool = True, **kwargs) -> EmbeddingResult:
        import random, time
        start = time.time()
        count = len(texts) if texts else len(images) if images else 1
        embeddings = [[random.random() for _ in range(512)] for _ in range(count)]
        return EmbeddingResult(
            embeddings=embeddings, dimensions=512,
            model=model or EmbeddingModel.CLIP_VIT_B32,
            input_type=EmbeddingType.MULTIMODAL,
            processing_time=time.time() - start
        )
    async def embed_text_image_pairs(self, pairs: List[Tuple[str, Any]], model: Optional[EmbeddingModel] = None, normalize: bool = True, **kwargs) -> EmbeddingResult:
        return await self.embed_multimodal(
            texts=[p[0] for p in pairs],
            images=[p[1] for p in pairs],
            model=model, normalize=normalize, **kwargs
        )


class MockCodeEmbeddingBackend(CodeEmbeddingBackend):
    async def initialize(self, config: Dict[str, Any]) -> None:
        pass
    async def cleanup(self) -> None:
        pass
    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy", "backend": "mock_code_embedding"}
    async def get_model_info(self) -> EmbeddingModelInfo:
        return EmbeddingModelInfo(
            model_id="mock", name="Mock Code Embedding", provider="mock",
            dimensions=768, max_sequence_length=512,
            supported_types=[EmbeddingType.CODE],
            supported_pooling=[PoolingStrategy.MEAN, PoolingStrategy.CLS]
        )
    async def embed_code(self, code_snippets: List[str], language: Optional[str] = None, model: Optional[EmbeddingModel] = None, normalize: bool = True, **kwargs) -> EmbeddingResult:
        import random, time
        start = time.time()
        embeddings = [[random.random() for _ in range(768)] for _ in code_snippets]
        return EmbeddingResult(
            embeddings=embeddings, dimensions=768,
            model=model or EmbeddingModel.CODEBERT,
            input_type=EmbeddingType.CODE,
            token_counts=[len(c.split()) for c in code_snippets],
            processing_time=time.time() - start
        )


class MockVectorOperationsBackend(VectorOperationsBackend):
    async def initialize(self, config: Dict[str, Any]) -> None:
        pass
    async def cleanup(self) -> None:
        pass
    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy", "backend": "mock_vector_operations"}
    async def compute_similarity(self, query: List[float], candidates: List[List[float]], metric: DistanceMetric = DistanceMetric.COSINE, top_k: int = 10, **kwargs) -> SimilarityResult:
        import time, numpy as np
        start = time.time()
        query_arr = np.array(query)
        candidates_arr = np.array(candidates)

        if metric == DistanceMetric.COSINE:
            query_norm = query_arr / (np.linalg.norm(query_arr) + 1e-8)
            cand_norms = candidates_arr / (np.linalg.norm(candidates_arr, axis=1, keepdims=True) + 1e-8)
            scores = np.dot(cand_norms, query_norm)
        elif metric == DistanceMetric.DOT_PRODUCT:
            scores = np.dot(candidates_arr, query_arr)
        else:
            scores = -np.linalg.norm(candidates_arr - query_arr, axis=1)

        indices = np.argsort(scores)[::-1][:top_k]
        return SimilarityResult(
            query_embedding=query,
            candidates=[{"index": int(i), "score": float(scores[i])} for i in indices],
            scores=[float(scores[i]) for i in indices],
            indices=[int(i) for i in indices],
            metric=metric,
            top_k=top_k,
            processing_time=time.time() - start
        )
    async def compute_pairwise_similarity(self, vectors_a: List[List[float]], vectors_b: List[List[float]], metric: DistanceMetric = DistanceMetric.COSINE, **kwargs) -> np.ndarray:
        import numpy as np
        a = np.array(vectors_a)
        b = np.array(vectors_b)
        if metric == DistanceMetric.COSINE:
            a_norm = a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-8)
            b_norm = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-8)
            return np.dot(a_norm, b_norm.T)
        return np.dot(a, b.T)
    async def normalize_vectors(self, vectors: List[List[float]], norm: str = "l2", **kwargs) -> List[List[float]]:
        import numpy as np
        arr = np.array(vectors)
        if norm == "l2":
            norms = np.linalg.norm(arr, axis=1, keepdims=True)
            arr = arr / (norms + 1e-8)
        return arr.tolist()
    async def reduce_dimensions(self, vectors: List[List[float]], target_dim: int, method: str = "pca", **kwargs) -> List[List[float]]:
        import numpy as np
        from sklearn.decomposition import PCA
        arr = np.array(vectors)
        if method == "pca":
            pca = PCA(n_components=target_dim)
            reduced = pca.fit_transform(arr)
            return reduced.tolist()
        return vectors
    async def cluster_vectors(self, vectors: List[List[float]], n_clusters: int, algorithm: str = "kmeans", **kwargs) -> Dict[str, Any]:
        import numpy as np
        from sklearn.cluster import KMeans
        arr = np.array(vectors)
        if algorithm == "kmeans":
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            labels = kmeans.fit_predict(arr)
            return {
                "labels": labels.tolist(),
                "centroids": kmeans.cluster_centers_.tolist(),
                "inertia": float(kmeans.inertia_)
            }
        return {"labels": [0]*len(vectors), "centroids": [], "inertia": 0.0}


class MockVectorStoreBackend(VectorStoreBackend):
    def __init__(self):
        self._stores: Dict[str, Dict[str, Dict[str, Any]]] = {}

    async def initialize(self, config: Dict[str, Any]) -> None:
        pass
    async def cleanup(self) -> None:
        pass
    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy", "backend": "mock_vector_store", "namespaces": list(self._stores.keys())}

    async def add_vectors(self, vectors: List[List[float]], ids: List[str], metadata: Optional[List[Dict[str, Any]]] = None, namespace: str = "default", **kwargs) -> bool:
        if namespace not in self._stores:
            self._stores[namespace] = {}
        for i, (vector, id) in enumerate(zip(vectors, ids)):
            self._stores[namespace][id] = {
                "vector": vector,
                "metadata": metadata[i] if metadata else {}
            }
        return True

    async def search(self, query_vector: List[float], top_k: int = 10, namespace: str = "default", filter: Optional[Dict[str, Any]] = None, metric: DistanceMetric = DistanceMetric.COSINE, **kwargs) -> VectorSearchResult:
        import time, numpy as np
        start = time.time()
        if namespace not in self._stores:
            return VectorSearchResult(hits=[], total_hits=0, search_time=time.time() - start)

        items = self._stores[namespace]
        if not items:
            return VectorSearchResult(hits=[], total_hits=0, search_time=time.time() - start)

        query_arr = np.array(query_vector)
        scores = []
        ids = []
        for id, data in items.items():
            vec = np.array(data["vector"])
            if metric == DistanceMetric.COSINE:
                score = np.dot(query_arr, vec) / (np.linalg.norm(query_arr) * np.linalg.norm(vec) + 1e-8)
            else:
                score = -np.linalg.norm(query_arr - vec)
            scores.append(score)
            ids.append(id)

        indices = np.argsort(scores)[::-1][:top_k]
        hits = [
            {"id": ids[i], "score": float(scores[i]), "metadata": items[ids[i]].get("metadata", {})}
            for i in indices
        ]
        return VectorSearchResult(
            query_vector=query_vector,
            hits=hits,
            total_hits=len(items),
            search_time=time.time() - start
        )

    async def search_by_id(self, vector_id: str, namespace: str = "default", **kwargs) -> Optional[List[float]]:
        if namespace in self._stores and vector_id in self._stores[namespace]:
            return self._stores[namespace][vector_id]["vector"]
        return None

    async def delete_vectors(self, ids: List[str], namespace: str = "default", **kwargs) -> bool:
        if namespace in self._stores:
            for id in ids:
                self._stores[namespace].pop(id, None)
        return True

    async def update_metadata(self, ids: List[str], metadata: List[Dict[str, Any]], namespace: str = "default", **kwargs) -> bool:
        if namespace in self._stores:
            for id, meta in zip(ids, metadata):
                if id in self._stores[namespace]:
                    self._stores[namespace][id]["metadata"] = meta
        return True

    async def count_vectors(self, namespace: str = "default", **kwargs) -> int:
        if namespace in self._stores:
            return len(self._stores[namespace])
        return 0


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