"""
Knowledge Runtime Module

Provides knowledge base management, document ingestion, vector search,
entity extraction, and knowledge graph capabilities.
"""

from runtime.knowledge.module import (
    KnowledgeModule,
    KnowledgeBaseBackend,
    LocalKnowledgeBackend,
    KnowledgeBase,
    Document,
    KnowledgeChunk,
    Entity,
    Relation,
    KnowledgeSearchResult,
    DocumentStatus,
    KnowledgeType,
)

__all__ = [
    "KnowledgeModule",
    "KnowledgeBaseBackend",
    "LocalKnowledgeBackend",
    "KnowledgeBase",
    "Document",
    "KnowledgeChunk",
    "Entity",
    "Relation",
    "KnowledgeSearchResult",
    "DocumentStatus",
    "KnowledgeType",
]