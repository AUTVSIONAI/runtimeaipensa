"""
Knowledge Runtime Module

Provides knowledge base management, document ingestion, vector search,
entity extraction, and knowledge graph capabilities.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional, Set
import asyncio
import json
import logging
import uuid
from pathlib import Path

import aiofiles

from runtime.modules import (
    RuntimeModule,
    ModuleMetadata,
    ModuleState,
)

logger = logging.getLogger(__name__)


class DocumentStatus(Enum):
    """Document processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"
    ARCHIVED = "archived"


class KnowledgeType(Enum):
    """Type of knowledge content."""
    DOCUMENT = "document"
    ARTICLE = "article"
    FAQ = "faq"
    MANUAL = "manual"
    SPECIFICATION = "specification"
    CODE = "code"
    WEBPAGE = "webpage"
    PDF = "pdf"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    CUSTOM = "custom"


@dataclass
class KnowledgeChunk:
    """A chunk of knowledge content."""
    chunk_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    document_id: str = ""
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    start_char: int = 0
    end_char: int = 0
    chunk_index: int = 0
    token_count: int = 0


@dataclass
class KnowledgeBase:
    """Knowledge base container."""
    kb_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    owner_id: str = ""
    settings: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    document_count: int = 0
    total_chunks: int = 0
    total_tokens: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kb_id": self.kb_id,
            "name": self.name,
            "description": self.description,
            "owner_id": self.owner_id,
            "settings": self.settings,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "document_count": self.document_count,
            "total_chunks": self.total_chunks,
            "total_tokens": self.total_tokens
        }


@dataclass
class Document:
    """Knowledge document."""
    document_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    knowledge_base_id: str = ""
    title: str = ""
    content: str = ""
    source: str = ""  # URL, file path, etc.
    source_type: str = ""
    knowledge_type: KnowledgeType = KnowledgeType.DOCUMENT
    status: DocumentStatus = DocumentStatus.PENDING
    language: str = "en"
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    chunks: List[KnowledgeChunk] = field(default_factory=list)
    entity_ids: List[str] = field(default_factory=list)
    version: int = 1
    parent_document_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "knowledge_base_id": self.knowledge_base_id,
            "title": self.title,
            "content": self.content,
            "source": self.source,
            "source_type": self.source_type,
            "knowledge_type": self.knowledge_type.value,
            "status": self.status.value,
            "language": self.language,
            "tags": self.tags,
            "metadata": self.metadata,
            "chunks": [c.__dict__ for c in self.chunks],
            "entity_ids": self.entity_ids,
            "version": self.version,
            "parent_document_id": self.parent_document_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "error": self.error
        }


@dataclass
class Entity:
    """Knowledge graph entity."""
    entity_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    entity_type: str = ""  # person, organization, location, concept, etc.
    description: str = ""
    aliases: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    source_documents: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Relation:
    """Knowledge graph relation."""
    relation_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    source_entity_id: str = ""
    target_entity_id: str = ""
    relation_type: str = ""  # works_for, located_in, part_of, etc.
    properties: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    source_documents: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class KnowledgeSearchResult:
    """Knowledge search result."""
    document_id: str
    title: str
    snippet: str
    score: float
    knowledge_type: KnowledgeType
    metadata: Dict[str, Any] = field(default_factory=dict)
    chunks: List[KnowledgeChunk] = field(default_factory=list)


class KnowledgeBaseBackend(ABC):
    """Abstract knowledge base backend."""

    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    async def create_knowledge_base(self, kb: KnowledgeBase) -> KnowledgeBase:
        pass

    @abstractmethod
    async def get_knowledge_base(self, kb_id: str) -> Optional[KnowledgeBase]:
        pass

    @abstractmethod
    async def list_knowledge_bases(self, **kwargs) -> List[KnowledgeBase]:
        pass

    @abstractmethod
    async def delete_knowledge_base(self, kb_id: str) -> bool:
        pass

    # Documents
    @abstractmethod
    async def add_document(self, document: Document) -> Document:
        pass

    @abstractmethod
    async def get_document(self, document_id: str) -> Optional[Document]:
        pass

    @abstractmethod
    async def update_document(self, document: Document) -> Document:
        pass

    @abstractmethod
    async def delete_document(self, document_id: str) -> bool:
        pass

    @abstractmethod
    async def list_documents(
        self,
        knowledge_base_id: str,
        status: Optional[DocumentStatus] = None,
        knowledge_type: Optional[KnowledgeType] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Document]:
        pass

    # Search
    @abstractmethod
    async def search(
        self,
        knowledge_base_id: str,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        search_type: str = "hybrid"  # vector, keyword, hybrid
    ) -> List[KnowledgeSearchResult]:
        pass

    # Entities and Relations
    @abstractmethod
    async def add_entity(self, entity: Entity) -> Entity:
        pass

    @abstractmethod
    async def get_entity(self, entity_id: str) -> Optional[Entity]:
        pass

    @abstractmethod
    async def add_relation(self, relation: Relation) -> Relation:
        pass

    @abstractmethod
    async def get_relations(self, entity_id: str) -> List[Relation]:
        pass


class LocalKnowledgeBackend(KnowledgeBaseBackend):
    """Local file-based knowledge backend."""

    def __init__(self):
        self._knowledge_bases: Dict[str, KnowledgeBase] = {}
        self._documents: Dict[str, Document] = {}
        self._entities: Dict[str, Entity] = {}
        self._relations: Dict[str, Relation] = {}
        self._index: Dict[str, Dict[str, Any]] = {}  # Simple inverted index

    async def initialize(self, config: Dict[str, Any]) -> None:
        self._storage_path = Path(config.get("storage_path", "./knowledge"))
        self._storage_path.mkdir(parents=True, exist_ok=True)
        await self._load_from_disk()
        logger.info(f"Local knowledge backend initialized at {self._storage_path}")

    async def _load_from_disk(self) -> None:
        """Load knowledge bases from disk."""
        # Implementation would load JSON files
        pass

    async def _save_to_disk(self) -> None:
        """Save knowledge bases to disk."""
        # Implementation would save JSON files
        pass

    async def create_knowledge_base(self, kb: KnowledgeBase) -> KnowledgeBase:
        kb.created_at = datetime.utcnow()
        kb.updated_at = datetime.utcnow()
        self._knowledge_bases[kb.kb_id] = kb
        await self._save_to_disk()
        return kb

    async def get_knowledge_base(self, kb_id: str) -> Optional[KnowledgeBase]:
        return self._knowledge_bases.get(kb_id)

    async def list_knowledge_bases(self, **kwargs) -> List[KnowledgeBase]:
        kbs = list(self._knowledge_bases.values())
        if "owner_id" in kwargs:
            kbs = [kb for kb in kbs if kb.owner_id == kwargs["owner_id"]]
        return kbs

    async def delete_knowledge_base(self, kb_id: str) -> bool:
        if kb_id in self._knowledge_bases:
            del self._knowledge_bases[kb_id]
            # Delete associated documents
            docs_to_delete = [d for d in self._documents.values() if d.knowledge_base_id == kb_id]
            for doc in docs_to_delete:
                del self._documents[doc.document_id]
            await self._save_to_disk()
            return True
        return False

    async def add_document(self, document: Document) -> Document:
        document.created_at = datetime.utcnow()
        document.updated_at = datetime.utcnow()
        self._documents[document.document_id] = document
        await self._save_to_disk()
        return document

    async def get_document(self, document_id: str) -> Optional[Document]:
        return self._documents.get(document_id)

    async def update_document(self, document: Document) -> Document:
        document.updated_at = datetime.utcnow()
        document.version += 1
        self._documents[document.document_id] = document
        await self._save_to_disk()
        return document

    async def delete_document(self, document_id: str) -> bool:
        if document_id in self._documents:
            del self._documents[document_id]
            await self._save_to_disk()
            return True
        return False

    async def list_documents(
        self,
        knowledge_base_id: str,
        status: Optional[DocumentStatus] = None,
        knowledge_type: Optional[KnowledgeType] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Document]:
        docs = [d for d in self._documents.values() if d.knowledge_base_id == knowledge_base_id]

        if status:
            docs = [d for d in docs if d.status == status]
        if knowledge_type:
            docs = [d for d in docs if d.knowledge_type == knowledge_type]

        docs.sort(key=lambda d: d.updated_at, reverse=True)
        return docs[offset:offset + limit]

    async def search(
        self,
        knowledge_base_id: str,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        search_type: str = "hybrid"
    ) -> List[KnowledgeSearchResult]:
        # Simple keyword search for local backend
        query_terms = query.lower().split()
        results = []

        for doc in self._documents.values():
            if doc.knowledge_base_id != knowledge_base_id:
                continue
            if doc.status != DocumentStatus.INDEXED:
                continue

            # Score based on keyword matches
            content_lower = doc.content.lower()
            title_lower = doc.title.lower()

            score = 0
            for term in query_terms:
                score += content_lower.count(term) * 1
                score += title_lower.count(term) * 5

            if score > 0:
                # Find best snippet
                snippet = ""
                for term in query_terms:
                    idx = content_lower.find(term)
                    if idx >= 0:
                        start = max(0, idx - 100)
                        end = min(len(doc.content), idx + 200)
                        snippet = doc.content[start:end]
                        break

                if not snippet:
                    snippet = doc.content[:300]

                results.append(KnowledgeSearchResult(
                    document_id=doc.document_id,
                    title=doc.title,
                    snippet=snippet,
                    score=score,
                    knowledge_type=doc.knowledge_type,
                    metadata=doc.metadata
                ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    async def add_entity(self, entity: Entity) -> Entity:
        entity.created_at = datetime.utcnow()
        entity.updated_at = datetime.utcnow()
        self._entities[entity.entity_id] = entity
        await self._save_to_disk()
        return entity

    async def get_entity(self, entity_id: str) -> Optional[Entity]:
        return self._entities.get(entity_id)

    async def add_relation(self, relation: Relation) -> Relation:
        relation.created_at = datetime.utcnow()
        self._relations[relation.relation_id] = relation
        await self._save_to_disk()
        return relation

    async def get_relations(self, entity_id: str) -> List[Relation]:
        return [r for r in self._relations.values()
                if r.source_entity_id == entity_id or r.target_entity_id == entity_id]


class KnowledgeModule(RuntimeModule):
    """
    Knowledge management module.

    Provides:
    - Knowledge base creation and management
    - Document ingestion and processing
    - Vector and keyword search
    - Entity extraction and knowledge graph
    - Version control for documents
    - Multi-language support
    """

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="knowledge",
            version="1.0.0",
            description="Knowledge base management with search and graph capabilities",
            author="AIPENSA",
            dependencies=["storage", "llm", "embedding"],
            provides=["knowledge_base", "document_processing", "semantic_search", "knowledge_graph"],
            tags={"knowledge", "search", "rag", "documents", "graph"}
        )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._backend: Optional[KnowledgeBaseBackend] = None
        self._config: Dict[str, Any] = {}
        self._processor_task: Optional[asyncio.Task] = None

    async def initialize(self, runtime: "Runtime", config: Dict[str, Any]) -> None:
        """Initialize knowledge module."""
        self._runtime = runtime
        self._config = {**self._config, **config}

        # Create backend
        backend_type = self._config.get("backend", "local")
        if backend_type == "local":
            self._backend = LocalKnowledgeBackend()
        else:
            raise ValueError(f"Unknown backend: {backend_type}")

        await self._backend.initialize(self._config.get("backend_config", {}))

        # Start document processor
        self._processor_task = asyncio.create_task(self._document_processor_loop())

        self.state = ModuleState.INITIALIZED
        logger.info("Knowledge module initialized")

    async def start(self) -> None:
        self.state = ModuleState.RUNNING
        logger.info("Knowledge module started")

    async def stop(self) -> None:
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        self.state = ModuleState.STOPPED
        logger.info("Knowledge module stopped")

    async def cleanup(self) -> None:
        await self.stop()
        self._backend = None
        self.state = ModuleState.UNINITIALIZED
        logger.info("Knowledge module cleaned up")

    async def health_check(self) -> Dict[str, Any]:
        return {
            "module": "knowledge",
            "status": self.state.value,
            "healthy": self.state == ModuleState.RUNNING,
            "knowledge_bases": len(await self.list_knowledge_bases()),
            "total_documents": len(self._documents) if hasattr(self, '_documents') else 0
        }

    # Knowledge Base Operations
    async def create_knowledge_base(
        self,
        name: str,
        owner_id: str,
        description: str = "",
        settings: Optional[Dict[str, Any]] = None,
        kb_id: Optional[str] = None
    ) -> KnowledgeBase:
        """Create a new knowledge base."""
        kb = KnowledgeBase(
            kb_id=kb_id or str(uuid.uuid4())[:8],
            name=name,
            description=description,
            owner_id=owner_id,
            settings=settings or {}
        )
        return await self._backend.create_knowledge_base(kb)

    async def get_knowledge_base(self, kb_id: str) -> Optional[KnowledgeBase]:
        """Get knowledge base by ID."""
        return await self._backend.get_knowledge_base(kb_id)

    async def list_knowledge_bases(self, owner_id: Optional[str] = None) -> List[KnowledgeBase]:
        """List knowledge bases."""
        return await self._backend.list_knowledge_bases(owner_id=owner_id)

    async def delete_knowledge_base(self, kb_id: str, user_id: str) -> bool:
        """Delete knowledge base."""
        kb = await self.get_knowledge_base(kb_id)
        if not kb:
            return False
        if kb.owner_id != user_id:
            raise PermissionError("Only owner can delete knowledge base")
        return await self._backend.delete_knowledge_base(kb_id)

    # Document Operations
    async def add_document(
        self,
        knowledge_base_id: str,
        title: str,
        content: str,
        source: str = "",
        source_type: str = "text",
        knowledge_type: KnowledgeType = KnowledgeType.DOCUMENT,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        document_id: Optional[str] = None
    ) -> Document:
        """Add document to knowledge base."""
        kb = await self.get_knowledge_base(knowledge_base_id)
        if not kb:
            raise ValueError("Knowledge base not found")

        document = Document(
            knowledge_base_id=knowledge_base_id,
            title=title,
            content=content,
            source=source,
            source_type=source_type,
            knowledge_type=knowledge_type,
            tags=tags or [],
            metadata=metadata or {},
            document_id=document_id or str(uuid.uuid4())[:8]
        )

        document = await self._backend.add_document(document)

        # Queue for processing
        document.status = DocumentStatus.PENDING
        await self._backend.update_document(document)

        return document

    async def get_document(self, document_id: str) -> Optional[Document]:
        """Get document by ID."""
        return await self._backend.get_document(document_id)

    async def update_document(self, document: Document) -> Document:
        """Update document."""
        return await self._backend.update_document(document)

    async def delete_document(self, document_id: str) -> bool:
        """Delete document."""
        return await self._backend.delete_document(document_id)

    async def list_documents(
        self,
        knowledge_base_id: str,
        status: Optional[DocumentStatus] = None,
        knowledge_type: Optional[KnowledgeType] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Document]:
        """List documents in knowledge base."""
        return await self._backend.list_documents(knowledge_base_id, status, knowledge_type, limit, offset)

    async def process_document(self, document_id: str) -> Document:
        """Process document (chunk, embed, extract entities)."""
        document = await self._backend.get_document(document_id)
        if not document:
            raise ValueError("Document not found")

        document.status = DocumentStatus.PROCESSING
        await self._backend.update_document(document)

        try:
            # Chunk document
            chunks = await self._chunk_document(document)
            document.chunks = chunks

            # Generate embeddings for chunks
            embedding_module = self._runtime.modules.get("embedding")
            if embedding_module:
                for chunk in chunks:
                    embedding_result = await embedding_module.execute(
                        "embed_text",
                        text=chunk.content
                    )
                    chunk.embedding = embedding_result.get("embedding", [])

            # Extract entities
            entities = await self._extract_entities(document)
            document.entity_ids = [e.entity_id for e in entities]

            document.status = DocumentStatus.INDEXED
            document.processed_at = datetime.utcnow()

        except Exception as e:
            document.status = DocumentStatus.FAILED
            document.error = str(e)
            logger.error(f"Document processing failed: {e}")

        await self._backend.update_document(document)
        return document

    async def _chunk_document(self, document: Document) -> List[KnowledgeChunk]:
        """Split document into chunks."""
        # Simple chunking by paragraphs
        paragraphs = document.content.split("\n\n")
        chunks = []

        for i, para in enumerate(paragraphs):
            if not para.strip():
                continue

            chunk = KnowledgeChunk(
                document_id=document.document_id,
                content=para.strip(),
                start_char=0,  # Would calculate actual position
                end_char=len(para.strip()),
                chunk_index=i,
                token_count=len(para.split())
            )
            chunks.append(chunk)

        return chunks

    async def _extract_entities(self, document: Document) -> List[Entity]:
        """Extract entities from document using LLM."""
        llm_module = self._runtime.modules.get("llm")
        if not llm_module:
            return []

        # Use LLM to extract entities
        prompt = f"""Extract entities from the following text. Return JSON array of entities with:
        - name: entity name
        - type: person, organization, location, concept, product, event
        - description: brief description
        - aliases: alternative names
        - confidence: 0-1

        Text: {document.content[:4000]}"""

        try:
            response = await llm_module.execute("complete", prompt=prompt)
            # Parse and create entities
            # Simplified for now
            return []
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return []

    # Search
    async def search(
        self,
        knowledge_base_id: str,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        search_type: str = "hybrid"
    ) -> List[KnowledgeSearchResult]:
        """Search knowledge base."""
        return await self._backend.search(knowledge_base_id, query, limit, filters, search_type)

    # Entity Operations
    async def add_entity(self, entity: Entity) -> Entity:
        """Add entity to knowledge graph."""
        return await self._backend.add_entity(entity)

    async def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID."""
        return await self._backend.get_entity(entity_id)

    async def add_relation(self, relation: Relation) -> Relation:
        """Add relation to knowledge graph."""
        return await self._backend.add_relation(relation)

    async def get_relations(self, entity_id: str) -> List[Relation]:
        """Get relations for entity."""
        return await self._backend.get_relations(entity_id)

    # Bulk Operations
    async def ingest_from_directory(
        self,
        knowledge_base_id: str,
        directory: str,
        file_patterns: Optional[List[str]] = None,
        recursive: bool = True
    ) -> List[Document]:
        """Ingest documents from directory."""
        patterns = file_patterns or ["*.txt", "*.md", "*.pdf", "*.html"]
        documents = []

        path = Path(directory)
        if not path.exists():
            raise ValueError("Directory not found")

        for pattern in patterns:
            files = path.rglob(pattern) if recursive else path.glob(pattern)
            for file in files:
                if file.is_file():
                    try:
                        content = file.read_text(encoding="utf-8")
                        doc = await self.add_document(
                            knowledge_base_id=knowledge_base_id,
                            title=file.stem,
                            content=content,
                            source=str(file),
                            source_type="file",
                            knowledge_type=KnowledgeType.DOCUMENT,
                            metadata={"size": file.stat().st_size}
                        )
                        documents.append(doc)
                    except Exception as e:
                        logger.error(f"Failed to ingest {file}: {e}")

        return documents

    # Document Processor Loop
    async def _document_processor_loop(self) -> None:
        """Background loop to process pending documents."""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds

                # Find pending documents
                for kb in await self.list_knowledge_bases():
                    docs = await self.list_documents(kb.kb_id, status=DocumentStatus.PENDING, limit=10)
                    for doc in docs:
                        await self.process_document(doc.document_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Document processor error: {e}")

    # Module Operations
    async def execute(self, operation: str, **kwargs) -> Any:
        mapping = {
            "create_knowledge_base": self.create_knowledge_base,
            "get_knowledge_base": self.get_knowledge_base,
            "list_knowledge_bases": self.list_knowledge_bases,
            "delete_knowledge_base": self.delete_knowledge_base,
            "add_document": self.add_document,
            "get_document": self.get_document,
            "update_document": self.update_document,
            "delete_document": self.delete_document,
            "list_documents": self.list_documents,
            "process_document": self.process_document,
            "search": self.search,
            "add_entity": self.add_entity,
            "get_entity": self.get_entity,
            "add_relation": self.add_relation,
            "get_relations": self.get_relations,
            "ingest_from_directory": self.ingest_from_directory,
        }
        if operation in mapping:
            return await mapping[operation](**kwargs)
        raise NotImplementedError(f"Operation '{operation}' not supported")


__all__ = [
    "KnowledgeModule",
    "KnowledgeBaseBackend",
    "LocalKnowledgeBackend",
    "Document",
    "KnowledgeChunk",
    "Entity",
    "Relation",
    "KnowledgeSearchResult",
    "DocumentStatus",
    "KnowledgeType",
]