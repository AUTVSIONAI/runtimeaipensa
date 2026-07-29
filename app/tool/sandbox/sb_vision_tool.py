import base64
import mimetypes
import os
from io import BytesIO
from typing import Any, Optional

from PIL import Image
from pydantic import Field

from app.tool.local_tool_base import LocalToolsBase, ThreadMessage
from app.tool.base import ToolResult

# Maximum file size (original 10MB, compressed 5MB)
MAX_IMAGE_SIZE = 10 * 1024 * 1024
MAX_COMPRESSED_SIZE = 5 * 1024 * 1024

# Compression settings
DEFAULT_MAX_WIDTH = 1920
DEFAULT_MAX_HEIGHT = 1080
DEFAULT_JPEG_QUALITY = 85
DEFAULT_PNG_COMPRESS_LEVEL = 6

_VISION_DESCRIPTION = """
A vision tool that allows the agent to read image files in the local workspace using the see_image action.
* Only the see_image action is supported, with the parameter being the relative path of the image under /workspace.
* The image will be compressed and converted to base64 for use in subsequent context.
* Supported formats: JPG, PNG, GIF, WEBP. Maximum size: 10MB.
"""


class SandboxVisionTool(LocalToolsBase):
    name: str = "sandbox_vision"
    description: str = _VISION_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["see_image"],
                "description": "Vision action to perform, currently only see_image",
            },
            "file_path": {
                "type": "string",
                "description": "Relative path of image under /workspace, e.g. 'screenshots/image.png'",
            },
        },
        "required": ["action", "file_path"],
        "dependencies": {"see_image": ["file_path"]},
    }

    vision_message: Optional[ThreadMessage] = Field(default=None, exclude=True)

    def __init__(
        self, sandbox: Optional[Any] = None, thread_id: Optional[str] = None, **data
    ):
        """Initialize with optional sandbox and thread_id."""
        super().__init__(**data)
        self._daytona_sandbox = sandbox
        self._use_daytona = sandbox is not None

    def compress_image(self, image_bytes: bytes, mime_type: str, file_path: str):
        """Compress image to reasonable size/quality."""
        try:
            img = Image.open(BytesIO(image_bytes))
            if img.mode in ("RGBA", "LA", "P"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                background.paste(
                    img, mask=img.split()[-1] if img.mode == "RGBA" else None
                )
                img = background
            width, height = img.size
            if width > DEFAULT_MAX_WIDTH or height > DEFAULT_MAX_HEIGHT:
                ratio = min(DEFAULT_MAX_WIDTH / width, DEFAULT_MAX_HEIGHT / height)
                new_width = int(width * ratio)
                new_height = int(height * ratio)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            output = BytesIO()
            if mime_type == "image/gif":
                img.save(output, format="GIF", optimize=True)
                output_mime = "image/gif"
            elif mime_type == "image/png":
                img.save(
                    output,
                    format="PNG",
                    optimize=True,
                    compress_level=DEFAULT_PNG_COMPRESS_LEVEL,
                )
                output_mime = "image/png"
            else:
                img.save(
                    output, format="JPEG", quality=DEFAULT_JPEG_QUALITY, optimize=True
                )
                output_mime = "image/jpeg"
            compressed_bytes = output.getvalue()
            return compressed_bytes, output_mime
        except Exception:
            return image_bytes, mime_type

    async def _read_image_local(self, full_path: str) -> ToolResult:
        """Read image from local filesystem."""
        try:
            if not os.path.exists(full_path):
                return self.fail_response(f"Image file not found: '{full_path}'")

            file_info = os.stat(full_path)
            if file_info.st_size > MAX_IMAGE_SIZE:
                return self.fail_response(
                    f"Image file '{full_path}' is too large ({file_info.st_size / (1024*1024):.2f}MB), "
                    f"maximum allowed {MAX_IMAGE_SIZE / (1024*1024)}MB."
                )

            with open(full_path, "rb") as f:
                image_bytes = f.read()

            mime_type, _ = mimetypes.guess_type(full_path)
            if not mime_type or not mime_type.startswith("image/"):
                ext = os.path.splitext(full_path)[1].lower()
                if ext in (".jpg", ".jpeg"):
                    mime_type = "image/jpeg"
                elif ext == ".png":
                    mime_type = "image/png"
                elif ext == ".gif":
                    mime_type = "image/gif"
                elif ext == ".webp":
                    mime_type = "image/webp"
                else:
                    return self.fail_response(
                        f"Unsupported or unknown image format: '{full_path}'. "
                        f"Supported: JPG, PNG, GIF, WEBP."
                    )

            compressed_bytes, compressed_mime_type = self.compress_image(
                image_bytes, mime_type, full_path
            )
            if len(compressed_bytes) > MAX_COMPRESSED_SIZE:
                return self.fail_response(
                    f"Image file '{full_path}' compressed size still too large "
                    f"({len(compressed_bytes) / (1024*1024):.2f}MB), maximum allowed "
                    f"{MAX_COMPRESSED_SIZE / (1024*1024)}MB."
                )

            base64_image = base64.b64encode(compressed_bytes).decode("utf-8")
            image_context_data = {
                "mime_type": compressed_mime_type,
                "base64": base64_image,
                "file_path": full_path,
                "original_size": file_info.st_size,
                "compressed_size": len(compressed_bytes),
            }
            message = ThreadMessage(
                type="image_context", content=image_context_data, is_llm_message=False
            )
            self.vision_message = message
            return ToolResult(
                output=f"Successfully loaded and compressed image '{full_path}'",
                base64_image=base64_image,
            )
        except Exception as e:
            return self.fail_response(f"Error reading image: {str(e)}")

    async def _read_image_daytona(self, file_path: str) -> ToolResult:
        """Read image from Daytona sandbox."""
        await self._ensure_sandbox()
        try:
            cleaned_path = self.clean_path(file_path)
            full_path = f"{self.workspace_path}/{cleaned_path}"
            try:
                file_info = self.sandbox.fs.get_file_info(full_path)
                if file_info.is_dir:
                    return self.fail_response(f"Path '{cleaned_path}' is a directory, not an image file.")
            except Exception:
                return self.fail_response(f"Image file not found: '{cleaned_path}'")

            if file_info.size > MAX_IMAGE_SIZE:
                return self.fail_response(
                    f"Image file '{cleaned_path}' too large "
                    f"({file_info.size / (1024*1024):.2f}MB), maximum allowed "
                    f"{MAX_IMAGE_SIZE / (1024*1024)}MB."
                )

            try:
                image_bytes = self.sandbox.fs.download_file(full_path)
            except Exception:
                return self.fail_response(f"Unable to read image file: {cleaned_path}")

            mime_type, _ = mimetypes.guess_type(full_path)
            if not mime_type or not mime_type.startswith("image/"):
                ext = os.path.splitext(cleaned_path)[1].lower()
                if ext in (".jpg", ".jpeg"):
                    mime_type = "image/jpeg"
                elif ext == ".png":
                    mime_type = "image/png"
                elif ext == ".gif":
                    mime_type = "image/gif"
                elif ext == ".webp":
                    mime_type = "image/webp"
                else:
                    return self.fail_response(
                        f"Unsupported or unknown image format: '{cleaned_path}'. "
                        f"Supported: JPG, PNG, GIF, WEBP."
                    )

            compressed_bytes, compressed_mime_type = self.compress_image(
                image_bytes, mime_type, cleaned_path
            )
            if len(compressed_bytes) > MAX_COMPRESSED_SIZE:
                return self.fail_response(
                    f"Image file '{cleaned_path}' compressed size still too large "
                    f"({len(compressed_bytes) / (1024*1024):.2f}MB), maximum allowed "
                    f"{MAX_COMPRESSED_SIZE / (1024*1024)}MB."
                )

            base64_image = base64.b64encode(compressed_bytes).decode("utf-8")
            image_context_data = {
                "mime_type": compressed_mime_type,
                "base64": base64_image,
                "file_path": cleaned_path,
                "original_size": file_info.size,
                "compressed_size": len(compressed_bytes),
            }
            message = ThreadMessage(
                type="image_context", content=image_context_data, is_llm_message=False
            )
            self.vision_message = message
            return ToolResult(
                output=f"Successfully loaded and compressed image '{cleaned_path}' "
                f"(from {file_info.size / 1024:.1f}KB to {len(compressed_bytes) / 1024:.1f}KB).",
                base64_image=base64_image,
            )
        except Exception as e:
            return self.fail_response(f"Error in Daytona see_image: {str(e)}")

    async def execute(
        self, action: str, file_path: Optional[str] = None, **kwargs
    ) -> ToolResult:
        """
        Execute vision action, currently only supports see_image.
        Args:
            action: Must be 'see_image'
            file_path: Relative path of the image
        """
        if action != "see_image":
            return self.fail_response(f"Unknown vision action: {action}")
        if not file_path:
            return self.fail_response("file_path parameter cannot be empty")

        if self._use_daytona:
            return await self._read_image_daytona(file_path)
        else:
            cleaned_path = self.clean_path(file_path)
            full_path = os.path.join(self.workspace_path, cleaned_path)
            return await self._read_image_local(full_path)

    async def _ensure_sandbox(self):
        """Ensure we have a valid Daytona sandbox instance (lazy init)."""
        if hasattr(self, '_sandbox_initialized') and self._sandbox_initialized:
            return

        # Lazy imports - only import daytona when actually needed
        from app.daytona.sandbox import create_sandbox, start_supervisord_session
        from app.config import config

        if self._daytona_sandbox is None:
            self._daytona_sandbox = await create_sandbox(password=config.daytona.VNC_password)
            start_supervisord_session(self._daytona_sandbox)
            self._sandbox_initialized = True

    @property
    def sandbox(self):
        """Get the sandbox instance (lazy init)."""
        if not hasattr(self, '_sandbox_initialized') or not self._sandbox_initialized:
            raise RuntimeError("Sandbox not initialized. Call _ensure_sandbox() first.")
        return self._daytona_sandbox