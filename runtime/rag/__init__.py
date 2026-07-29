"""
RAG Runtime Module

Provides Retrieval-Augmented Generation capabilities including:
- Document retrieval (dense, sparse, hybrid)
- Query rewriting and expansion
- Reranking
- Answer generation with citations
- Multi-hop reasoning
- RAG evaluation
"""

from runtime.rag.module import (
    RAGModule,
    RetrievalMethod,
    RerankMethod,
    QueryRewriteMethod,
    GenerationMethod,
    RetrievalStrategy,
    RetrievalResult,
    RetrievalResponse,
    RerankResult,
    RewrittenQuery,
    GeneratedAnswer,
    RAGResponse,
    Document,
    RetrievalBackend,
    RerankBackend,
    QueryRewriteBackend,
    GeneratorBackend,
    EvaluationBackend,
)

__all__ = [
    "RAGModule",
    "RetrievalMethod",
    "RerankMethod",
    "QueryRewriteMethod",
    "GenerationMethod",
    "RetrievalStrategy",
    "RetrievalResult",
    "RetrievalResponse",
    "RerankResult",
    "RewrittenQuery",
    "GeneratedAnswer",
    "RAGResponse",
    "Document",
    "RetrievalBackend",
    "RerankBackend",
    "QueryRewriteBackend",
    "GeneratorBackend",
    "EvaluationBackend",
]