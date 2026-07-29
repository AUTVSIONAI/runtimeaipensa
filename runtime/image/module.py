"""
Image Runtime Module

Provides comprehensive image processing, editing, generation, and analysis capabilities.
This module complements the Vision module with more image-focused operations
including batch processing, format conversion, and specialized filters.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple, Union
import asyncio
import logging
import uuid
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageEnhance, ImageOps

from runtime.base.module import (
    RuntimeModule,
    ModuleMetadata,
    ModuleState,
)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from runtime.runtime import Runtime

logger = logging.getLogger(__name__)


class ImageFormat(Enum):
    """Supported image formats."""
    JPEG = "jpeg"
    PNG = "png"
    WEBP = "webp"
    BMP = "bmp"
    TIFF = "tiff"
    GIF = "gif"
    RAW = "raw"
    HEIC = "heic"
    AVIF = "avif"


class ColorSpace(Enum):
    """Color space types."""
    RGB = "rgb"
    RGBA = "rgba"
    GRAYSCALE = "l"
    CMYK = "cmyk"
    LAB = "lab"
    HSV = "hsv"
    YUV = "yuv"


class ImageModel(Enum):
    """Image processing models."""
    # Enhancement
    ESRGAN = "esrgan"
    REAL_ESRGAN = "real_esrgan"
    SWINIR = "swinir"
    GFPGAN = "gfpgan"
    CODE_FORMER = "codeformer"

    # Generation
    STABLE_DIFFUSION_XL = "sdxl"
    STABLE_DIFFUSION_3 = "sd3"
    MIDJOURNEY_V6 = "midjourney_v6"
    DALLE_3 = "dalle_3"
    FLUX = "flux"
    KANDINSKY = "kandinsky"
    PLAYGROUND_V2 = "playground_v2"

    # Editing
    INSTRUCT_PIX2PIX = "instruct_pix2pix"
    CONTROLNET = "controlnet"
    INPAINTING = "inpainting"
    OUTPAINTING = "outpainting"

    # Style Transfer
    ADA_IN = "ada_in"
    WCT = "wct"
    STROTSS = "strotss"
    NEURAL_STYLE = "neural_style"

    # Segmentation/Analysis
    SAM = "sam"
    SAM2 = "sam2"
    DEEPLAB_V3 = "deeplab_v3"
    MASK_RCNN = "mask_rcnn"
    YOLO_SEG = "yolo_seg"
    CLIP = "clip"
    DINO_V2 = "dino_v2"

    CUSTOM = "custom"


class FilterType(Enum):
    """Image filter types."""
    BLUR = "blur"
    GAUSSIAN_BLUR = "gaussian_blur"
    BOX_BLUR = "box_blur"
    MEDIAN_FILTER = "median_filter"
    BILATERAL_FILTER = "bilateral_filter"
    SHARPEN = "sharpen"
    UNSHARP_MASK = "unsharp_mask"
    EDGE_ENHANCE = "edge_enhance"
    EDGE_ENHANCE_MORE = "edge_enhance_more"
    FIND_EDGES = "find_edges"
    EMBOSS = "emboss"
    CONTOUR = "contour"
    SMOOTH = "smooth"
    SMOOTH_MORE = "smooth_more"
    DETAIL = "detail"
    MIN_FILTER = "min_filter"
    MAX_FILTER = "max_filter"
    MODE_FILTER = "mode_filter"


class AdjustmentType(Enum):
    """Image adjustment types."""
    BRIGHTNESS = "brightness"
    CONTRAST = "contrast"
    SATURATION = "saturation"
    HUE = "hue"
    COLOR_BALANCE = "color_balance"
    LEVELS = "levels"
    CURVES = "curves"
    EXPOSURE = "exposure"
    GAMMA = "gamma"
    VIBRANCE = "vibrance"
    TEMPERATURE = "temperature"
    TINT = "tint"


@dataclass
class ImageData:
    """Image data container."""
    image_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    data: np.ndarray = field(default_factory=lambda: np.array([]))
    width: int = 0
    height: int = 0
    channels: int = 3
    format: ImageFormat = ImageFormat.PNG
    color_space: ColorSpace = ColorSpace.RGB
    mode: str = "RGB"
    metadata: Dict[str, Any] = field(default_factory=dict)
    exif: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        if len(self.data) > 0:
            if self.data.ndim == 3:
                self.height, self.width, self.channels = self.data.shape
            elif self.data.ndim == 2:
                self.height, self.width = self.data.shape
                self.channels = 1
            self.mode = "RGB" if self.channels == 3 else "RGBA" if self.channels == 4 else "L"

    def to_pil(self) -> Image.Image:
        """Convert to PIL Image."""
        if self.data.dtype != np.uint8:
            data = (np.clip(self.data, 0, 1) * 255).astype(np.uint8)
        else:
            data = self.data
        return Image.fromarray(data, mode=self.mode)

    def to_bytes(self, format: ImageFormat = ImageFormat.PNG, quality: int = 95) -> bytes:
        """Convert to bytes."""
        pil_img = self.to_pil()
        import io
        buffer = io.BytesIO()
        pil_img.save(buffer, format=format.value.upper(), quality=quality)
        return buffer.getvalue()

    def to_base64(self, format: ImageFormat = ImageFormat.PNG, quality: int = 95) -> str:
        """Convert to base64 string."""
        import base64
        return base64.b64encode(self.to_bytes(format, quality)).decode('utf-8')

    @classmethod
    def from_pil(cls, pil_image: Image.Image, format: ImageFormat = ImageFormat.PNG) -> "ImageData":
        """Create from PIL Image."""
        data = np.array(pil_image)
        return cls(
            data=data,
            width=pil_image.width,
            height=pil_image.height,
            channels=len(pil_image.getbands()),
            format=format,
            mode=pil_image.mode
        )

    @classmethod
    def from_bytes(cls, data: bytes, format: Optional[ImageFormat] = None) -> "ImageData":
        """Create from bytes."""
        import io
        pil_image = Image.open(io.BytesIO(data))
        if format is None:
            format_map = {fmt.value: fmt for fmt in ImageFormat}
            format = format_map.get(pil_image.format.lower(), ImageFormat.PNG)
        return cls.from_pil(pil_image, format)

    @classmethod
    def from_file(cls, file_path: Union[str, Path], format: Optional[ImageFormat] = None) -> "ImageData":
        """Create from file."""
        path = Path(file_path)
        pil_image = Image.open(path)
        if format is None:
            format_map = {fmt.value: fmt for fmt in ImageFormat}
            format = format_map.get(path.suffix.lower().lstrip('.'), ImageFormat.PNG)
        return cls.from_pil(pil_image, format)

    def save(self, file_path: Union[str, Path], format: Optional[ImageFormat] = None, quality: int = 95) -> None:
        """Save to file."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if format is None:
            format_map = {fmt.value: fmt for fmt in ImageFormat}
            format = format_map.get(path.suffix.lower().lstrip('.'), ImageFormat.PNG)
        pil_img = self.to_pil()
        pil_img.save(path, format=format.value.upper(), quality=quality)


@dataclass
class ProcessingResult:
    """Generic image processing result."""
    result_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    image: Optional[ImageData] = None
    images: List[ImageData] = field(default_factory=list)
    processing_time: float = 0.0
    model: Optional[ImageModel] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class GenerationResult:
    """Image generation result."""
    result_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    images: List[ImageData] = field(default_factory=list)
    prompt: str = ""
    negative_prompt: str = ""
    model: ImageModel = ImageModel.STABLE_DIFFUSION_XL
    width: int = 1024
    height: int = 1024
    steps: int = 50
    guidance_scale: float = 7.5
    seed: Optional[int] = None
    processing_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class EditingResult:
    """Image editing result."""
    result_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    image: Optional[ImageData] = None
    edit_type: str = ""
    prompt: str = ""
    mask: Optional[ImageData] = None
    model: ImageModel = ImageModel.INSTRUCT_PIX2PIX
    processing_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class EnhancementResult:
    """Image enhancement result."""
    result_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    image: Optional[ImageData] = None
    enhancement_type: str = ""
    scale: int = 1
    model: ImageModel = ImageModel.ESRGAN
    processing_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class BatchProcessingResult:
    """Batch processing result."""
    result_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    results: List[ProcessingResult] = field(default_factory=list)
    total_images: int = 0
    successful: int = 0
    failed: int = 0
    total_time: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)


class ImageBackend(ABC):
    """Abstract base class for image backends."""

    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        pass


class GenerationBackend(ImageBackend):
    """Image generation backend interface."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
        num_images: int = 1,
        steps: int = 50,
        guidance_scale: float = 7.5,
        seed: Optional[int] = None,
        model: Optional[ImageModel] = None,
        **kwargs
    ) -> GenerationResult:
        pass

    @abstractmethod
    async def generate_image_to_image(
        self,
        image: ImageData,
        prompt: str,
        strength: float = 0.8,
        negative_prompt: str = "",
        steps: int = 50,
        guidance_scale: float = 7.5,
        seed: Optional[int] = None,
        model: Optional[ImageModel] = None,
        **kwargs
    ) -> GenerationResult:
        pass


class EditingBackend(ImageBackend):
    """Image editing backend interface."""

    @abstractmethod
    async def edit(
        self,
        image: ImageData,
        prompt: str,
        edit_type: str = "instruct",
        mask: Optional[ImageData] = None,
        model: Optional[ImageModel] = None,
        **kwargs
    ) -> EditingResult:
        pass

    @abstractmethod
    async def inpaint(
        self,
        image: ImageData,
        mask: ImageData,
        prompt: str,
        negative_prompt: str = "",
        steps: int = 50,
        guidance_scale: float = 7.5,
        model: Optional[ImageModel] = None,
        **kwargs
    ) -> EditingResult:
        pass

    @abstractmethod
    async def outpaint(
        self,
        image: ImageData,
        prompt: str,
        direction: str = "all",
        model: Optional[ImageModel] = None,
        **kwargs
    ) -> EditingResult:
        pass


class EnhancementBackend(ImageBackend):
    """Image enhancement backend interface."""

    @abstractmethod
    async def super_resolution(
        self,
        image: ImageData,
        scale: int = 4,
        model: Optional[ImageModel] = None,
        **kwargs
    ) -> EnhancementResult:
        pass

    @abstractmethod
    async def denoise(
        self,
        image: ImageData,
        strength: float = 0.5,
        model: Optional[ImageModel] = None,
        **kwargs
    ) -> EnhancementResult:
        pass

    @abstractmethod
    async def restore_faces(
        self,
        image: ImageData,
        model: Optional[ImageModel] = None,
        **kwargs
    ) -> EnhancementResult:
        pass

    @abstractmethod
    async def colorize(
        self,
        image: ImageData,
        model: Optional[ImageModel] = None,
        **kwargs
    ) -> EnhancementResult:
        pass


class ProcessingBackend(ImageBackend):
    """Image processing backend interface."""

    @abstractmethod
    async def apply_filter(
        self,
        image: ImageData,
        filter_type: FilterType,
        **kwargs
    ) -> ProcessingResult:
        pass

    @abstractmethod
    async def adjust(
        self,
        image: ImageData,
        adjustment_type: AdjustmentType,
        value: float,
        **kwargs
    ) -> ProcessingResult:
        pass

    @abstractmethod
    async def crop(
        self,
        image: ImageData,
        x: int,
        y: int,
        width: int,
        height: int,
        **kwargs
    ) -> ProcessingResult:
        pass

    @abstractmethod
    async def resize(
        self,
        image: ImageData,
        width: int,
        height: int,
        method: str = "lanczos",
        **kwargs
    ) -> ProcessingResult:
        pass

    @abstractmethod
    async def rotate(
        self,
        image: ImageData,
        angle: float,
        expand: bool = True,
        **kwargs
    ) -> ProcessingResult:
        pass

    @abstractmethod
    async def flip(
        self,
        image: ImageData,
        horizontal: bool = False,
        vertical: bool = False,
        **kwargs
    ) -> ProcessingResult:
        pass

    @abstractmethod
    async def convert_format(
        self,
        image: ImageData,
        format: ImageFormat,
        quality: int = 95,
        **kwargs
    ) -> ProcessingResult:
        pass

    @abstractmethod
    async def convert_color_space(
        self,
        image: ImageData,
        color_space: ColorSpace,
        **kwargs
    ) -> ProcessingResult:
        pass


class AnalysisBackend(ImageBackend):
    """Image analysis backend interface."""

    @abstractmethod
    async def analyze(
        self,
        image: ImageData,
        analysis_type: str = "comprehensive",
        model: Optional[ImageModel] = None,
        **kwargs
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def extract_features(
        self,
        image: ImageData,
        model: Optional[ImageModel] = None,
        **kwargs
    ) -> np.ndarray:
        pass

    @abstractmethod
    async def detect_objects(
        self,
        image: ImageData,
        model: Optional[ImageModel] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        pass


class ImageModule(RuntimeModule):
    """
    Image Runtime Module

    Provides comprehensive image processing capabilities:
    - Image generation (text-to-image, image-to-image)
    - Image editing (inpainting, outpainting, instructed editing)
    - Image enhancement (super-resolution, denoising, face restoration, colorization)
    - Image processing (filters, adjustments, geometric transforms, format conversion)
    - Image analysis (feature extraction, object detection, comprehensive analysis)
    - Batch processing for multiple images
    """

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="image",
            version="1.0.0",
            description="Image processing: generation, editing, enhancement, processing, analysis, batch operations",
            author="AIPENSA",
            dependencies=["numpy", "PIL"],
            provides=["generation", "editing", "enhancement", "processing", "analysis", "batch"],
            tags={"image", "image-processing", "image-generation", "image-editing"}
        )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        # Backends
        self._generation_backend: Optional[GenerationBackend] = None
        self._editing_backend: Optional[EditingBackend] = None
        self._enhancement_backend: Optional[EnhancementBackend] = None
        self._processing_backend: Optional[ProcessingBackend] = None
        self._analysis_backend: Optional[AnalysisBackend] = None

    async def initialize(self, runtime: "Runtime", config: Dict[str, Any]) -> None:
        """Initialize image backends based on configuration."""
        await super().initialize(runtime, config)

        config = self.config

        # Generation backend
        gen_config = config.get("generation", {})
        backend_type = gen_config.get("backend", "mock")
        if backend_type == "mock":
            self._generation_backend = MockGenerationBackend()
        await self._generation_backend.initialize(gen_config)

        # Editing backend
        edit_config = config.get("editing", {})
        backend_type = edit_config.get("backend", "mock")
        if backend_type == "mock":
            self._editing_backend = MockEditingBackend()
        await self._editing_backend.initialize(edit_config)

        # Enhancement backend
        enh_config = config.get("enhancement", {})
        backend_type = enh_config.get("backend", "mock")
        if backend_type == "mock":
            self._enhancement_backend = MockEnhancementBackend()
        await self._enhancement_backend.initialize(enh_config)

        # Processing backend
        proc_config = config.get("processing", {})
        backend_type = proc_config.get("backend", "mock")
        if backend_type == "mock":
            self._processing_backend = MockProcessingBackend()
        await self._processing_backend.initialize(proc_config)

        # Analysis backend
        ana_config = config.get("analysis", {})
        backend_type = ana_config.get("backend", "mock")
        if backend_type == "mock":
            self._analysis_backend = MockAnalysisBackend()
        await self._analysis_backend.initialize(ana_config)

        logger.info("Image module initialized with all backends")

    async def start(self) -> None:
        """Start image module."""
        await super().start()
        logger.info("Image module started")

    async def stop(self) -> None:
        """Stop image module and cleanup backends."""
        for backend in [
            self._generation_backend,
            self._editing_backend,
            self._enhancement_backend,
            self._processing_backend,
            self._analysis_backend
        ]:
            if backend:
                await backend.cleanup()

        await super().stop()
        logger.info("Image module stopped")

    async def cleanup(self) -> None:
        """Clean up all resources."""
        # Cleanup backends
        for backend in [
            self._generation_backend,
            self._editing_backend,
            self._enhancement_backend,
            self._processing_backend,
            self._analysis_backend
        ]:
            if backend:
                await backend.cleanup()

        await super().cleanup()
        logger.info("Image module cleaned up")

    async def health_check(self) -> Dict[str, Any]:
        """Check health of all backends."""
        health = await super().health_check()
        health["backends"] = {}

        for name, backend in [
            ("generation", self._generation_backend),
            ("editing", self._editing_backend),
            ("enhancement", self._enhancement_backend),
            ("processing", self._processing_backend),
            ("analysis", self._analysis_backend)
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

    # Generation Operations
    async def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
        num_images: int = 1,
        steps: int = 50,
        guidance_scale: float = 7.5,
        seed: Optional[int] = None,
        model: Optional[ImageModel] = None,
        **kwargs
    ) -> GenerationResult:
        """Generate images from text prompt."""
        if not self._generation_backend:
            raise RuntimeError("Generation backend not initialized")
        return await self._generation_backend.generate(
            prompt, negative_prompt, width, height, num_images,
            steps, guidance_scale, seed, model, **kwargs
        )

    async def generate_image_to_image(
        self,
        image: ImageData,
        prompt: str,
        strength: float = 0.8,
        negative_prompt: str = "",
        steps: int = 50,
        guidance_scale: float = 7.5,
        seed: Optional[int] = None,
        model: Optional[ImageModel] = None,
        **kwargs
    ) -> GenerationResult:
        """Generate image from image + prompt."""
        if not self._generation_backend:
            raise RuntimeError("Generation backend not initialized")
        return await self._generation_backend.generate_image_to_image(
            image, prompt, strength, negative_prompt, steps,
            guidance_scale, seed, model, **kwargs
        )

    # Editing Operations
    async def edit_image(
        self,
        image: ImageData,
        prompt: str,
        edit_type: str = "instruct",
        mask: Optional[ImageData] = None,
        model: Optional[ImageModel] = None,
        **kwargs
    ) -> EditingResult:
        """Edit image with prompt."""
        if not self._editing_backend:
            raise RuntimeError("Editing backend not initialized")
        return await self._editing_backend.edit(
            image, prompt, edit_type, mask, model, **kwargs
        )

    async def inpaint(
        self,
        image: ImageData,
        mask: ImageData,
        prompt: str,
        negative_prompt: str = "",
        steps: int = 50,
        guidance_scale: float = 7.5,
        model: Optional[ImageModel] = None,
        **kwargs
    ) -> EditingResult:
        """Inpaint masked region."""
        if not self._editing_backend:
            raise RuntimeError("Editing backend not initialized")
        return await self._editing_backend.inpaint(
            image, mask, prompt, negative_prompt, steps,
            guidance_scale, model, **kwargs
        )

    async def outpaint(
        self,
        image: ImageData,
        prompt: str,
        direction: str = "all",
        model: Optional[ImageModel] = None,
        **kwargs
    ) -> EditingResult:
        """Outpaint image beyond boundaries."""
        if not self._editing_backend:
            raise RuntimeError("Editing backend not initialized")
        return await self._editing_backend.outpaint(
            image, prompt, direction, model, **kwargs
        )

    # Enhancement Operations
    async def super_resolution(
        self,
        image: ImageData,
        scale: int = 4,
        model: Optional[ImageModel] = None,
        **kwargs
    ) -> EnhancementResult:
        """Super-resolution upscaling."""
        if not self._enhancement_backend:
            raise RuntimeError("Enhancement backend not initialized")
        return await self._enhancement_backend.super_resolution(
            image, scale, model, **kwargs
        )

    async def denoise(
        self,
        image: ImageData,
        strength: float = 0.5,
        model: Optional[ImageModel] = None,
        **kwargs
    ) -> EnhancementResult:
        """Denoise image."""
        if not self._enhancement_backend:
            raise RuntimeError("Enhancement backend not initialized")
        return await self._enhancement_backend.denoise(
            image, strength, model, **kwargs
        )

    async def restore_faces(
        self,
        image: ImageData,
        model: Optional[ImageModel] = None,
        **kwargs
    ) -> EnhancementResult:
        """Restore faces in image."""
        if not self._enhancement_backend:
            raise RuntimeError("Enhancement backend not initialized")
        return await self._enhancement_backend.restore_faces(
            image, model, **kwargs
        )

    async def colorize(
        self,
        image: ImageData,
        model: Optional[ImageModel] = None,
        **kwargs
    ) -> EnhancementResult:
        """Colorize grayscale image."""
        if not self._enhancement_backend:
            raise RuntimeError("Enhancement backend not initialized")
        return await self._enhancement_backend.colorize(
            image, model, **kwargs
        )

    # Processing Operations
    async def apply_filter(
        self,
        image: ImageData,
        filter_type: FilterType,
        **kwargs
    ) -> ProcessingResult:
        """Apply image filter."""
        if not self._processing_backend:
            raise RuntimeError("Processing backend not initialized")
        return await self._processing_backend.apply_filter(
            image, filter_type, **kwargs
        )

    async def adjust(
        self,
        image: ImageData,
        adjustment_type: AdjustmentType,
        value: float,
        **kwargs
    ) -> ProcessingResult:
        """Apply image adjustment."""
        if not self._processing_backend:
            raise RuntimeError("Processing backend not initialized")
        return await self._processing_backend.adjust(
            image, adjustment_type, value, **kwargs
        )

    async def crop(
        self,
        image: ImageData,
        x: int,
        y: int,
        width: int,
        height: int,
        **kwargs
    ) -> ProcessingResult:
        """Crop image."""
        if not self._processing_backend:
            raise RuntimeError("Processing backend not initialized")
        return await self._processing_backend.crop(
            image, x, y, width, height, **kwargs
        )

    async def resize(
        self,
        image: ImageData,
        width: int,
        height: int,
        method: str = "lanczos",
        **kwargs
    ) -> ProcessingResult:
        """Resize image."""
        if not self._processing_backend:
            raise RuntimeError("Processing backend not initialized")
        return await self._processing_backend.resize(
            image, width, height, method, **kwargs
        )

    async def rotate(
        self,
        image: ImageData,
        angle: float,
        expand: bool = True,
        **kwargs
    ) -> ProcessingResult:
        """Rotate image."""
        if not self._processing_backend:
            raise RuntimeError("Processing backend not initialized")
        return await self._processing_backend.rotate(
            image, angle, expand, **kwargs
        )

    async def flip(
        self,
        image: ImageData,
        horizontal: bool = False,
        vertical: bool = False,
        **kwargs
    ) -> ProcessingResult:
        """Flip image."""
        if not self._processing_backend:
            raise RuntimeError("Processing backend not initialized")
        return await self._processing_backend.flip(
            image, horizontal, vertical, **kwargs
        )

    async def convert_format(
        self,
        image: ImageData,
        format: ImageFormat,
        quality: int = 95,
        **kwargs
    ) -> ProcessingResult:
        """Convert image format."""
        if not self._processing_backend:
            raise RuntimeError("Processing backend not initialized")
        return await self._processing_backend.convert_format(
            image, format, quality, **kwargs
        )

    async def convert_color_space(
        self,
        image: ImageData,
        color_space: ColorSpace,
        **kwargs
    ) -> ProcessingResult:
        """Convert color space."""
        if not(self._processing_backend):
            raise RuntimeError("Processing backend not initialized")
        return await self._processing_backend.convert_color_space(
            image, color_space, **kwargs
        )

    # Analysis Operations
    async def analyze(
        self,
        image: ImageData,
        analysis_type: str = "comprehensive",
        model: Optional[ImageModel] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Analyze image."""
        if not self._analysis_backend:
            raise RuntimeError("Analysis backend not initialized")
        return await self._analysis_backend.analyze(
            image, analysis_type, model, **kwargs
        )

    async def extract_features(
        self,
        image: ImageData,
        model: Optional[ImageModel] = None,
        **kwargs
    ) -> np.ndarray:
        """Extract feature vector."""
        if not self._analysis_backend:
            raise RuntimeError("Analysis backend not initialized")
        return await self._analysis_backend.extract_features(
            image, model, **kwargs
        )

    async def detect_objects(
        self,
        image: ImageData,
        model: Optional[ImageModel] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Detect objects in image."""
        if not self._analysis_backend:
            raise RuntimeError("Analysis backend not initialized")
        return await self._analysis_backend.detect_objects(
            image, model, **kwargs
        )

    # Batch Operations
    async def batch_process(
        self,
        images: List[ImageData],
        operations: List[Dict[str, Any]],
        parallel: bool = True,
        max_workers: int = 4
    ) -> BatchProcessingResult:
        """Process multiple images with a series of operations."""
        result = BatchProcessingResult(total_images=len(images))
        start_time = asyncio.get_event_loop().time()

        semaphore = asyncio.Semaphore(max_workers) if parallel else None

        async def process_image(image: ImageData, idx: int) -> ProcessingResult:
            if semaphore:
                async with semaphore:
                    return await self._process_single_image(image, operations, idx)
            return await self._process_single_image(image, operations, idx)

        tasks = [process_image(img, i) for i, img in enumerate(images)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, res in enumerate(results):
            if isinstance(res, Exception):
                result.failed += 1
                result.results.append(ProcessingResult(
                    image_id=images[i].image_id,
                    processing_time=0,
                    metadata={"error": str(res)}
                ))
            else:
                result.successful += 1
                result.results.append(res)

        result.total_time = asyncio.get_event_loop().time() - start_time
        return result

    async def _process_single_image(
        self,
        image: ImageData,
        operations: List[Dict[str, Any]],
        idx: int
    ) -> ProcessingResult:
        """Process single image through operations chain."""
        current_image = image
        total_time = 0.0

        for op in operations:
            op_type = op.get("type")
            params = op.get("params", {})

            if op_type == "filter":
                res = await self.apply_filter(current_image, params.get("filter_type"), **params)
            elif op_type == "adjust":
                res = await self.adjust(current_image, params.get("adjustment_type"), params.get("value"), **params)
            elif op_type == "crop":
                res = await self.crop(current_image, **params)
            elif op_type == "resize":
                res = await self.resize(current_image, **params)
            elif op_type == "rotate":
                res = await self.rotate(current_image, **params)
            elif op_type == "flip":
                res = await self.flip(current_image, **params)
            elif op_type == "enhance":
                res = await self.super_resolution(current_image, **params)
            else:
                continue

            total_time += res.processing_time
            if res.image:
                current_image = res.image

        return ProcessingResult(
            image=current_image,
            processing_time=total_time,
            metadata={"operations": len(operations)}
        )

    # Convenience Methods
    async def load_image(self, file_path: Union[str, Path]) -> ImageData:
        """Load image from file."""
        return ImageData.from_file(file_path)

    async def save_image(
        self,
        image: ImageData,
        file_path: Union[str, Path],
        format: Optional[ImageFormat] = None,
        quality: int = 95
    ) -> None:
        """Save image to file."""
        image.save(file_path, format, quality)

    async def execute(self, operation: str, **kwargs) -> Any:
        """Execute image module operation."""
        operations = {
            # Generation
            "generate": self.generate,
            "generate_image_to_image": self.generate_image_to_image,
            # Editing
            "edit_image": self.edit_image,
            "inpaint": self.inpaint,
            "outpaint": self.outpaint,
            # Enhancement
            "super_resolution": self.super_resolution,
            "denoise": self.denoise,
            "restore_faces": self.restore_faces,
            "colorize": self.colorize,
            # Processing
            "apply_filter": self.apply_filter,
            "adjust": self.adjust,
            "crop": self.crop,
            "resize": self.resize,
            "rotate": self.rotate,
            "flip": self.flip,
            "convert_format": self.convert_format,
            "convert_color_space": self.convert_color_space,
            # Analysis
            "analyze": self.analyze,
            "extract_features": self.extract_features,
            "detect_objects": self.detect_objects,
            # Batch
            "batch_process": self.batch_process,
            # Utils
            "load_image": self.load_image,
            "save_image": self.save_image,
        }
        if operation in operations:
            return await operations[operation](**kwargs)
        raise NotImplementedError(f"Operation '{operation}' not supported")


# Mock backends for testing/fallback
class MockGenerationBackend(GenerationBackend):
    async def initialize(self, config: Dict[str, Any]) -> None:
        pass
    async def cleanup(self) -> None:
        pass
    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy", "backend": "mock_generation"}
    async def generate(self, prompt: str, negative_prompt: str = "", width: int = 1024, height: int = 1024, num_images: int = 1, steps: int = 50, guidance_scale: float = 7.5, seed: Optional[int] = None, model: Optional[ImageModel] = None, **kwargs) -> GenerationResult:
        import random
        images = []
        for i in range(num_images):
            data = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
            images.append(ImageData.from_pil(Image.fromarray(data)))
        return GenerationResult(
            images=images, prompt=prompt, negative_prompt=negative_prompt,
            model=model or ImageModel.STABLE_DIFFUSION_XL, width=width, height=height,
            steps=steps, guidance_scale=guidance_scale, seed=seed or random.randint(0, 2**32)
        )
    async def generate_image_to_image(self, image: ImageData, prompt: str, strength: float = 0.8, negative_prompt: str = "", steps: int = 50, guidance_scale: float = 7.5, seed: Optional[int] = None, model: Optional[ImageModel] = None, **kwargs) -> GenerationResult:
        return await self.generate(prompt, negative_prompt, image.width, image.height, 1, steps, guidance_scale, seed, model, **kwargs)


class MockEditingBackend(EditingBackend):
    async def initialize(self, config: Dict[str, Any]) -> None:
        pass
    async def cleanup(self) -> None:
        pass
    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy", "backend": "mock_editing"}
    async def edit(self, image: ImageData, prompt: str, edit_type: str = "instruct", mask: Optional[ImageData] = None, model: Optional[ImageModel] = None, **kwargs) -> EditingResult:
        return EditingResult(image=image, edit_type=edit_type, prompt=prompt, mask=mask, model=model or ImageModel.INSTRUCT_PIX2PIX)
    async def inpaint(self, image: ImageData, mask: ImageData, prompt: str, negative_prompt: str = "", steps: int = 50, guidance_scale: float = 7.5, model: Optional[ImageModel] = None, **kwargs) -> EditingResult:
        return EditingResult(image=image, edit_type="inpaint", prompt=prompt, mask=mask, model=model or ImageModel.INPAINTING)
    async def outpaint(self, image: ImageData, prompt: str, direction: str = "all", model: Optional[ImageModel] = None, **kwargs) -> EditingResult:
        return EditingResult(image=image, edit_type="outpaint", prompt=prompt, model=model or ImageModel.OUTPAINTING)


class MockEnhancementBackend(EnhancementBackend):
    async def initialize(self, config: Dict[str, Any]) -> None:
        pass
    async def cleanup(self) -> None:
        pass
    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy", "backend": "mock_enhancement"}
    async def super_resolution(self, image: ImageData, scale: int = 4, model: Optional[ImageModel] = None, **kwargs) -> EnhancementResult:
        new_w, new_h = image.width * scale, image.height * scale
        data = np.random.randint(0, 255, (new_h, new_w, 3), dtype=np.uint8)
        return EnhancementResult(image=ImageData.from_pil(Image.fromarray(data)), enhancement_type="super_resolution", scale=scale, model=model or ImageModel.REAL_ESRGAN)
    async def denoise(self, image: ImageData, strength: float = 0.5, model: Optional[ImageModel] = None, **kwargs) -> EnhancementResult:
        return EnhancementResult(image=image, enhancement_type="denoise", model=model or ImageModel.REAL_ESRGAN)
    async def restore_faces(self, image: ImageData, model: Optional[ImageModel] = None, **kwargs) -> EnhancementResult:
        return EnhancementResult(image=image, enhancement_type="face_restore", model=model or ImageModel.GFPGAN)
    async def colorize(self, image: ImageData, model: Optional[ImageModel] = None, **kwargs) -> EnhancementResult:
        return EnhancementResult(image=image, enhancement_type="colorize", model=model or ImageModel.CUSTOM)


class MockProcessingBackend(ProcessingBackend):
    async def initialize(self, config: Dict[str, Any]) -> None:
        pass
    async def cleanup(self) -> None:
        pass
    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy", "backend": "mock_processing"}
    async def apply_filter(self, image: ImageData, filter_type: FilterType, **kwargs) -> ProcessingResult:
        return ProcessingResult(image=image, model=ImageModel.CUSTOM)
    async def adjust(self, image: ImageData, adjustment_type: AdjustmentType, value: float, **kwargs) -> ProcessingResult:
        return ProcessingResult(image=image, model=ImageModel.CUSTOM)
    async def crop(self, image: ImageData, x: int, y: int, width: int, height: int, **kwargs) -> ProcessingResult:
        pil = image.to_pil()
        cropped = pil.crop((x, y, x+width, y+height))
        return ProcessingResult(image=ImageData.from_pil(cropped), model=ImageModel.CUSTOM)
    async def resize(self, image: ImageData, width: int, height: int, method: str = "lanczos", **kwargs) -> ProcessingResult:
        pil = image.to_pil()
        resized = pil.resize((width, height), getattr(Image.Resampling, method.upper(), Image.Resampling.LANCZOS))
        return ProcessingResult(image=ImageData.from_pil(resized), model=ImageModel.CUSTOM)
    async def rotate(self, image: ImageData, angle: float, expand: bool = True, **kwargs) -> ProcessingResult:
        pil = image.to_pil()
        rotated = pil.rotate(angle, expand=expand)
        return ProcessingResult(image=ImageData.from_pil(rotated), model=ImageModel.CUSTOM)
    async def flip(self, image: ImageData, horizontal: bool = False, vertical: bool = False, **kwargs) -> ProcessingResult:
        pil = image.to_pil()
        if horizontal:
            pil = pil.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        if vertical:
            pil = pil.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        return ProcessingResult(image=ImageData.from_pil(pil), model=ImageModel.CUSTOM)
    async def convert_format(self, image: ImageData, format: ImageFormat, quality: int = 95, **kwargs) -> ProcessingResult:
        return ProcessingResult(image=image, model=ImageModel.CUSTOM)
    async def convert_color_space(self, image: ImageData, color_space: ColorSpace, **kwargs) -> ProcessingResult:
        return ProcessingResult(image=image, model=ImageModel.CUSTOM)


class MockAnalysisBackend(AnalysisBackend):
    async def initialize(self, config: Dict[str, Any]) -> None:
        pass
    async def cleanup(self) -> None:
        pass
    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy", "backend": "mock_analysis"}
    async def analyze(self, image: ImageData, analysis_type: str = "comprehensive", model: Optional[ImageModel] = None, **kwargs) -> Dict[str, Any]:
        return {"width": image.width, "height": image.height, "channels": image.channels, "format": image.format.value, "dominant_colors": ["#FF0000", "#00FF00", "#0000FF"]}
    async def extract_features(self, image: ImageData, model: Optional[ImageModel] = None, **kwargs) -> np.ndarray:
        return np.random.rand(512).astype(np.float32)
    async def detect_objects(self, image: ImageData, model: Optional[ImageModel] = None, **kwargs) -> List[Dict[str, Any]]:
        return [{"class": "person", "confidence": 0.9, "bbox": [10, 10, 100, 200]}]


__all__ = [
    "ImageModule",
    "ImageData",
    "ImageFormat",
    "ColorSpace",
    "ImageModel",
    "FilterType",
    "AdjustmentType",
    "ProcessingResult",
    "GenerationResult",
    "EditingResult",
    "EnhancementResult",
    "BatchProcessingResult",
    "ImageBackend",
    "GenerationBackend",
    "EditingBackend",
    "EnhancementBackend",
    "ProcessingBackend",
    "AnalysisBackend",
]