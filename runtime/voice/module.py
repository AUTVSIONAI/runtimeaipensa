"""
Voice Runtime Module

Provides speech-to-text, text-to-speech, voice activity detection,
speaker identification, and voice command processing capabilities.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional, Callable
import asyncio
import base64
import logging
import uuid

import numpy as np

from runtime.base.module import (
    RuntimeModule,
    ModuleMetadata,
    ModuleState,
)

logger = logging.getLogger(__name__)


class AudioFormat(Enum):
    """Audio format types."""
    WAV = "wav"
    MP3 = "mp3"
    OGG = "ogg"
    FLAC = "flac"
    PCM = "pcm"
    WEBM = "webm"
    M4A = "m4a"


class VoiceModel(Enum):
    """Voice model types."""
    WHISPER_TINY = "whisper-tiny"
    WHISPER_BASE = "whisper-base"
    WHISPER_SMALL = "whisper-small"
    WHISPER_MEDIUM = "whisper-medium"
    WHISPER_LARGE = "whisper-large"
    DEEPGRAM_NOVA = "deepgram-nova"
    DEEPGRAM_ENHANCED = "deepgram-enhanced"
    GOOGLE_CHIRP = "google-chirp"
    AZURE_WHISPER = "azure-whisper"
    AZURE_NEURAL = "azure-neural"
    ELEVENLABS = "elevenlabs"
    OPENVOICE = "openvoice"
    BARK = "bark"
    VITS = "vits"
    TACOTRON2 = "tacotron2"
    COQUI = "coqui"
    CUSTOM = "custom"


class VoiceActivityStatus(Enum):
    """Voice activity detection status."""
    SPEECH = "speech"
    SILENCE = "silence"
    NOISE = "noise"
    UNKNOWN = "unknown"


class SpeakerGender(Enum):
    """Speaker gender classification."""
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNKNOWN = "unknown"


class SpeakerAgeGroup(Enum):
    """Speaker age group classification."""
    CHILD = "child"
    TEENAGER = "teenager"
    YOUNG_ADULT = "young_adult"
    ADULT = "adult"
    SENIOR = "senior"
    UNKNOWN = "unknown"


@dataclass
class AudioData:
    """Raw audio data container."""
    audio_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    data: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float32))
    sample_rate: int = 16000
    channels: int = 1
    format: AudioFormat = AudioFormat.WAV
    duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        if len(self.data) > 0:
            self.duration = len(self.data) / self.sample_rate

    def to_bytes(self) -> bytes:
        """Convert audio data to bytes."""
        if self.format == AudioFormat.WAV:
            import io
            import wave
            buffer = io.BytesIO()
            with wave.open(buffer, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(self.sample_rate)
                # Convert float32 to int16
                int16_data = (self.data * 32767).astype('<i2')
                wf.writeframes(int16_data.tobytes())
            return buffer.getvalue()
        return base64.b64encode(self.data.tobytes())

    @classmethod
    def from_bytes(cls, data: bytes, sample_rate: int = 16000, channels: int = 1,
                   format: AudioFormat = AudioFormat.WAV) -> "AudioData":
        """Create audio data from bytes."""
        if format == AudioFormat.WAV:
            import io
            import wave
            buffer = io.BytesIO(data)
            with wave.open(buffer, 'rb') as wf:
                n_channels = wf.getnchannels()
                sample_rate = wf.getframerate()
                n_frames = wf.getnframes()
                audio_bytes = wf.readframes(n_frames)
                audio_data = np.frombuffer(audio_bytes, dtype='<i2').astype(np.float32) / 32767.0
                if n_channels > 1:
                    audio_data = audio_data.reshape(-1, n_channels).mean(axis=1)
                return cls(data=audio_data, sample_rate=sample_rate, channels=1, format=format)
        # For other formats, assume raw PCM
        audio_data = np.frombuffer(data, dtype=np.float32)
        return cls(data=audio_data, sample_rate=sample_rate, channels=channels, format=format)


@dataclass
class TranscriptionResult:
    """Speech-to-text transcription result."""
    transcription_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    text: str = ""
    confidence: float = 0.0
    language: str = "en"
    language_probability: float = 0.0
    segments: List[Dict[str, Any]] = field(default_factory=list)
    words: List[Dict[str, Any]] = field(default_factory=list)
    duration: float = 0.0
    processing_time: float = 0.0
    model: VoiceModel = VoiceModel.WHISPER_BASE
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transcription_id": self.transcription_id,
            "text": self.text,
            "confidence": self.confidence,
            "language": self.language,
            "language_probability": self.language_probability,
            "segments": self.segments,
            "words": self.words,
            "duration": self.duration,
            "processing_time": self.processing_time,
            "model": self.model.value,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class SpeechSynthesisResult:
    """Text-to-speech synthesis result."""
    synthesis_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    audio: Optional[AudioData] = None
    text: str = ""
    voice: str = ""
    model: VoiceModel = VoiceModel.ELEVENLABS
    duration: float = 0.0
    processing_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "synthesis_id": self.synthesis_id,
            "audio_id": self.audio.audio_id if self.audio else None,
            "text": self.text,
            "voice": self.voice,
            "model": self.model.value,
            "duration": self.duration,
            "processing_time": self.processing_time,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class VoiceActivityResult:
    """Voice activity detection result."""
    vad_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    status: VoiceActivityStatus = VoiceActivityStatus.UNKNOWN
    confidence: float = 0.0
    speech_segments: List[Dict[str, Any]] = field(default_factory=list)
    silence_segments: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vad_id": self.vad_id,
            "status": self.status.value,
            "confidence": self.confidence,
            "speech_segments": self.speech_segments,
            "silence_segments": self.silence_segments,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class SpeakerProfile:
    """Speaker identification profile."""
    speaker_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    embedding: Optional[List[float]] = None
    gender: SpeakerGender = SpeakerGender.UNKNOWN
    age_group: SpeakerAgeGroup = SpeakerAgeGroup.UNKNOWN
    enrolled_audio_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "speaker_id": self.speaker_id,
            "name": self.name,
            "has_embedding": self.embedding is not None,
            "gender": self.gender.value,
            "age_group": self.age_group.value,
            "enrolled_audio_count": self.enrolled_audio_count,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


@dataclass
class SpeakerIdentificationResult:
    """Speaker identification result."""
    identification_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    speaker_id: Optional[str] = None
    speaker_name: Optional[str] = None
    confidence: float = 0.0
    all_scores: Dict[str, float] = field(default_factory=dict)
    is_unknown: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "identification_id": self.identification_id,
            "speaker_id": self.speaker_id,
            "speaker_name": self.speaker_name,
            "confidence": self.confidence,
            "all_scores": self.all_scores,
            "is_unknown": self.is_unknown,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class VoiceCommand:
    """Voice command structure."""
    command_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    intent: str = ""
    entities: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    raw_text: str = ""
    action: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command_id": self.command_id,
            "intent": self.intent,
            "entities": self.entities,
            "confidence": self.confidence,
            "raw_text": self.raw_text,
            "action": self.action,
            "parameters": self.parameters,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


class VoiceBackend(ABC):
    """Abstract base class for voice backends."""

    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the backend."""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up backend resources."""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check backend health."""
        pass


class STTBackend(VoiceBackend):
    """Speech-to-text backend interface."""

    @abstractmethod
    async def transcribe(
        self,
        audio: AudioData,
        language: Optional[str] = None,
        model: Optional[VoiceModel] = None,
        **kwargs
    ) -> TranscriptionResult:
        """Transcribe audio to text."""
        pass

    @abstractmethod
    async def transcribe_stream(
        self,
        audio_stream: AsyncIterator[AudioData],
        language: Optional[str] = None,
        model: Optional[VoiceModel] = None,
        **kwargs
    ) -> AsyncIterator[TranscriptionResult]:
        """Stream transcription of audio chunks."""
        pass


class TTSBackend(VoiceBackend):
    """Text-to-speech backend interface."""

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        model: Optional[VoiceModel] = None,
        speed: float = 1.0,
        pitch: float = 1.0,
        **kwargs
    ) -> SpeechSynthesisResult:
        """Synthesize speech from text."""
        pass

    @abstractmethod
    async def synthesize_stream(
        self,
        text_stream: AsyncIterator[str],
        voice: Optional[str] = None,
        model: Optional[VoiceModel] = None,
        **kwargs
    ) -> AsyncIterator[SpeechSynthesisResult]:
        """Stream synthesis of text chunks."""
        pass

    @abstractmethod
    async def list_voices(self) -> List[Dict[str, Any]]:
        """List available voices."""
        pass


class VADBackend(VoiceBackend):
    """Voice activity detection backend interface."""

    @abstractmethod
    async def detect(
        self,
        audio: AudioData,
        **kwargs
    ) -> VoiceActivityResult:
        """Detect voice activity in audio."""
        pass

    @abstractmethod
    async def detect_stream(
        self,
        audio_stream: AsyncIterator[AudioData],
        **kwargs
    ) -> AsyncIterator[VoiceActivityResult]:
        """Stream voice activity detection."""
        pass


class SpeakerBackend(VoiceBackend):
    """Speaker identification backend interface."""

    @abstractmethod
    async def enroll(
        self,
        audio: AudioData,
        speaker_id: Optional[str] = None,
        name: Optional[str] = None,
        **kwargs
    ) -> SpeakerProfile:
        """Enroll a speaker from audio."""
        pass

    @abstractmethod
    async def identify(
        self,
        audio: AudioData,
        **kwargs
    ) -> SpeakerIdentificationResult:
        """Identify speaker from audio."""
        pass

    @abstractmethod
    async def verify(
        self,
        audio: AudioData,
        speaker_id: str,
        **kwargs
    ) -> SpeakerIdentificationResult:
        """Verify if audio matches enrolled speaker."""
        pass

    @abstractmethod
    async def delete_speaker(self, speaker_id: str) -> bool:
        """Delete enrolled speaker."""
        pass

    @abstractmethod
    async def list_speakers(self) -> List[SpeakerProfile]:
        """List enrolled speakers."""
        pass


class VoiceCommandBackend(VoiceBackend):
    """Voice command processing backend interface."""

    @abstractmethod
    async def parse_command(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> VoiceCommand:
        """Parse voice command from transcribed text."""
        pass

    @abstractmethod
    async def add_intent(
        self,
        intent: str,
        patterns: List[str],
        action: str,
        entities: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> None:
        """Add custom intent pattern."""
        pass


class WhisperSTTBackend(STTBackend):
    """Whisper-based speech-to-text backend."""

    def __init__(self):
        self._model = None
        self._config = {}

    async def initialize(self, config: Dict[str, Any]) -> None:
        self._config = config
        model_size = config.get("model_size", "base")
        device = config.get("device", "cpu")
        compute_type = config.get("compute_type", "int8")

        try:
            import whisper
            self._model = whisper.load_model(model_size, device=device)
            logger.info(f"Whisper model '{model_size}' loaded on {device}")
        except ImportError:
            logger.warning("Whisper not installed. Using mock implementation.")

    async def cleanup(self) -> None:
        self._model = None

    async def health_check(self) -> Dict[str, Any]:
        return {
            "status": "healthy" if self._model else "degraded",
            "model": self._config.get("model_size", "unknown"),
            "device": self._config.get("device", "cpu")
        }

    async def transcribe(
        self,
        audio: AudioData,
        language: Optional[str] = None,
        model: Optional[VoiceModel] = None,
        **kwargs
    ) -> TranscriptionResult:
        start_time = datetime.utcnow()

        if self._model:
            import tempfile
            import os

            # Save audio to temp file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                audio_bytes = audio.to_bytes()
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            try:
                result = self._model.transcribe(
                    tmp_path,
                    language=language,
                    **kwargs
                )
                text = result.get("text", "").strip()
                segments = result.get("segments", [])
                language = result.get("language", language or "en")

                confidence = np.mean([s.get("avg_logprob", 0) for s in segments]) if segments else 0.0
                confidence = max(0.0, min(1.0, (confidence + 1.0) / 2.0))  # Normalize

                words = []
                for seg in segments:
                    for word in seg.get("words", []):
                        words.append({
                            "word": word.get("word", ""),
                            "start": word.get("start", 0),
                            "end": word.get("end", 0),
                            "confidence": word.get("probability", 0)
                        })

                processing_time = (datetime.utcnow() - start_time).total_seconds()

                return TranscriptionResult(
                    text=text,
                    confidence=confidence,
                    language=language,
                    language_probability=0.9,
                    segments=[{"start": s["start"], "end": s["end"], "text": s["text"]} for s in segments],
                    words=words,
                    duration=audio.duration,
                    processing_time=processing_time,
                    model=model or VoiceModel.WHISPER_BASE,
                    metadata={"segments_count": len(segments)}
                )
            finally:
                os.unlink(tmp_path)

        # Mock implementation
        return TranscriptionResult(
            text="[Mock transcription] This is a mock transcription result.",
            confidence=0.95,
            language=language or "en",
            language_probability=0.95,
            duration=audio.duration,
            processing_time=(datetime.utcnow() - start_time).total_seconds(),
            model=model or VoiceModel.WHISPER_BASE,
            metadata={"mock": True}
        )

    async def transcribe_stream(
        self,
        audio_stream: AsyncIterator[AudioData],
        language: Optional[str] = None,
        model: Optional[VoiceModel] = None,
        **kwargs
    ) -> AsyncIterator[TranscriptionResult]:
        async for audio in audio_stream:
            yield await self.transcribe(audio, language, model, **kwargs)


class MockTTSBackend(TTSBackend):
    """Mock text-to-speech backend for testing."""

    def __init__(self):
        self._voices = [
            {"id": "voice_1", "name": "Alice", "gender": "female", "language": "en-US"},
            {"id": "voice_2", "name": "Bob", "gender": "male", "language": "en-US"},
            {"id": "voice_3", "name": "Carol", "gender": "female", "language": "en-GB"},
            {"id": "voice_4", "name": "David", "gender": "male", "language": "en-AU"},
        ]
        self._config = {}

    async def initialize(self, config: Dict[str, Any]) -> None:
        self._config = config
        logger.info("Mock TTS backend initialized")

    async def cleanup(self) -> None:
        pass

    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy", "backend": "mock_tts"}

    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        model: Optional[VoiceModel] = None,
        speed: float = 1.0,
        pitch: float = 1.0,
        **kwargs
    ) -> SpeechSynthesisResult:
        start_time = datetime.utcnow()

        # Generate mock audio data
        duration = len(text) * 0.05 / speed  # Rough estimate
        sample_rate = 22050
        num_samples = int(duration * sample_rate)
        audio_data = np.random.randn(num_samples).astype(np.float32) * 0.1

        audio = AudioData(
            data=audio_data,
            sample_rate=sample_rate,
            channels=1,
            format=AudioFormat.WAV
        )

        processing_time = (datetime.utcnow() - start_time).total_seconds()

        return SpeechSynthesisResult(
            audio=audio,
            text=text,
            voice=voice or "voice_1",
            model=model or VoiceModel.ELEVENLABS,
            duration=duration,
            processing_time=processing_time,
            metadata={"mock": True, "speed": speed, "pitch": pitch}
        )

    async def synthesize_stream(
        self,
        text_stream: AsyncIterator[str],
        voice: Optional[str] = None,
        model: Optional[VoiceModel] = None,
        **kwargs
    ) -> AsyncIterator[SpeechSynthesisResult]:
        async for text in text_stream:
            yield await self.synthesize(text, voice, model, **kwargs)

    async def list_voices(self) -> List[Dict[str, Any]]:
        return self._voices


class SileroVADBackend(VADBackend):
    """Silero VAD backend for voice activity detection."""

    def __init__(self):
        self._model = None
        self._config = {}

    async def initialize(self, config: Dict[str, Any]) -> None:
        self._config = config
        threshold = config.get("threshold", 0.5)
        min_speech_duration_ms = config.get("min_speech_duration_ms", 250)
        min_silence_duration_ms = config.get("min_silence_duration_ms", 100)

        try:
            import torch
            model, utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                trust_repo=True
            )
            self._model = model
            self._get_speech_timestamps = utils[0]
            logger.info(f"Silero VAD loaded with threshold={threshold}")
        except Exception as e:
            logger.warning(f"Silero VAD not available: {e}. Using mock.")

    async def cleanup(self) -> None:
        self._model = None

    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy" if self._model else "degraded"}

    async def detect(
        self,
        audio: AudioData,
        **kwargs
    ) -> VoiceActivityResult:
        if self._model:
            import torch

            # Ensure audio is correct format for Silero (16kHz, mono)
            if audio.sample_rate != 16000:
                # Resample if needed (simplified)
                pass

            audio_tensor = torch.from_numpy(audio.data).float()
            speech_timestamps = self._get_speech_timestamps(
                audio_tensor,
                self._model,
                threshold=kwargs.get("threshold", 0.5),
                sampling_rate=audio.sample_rate,
                min_speech_duration_ms=kwargs.get("min_speech_duration_ms", 250),
                min_silence_duration_ms=kwargs.get("min_silence_duration_ms", 100)
            )

            speech_segments = [
                {"start": ts["start"] / audio.sample_rate, "end": ts["end"] / audio.sample_rate}
                for ts in speech_timestamps
            ]

            # Calculate silence segments
            silence_segments = []
            prev_end = 0
            for seg in speech_segments:
                if seg["start"] > prev_end:
                    silence_segments.append({"start": prev_end, "end": seg["start"]})
                prev_end = seg["end"]
            if prev_end < audio.duration:
                silence_segments.append({"start": prev_end, "end": audio.duration})

            status = VoiceActivityStatus.SPEECH if speech_segments else VoiceActivityStatus.SILENCE
            confidence = 0.9 if speech_segments else 0.1

            return VoiceActivityResult(
                status=status,
                confidence=confidence,
                speech_segments=speech_segments,
                silence_segments=silence_segments
            )

        # Mock implementation
        import random
        is_speech = random.random() > 0.3
        return VoiceActivityResult(
            status=VoiceActivityStatus.SPEECH if is_speech else VoiceActivityStatus.SILENCE,
            confidence=0.8 if is_speech else 0.9,
            speech_segments=[{"start": 0, "end": audio.duration}] if is_speech else [],
            silence_segments=[] if is_speech else [{"start": 0, "end": audio.duration}],
            metadata={"mock": True}
        )

    async def detect_stream(
        self,
        audio_stream: AsyncIterator[AudioData],
        **kwargs
    ) -> AsyncIterator[VoiceActivityResult]:
        async for audio in audio_stream:
            yield await self.detect(audio, **kwargs)


class MockSpeakerBackend(SpeakerBackend):
    """Mock speaker identification backend."""

    def __init__(self):
        self._speakers: Dict[str, SpeakerProfile] = {}
        self._config = {}

    async def initialize(self, config: Dict[str, Any]) -> None:
        self._config = config
        logger.info("Mock speaker backend initialized")

    async def cleanup(self) -> None:
        self._speakers.clear()

    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy", "speakers_enrolled": len(self._speakers)}

    async def enroll(
        self,
        audio: AudioData,
        speaker_id: Optional[str] = None,
        name: Optional[str] = None,
        **kwargs
    ) -> SpeakerProfile:
        speaker_id = speaker_id or str(uuid.uuid4())[:8]
        profile = SpeakerProfile(
            speaker_id=speaker_id,
            name=name or f"Speaker {speaker_id}",
            embedding=[0.1] * 256,  # Mock embedding
            enrolled_audio_count=1,
            metadata={"mock": True}
        )
        self._speakers[speaker_id] = profile
        return profile

    async def identify(
        self,
        audio: AudioData,
        **kwargs
    ) -> SpeakerIdentificationResult:
        if not self._speakers:
            return SpeakerIdentificationResult(
                is_unknown=True,
                confidence=0.0,
                metadata={"mock": True, "reason": "no_speakers_enrolled"}
            )

        # Mock: pick random speaker
        import random
        speaker_id = random.choice(list(self._speakers.keys()))
        speaker = self._speakers[speaker_id]

        return SpeakerIdentificationResult(
            speaker_id=speaker_id,
            speaker_name=speaker.name,
            confidence=random.uniform(0.7, 0.95),
            all_scores={speaker_id: random.uniform(0.7, 0.95)},
            is_unknown=False,
            metadata={"mock": True}
        )

    async def verify(
        self,
        audio: AudioData,
        speaker_id: str,
        **kwargs
    ) -> SpeakerIdentificationResult:
        speaker = self._speakers.get(speaker_id)
        if not speaker:
            return SpeakerIdentificationResult(
                is_unknown=True,
                confidence=0.0,
                metadata={"mock": True, "reason": "speaker_not_found"}
            )

        import random
        confidence = random.uniform(0.6, 0.95)
        return SpeakerIdentificationResult(
            speaker_id=speaker_id,
            speaker_name=speaker.name,
            confidence=confidence,
            all_scores={speaker_id: confidence},
            is_unknown=confidence < 0.5,
            metadata={"mock": True}
        )

    async def delete_speaker(self, speaker_id: str) -> bool:
        if speaker_id in self._speakers:
            del self._speakers[speaker_id]
            return True
        return False

    async def list_speakers(self) -> List[SpeakerProfile]:
        return list(self._speakers.values())


class MockVoiceCommandBackend(VoiceCommandBackend):
    """Mock voice command processing backend."""

    def __init__(self):
        self._intents: Dict[str, Dict[str, Any]] = {}
        self._config = {}

    async def initialize(self, config: Dict[str, Any]) -> None:
        self._config = config
        # Add default intents
        await self.add_intent(
            intent="play_music",
            patterns=["play music", "play song", "start music"],
            action="music.play",
            entities={"song": "string", "artist": "string"}
        )
        await self.add_intent(
            intent="set_timer",
            patterns=["set timer", "start timer", "timer for"],
            action="timer.set",
            entities={"duration": "duration"}
        )
        await self.add_intent(
            intent="get_weather",
            patterns=["weather", "what's the weather", "temperature"],
            action="weather.get",
            entities={"location": "string"}
        )
        logger.info("Mock voice command backend initialized")

    async def cleanup(self) -> None:
        self._intents.clear()

    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy", "intents_count": len(self._intents)}

    async def parse_command(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> VoiceCommand:
        text_lower = text.lower()

        # Simple pattern matching
        best_intent = None
        best_confidence = 0.0
        entities = {}

        for intent_name, intent_data in self._intents.items():
            for pattern in intent_data["patterns"]:
                if pattern.lower() in text_lower:
                    confidence = len(pattern) / len(text_lower)
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_intent = intent_name

        # Extract entities (simplified)
        if best_intent and best_intent in self._intents:
            intent_data = self._intents[best_intent]
            for entity_name, entity_type in intent_data.get("entities", {}).items():
                # Simplified extraction
                entities[entity_name] = f"extracted_{entity_name}"

        return VoiceCommand(
            intent=best_intent or "unknown",
            entities=entities,
            confidence=best_confidence,
            raw_text=text,
            action=self._intents.get(best_intent, {}).get("action") if best_intent else None,
            metadata={"mock": True}
        )

    async def add_intent(
        self,
        intent: str,
        patterns: List[str],
        action: str,
        entities: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> None:
        self._intents[intent] = {
            "patterns": patterns,
            "action": action,
            "entities": entities or {}
        }


# Mock backend classes for fallback
class MockSTTBackend(STTBackend):
    async def initialize(self, config: Dict[str, Any]) -> None:
        pass
    async def cleanup(self) -> None:
        pass
    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy", "backend": "mock_stt"}
    async def transcribe(self, audio: AudioData, language: Optional[str] = None, model: Optional[VoiceModel] = None, **kwargs) -> TranscriptionResult:
        return TranscriptionResult(text="[Mock] " + "a" * 10, confidence=0.9, language=language or "en", duration=audio.duration, model=model or VoiceModel.WHISPER_BASE)
    async def transcribe_stream(self, audio_stream: AsyncIterator[AudioData], language: Optional[str] = None, model: Optional[VoiceModel] = None, **kwargs) -> AsyncIterator[TranscriptionResult]:
        async for audio in audio_stream:
            yield await self.transcribe(audio, language, model, **kwargs)


class MockVADBackend(VADBackend):
    async def initialize(self, config: Dict[str, Any]) -> None:
        pass
    async def cleanup(self) -> None:
        pass
    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy", "backend": "mock_vad"}
    async def detect(self, audio: AudioData, **kwargs) -> VoiceActivityResult:
        return VoiceActivityResult(status=VoiceActivityStatus.SPEECH, confidence=0.8, metadata={"mock": True})
    async def detect_stream(self, audio_stream: AsyncIterator[AudioData], **kwargs) -> AsyncIterator[VoiceActivityResult]:
        async for audio in audio_stream:
            yield await self.detect(audio, **kwargs)


class VoiceModule(RuntimeModule):
    """Voice runtime module providing speech-to-text, text-to-speech, VAD, speaker ID, and voice commands."""

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="voice",
            version="1.0.0",
            description="Speech-to-text, text-to-speech, voice activity detection, speaker identification, and voice commands",
            author="AIPENSA",
            dependencies=["numpy"],
            provides=["stt", "tts", "vad", "speaker_id", "voice_commands"],
            tags={"voice", "speech", "audio", "stt", "tts"}
        )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__()

        self._config = config or {}

        # Backends
        self._stt_backend: Optional[STTBackend] = None
        self._tts_backend: Optional[TTSBackend] = None
        self._vad_backend: Optional[VADBackend] = None
        self._speaker_backend: Optional[SpeakerBackend] = None
        self._command_backend: Optional[VoiceCommandBackend] = None

        # Audio processing queue
        self._audio_queue: asyncio.Queue = asyncio.Queue()
        self._processing_task: Optional[asyncio.Task] = None

    async def initialize(self, runtime: "Runtime", config: Dict[str, Any]) -> None:
        """Initialize voice backends based on configuration."""
        await super().initialize(runtime, config)

        stt_config = self.config.get("stt", {})
        tts_config = self.config.get("tts", {})
        vad_config = self.config.get("vad", {})
        speaker_config = self.config.get("speaker", {})
        command_config = self.config.get("commands", {})

        # Initialize STT backend
        stt_backend = stt_config.get("backend", "whisper")
        if stt_backend == "whisper":
            self._stt_backend = WhisperSTTBackend()
            await self._stt_backend.initialize(stt_config)
        else:
            # Default to mock
            self._stt_backend = MockSTTBackend()
            await self._stt_backend.initialize(stt_config)

        # Initialize TTS backend
        tts_backend = tts_config.get("backend", "mock")
        if tts_backend == "mock":
            self._tts_backend = MockTTSBackend()
        else:
            self._tts_backend = MockTTSBackend()
        await self._tts_backend.initialize(tts_config)

        # Initialize VAD backend
        vad_backend = vad_config.get("backend", "silero")
        if vad_backend == "silero":
            self._vad_backend = SileroVADBackend()
            await self._vad_backend.initialize(vad_config)
        else:
            self._vad_backend = MockVADBackend()
            await self._vad_backend.initialize(vad_config)

        # Initialize Speaker backend
        speaker_backend = speaker_config.get("backend", "mock")
        if speaker_backend == "mock":
            self._speaker_backend = MockSpeakerBackend()
        else:
            self._speaker_backend = MockSpeakerBackend()
        await self._speaker_backend.initialize(speaker_config)

        # Initialize Command backend
        command_backend = command_config.get("backend", "mock")
        if command_backend == "mock":
            self._command_backend = MockVoiceCommandBackend()
        else:
            self._command_backend = MockVoiceCommandBackend()
        await self._command_backend.initialize(command_config)

        # Start audio processing loop
        self._processing_task = asyncio.create_task(self._audio_processing_loop())

        logger.info("Voice module initialized with all backends")

    async def start(self) -> None:
        """Start voice module."""
        await super().start()
        logger.info("Voice module started")

    async def stop(self) -> None:
        """Stop voice module."""
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass

        # Cleanup backends
        for backend in [self._stt_backend, self._tts_backend, self._vad_backend,
                        self._speaker_backend, self._command_backend]:
            if backend:
                await backend.cleanup()

        await super().stop()
        logger.info("Voice module stopped")

    async def cleanup(self) -> None:
        """Clean up all resources."""
        # Cleanup backends
        for backend in [self._stt_backend, self._tts_backend, self._vad_backend,
                        self._speaker_backend, self._command_backend]:
            if backend:
                await backend.cleanup()

        self._audio_queue = asyncio.Queue()
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass

        await super().cleanup()
        logger.info("Voice module cleaned up")

    async def health_check(self) -> Dict[str, Any]:
        """Check health of all backends."""
        health = await super().health_check()
        health["backends"] = {}

        for name, backend in [
            ("stt", self._stt_backend),
            ("tts", self._tts_backend),
            ("vad", self._vad_backend),
            ("speaker", self._speaker_backend),
            ("commands", self._command_backend)
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

    async def _audio_processing_loop(self) -> None:
        """Background audio processing loop."""
        while True:
            try:
                await asyncio.sleep(0.1)
                # Process any queued audio
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Audio processing error: {e}")

    # Speech-to-Text Operations
    async def transcribe(
        self,
        audio: AudioData,
        language: Optional[str] = None,
        model: Optional[VoiceModel] = None,
        **kwargs
    ) -> TranscriptionResult:
        """Transcribe audio to text."""
        if not self._stt_backend:
            raise RuntimeError("STT backend not initialized")
        return await self._stt_backend.transcribe(audio, language, model, **kwargs)

    async def transcribe_stream(
        self,
        audio_stream: AsyncIterator[AudioData],
        language: Optional[str] = None,
        model: Optional[VoiceModel] = None,
        **kwargs
    ) -> AsyncIterator[TranscriptionResult]:
        """Stream transcription of audio chunks."""
        if not self._stt_backend:
            raise RuntimeError("STT backend not initialized")
        async for result in self._stt_backend.transcribe_stream(audio_stream, language, model, **kwargs):
            yield result

    # Text-to-Speech Operations
    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        model: Optional[VoiceModel] = None,
        speed: float = 1.0,
        pitch: float = 1.0,
        **kwargs
    ) -> SpeechSynthesisResult:
        """Synthesize speech from text."""
        if not self._tts_backend:
            raise RuntimeError("TTS backend not initialized")
        return await self._tts_backend.synthesize(text, voice, model, speed, pitch, **kwargs)

    async def synthesize_stream(
        self,
        text_stream: AsyncIterator[str],
        voice: Optional[str] = None,
        model: Optional[VoiceModel] = None,
        **kwargs
    ) -> AsyncIterator[SpeechSynthesisResult]:
        """Stream synthesis of text chunks."""
        if not self._tts_backend:
            raise RuntimeError("TTS backend not initialized")
        async for result in self._tts_backend.synthesize_stream(text_stream, voice, model, **kwargs):
            yield result

    async def list_voices(self) -> List[Dict[str, Any]]:
        """List available TTS voices."""
        if not self._tts_backend:
            raise RuntimeError("TTS backend not initialized")
        return await self._tts_backend.list_voices()

    # Voice Activity Detection
    async def detect_voice_activity(
        self,
        audio: AudioData,
        **kwargs
    ) -> VoiceActivityResult:
        """Detect voice activity in audio."""
        if not self._vad_backend:
            raise RuntimeError("VAD backend not initialized")
        return await self._vad_backend.detect(audio, **kwargs)

    async def detect_voice_activity_stream(
        self,
        audio_stream: AsyncIterator[AudioData],
        **kwargs
    ) -> AsyncIterator[VoiceActivityResult]:
        """Stream voice activity detection."""
        if not self._vad_backend:
            raise RuntimeError("VAD backend not initialized")
        async for result in self._vad_backend.detect_stream(audio_stream, **kwargs):
            yield result

    # Speaker Identification
    async def enroll_speaker(
        self,
        audio: AudioData,
        speaker_id: Optional[str] = None,
        name: Optional[str] = None,
        **kwargs
    ) -> SpeakerProfile:
        """Enroll a speaker from audio."""
        if not self._speaker_backend:
            raise RuntimeError("Speaker backend not initialized")
        return await self._speaker_backend.enroll(audio, speaker_id, name, **kwargs)

    async def identify_speaker(
        self,
        audio: AudioData,
        **kwargs
    ) -> SpeakerIdentificationResult:
        """Identify speaker from audio."""
        if not self._speaker_backend:
            raise RuntimeError("Speaker backend not initialized")
        return await self._speaker_backend.identify(audio, **kwargs)

    async def verify_speaker(
        self,
        audio: AudioData,
        speaker_id: str,
        **kwargs
    ) -> SpeakerIdentificationResult:
        """Verify if audio matches enrolled speaker."""
        if not self._speaker_backend:
            raise RuntimeError("Speaker backend not initialized")
        return await self._speaker_backend.verify(audio, speaker_id, **kwargs)

    async def delete_speaker(self, speaker_id: str) -> bool:
        """Delete enrolled speaker."""
        if not self._speaker_backend:
            raise RuntimeError("Speaker backend not initialized")
        return await self._speaker_backend.delete_speaker(speaker_id)

    async def list_speakers(self) -> List[SpeakerProfile]:
        """List enrolled speakers."""
        if not self._speaker_backend:
            raise RuntimeError("Speaker backend not initialized")
        return await self._speaker_backend.list_speakers()

    # Voice Commands
    async def parse_voice_command(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> VoiceCommand:
        """Parse voice command from transcribed text."""
        if not self._command_backend:
            raise RuntimeError("Command backend not initialized")
        return await self._command_backend.parse_command(text, context, **kwargs)

    async def add_voice_intent(
        self,
        intent: str,
        patterns: List[str],
        action: str,
        entities: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> None:
        """Add custom voice intent."""
        if not self._command_backend:
            raise RuntimeError("Command backend not initialized")
        await self._command_backend.add_intent(intent, patterns, action, entities, **kwargs)

    # Convenience methods
    async def transcribe_audio_file(
        self,
        file_path: str,
        language: Optional[str] = None,
        **kwargs
    ) -> TranscriptionResult:
        """Transcribe audio from file."""
        import aiofiles
        async with aiofiles.open(file_path, 'rb') as f:
            data = await f.read()
        audio = AudioData.from_bytes(data, format=AudioFormat.WAV)
        return await self.transcribe(audio, language, **kwargs)

    async def synthesize_to_file(
        self,
        text: str,
        file_path: str,
        voice: Optional[str] = None,
        **kwargs
    ) -> SpeechSynthesisResult:
        """Synthesize speech and save to file."""
        import aiofiles
        result = await self.synthesize(text, voice, **kwargs)
        if result.audio:
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(result.audio.to_bytes())
        return result

    async def process_voice_command_from_audio(
        self,
        audio: AudioData,
        language: Optional[str] = None,
        **kwargs
    ) -> VoiceCommand:
        """Full pipeline: transcribe audio then parse command."""
        transcription = await self.transcribe(audio, language=language)
        if transcription.text:
            return await self.parse_voice_command(transcription.text, **kwargs)
        return VoiceCommand(intent="unknown", raw_text="", confidence=0.0)

    # Module operations interface
    async def execute(self, operation: str, **kwargs) -> Any:
        """Execute voice module operation."""
        operations = {
            # STT
            "transcribe": self.transcribe,
            "transcribe_stream": self.transcribe_stream,
            "transcribe_audio_file": self.transcribe_audio_file,
            # TTS
            "synthesize": self.synthesize,
            "synthesize_stream": self.synthesize_stream,
            "synthesize_to_file": self.synthesize_to_file,
            "list_voices": self.list_voices,
            # VAD
            "detect_voice_activity": self.detect_voice_activity,
            "detect_voice_activity_stream": self.detect_voice_activity_stream,
            # Speaker
            "enroll_speaker": self.enroll_speaker,
            "identify_speaker": self.identify_speaker,
            "verify_speaker": self.verify_speaker,
            "delete_speaker": self.delete_speaker,
            "list_speakers": self.list_speakers,
            # Commands
            "parse_voice_command": self.parse_voice_command,
            "add_voice_intent": self.add_voice_intent,
            "process_voice_command_from_audio": self.process_voice_command_from_audio,
        }
        if operation in operations:
            return await operations[operation](**kwargs)
        raise NotImplementedError(f"Operation '{operation}' not supported")


__all__ = [
    "VoiceModule",
    "AudioData",
    "AudioFormat",
    "VoiceModel",
    "VoiceActivityStatus",
    "SpeakerGender",
    "SpeakerAgeGroup",
    "TranscriptionResult",
    "SpeechSynthesisResult",
    "VoiceActivityResult",
    "SpeakerProfile",
    "SpeakerIdentificationResult",
    "VoiceCommand",
    "VoiceBackend",
    "STTBackend",
    "TTSBackend",
    "VADBackend",
    "SpeakerBackend",
    "VoiceCommandBackend",
    "WhisperSTTBackend",
    "MockTTSBackend",
    "SileroVADBackend",
    "MockSpeakerBackend",
    "MockVoiceCommandBackend",
]