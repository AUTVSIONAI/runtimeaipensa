"""
Storage Runtime Module

Provides object storage, file storage, blob storage with S3-compatible API,
metadata management, and multiple backend support.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, BinaryIO, Dict, List, Optional, Union
import asyncio
import hashlib
import logging
import mimetypes
import os
import uuid
from pathlib import Path
from io import BytesIO

import aiofiles
import aiohttp

from runtime.modules import (
    RuntimeModule,
    ModuleMetadata,
    ModuleState,
)

logger = logging.getLogger(__name__)


class StorageClass(Enum):
    """Storage class/tier."""
    STANDARD = "standard"
    INFREQUENT_ACCESS = "infrequent_access"
    ARCHIVE = "archive"
    REDUCED_REDUNDANCY = "reduced_redundancy"


class ObjectVersioning(Enum):
    """Object versioning mode."""
    DISABLED = "disabled"
    ENABLED = "enabled"
    SUSPENDED = "suspended"


@dataclass
class StorageObject:
    """Storage object metadata."""
    key: str
    bucket: str
    size: int = 0
    etag: str = ""
    content_type: str = "application/octet-stream"
    content_encoding: Optional[str] = None
    content_disposition: Optional[str] = None
    content_language: Optional[str] = None
    cache_control: Optional[str] = None
    metadata: Dict[str, str] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)
    version_id: Optional[str] = None
    is_latest: bool = True
    storage_class: StorageClass = StorageClass.STANDARD
    created_at: datetime = field(default_factory=datetime.utcnow)
    modified_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    owner: Optional[str] = None
    acl: List[Dict[str, Any]] = field(default_factory=list)
    legal_hold: bool = False
    retention_until: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "bucket": self.bucket,
            "size": self.size,
            "etag": self.etag,
            "content_type": self.content_type,
            "content_encoding": self.content_encoding,
            "content_disposition": self.content_disposition,
            "content_language": self.content_language,
            "cache_control": self.cache_control,
            "metadata": self.metadata,
            "tags": self.tags,
            "version_id": self.version_id,
            "is_latest": self.is_latest,
            "storage_class": self.storage_class.value,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "owner": self.owner,
            "acl": self.acl,
            "legal_hold": self.legal_hold,
            "retention_until": self.retention_until.isoformat() if self.retention_until else None
        }


@dataclass
class Bucket:
    """Storage bucket."""
    name: str
    region: str = "us-east-1"
    creation_date: datetime = field(default_factory=datetime.utcnow)
    versioning: ObjectVersioning = ObjectVersioning.DISABLED
    default_storage_class: StorageClass = StorageClass.STANDARD
    cors_rules: List[Dict[str, Any]] = field(default_factory=list)
    lifecycle_rules: List[Dict[str, Any]] = field(default_factory=list)
    policy: Optional[Dict[str, Any]] = None
    tags: Dict[str, str] = field(default_factory=dict)
    owner: Optional[str] = None
    acl: List[Dict[str, Any]] = field(default_factory=list)
    encryption: Optional[Dict[str, Any]] = None
    logging: Optional[Dict[str, Any]] = None
    website: Optional[Dict[str, Any]] = None
    requester_pays: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "region": self.region,
            "creation_date": self.creation_date.isoformat(),
            "versioning": self.versioning.value,
            "default_storage_class": self.default_storage_class.value,
            "cors_rules": self.cors_rules,
            "lifecycle_rules": self.lifecycle_rules,
            "policy": self.policy,
            "tags": self.tags,
            "owner": self.owner,
            "acl": self.acl,
            "encryption": self.encryption,
            "logging": self.logging,
            "website": self.website,
            "requester_pays": self.requester_pays
        }


@dataclass
class PutObjectResult:
    """Result of put object operation."""
    key: str
    bucket: str
    etag: str
    version_id: Optional[str] = None
    size: int = 0
    storage_class: StorageClass = StorageClass.STANDARD
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ListObjectsResult:
    """Result of list objects operation."""
    objects: List[StorageObject]
    prefixes: List[str]  # Common prefixes (folders)
    is_truncated: bool
    next_marker: Optional[str] = None
    max_keys: int = 1000
    marker: Optional[str] = None
    prefix: str = ""
    delimiter: str = ""


@dataclass
class PresignedUrl:
    """Presigned URL for temporary access."""
    url: str
    method: str
    expires_at: datetime
    headers: Dict[str, str] = field(default_factory=dict)


class StorageBackend(ABC):
    """Abstract storage backend."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Backend name."""
        pass

    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize backend."""
        pass

    @abstractmethod
    async def start(self) -> None:
        """Start backend."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop backend."""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Health check."""
        pass

    # Bucket operations
    @abstractmethod
    async def create_bucket(self, bucket: Bucket) -> Bucket:
        pass

    @abstractmethod
    async def get_bucket(self, bucket: str) -> Optional[Bucket]:
        pass

    @abstractmethod
    async def list_buckets(self) -> List[Bucket]:
        pass

    @abstractmethod
    async def delete_bucket(self, bucket: str) -> bool:
        pass

    @abstractmethod
    async def bucket_exists(self, bucket: str) -> bool:
        pass

    # Object operations
    @abstractmethod
    async def put_object(
        self,
        bucket: str,
        key: str,
        data: Union[bytes, BinaryIO, AsyncIterator[bytes]],
        metadata: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None,
        storage_class: StorageClass = StorageClass.STANDARD,
        tags: Optional[Dict[str, str]] = None,
        acl: Optional[List[Dict[str, Any]]] = None
    ) -> PutObjectResult:
        pass

    @abstractmethod
    async def get_object(
        self,
        bucket: str,
        key: str,
        version_id: Optional[str] = None,
        range_start: Optional[int] = None,
        range_end: Optional[int] = None
    ) -> Optional[tuple[bytes, StorageObject]]:
        pass

    @abstractmethod
    async def get_object_stream(
        self,
        bucket: str,
        key: str,
        version_id: Optional[str] = None,
        chunk_size: int = 8192
    ) -> Optional[AsyncIterator[bytes]]:
        pass

    @abstractmethod
    async def delete_object(
        self,
        bucket: str,
        key: str,
        version_id: Optional[str] = None
    ) -> bool:
        pass

    @abstractmethod
    async def head_object(
        self,
        bucket: str,
        key: str,
        version_id: Optional[str] = None
    ) -> Optional[StorageObject]:
        pass

    @abstractmethod
    async def list_objects(
        self,
        bucket: str,
        prefix: str = "",
        delimiter: str = "/",
        marker: Optional[str] = None,
        max_keys: int = 1000
    ) -> ListObjectsResult:
        pass

    @abstractmethod
    async def copy_object(
        self,
        src_bucket: str,
        src_key: str,
        dst_bucket: str,
        dst_key: str,
        metadata_directive: str = "COPY"
    ) -> PutObjectResult:
        pass

    @abstractmethod
    async def move_object(
        self,
        src_bucket: str,
        src_key: str,
        dst_bucket: str,
        dst_key: str
    ) -> bool:
        pass

    # Multipart upload
    @abstractmethod
    async def create_multipart_upload(
        self,
        bucket: str,
        key: str,
        metadata: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None,
        storage_class: StorageClass = StorageClass.STANDARD
    ) -> str:
        pass

    @abstractmethod
    async def upload_part(
        self,
        bucket: str,
        key: str,
        upload_id: str,
        part_number: int,
        data: Union[bytes, BinaryIO, AsyncIterator[bytes]]
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def complete_multipart_upload(
        self,
        bucket: str,
        key: str,
        upload_id: str,
        parts: List[Dict[str, Any]]
    ) -> PutObjectResult:
        pass

    @abstractmethod
    async def abort_multipart_upload(
        self,
        bucket: str,
        key: str,
        upload_id: str
    ) -> bool:
        pass

    # Presigned URLs
    @abstractmethod
    async def generate_presigned_url(
        self,
        bucket: str,
        key: str,
        method: str = "GET",
        expiration: int = 3600,
        headers: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None
    ) -> PresignedUrl:
        pass

    # Tags and metadata
    @abstractmethod
    async def set_object_tags(
        self,
        bucket: str,
        key: str,
        tags: Dict[str, str],
        version_id: Optional[str] = None
    ) -> bool:
        pass

    @abstractmethod
    async def get_object_tags(
        self,
        bucket: str,
        key: str,
        version_id: Optional[str] = None
    ) -> Optional[Dict[str, str]]:
        pass


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage backend."""

    @property
    def name(self) -> str:
        return "local"

    def __init__(self):
        self._root_path: Optional[Path] = None

    async def initialize(self, config: Dict[str, Any]) -> None:
        root = config.get("root_path", "./storage")
        self._root_path = Path(root).absolute()
        self._root_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Local storage initialized at {self._root_path}")

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def health_check(self) -> Dict[str, Any]:
        return {"backend": "local", "healthy": True, "root": str(self._root_path)}

    def _bucket_path(self, bucket: str) -> Path:
        return self._root_path / bucket

    def _object_path(self, bucket: str, key: str, version_id: Optional[str] = None) -> Path:
        path = self._bucket_path(bucket) / key
        if version_id:
            path = path.with_suffix(f".{version_id}{path.suffix}")
        return path

    async def create_bucket(self, bucket: Bucket) -> Bucket:
        bucket_path = self._bucket_path(bucket.name)
        bucket_path.mkdir(parents=True, exist_ok=True)
        # Save bucket metadata
        meta_file = bucket_path / ".bucket_metadata.json"
        async with aiofiles.open(meta_file, 'w') as f:
            import json
            await f.write(json.dumps(bucket.to_dict()))
        return bucket

    async def get_bucket(self, bucket: str) -> Optional[Bucket]:
        bucket_path = self._bucket_path(bucket)
        if not bucket_path.exists():
            return None
        meta_file = bucket_path / ".bucket_metadata.json"
        if meta_file.exists():
            async with aiofiles.open(meta_file, 'r') as f:
                import json
                data = json.loads(await f.read())
                return Bucket(**data)
        return Bucket(name=bucket)

    async def list_buckets(self) -> List[Bucket]:
        buckets = []
        for item in self._root_path.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                bucket = await self.get_bucket(item.name)
                if bucket:
                    buckets.append(bucket)
        return buckets

    async def delete_bucket(self, bucket: str) -> bool:
        bucket_path = self._bucket_path(bucket)
        if not bucket_path.exists():
            return False
        # Check if empty
        if any(bucket_path.iterdir()):
            return False
        bucket_path.rmdir()
        return True

    async def bucket_exists(self, bucket: str) -> bool:
        return self._bucket_path(bucket).exists()

    async def _calculate_etag(self, data: bytes) -> str:
        return hashlib.md5(data).hexdigest()

    async def put_object(
        self,
        bucket: str,
        key: str,
        data: Union[bytes, BinaryIO, AsyncIterator[bytes]],
        metadata: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None,
        storage_class: StorageClass = StorageClass.STANDARD,
        tags: Optional[Dict[str, str]] = None,
        acl: Optional[List[Dict[str, Any]]] = None
    ) -> PutObjectResult:
        # Ensure bucket exists
        await self.create_bucket(Bucket(name=bucket))

        object_path = self._object_path(bucket, key)
        object_path.parent.mkdir(parents=True, exist_ok=True)

        # Read data
        if isinstance(data, bytes):
            data_bytes = data
        elif hasattr(data, 'read'):
            data_bytes = data.read()
        else:
            chunks = []
            async for chunk in data:
                chunks.append(chunk)
            data_bytes = b''.join(chunks)

        etag = await self._calculate_etag(data_bytes)

        # Write data
        async with aiofiles.open(object_path, 'wb') as f:
            await f.write(data_bytes)

        # Write metadata
        meta_path = object_path.with_suffix(f".{object_path.suffix}.meta")
        obj = StorageObject(
            key=key,
            bucket=bucket,
            size=len(data_bytes),
            etag=etag,
            content_type=content_type or mimetypes.guess_type(key)[0] or "application/octet-stream",
            metadata=metadata or {},
            tags=tags or {},
            storage_class=storage_class
        )
        import json
        async with aiofiles.open(meta_path, 'w') as f:
            await f.write(json.dumps(obj.to_dict()))

        return PutObjectResult(
            key=key,
            bucket=bucket,
            etag=etag,
            size=len(data_bytes),
            storage_class=storage_class
        )

    async def get_object(
        self,
        bucket: str,
        key: str,
        version_id: Optional[str] = None,
        range_start: Optional[int] = None,
        range_end: Optional[int] = None
    ) -> Optional[tuple[bytes, StorageObject]]:
        object_path = self._object_path(bucket, key, version_id)
        if not object_path.exists():
            return None

        meta_path = object_path.with_suffix(f".{object_path.suffix}.meta")
        obj = None
        if meta_path.exists():
            async with aiofiles.open(meta_path, 'r') as f:
                import json
                data = json.loads(await f.read())
                obj = StorageObject(**data)

        async with aiofiles.open(object_path, 'rb') as f:
            if range_start is not None:
                await f.seek(range_start)
                size = (range_end - range_start + 1) if range_end else None
                data = await f.read(size)
            else:
                data = await f.read()

        if not obj:
            obj = StorageObject(key=key, bucket=bucket, size=len(data), etag=await self._calculate_etag(data))

        return data, obj

    async def get_object_stream(
        self,
        bucket: str,
        key: str,
        version_id: Optional[str] = None,
        chunk_size: int = 8192
    ) -> Optional[AsyncIterator[bytes]]:
        object_path = self._object_path(bucket, key, version_id)
        if not object_path.exists():
            return None

        async def stream():
            async with aiofiles.open(object_path, 'rb') as f:
                while True:
                    chunk = await f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk

        return stream()

    async def delete_object(
        self,
        bucket: str,
        key: str,
        version_id: Optional[str] = None
    ) -> bool:
        object_path = self._object_path(bucket, key, version_id)
        meta_path = object_path.with_suffix(f".{object_path.suffix}.meta")

        deleted = False
        if object_path.exists():
            object_path.unlink()
            deleted = True
        if meta_path.exists():
            meta_path.unlink()
            deleted = True

        return deleted

    async def head_object(
        self,
        bucket: str,
        key: str,
        version_id: Optional[str] = None
    ) -> Optional[StorageObject]:
        object_path = self._object_path(bucket, key, version_id)
        meta_path = object_path.with_suffix(f".{object_path.suffix}.meta")

        if meta_path.exists():
            async with aiofiles.open(meta_path, 'r') as f:
                import json
                data = json.loads(await f.read())
                return StorageObject(**data)

        if object_path.exists():
            stat = object_path.stat()
            return StorageObject(
                key=key,
                bucket=bucket,
                size=stat.st_size,
                etag=await self._calculate_etag(object_path.read_bytes()),
                content_type=mimetypes.guess_type(key)[0] or "application/octet-stream",
                modified_at=datetime.fromtimestamp(stat.st_mtime)
            )
        return None

    async def list_objects(
        self,
        bucket: str,
        prefix: str = "",
        delimiter: str = "/",
        marker: Optional[str] = None,
        max_keys: int = 1000
    ) -> ListObjectsResult:
        bucket_path = self._bucket_path(bucket)
        if not bucket_path.exists():
            return ListObjectsResult(objects=[], prefixes=[], is_truncated=False)

        objects = []
        prefixes = set()
        count = 0

        for item in sorted(bucket_path.rglob("*")):
            if item.name.startswith(".") or item.is_dir():
                continue

            rel_path = item.relative_to(bucket_path)
            key = str(rel_path)

            if not key.startswith(prefix):
                continue

            if marker and key <= marker:
                continue

            # Handle delimiter
            if delimiter and delimiter in key[len(prefix):]:
                common_prefix = key[:key.index(delimiter, len(prefix)) + 1]
                prefixes.add(common_prefix)
                continue

            obj = await self.head_object(bucket, key)
            if obj:
                objects.append(obj)
                count += 1
                if count >= max_keys:
                    break

        return ListObjectsResult(
            objects=objects,
            prefixes=sorted(prefixes),
            is_truncated=count >= max_keys,
            max_keys=max_keys,
            marker=marker,
            prefix=prefix,
            delimiter=delimiter
        )

    async def copy_object(
        self,
        src_bucket: str,
        src_key: str,
        dst_bucket: str,
        dst_key: str,
        metadata_directive: str = "COPY"
    ) -> PutObjectResult:
        result = await self.get_object(src_bucket, src_key)
        if not result:
            raise ValueError(f"Source object not found: {src_bucket}/{src_key}")

        data, src_obj = result
        metadata = src_obj.metadata if metadata_directive == "COPY" else None

        return await self.put_object(
            dst_bucket,
            dst_key,
            data,
            metadata=metadata,
            content_type=src_obj.content_type,
            storage_class=src_obj.storage_class,
            tags=src_obj.tags
        )

    async def move_object(
        self,
        src_bucket: str,
        src_key: str,
        dst_bucket: str,
        dst_key: str
    ) -> bool:
        await self.copy_object(src_bucket, src_key, dst_bucket, dst_key)
        return await self.delete_object(src_bucket, src_key)

    # Multipart upload stubs
    async def create_multipart_upload(
        self,
        bucket: str,
        key: str,
        metadata: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None,
        storage_class: StorageClass = StorageClass.STANDARD
    ) -> str:
        upload_id = str(uuid.uuid4())
        # Store upload info
        upload_path = self._bucket_path(bucket) / ".uploads" / upload_id
        upload_path.parent.mkdir(parents=True, exist_ok=True)
        await self.put_object(bucket, f".uploads/{upload_id}/info.json",
            json.dumps({
                "key": key,
                "metadata": metadata or {},
                "content_type": content_type,
                "storage_class": storage_class.value,
                "created_at": datetime.utcnow().isoformat()
            }).encode())
        return upload_id

    async def upload_part(
        self,
        bucket: str,
        key: str,
        upload_id: str,
        part_number: int,
        data: Union[bytes, BinaryIO, AsyncIterator[bytes]]
    ) -> Dict[str, Any]:
        part_key = f".uploads/{upload_id}/part_{part_number}"
        result = await self.put_object(bucket, part_key, data)
        return {"part_number": part_number, "etag": result.etag}

    async def complete_multipart_upload(
        self,
        bucket: str,
        key: str,
        upload_id: str,
        parts: List[Dict[str, Any]]
    ) -> PutObjectResult:
        # Combine parts
        all_data = b""
        for part in sorted(parts, key=lambda p: p["part_number"]):
            part_data, _ = await self.get_object(bucket, f".uploads/{upload_id}/part_{part['part_number']}")
            if part_data:
                all_data += part_data

        result = await self.put_object(bucket, key, all_data)

        # Cleanup
        await self.delete_object(bucket, f".uploads/{upload_id}")
        return result

    async def abort_multipart_upload(
        self,
        bucket: str,
        key: str,
        upload_id: str
    ) -> bool:
        # Clean up all parts
        upload_path = self._bucket_path(bucket) / ".uploads" / upload_id
        if upload_path.exists():
            import shutil
            shutil.rmtree(upload_path)
        return True

    async def generate_presigned_url(
        self,
        bucket: str,
        key: str,
        method: str = "GET",
        expiration: int = 3600,
        headers: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None
    ) -> PresignedUrl:
        # Local storage doesn't really support presigned URLs
        # Return a local URL that would work within the same system
        base_url = f"http://localhost:8080/storage/{bucket}/{key}"
        return PresignedUrl(
            url=base_url,
            method=method,
            expires_at=datetime.utcnow() + timedelta(seconds=expiration)
        )
        # Note: Need to import timedelta

    async def set_object_tags(
        self,
        bucket: str,
        key: str,
        tags: Dict[str, str],
        version_id: Optional[str] = None
    ) -> bool:
        obj = await self.head_object(bucket, key, version_id)
        if not obj:
            return False
        obj.tags = tags
        meta_path = self._object_path(bucket, key, version_id).with_suffix(f".{obj.key.split('.')[-1]}.meta")
        import json
        async with aiofiles.open(meta_path, 'w') as f:
            await f.write(json.dumps(obj.to_dict()))
        return True

    async def get_object_tags(
        self,
        bucket: str,
        key: str,
        version_id: Optional[str] = None
    ) -> Optional[Dict[str, str]]:
        obj = await self.head_object(bucket, key, version_id)
        return obj.tags if obj else None


class S3StorageBackend(StorageBackend):
    """S3-compatible storage backend (AWS S3, MinIO, DigitalOcean Spaces, etc.)."""

    @property
    def name(self) -> str:
        return "s3"

    def __init__(self):
        self._client = None
        self._config: Dict[str, Any] = {}

    async def initialize(self, config: Dict[str, Any]) -> None:
        self._config = config
        # Import aioboto3 lazily
        import aioboto3
        self._session = aioboto3.Session(
            aws_access_key_id=config.get("access_key"),
            aws_secret_access_key=config.get("secret_key"),
            region_name=config.get("region", "us-east-1")
        )
        self._endpoint_url = config.get("endpoint_url")
        logger.info(f"S3 backend initialized: {config.get('region')}")

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def health_check(self) -> Dict[str, Any]:
        try:
            async with self._session.client('s3', endpoint_url=self._endpoint_url) as s3:
                await s3.list_buckets()
            return {"backend": "s3", "healthy": True}
        except Exception as e:
            return {"backend": "s3", "healthy": False, "error": str(e)}

    async def create_bucket(self, bucket: Bucket) -> Bucket:
        async with self._session.client('s3', endpoint_url=self._endpoint_url) as s3:
            await s3.create_bucket(Bucket=bucket.name)
        return bucket

    async def get_bucket(self, bucket: str) -> Optional[Bucket]:
        async with self._session.client('s3', endpoint_url=self._endpoint_url) as s3:
            try:
                await s3.head_bucket(Bucket=bucket)
                return Bucket(name=bucket)
            except:
                return None

    async def list_buckets(self) -> List[Bucket]:
        async with self._session.client('s3', endpoint_url=self._endpoint_url) as s3:
            response = await s3.list_buckets()
            return [Bucket(name=b['Name'], creation_date=b['CreationDate']) for b in response['Buckets']]

    async def delete_bucket(self, bucket: str) -> bool:
        try:
            async with self._session.client('s3', endpoint_url=self._endpoint_url) as s3:
                await s3.delete_bucket(Bucket=bucket)
            return True
        except:
            return False

    async def bucket_exists(self, bucket: str) -> bool:
        return await self.get_bucket(bucket) is not None

    async def put_object(
        self,
        bucket: str,
        key: str,
        data: Union[bytes, BinaryIO, AsyncIterator[bytes]],
        metadata: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None,
        storage_class: StorageClass = StorageClass.STANDARD,
        tags: Optional[Dict[str, str]] = None,
        acl: Optional[List[Dict[str, Any]]] = None
    ) -> PutObjectResult:
        # Read data
        if isinstance(data, bytes):
            data_bytes = data
        elif hasattr(data, 'read'):
            data_bytes = data.read()
        else:
            chunks = []
            async for chunk in data:
                chunks.append(chunk)
            data_bytes = b''.join(chunks)

        async with self._session.client('s3', endpoint_url=self._endpoint_url) as s3:
            params = {
                'Bucket': bucket,
                'Key': key,
                'Body': data_bytes,
                'StorageClass': storage_class.value.upper()
            }
            if content_type:
                params['ContentType'] = content_type
            if metadata:
                params['Metadata'] = metadata
            if tags:
                params['Tagging'] = '&'.join(f'{k}={v}' for k, v in tags.items())
            if acl:
                params['ACL'] = 'private'  # Simplified

            response = await s3.put_object(**params)
            return PutObjectResult(
                key=key,
                bucket=bucket,
                etag=response['ETag'].strip('"'),
                size=len(data_bytes),
                storage_class=storage_class
            )

    async def get_object(
        self,
        bucket: str,
        key: str,
        version_id: Optional[str] = None,
        range_start: Optional[int] = None,
        range_end: Optional[int] = None
    ) -> Optional[tuple[bytes, StorageObject]]:
        async with self._session.client('s3', endpoint_url=self._endpoint_url) as s3:
            params = {'Bucket': bucket, 'Key': key}
            if version_id:
                params['VersionId'] = version_id
            if range_start is not None:
                range_header = f"bytes={range_start}-"
                if range_end is not None:
                    range_header += str(range_end)
                params['Range'] = range_header

            try:
                response = await s3.get_object(**params)
                data = await response['Body'].read()

                obj = StorageObject(
                    key=key,
                    bucket=bucket,
                    size=response.get('ContentLength', len(data)),
                    etag=response.get('ETag', '').strip('"'),
                    content_type=response.get('ContentType', 'application/octet-stream'),
                    version_id=response.get('VersionId'),
                    storage_class=StorageClass(response.get('StorageClass', 'STANDARD')),
                    metadata=response.get('Metadata', {}),
                    modified_at=response.get('LastModified', datetime.utcnow())
                )
                return data, obj
            except:
                return None

    async def get_object_stream(
        self,
        bucket: str,
        key: str,
        version_id: Optional[str] = None,
        chunk_size: int = 8192
    ) -> Optional[AsyncIterator[bytes]]:
        async with self._session.client('s3', endpoint_url=self._endpoint_url) as s3:
            params = {'Bucket': bucket, 'Key': key}
            if version_id:
                params['VersionId'] = version_id
            try:
                response = await s3.get_object(**params)
                body = response['Body']

                async def stream():
                    while True:
                        chunk = await body.read(chunk_size)
                        if not chunk:
                            break
                        yield chunk

                return stream()
            except:
                return None

    async def delete_object(
        self,
        bucket: str,
        key: str,
        version_id: Optional[str] = None
    ) -> bool:
        async with self._session.client('s3', endpoint_url=self._endpoint_url) as s3:
            params = {'Bucket': bucket, 'Key': key}
            if version_id:
                params['VersionId'] = version_id
            try:
                await s3.delete_object(**params)
                return True
            except:
                return False

    async def head_object(
        self,
        bucket: str,
        key: str,
        version_id: Optional[str] = None
    ) -> Optional[StorageObject]:
        async with self._session.client('s3', endpoint_url=self._endpoint_url) as s3:
            params = {'Bucket': bucket, 'Key': key}
            if version_id:
                params['VersionId'] = version_id
            try:
                response = await s3.head_object(**params)
                return StorageObject(
                    key=key,
                    bucket=bucket,
                    size=response.get('ContentLength', 0),
                    etag=response.get('ETag', '').strip('"'),
                    content_type=response.get('ContentType', 'application/octet-stream'),
                    version_id=response.get('VersionId'),
                    storage_class=StorageClass(response.get('StorageClass', 'STANDARD')),
                    metadata=response.get('Metadata', {}),
                    modified_at=response.get('LastModified', datetime.utcnow())
                )
            except:
                return None

    async def list_objects(
        self,
        bucket: str,
        prefix: str = "",
        delimiter: str = "/",
        marker: Optional[str] = None,
        max_keys: int = 1000
    ) -> ListObjectsResult:
        async with self._session.client('s3', endpoint_url=self._endpoint_url) as s3:
            params = {'Bucket': bucket, 'MaxKeys': max_keys}
            if prefix:
                params['Prefix'] = prefix
            if delimiter:
                params['Delimiter'] = delimiter
            if marker:
                params['Marker'] = marker

            response = await s3.list_objects_v2(**params)

            objects = []
            for obj in response.get('Contents', []):
                objects.append(StorageObject(
                    key=obj['Key'],
                    bucket=bucket,
                    size=obj['Size'],
                    etag=obj['ETag'].strip('"'),
                    storage_class=StorageClass(obj.get('StorageClass', 'STANDARD')),
                    modified_at=obj['LastModified'],
                    version_id=obj.get('VersionId')
                ))

            prefixes = [p['Prefix'] for p in response.get('CommonPrefixes', [])]

            return ListObjectsResult(
                objects=objects,
                prefixes=prefixes,
                is_truncated=response.get('IsTruncated', False),
                next_marker=response.get('NextMarker') or response.get('NextContinuationToken'),
                max_keys=max_keys,
                marker=marker,
                prefix=prefix,
                delimiter=delimiter
            )

    async def copy_object(
        self,
        src_bucket: str,
        src_key: str,
        dst_bucket: str,
        dst_key: str,
        metadata_directive: str = "COPY"
    ) -> PutObjectResult:
        async with self._session.client('s3', endpoint_url=self._endpoint_url) as s3:
            copy_source = {'Bucket': src_bucket, 'Key': src_key}
            response = await s3.copy_object(
                CopySource=copy_source,
                Bucket=dst_bucket,
                Key=dst_key,
                MetadataDirective=metadata_directive
            )
            return PutObjectResult(
                key=dst_key,
                bucket=dst_bucket,
                etag=response['CopyObjectResult']['ETag'].strip('"'),
                size=0,  # Not returned in copy response
                storage_class=StorageClass.STANDARD
            )

    async def move_object(
        self,
        src_bucket: str,
        src_key: str,
        dst_bucket: str,
        dst_key: str
    ) -> bool:
        await self.copy_object(src_bucket, src_key, dst_bucket, dst_key)
        return await self.delete_object(src_bucket, src_key)

    # Multipart upload
    async def create_multipart_upload(
        self,
        bucket: str,
        key: str,
        metadata: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None,
        storage_class: StorageClass = StorageClass.STANDARD
    ) -> str:
        async with self._session.client('s3', endpoint_url=self._endpoint_url) as s3:
            params = {'Bucket': bucket, 'Key': key}
            if content_type:
                params['ContentType'] = content_type
            if metadata:
                params['Metadata'] = metadata
            response = await s3.create_multipart_upload(**params)
            return response['UploadId']

    async def upload_part(
        self,
        bucket: str,
        key: str,
        upload_id: str,
        part_number: int,
        data: Union[bytes, BinaryIO, AsyncIterator[bytes]]
    ) -> Dict[str, Any]:
        if isinstance(data, bytes):
            pass
        elif hasattr(data, 'read'):
            data = data.read()
        else:
            chunks = []
            async for chunk in data:
                chunks.append(chunk)
            data = b''.join(chunks)

        async with self._session.client('s3', endpoint_url=self._endpoint_url) as s3:
            response = await s3.upload_part(
                Bucket=bucket,
                Key=key,
                UploadId=upload_id,
                PartNumber=part_number,
                Body=data
            )
            return {'part_number': part_number, 'etag': response['ETag'].strip('"')}

    async def complete_multipart_upload(
        self,
        bucket: str,
        key: str,
        upload_id: str,
        parts: List[Dict[str, Any]]
    ) -> PutObjectResult:
        async with self._session.client('s3', endpoint_url=self._endpoint_url) as s3:
            response = await s3.complete_multipart_upload(
                Bucket=bucket,
                Key=key,
                UploadId=upload_id,
                MultipartUpload={'Parts': [
                    {'PartNumber': p['part_number'], 'ETag': p['etag']} for p in parts
                ]}
            )
            return PutObjectResult(
                key=key,
                bucket=bucket,
                etag=response['ETag'].strip('"'),
                size=0,
                storage_class=StorageClass.STANDARD
            )

    async def abort_multipart_upload(
        self,
        bucket: str,
        key: str,
        upload_id: str
    ) -> bool:
        async with self._session.client('s3', endpoint_url=self._endpoint_url) as s3:
            try:
                await s3.abort_multipart_upload(
                    Bucket=bucket, Key=key, UploadId=upload_id)
                return True
            except:
                return False

    async def generate_presigned_url(
        self,
        bucket: str,
        key: str,
        method: str = "GET",
        expiration: int = 3600,
        headers: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None
    ) -> PresignedUrl:
        async with self._session.client('s3', endpoint_url=self._endpoint_url) as s3:
            params = {'Bucket': bucket, 'Key': key}
            if content_type:
                params['ResponseContentType'] = content_type
            if headers:
                for k, v in headers.items():
                    params[f'Response{k}'] = v

            if method.upper() == "GET":
                url = await s3.generate_presigned_url(
                    'get_object', Params=params, ExpiresIn=expiration)
            elif method.upper() == "PUT":
                url = await s3.generate_presigned_url(
                    'put_object', Params=params, ExpiresIn=expiration)
            else:
                raise ValueError(f"Unsupported method: {method}")

            return PresignedUrl(
                url=url,
                method=method,
                expires_at=datetime.utcnow() + timedelta(seconds=expiration)
            )

    async def set_object_tags(
        self,
        bucket: str,
        key: str,
        tags: Dict[str, str],
        version_id: Optional[str] = None
    ) -> bool:
        async with self._session.client('s3', endpoint_url=self._endpoint_url) as s3:
            try:
                params = {
                    'Bucket': bucket,
                    'Key': key,
                    'Tagging': {'TagSet': [{'Key': k, 'Value': v} for k, v in tags.items()]}
                }
                if version_id:
                    params['VersionId'] = version_id
                await s3.put_object_tagging(**params)
                return True
            except:
                return False

    async def get_object_tags(
        self,
        bucket: str,
        key: str,
        version_id: Optional[str] = None
    ) -> Optional[Dict[str, str]]:
        async with self._session.client('s3', endpoint_url=self._endpoint_url) as s3:
            try:
                params = {'Bucket': bucket, 'Key': key}
                if version_id:
                    params['VersionId'] = version_id
                response = await s3.get_object_tagging(**params)
                return {tag['Key']: tag['Value'] for tag in response.get('TagSet', [])}
            except:
                return None


class StorageModule(RuntimeModule):
    """
    Unified storage module with multiple backend support.

    Supports:
    - Local filesystem
    - S3-compatible (AWS S3, MinIO, DigitalOcean Spaces, etc.)
    - Google Cloud Storage
    - Azure Blob Storage
    """

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="storage",
            version="1.0.0",
            description="Unified object storage with multiple backends",
            author="AIPENSA",
            dependencies=[],
            provides=["object_storage", "file_storage", "blob_storage", "s3_compatible"],
            tags={"storage", "s3", "object_store", "files"}
        )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._backends: Dict[str, StorageBackend] = {}
        self._default_backend = config.get("default_backend", "local") if config else "local"
        self._buckets_cache: Dict[str, Bucket] = {}
        self._bucket_cache_ttl = config.get("bucket_cache_ttl", 300) if config else 300  # 5 minutes
        self._bucket_cache_time: Dict[str, datetime] = {}

    async def initialize(self, runtime: "Runtime", config: Dict[str, Any]) -> None:
        """Initialize storage module."""
        self._runtime = runtime
        self._config = {**self._config, **config}
        self._default_backend = self._config.get("default_backend", self._default_backend)

        # Initialize backends
        backends_config = self._config.get("backends", {})
        for name, backend_config in backends_config.items():
            backend_type = backend_config.get("type", "local")
            await self._create_backend(name, backend_type, backend_config)

        # Create default bucket if configured
        default_bucket = self._config.get("default_bucket")
        if default_bucket:
            await self.ensure_bucket(default_bucket)

        self.state = ModuleState.INITIALIZED
        logger.info(f"Storage module initialized with backends: {list(self._backends.keys())}")

    async def _create_backend(self, name: str, backend_type: str, config: Dict[str, Any]) -> None:
        """Create and initialize a storage backend."""
        if backend_type == "local":
            backend = LocalStorageBackend()
        elif backend_type == "s3":
            backend = S3StorageBackend()
        else:
            logger.warning(f"Unknown backend type: {backend_type}")
            return

        await backend.initialize(config)
        await backend.start()
        self._backends[name] = backend
        logger.info(f"Created backend: {name} ({backend_type})")

    async def start(self) -> None:
        self.state = ModuleState.RUNNING
        logger.info("Storage module started")

    async def stop(self) -> None:
        for _, backend in self._backends.items():
            await backend.stop()
        self.state = ModuleState.STOPPED
        logger.info("Storage module stopped")

    async def cleanup(self) -> None:
        await self.stop()
        self._backends.clear()
        self._buckets_cache.clear()
        self._bucket_cache_time.clear()
        self.state = ModuleState.UNINITIALIZED
        logger.info("Storage module cleaned up")

    async def health_check(self) -> Dict[str, Any]:
        backend_status = {}
        for name, backend in self._backends.items():
            backend_status[name] = await backend.health_check()

        healthy = all(s.get("healthy", False) for s in backend_status.values())
        return {
            "module": "storage",
            "status": self.state.value,
            "healthy": healthy,
            "backends": backend_status,
            "cached_buckets": len(self._buckets_cache)
        }

    def _get_backend(self, backend_name: Optional[str] = None) -> StorageBackend:
        """Get backend by name or default."""
        name = backend_name or self._default_backend
        if name not in self._backends:
            raise ValueError(f"Backend not found: {name}")
        return self._backends[name]

    # Bucket Operations
    async def create_bucket(
        self,
        name: str,
        backend: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Bucket:
        """Create a new bucket."""
        b = self._get_backend(backend)
        bucket = Bucket(
            name=name,
            **(config or {})
        )
        result = await b.create_bucket(bucket)
        self._invalidate_bucket_cache(name)
        return result

    async def get_bucket(self, name: str, backend: Optional[str] = None) -> Optional[Bucket]:
        """Get bucket by name."""
        # Check cache
        if name in self._buckets_cache:
            cached_time = self._bucket_cache_time.get(name, datetime.min)
            if (datetime.utcnow() - cached_time).total_seconds() < self._bucket_cache_ttl:
                return self._buckets_cache[name]

        # Get from backend
        b = self._get_backend(backend)
        bucket = await b.get_bucket(name)
        if bucket:
            self._buckets_cache[name] = bucket
            self._bucket_cache_time[name] = datetime.utcnow()
        return bucket

    async def list_buckets(self, backend: Optional[str] = None) -> List[Bucket]:
        """List all buckets."""
        b = self._get_backend(backend)
        buckets = await b.list_buckets()

        # Update cache
        for bucket in buckets:
            self._buckets_cache[bucket.name] = bucket
            self._bucket_cache_time[bucket.name] = datetime.utcnow()

        return buckets

    async def delete_bucket(self, name: str, backend: Optional[str] = None) -> bool:
        """Delete bucket."""
        b = self._get_backend(backend)
        result = await b.delete_bucket(name)
        if result:
            self._invalidate_bucket_cache(name)
        return result

    async def bucket_exists(self, name: str, backend: Optional[str] = None) -> bool:
        """Check if bucket exists."""
        b = self._get_backend(backend)
        return await b.bucket_exists(name)

    async def ensure_bucket(self, name: str, backend: Optional[str] = None, config: Optional[Dict[str, Any]] = None) -> Bucket:
        """Ensure bucket exists, create if not."""
        if await self.bucket_exists(name, backend):
            return await self.get_bucket(name, backend)
        return await self.create_bucket(name, backend, config)

    def _invalidate_bucket_cache(self, name: str) -> None:
        self._buckets_cache.pop(name, None)
        self._bucket_cache_time.pop(name, None)

    # Object Operations
    async def put_object(
        self,
        bucket: str,
        key: str,
        data: Union[bytes, BinaryIO, AsyncIterator[bytes]],
        backend: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None,
        storage_class: StorageClass = StorageClass.STANDARD,
        tags: Optional[Dict[str, str]] = None,
        acl: Optional[List[Dict[str, Any]]] = None
    ) -> PutObjectResult:
        """Put object into storage."""
        b = self._get_backend(backend)
        return await b.put_object(bucket, key, data, metadata, content_type, storage_class, tags, acl)

    async def get_object(
        self,
        bucket: str,
        key: str,
        backend: Optional[str] = None,
        version_id: Optional[str] = None,
        range_start: Optional[int] = None,
        range_end: Optional[int] = None
    ) -> Optional[tuple[bytes, StorageObject]]:
        """Get object from storage."""
        b = self._get_backend(backend)
        return await b.get_object(bucket, key, version_id, range_start, range_end)

    async def get_object_stream(
        self,
        bucket: str,
        key: str,
        backend: Optional[str] = None,
        version_id: Optional[str] = None,
        chunk_size: int = 8192
    ) -> Optional[AsyncIterator[bytes]]:
        """Get object as stream."""
        b = self._get_backend(backend)
        return await b.get_object_stream(bucket, key, version_id, chunk_size)

    async def delete_object(
        self,
        bucket: str,
        key: str,
        backend: Optional[str] = None,
        version_id: Optional[str] = None
    ) -> bool:
        """Delete object from storage."""
        b = self._get_backend(backend)
        return await b.delete_object(bucket, key, version_id)

    async def head_object(
        self,
        bucket: str,
        key: str,
        backend: Optional[str] = None,
        version_id: Optional[str] = None
    ) -> Optional[StorageObject]:
        """Get object metadata without data."""
        b = self._get_backend(backend)
        return await b.head_object(bucket, key, version_id)

    async def list_objects(
        self,
        bucket: str,
        backend: Optional[str] = None,
        prefix: str = "",
        delimiter: str = "/",
        marker: Optional[str] = None,
        max_keys: int = 1000
    ) -> ListObjectsResult:
        """List objects in bucket."""
        b = self._get_backend(backend)
        return await b.list_objects(bucket, prefix, delimiter, marker, max_keys)

    async def copy_object(
        self,
        src_bucket: str,
        src_key: str,
        dst_bucket: str,
        dst_key: str,
        backend: Optional[str] = None,
        metadata_directive: str = "COPY"
    ) -> PutObjectResult:
        """Copy object within/between buckets."""
        b = self._get_backend(backend)
        return await b.copy_object(src_bucket, src_key, dst_bucket, dst_key, metadata_directive)

    async def move_object(
        self,
        src_bucket: str,
        src_key: str,
        dst_bucket: str,
        dst_key: str,
        backend: Optional[str] = None
    ) -> bool:
        """Move object."""
        b = self._get_backend(backend)
        return await b.move_object(src_bucket, src_key, dst_bucket, dst_key)

    # Multipart Upload
    async def create_multipart_upload(
        self,
        bucket: str,
        key: str,
        backend: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None,
        storage_class: StorageClass = StorageClass.STANDARD
    ) -> str:
        b = self._get_backend(backend)
        return await b.create_multipart_upload(bucket, key, metadata, content_type, storage_class)

    async def upload_part(
        self,
        bucket: str,
        key: str,
        upload_id: str,
        part_number: int,
        data: Union[bytes, BinaryIO, AsyncIterator[bytes]],
        backend: Optional[str] = None
    ) -> Dict[str, Any]:
        b = self._get_backend(backend)
        return await b.upload_part(bucket, key, upload_id, part_number, data)

    async def complete_multipart_upload(
        self,
        bucket: str,
        key: str,
        upload_id: str,
        parts: List[Dict[str, Any]],
        backend: Optional[str] = None
    ) -> PutObjectResult:
        b = self._get_backend(backend)
        return await b.complete_multipart_upload(bucket, key, upload_id, parts)

    async def abort_multipart_upload(
        self,
        bucket: str,
        key: str,
        upload_id: str,
        backend: Optional[str] = None
    ) -> bool:
        b = self._get_backend(backend)
        return await b.abort_multipart_upload(bucket, key, upload_id)

    # Presigned URLs
    async def generate_presigned_url(
        self,
        bucket: str,
        key: str,
        backend: Optional[str] = None,
        method: str = "GET",
        expiration: int = 3600,
        headers: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None
    ) -> PresignedUrl:
        b = self._get_backend(backend)
        return await b.generate_presigned_url(bucket, key, method, expiration, headers, content_type)

    # Tags and Metadata
    async def set_object_tags(
        self,
        bucket: str,
        key: str,
        tags: Dict[str, str],
        backend: Optional[str] = None,
        version_id: Optional[str] = None
    ) -> bool:
        b = self._get_backend(backend)
        return await b.set_object_tags(bucket, key, tags, version_id)

    async def get_object_tags(
        self,
        bucket: str,
        key: str,
        backend: Optional[str] = None,
        version_id: Optional[str] = None
    ) -> Optional[Dict[str, str]]:
        b = self._get_backend(backend)
        return await b.get_object_tags(bucket, key, version_id)

    # File Operations (Convenience)
    async def upload_file(
        self,
        file_path: str,
        bucket: str,
        key: Optional[str] = None,
        **kwargs
    ) -> PutObjectResult:
        """Upload a local file."""
        key = key or Path(file_path).name
        async with aiofiles.open(file_path, 'rb') as f:
            data = await f.read()
        return await self.put_object(bucket, key, data, **kwargs)

    async def download_file(
        self,
        bucket: str,
        key: str,
        file_path: str,
        backend: Optional[str] = None
    ) -> bool:
        """Download object to local file."""
        result = await self.get_object(bucket, key, backend)
        if not result:
            return False
        data, _ = result
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(data)
        return True

    # Module Operations
    async def execute(self, operation: str, **kwargs) -> Any:
        """Execute module operations."""
        mapping = {
            "create_bucket": self.create_bucket,
            "get_bucket": self.get_bucket,
            "list_buckets": self.list_buckets,
            "delete_bucket": self.delete_bucket,
            "ensure_bucket": self.ensure_bucket,
            "put_object": self.put_object,
            "get_object": self.get_object,
            "get_object_stream": self.get_object_stream,
            "delete_object": self.delete_object,
            "head_object": self.head_object,
            "list_objects": self.list_objects,
            "copy_object": self.copy_object,
            "move_object": self.move_object,
            "create_multipart_upload": self.create_multipart_upload,
            "upload_part": self.upload_part,
            "complete_multipart_upload": self.complete_multipart_upload,
            "abort_multipart_upload": self.abort_multipart_upload,
            "generate_presigned_url": self.generate_presigned_url,
            "set_object_tags": self.set_object_tags,
            "get_object_tags": self.get_object_tags,
            "upload_file": self.upload_file,
            "download_file": self.download_file,
        }
        if operation in mapping:
            return await mapping[operation](**kwargs)
        raise NotImplementedError(f"Operation '{operation}' not supported")


from datetime import timedelta
import json

__all__ = [
    "StorageModule",
    "StorageBackend",
    "LocalStorageBackend",
    "S3StorageBackend",
    "StorageObject",
    "Bucket",
    "PutObjectResult",
    "ListObjectsResult",
    "PresignedUrl",
    "StorageClass",
    "ObjectVersioning",
]