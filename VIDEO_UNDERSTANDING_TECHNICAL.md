# Video Understanding — Technical Implementation Plan

## Overview

This document provides the complete technical blueprint for adding video understanding to PRISM. It covers model selection, architecture decisions, code-level integration points, VRAM budgeting, latency analysis, and a phased implementation roadmap with specific file changes.

### Constraints

| Constraint | Value |
|-----------|-------|
| GPU | NVIDIA A6000, 48GB VRAM |
| LLM Access | Local only — no external API calls |
| Latency Budget | ≤10% increase on current retrieval + inference |

---

## 1. Architecture Decision: Video-to-Text-First

### 1.1 Chosen Approach

**Convert video content to text at ingestion time, then use the existing text RAG pipeline unchanged.**

```
Video → [Scene Detection + Audio Extraction]
            │                    │
            ▼                    ▼
      [Keyframe VLM]     [Whisper Transcription]
            │                    │
            ▼                    ▼
      Visual Descriptions    Speech Transcript
            │                    │
            └────────┬───────────┘
                     ▼
              Merged Text Segments
                     │
                     ▼
         Document(type="video", content=[Page, ...])
                     │
                     ▼
          Existing Pipeline: Chunk → Embed → ChromaDB → BM25
```

### 1.2 Why This Approach

| Alternative | Pros | Cons | Decision |
|------------|------|------|----------|
| **Video-to-Text-First** (chosen) | Zero changes to retrieval/ranking pipeline; proven pattern; no extra VRAM at query time | VLM processing adds ingestion time | **Selected** — simplest, most proven, meets all constraints |
| Multimodal Embeddings | Native visual similarity search | Requires separate ChromaDB collection (different dimensions), dual embedding at query time, immature tooling | Rejected — too complex, ChromaDB doesn't support mixed dimensions per collection |
| Frame-level Video LLM at Query Time | Most flexible visual QA | Requires VLM loaded during queries (15GB VRAM), violates ≤10% latency constraint | Rejected — unacceptable latency and VRAM impact at query time |

### 1.3 Key Insight: Temporal Separation of Models

Video processing (VLM + Whisper) happens at **upload time**. Query answering (main text LLM) happens at **query time**. These are temporally separated — the models don't need to coexist in VRAM simultaneously. Ollama's automatic model unloading (controlled by `OLLAMA_KEEP_ALIVE`) ensures the VLM is evicted when not in use.

---

## 2. Model Selection

### 2.1 Video Language Model — Qwen2.5-VL-7B-Instruct

| Property | Value |
|----------|-------|
| **Model** | `Qwen/Qwen2.5-VL-7B-Instruct` |
| **Parameters** | 7B |
| **VRAM (FP16)** | ~16-18GB |
| **VRAM (INT4 AWQ)** | ~6-8GB |
| **Ollama Availability** | Yes (`qwen2.5-vl:7b`) |
| **License** | Apache 2.0 |
| **Video Support** | Native — dynamic FPS, temporal position encoding (mRoPE), >1 hour videos |
| **OCR** | Built-in, strong on slides/whiteboards/screenshots |
| **Context Window** | 32,768 tokens (extendable to 64k via YaRN) |

**Benchmarks** (7B class, best-in-class):

| Benchmark | Qwen2.5-VL-7B | Next Best (7-8B) |
|-----------|--------------|------------------|
| MVBench | **69.6** | InternVL2.5-8B: ~67 |
| PerceptionTest | **70.5** | LLaVA-OneVision: 57.1 |
| Video-MME (w/ subs) | **71.6** | MiniCPM-V 2.6: 63.6 |

**Why over alternatives**:
- Already in the Qwen family (PRISM uses `qwen3:14b` as main model and `qwen3-vl:8b` for PDF VLM)
- Available via Ollama — no new serving infrastructure needed
- Best video understanding benchmarks at the 7-8B scale
- Native video input (not just frame-by-frame image processing)
- Strong OCR built in (critical for slides/screen recordings)

**Fallback option**: `InternVL2.5-8B` (AWQ quantized, ~6-8GB) — slightly lower benchmarks but competitive. Available via HuggingFace transformers.

### 2.2 Speech-to-Text — faster-whisper large-v3

| Property | Value |
|----------|-------|
| **Library** | `faster-whisper` (CTranslate2 backend) |
| **Model** | `large-v3` |
| **VRAM** | ~3GB (FP16), ~1.5GB (INT8) |
| **Speed** | 4-8x realtime (i.e., 1 hour audio in 7-15 minutes) |
| **WER** | ~5% (English), comparable across 99 languages |
| **Features** | Word-level timestamps, VAD filtering, language detection, batched inference |
| **License** | MIT |

**Why over alternatives**:

| Model | Speed | VRAM | Accuracy | Python | Decision |
|-------|-------|------|----------|--------|----------|
| **faster-whisper large-v3** | 4-8x RT | 3GB | Best | Native | **Selected** |
| whisper.cpp large-v3 | 3-5x RT (CPU) | CPU only | Same | Bindings | CPU fallback option |
| distil-whisper large-v3 | 6x RT | 2GB | -1% WER | Native | Viable alternative if VRAM tight |
| Original Whisper large-v3 | 1x RT | 5GB | Same | Native | Too slow and heavy |

### 2.3 Speaker Diarization — pyannote.audio 3.1

| Property | Value |
|----------|-------|
| **Library** | `pyannote.audio` |
| **Version** | 3.1.x |
| **VRAM** | ~1-2GB |
| **DER** | ~10-15% on standard benchmarks |
| **Features** | Overlapped speech detection, voice activity detection, speaker embedding clustering |
| **License** | MIT (requires HuggingFace token for gated model download) |

### 2.4 Scene Detection — PySceneDetect

| Property | Value |
|----------|-------|
| **Library** | `scenedetect` |
| **Algorithm** | ContentDetector (HSV histogram delta) |
| **Compute** | CPU only (no GPU needed) |
| **Speed** | Real-time or faster |
| **License** | BSD-3-Clause |

### 2.5 Video Frame Extraction — decord

| Property | Value |
|----------|-------|
| **Library** | `decord` |
| **Hardware Accel** | NVIDIA NVDEC (H.264, H.265, VP9, AV1) |
| **Features** | Efficient random access, batch frame extraction, numpy output |
| **License** | Apache 2.0 |

---

## 3. VRAM Budget

### 3.1 Current VRAM Usage

| Component | VRAM | Loaded |
|-----------|------|--------|
| Main LLM (qwen3:14b, quantized via Ollama) | ~28GB | Always (query time) |
| nomic-embed-text-v1.5 | ~0.5GB | Always |
| cross-encoder/ms-marco-MiniLM-L-6-v2 | ~0.1GB | Query time (lazy) |
| EasyOCR | ~0.2GB | Upload time (lazy) |
| **Current Total** | **~29GB** | |

### 3.2 Video Processing VRAM (Upload Time Only)

| Component | VRAM | Loaded |
|-----------|------|--------|
| faster-whisper large-v3 (FP16) | ~3GB | Upload time only |
| Qwen2.5-VL-7B (FP16, via Ollama) | ~16GB | Upload time only |
| pyannote.audio 3.1 (Phase 3) | ~1.5GB | Upload time only |
| **Video Processing Total** | **~20.5GB** | |

### 3.3 Time-Multiplexed Loading Strategy

The main text LLM and video models do **not** need to be loaded simultaneously:

```
UPLOAD MODE (video ingestion):
┌─────────────────────────────────────────────────┐
│ faster-whisper (3GB) │ Qwen2.5-VL (16GB) │ nomic-embed (0.5GB) │ = ~19.5GB
│                      │                    │                      │
│ Main text LLM: UNLOADED (Ollama auto-evicts after KEEP_ALIVE)   │
└─────────────────────────────────────────────────┘

QUERY MODE (normal operation):
┌─────────────────────────────────────────────────┐
│ Main text LLM (28GB) │ nomic-embed (0.5GB) │ cross-encoder (0.1GB) │ = ~29GB
│                       │                      │                        │
│ Video models: UNLOADED                                                │
└─────────────────────────────────────────────────┘
```

**Worst case** (video upload starts while a query is in-flight):
- Main text LLM: 28GB + faster-whisper: 3GB + nomic-embed: 0.5GB = ~31.5GB
- Whisper can start immediately; VLM waits for query to finish and main LLM to unload
- Within 48GB budget at all times

### 3.4 Ollama Model Management

```bash
# Force unload a model (0 second keep-alive)
curl -X POST http://localhost:11434/api/generate \
  -d '{"model": "qwen3:14b", "keep_alive": 0}'

# Load the video VLM
curl -X POST http://localhost:11434/api/generate \
  -d '{"model": "qwen2.5-vl:7b", "keep_alive": "10m"}'
```

In code, implement a model manager:
```python
async def ensure_video_models_loaded():
    """Unload text LLM, load video VLM for processing."""
    # Signal Ollama to evict the main text LLM
    async with httpx.AsyncClient() as client:
        await client.post(f"{OLLAMA_BASE_URL}/api/generate",
            json={"model": MAIN_MODEL, "keep_alive": 0})
        # Small delay for GPU memory release
        await asyncio.sleep(2)

async def ensure_query_models_loaded():
    """Unload video VLM, load text LLM for querying."""
    async with httpx.AsyncClient() as client:
        await client.post(f"{OLLAMA_BASE_URL}/api/generate",
            json={"model": "qwen2.5-vl:7b", "keep_alive": 0})
```

---

## 4. Latency Analysis

### 4.1 Ingestion Latency (Acceptable — Background Task)

Video processing is a background task (like current summarization/mind map generation). Users don't wait for it.

| Stage | Time (per minute of video) | Parallelizable |
|-------|--------------------------|----------------|
| Audio extraction (ffmpeg) | ~2 seconds | Yes (with scene detection) |
| Scene detection (PySceneDetect) | ~3 seconds | Yes (with audio extraction) |
| Keyframe extraction (decord) | ~1 second | After scene detection |
| Transcription (faster-whisper) | ~8-15 seconds | After audio extraction |
| VLM description (Qwen2.5-VL) | ~20-40 seconds | After keyframe extraction |
| Embedding + indexing | ~2 seconds | After text assembly |
| **Total per minute** | **~35-60 seconds** | |

**Pipeline parallelism**:
```
Time  ──────────────────────────────────────────────────────▶

      [Audio Extraction]──▶[Transcription]──────────────────▶
      [Scene Detection]──▶[Keyframe Extract]──▶[VLM Batch]──▶[Embed+Index]
                                                              ▲
                                              Merge transcript + VLM
```

### 4.2 Query Latency (Critical — Must Stay Within 10%)

| Component | Impact | Reason |
|-----------|--------|--------|
| ChromaDB retrieval | **0%** | Same embedding model, same collection, same query |
| BM25 retrieval | **0%** | Same index format, same tokenizer |
| RRF fusion | **~0%** | Slightly more chunks to fuse (negligible) |
| Cross-encoder re-ranking | **0-2%** | May rank a few more chunks if video segments are retrieved |
| LLM generation | **0%** | Same model, same prompt format, same context window |
| **Total query impact** | **<3%** | **Well within 10% budget** |

**Why zero query-time impact**: At query time, video content is already text in ChromaDB. The retrieval pipeline doesn't know the text came from a video. No additional models are loaded. No additional processing steps.

---

## 5. Code-Level Integration Plan

### 5.1 New Files to Create

```
core/parsers/video.py              # Video document parser (main orchestrator)
core/parsers/audio.py              # Audio extraction + transcription
core/parsers/scene_detect.py       # Scene detection + keyframe extraction
core/parsers/video_vlm.py          # VLM description of keyframes
core/services/model_manager.py     # GPU model loading/unloading (optional)
```

### 5.2 Existing Files to Modify

| File | Change |
|------|--------|
| `core/parsers/extensions.py` | Add `VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}` |
| `core/parsers/main.py` | Add video handler in `extract_document()` |
| `core/constants.py` | Add `VIDEO_*` constants, VLM config, feature switch |
| `core/config.py` | Add `WHISPER_MODEL`, `VIDEO_VLM_MODEL` settings |
| `agent/state.py` | Add `has_video_content: bool = False` field |
| `app/routes/upload.py` | Add video file type validation + progress events |
| `requirements.txt` | Add new dependencies |

### 5.3 Files That Do NOT Change

These are the key files that remain completely unchanged — this is the strength of the video-to-text-first approach:

| File | Why Unchanged |
|------|--------------|
| `core/embeddings/vectorstore.py` | Video text chunks use same embedding + ChromaDB |
| `core/embeddings/retriever.py` | Same hybrid retrieval, RRF, re-ranking |
| `core/embeddings/embedding_function.py` | Same nomic-embed-text-v1.5 |
| `core/embeddings/context_enrichment.py` | Same NER + triple extraction |
| `core/llm/client.py` | Same invoke_llm() for all LLM calls |
| `agent/builder.py` | Same graph topology |
| `agent/graph_nodes.py` | Same node implementations |
| `core/llm/prompts/main_prompt.py` | Same prompt (video text looks like any other text) |

---

## 6. Detailed Implementation

### 6.1 File Extension Registry

**File**: `core/parsers/extensions.py`

```python
# Add to existing extensions
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
```

### 6.2 Constants & Configuration

**File**: `core/constants.py` — Add:

```python
# Video processing constants
VIDEO_SCENE_THRESHOLD = 27.0          # PySceneDetect ContentDetector threshold
VIDEO_UNIFORM_SAMPLE_INTERVAL = 10    # Seconds between uniform keyframe samples
VIDEO_MAX_SCENE_LENGTH = 90           # Seconds — scenes longer than this get sub-sampled
VIDEO_KEYFRAME_QUALITY = 85           # JPEG quality for saved keyframes
VIDEO_CHUNK_DURATION = 60             # Seconds per temporal chunk
VIDEO_CHUNK_OVERLAP = 15              # Seconds overlap between temporal chunks
VIDEO_MAX_CONCURRENT_VLM = 3          # Max parallel VLM calls for keyframes
VIDEO_MAX_DURATION_SECONDS = 14400    # 4 hours max
VIDEO_MAX_FILE_SIZE_MB = 2048         # 2GB max

# VLM configuration for video
GPU_VIDEO_VLM = GPULLMConfig(model="qwen2.5-vl:7b", port=PORT1)

# Feature switch
SWITCHES["VIDEO_UNDERSTANDING"] = True
```

**File**: `core/config.py` — Add:

```python
WHISPER_MODEL: str = "large-v3"
WHISPER_COMPUTE_TYPE: str = "float16"
WHISPER_DEVICE: str = "cuda"
VIDEO_VLM_MODEL: str = "qwen2.5-vl:7b"
```

### 6.3 Audio Processing Module

**File**: `core/parsers/audio.py`

```python
"""Audio extraction and transcription for video files."""

import subprocess
import tempfile
import os
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class TranscriptSegment:
    """A segment of transcribed speech."""
    start: float        # Start time in seconds
    end: float          # End time in seconds
    text: str           # Transcribed text
    speaker: Optional[str] = None  # Speaker label (Phase 3)
    words: Optional[List[dict]] = None  # Word-level timestamps


@dataclass
class Transcript:
    """Complete transcript of an audio track."""
    segments: List[TranscriptSegment]
    language: str
    duration: float

    @property
    def full_text(self) -> str:
        return " ".join(seg.text for seg in self.segments)

    def get_text_for_timerange(self, start: float, end: float) -> str:
        """Get transcript text within a time range."""
        relevant = [
            seg for seg in self.segments
            if seg.start < end and seg.end > start
        ]
        return " ".join(seg.text for seg in relevant)


def extract_audio(video_path: str, output_dir: str) -> str:
    """Extract audio from video as 16kHz mono WAV (optimal for Whisper).

    Args:
        video_path: Path to video file
        output_dir: Directory to save extracted audio

    Returns:
        Path to extracted WAV file
    """
    audio_path = os.path.join(output_dir, "audio.wav")
    subprocess.run([
        "ffmpeg", "-i", video_path,
        "-vn",                    # No video
        "-acodec", "pcm_s16le",  # 16-bit PCM
        "-ar", "16000",          # 16kHz (Whisper's native rate)
        "-ac", "1",              # Mono
        "-y",                    # Overwrite
        audio_path
    ], check=True, capture_output=True)
    return audio_path


async def transcribe_audio(audio_path: str) -> Transcript:
    """Transcribe audio using faster-whisper.

    Returns:
        Transcript object with segments, timestamps, and language info
    """
    from faster_whisper import WhisperModel
    from core.config import settings

    model = WhisperModel(
        settings.WHISPER_MODEL,
        device=settings.WHISPER_DEVICE,
        compute_type=settings.WHISPER_COMPUTE_TYPE,
    )

    segments_gen, info = model.transcribe(
        audio_path,
        beam_size=5,
        vad_filter=True,        # Filter silence (reduces hallucination)
        vad_parameters=dict(
            min_silence_duration_ms=500,
        ),
        word_timestamps=True,   # Word-level timing
    )

    segments = []
    for seg in segments_gen:
        segments.append(TranscriptSegment(
            start=seg.start,
            end=seg.end,
            text=seg.text.strip(),
            words=[
                {"word": w.word, "start": w.start, "end": w.end, "probability": w.probability}
                for w in (seg.words or [])
            ],
        ))

    return Transcript(
        segments=segments,
        language=info.language,
        duration=info.duration,
    )


def unload_whisper():
    """Release Whisper model from GPU memory."""
    import torch
    import gc
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
```

### 6.4 Scene Detection Module

**File**: `core/parsers/scene_detect.py`

```python
"""Scene detection and keyframe extraction for video files."""

import os
import cv2
from typing import List
from dataclasses import dataclass
from scenedetect import detect, ContentDetector
from core.constants import (
    VIDEO_SCENE_THRESHOLD,
    VIDEO_UNIFORM_SAMPLE_INTERVAL,
    VIDEO_MAX_SCENE_LENGTH,
    VIDEO_KEYFRAME_QUALITY,
)


@dataclass
class Scene:
    """A detected scene in a video."""
    index: int
    start_time: float     # Seconds
    end_time: float       # Seconds
    duration: float       # Seconds

    @property
    def midpoint(self) -> float:
        return (self.start_time + self.end_time) / 2


@dataclass
class Keyframe:
    """An extracted keyframe from a video."""
    path: str             # Path to saved JPEG
    scene_index: int
    timestamp: float      # Seconds
    scene_start: float
    scene_end: float


def detect_scenes(video_path: str) -> List[Scene]:
    """Detect scene boundaries using content-based detection.

    Uses PySceneDetect's ContentDetector which analyzes HSV histogram
    changes between frames.

    Args:
        video_path: Path to video file

    Returns:
        List of Scene objects with timing information
    """
    scene_list = detect(video_path, ContentDetector(threshold=VIDEO_SCENE_THRESHOLD))

    scenes = []
    for i, (start, end) in enumerate(scene_list):
        scenes.append(Scene(
            index=i,
            start_time=start.get_seconds(),
            end_time=end.get_seconds(),
            duration=end.get_seconds() - start.get_seconds(),
        ))

    # If no scenes detected (e.g., static video), treat entire video as one scene
    if not scenes:
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        duration = total_frames / fps if fps > 0 else 0
        cap.release()
        scenes = [Scene(index=0, start_time=0, end_time=duration, duration=duration)]

    return scenes


def extract_keyframes(
    video_path: str,
    scenes: List[Scene],
    output_dir: str,
) -> List[Keyframe]:
    """Extract keyframes from detected scenes.

    Strategy:
    1. Extract frame at midpoint of each scene
    2. For long scenes (>VIDEO_MAX_SCENE_LENGTH), add uniform samples every
       VIDEO_UNIFORM_SAMPLE_INTERVAL seconds
    3. Deduplicate near-identical frames via structural similarity

    Args:
        video_path: Path to video file
        scenes: Detected scenes
        output_dir: Directory to save keyframe images

    Returns:
        List of Keyframe objects with paths and timing
    """
    os.makedirs(output_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)

    keyframes = []
    frame_idx = 0

    for scene in scenes:
        # Always extract scene midpoint
        timestamps = [scene.midpoint]

        # For long scenes, add uniform samples
        if scene.duration > VIDEO_MAX_SCENE_LENGTH:
            t = scene.start_time + VIDEO_UNIFORM_SAMPLE_INTERVAL
            while t < scene.end_time - 5:  # Stop 5s before end
                if abs(t - scene.midpoint) > 5:  # Don't duplicate midpoint
                    timestamps.append(t)
                t += VIDEO_UNIFORM_SAMPLE_INTERVAL

        timestamps.sort()

        for ts in timestamps:
            frame_number = int(ts * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = cap.read()
            if not ret:
                continue

            # Check frame quality (skip blurry frames)
            if is_blurry(frame):
                continue

            frame_path = os.path.join(output_dir, f"keyframe_{frame_idx:04d}.jpg")
            cv2.imwrite(
                frame_path, frame,
                [cv2.IMWRITE_JPEG_QUALITY, VIDEO_KEYFRAME_QUALITY]
            )

            keyframes.append(Keyframe(
                path=frame_path,
                scene_index=scene.index,
                timestamp=ts,
                scene_start=scene.start_time,
                scene_end=scene.end_time,
            ))
            frame_idx += 1

    cap.release()
    return keyframes


def is_blurry(frame, threshold: float = 100.0) -> bool:
    """Check if a frame is blurry using Laplacian variance."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    variance = cv2.Laplacian(gray, cv2.CV_64F).var()
    return variance < threshold


def format_timestamp(seconds: float) -> str:
    """Format seconds as HH:MM:SS or MM:SS."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
```

### 6.5 Video VLM Module

**File**: `core/parsers/video_vlm.py`

```python
"""Vision Language Model processing for video keyframes."""

import asyncio
import base64
from typing import List
from core.parsers.scene_detect import Keyframe, format_timestamp
from core.constants import GPU_VIDEO_VLM, VIDEO_MAX_CONCURRENT_VLM


VLM_FRAME_PROMPT = """Describe this video frame in detail. Include:
1. The main visual content (people, objects, text, diagrams, charts)
2. Any on-screen text (titles, labels, captions, slide content)
3. The setting or environment
4. Any actions or activities occurring

If this appears to be a presentation slide, extract all text content verbatim.
If this contains a diagram or chart, describe its structure and data.
Be factual and concise."""


async def describe_keyframe(keyframe: Keyframe) -> str:
    """Describe a single keyframe using the VLM.

    Args:
        keyframe: Keyframe object with path to image

    Returns:
        Text description of the frame content
    """
    from core.llm.client import invoke_llm
    from core.llm.output_schemas.main_outputs import LLMOutputBase
    from pydantic import BaseModel, Field

    class FrameDescription(BaseModel):
        description: str = Field(description="Detailed description of the video frame")
        on_screen_text: str = Field(default="", description="Any text visible on screen")

    # Read and encode the keyframe image
    with open(keyframe.path, "rb") as f:
        image_bytes = f.read()
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    prompt = (
        f"[Video frame at timestamp {format_timestamp(keyframe.timestamp)}]\n\n"
        f"[Image: data:image/jpeg;base64,{image_b64}]\n\n"
        f"{VLM_FRAME_PROMPT}"
    )

    result = await invoke_llm(
        gpu_model=GPU_VIDEO_VLM.model,
        response_schema=FrameDescription,
        contents=prompt,
        port=GPU_VIDEO_VLM.port,
    )

    result = FrameDescription.model_validate(result)
    desc = result.description
    if result.on_screen_text:
        desc += f"\n[On-Screen Text]: {result.on_screen_text}"
    return desc


async def batch_describe_keyframes(keyframes: List[Keyframe]) -> List[str]:
    """Describe multiple keyframes with concurrency limiting.

    Processes up to VIDEO_MAX_CONCURRENT_VLM keyframes in parallel.
    Mirrors the vlm_parse_concurrent pattern in core/parsers/vlm_parser.py.

    Args:
        keyframes: List of Keyframe objects

    Returns:
        List of descriptions (same order as input)
    """
    semaphore = asyncio.Semaphore(VIDEO_MAX_CONCURRENT_VLM)

    async def describe_with_semaphore(kf: Keyframe) -> str:
        async with semaphore:
            try:
                return await describe_keyframe(kf)
            except Exception as e:
                print(f"VLM error for keyframe at {format_timestamp(kf.timestamp)}: {e}")
                return f"[Frame at {format_timestamp(kf.timestamp)}]"

    tasks = [describe_with_semaphore(kf) for kf in keyframes]
    return await asyncio.gather(*tasks)
```

### 6.6 Main Video Parser

**File**: `core/parsers/video.py`

```python
"""Video document parser — orchestrates audio, scene, and VLM processing."""

import os
import asyncio
import traceback
from typing import Optional
from core.models.document import Document, Page
from core.parsers.audio import extract_audio, transcribe_audio, Transcript
from core.parsers.scene_detect import (
    detect_scenes, extract_keyframes, format_timestamp, Scene, Keyframe
)
from core.parsers.video_vlm import batch_describe_keyframes
from core.constants import VIDEO_MAX_DURATION_SECONDS, VIDEO_MAX_FILE_SIZE_MB
from app.socket_handler import safe_emit


async def parse_video(
    file_path: str,
    doc_id: str,
    title: str,
    file_name: str,
    user_id: str,
    thread_id: str,
    output_dir: str,
) -> Optional[Document]:
    """Parse a video file into a Document with page-per-segment structure.

    Processing pipeline:
    1. Extract audio + detect scenes (parallel)
    2. Transcribe audio + extract keyframes (parallel)
    3. VLM describe keyframes (batched)
    4. Merge transcript + visual descriptions into segments
    5. Return Document with one Page per segment

    Args:
        file_path: Path to video file
        doc_id: Document ID
        title: Document title
        file_name: Original filename
        user_id: User ID (for progress events)
        thread_id: Thread ID
        output_dir: Directory for intermediate files (keyframes, audio)

    Returns:
        Document object or None on failure
    """
    try:
        keyframe_dir = os.path.join(output_dir, "keyframes")
        os.makedirs(keyframe_dir, exist_ok=True)

        # --- Stage 1: Audio Extraction + Scene Detection (parallel) ---
        await safe_emit(f"{user_id}/progress", {
            "message": f"Extracting audio and detecting scenes in {title}..."
        })

        audio_path_future = asyncio.get_event_loop().run_in_executor(
            None, extract_audio, file_path, output_dir
        )
        scenes = detect_scenes(file_path)

        audio_path = await audio_path_future

        # --- Stage 2: Transcription + Keyframe Extraction (parallel) ---
        await safe_emit(f"{user_id}/progress", {
            "message": f"Transcribing audio from {title} ({len(scenes)} scenes detected)..."
        })

        transcript_future = transcribe_audio(audio_path)
        keyframes = extract_keyframes(file_path, scenes, keyframe_dir)

        transcript = await transcript_future

        await safe_emit(f"{user_id}/progress", {
            "message": f"Transcription complete ({transcript.language}). "
                       f"Analyzing {len(keyframes)} video frames..."
        })

        # --- Stage 3: VLM Description of Keyframes (batched) ---
        vlm_descriptions = await batch_describe_keyframes(keyframes)

        # Build keyframe description lookup: scene_index -> list of descriptions
        scene_descriptions = {}
        for kf, desc in zip(keyframes, vlm_descriptions):
            scene_descriptions.setdefault(kf.scene_index, []).append(desc)

        # --- Stage 4: Merge into Document Pages ---
        await safe_emit(f"{user_id}/progress", {
            "message": f"Assembling video content for {title}..."
        })

        pages = []
        for scene in scenes:
            # Get transcript for this scene's time range
            scene_transcript = transcript.get_text_for_timerange(
                scene.start_time, scene.end_time
            )

            # Get VLM descriptions for this scene
            descriptions = scene_descriptions.get(scene.index, [])
            visual_desc = "\n".join(descriptions) if descriptions else ""

            # Build page text
            parts = [
                f"[Video Segment {scene.index + 1}: "
                f"{format_timestamp(scene.start_time)} - "
                f"{format_timestamp(scene.end_time)}]",
            ]

            if visual_desc:
                parts.append(f"\n[Visual Content]\n{visual_desc}")

            if scene_transcript:
                parts.append(f"\n[Speech Transcript]\n{scene_transcript}")

            if not visual_desc and not scene_transcript:
                parts.append("\n[No speech or significant visual content in this segment]")

            page_text = "\n".join(parts)

            # Collect keyframe paths for this scene
            scene_keyframe_paths = [
                os.path.basename(kf.path)
                for kf in keyframes
                if kf.scene_index == scene.index
            ]

            pages.append(Page(
                number=scene.index + 1,
                text=page_text,
                images=scene_keyframe_paths,
            ))

        # Assemble full text
        full_text = "\n\n".join(p.text for p in pages)

        # Clean up audio temp file
        try:
            os.remove(audio_path)
        except OSError:
            pass

        await safe_emit(f"{user_id}/progress", {
            "message": f"Video {title} processed: {len(pages)} segments, "
                       f"{len(keyframes)} keyframes, "
                       f"{format_timestamp(transcript.duration)} duration"
        })

        return Document(
            id=doc_id,
            type="video",
            file_name=file_name,
            content=pages,
            title=title,
            full_text=full_text,
        )

    except Exception as e:
        print(f"Error processing video {file_name}: {str(e)}")
        traceback.print_exc()
        await safe_emit(f"{user_id}/progress", {
            "message": f"Error processing video {title}: {str(e)}"
        })
        return None
```

### 6.7 Integration with Main Parser

**File**: `core/parsers/main.py` — Add video handling:

```python
# Add import at top
from core.parsers.extensions import VIDEO_EXTENSIONS
from core.parsers.video import parse_video

# In extract_document() function, add handler:
if ext in VIDEO_EXTENSIONS:
    output_dir = os.path.join(
        "data", user_id, "threads", thread_id, "video_data", doc_id
    )
    os.makedirs(output_dir, exist_ok=True)

    document = await parse_video(
        file_path=file_path,
        doc_id=doc_id,
        title=title,
        file_name=safe_file_name,
        user_id=user_id,
        thread_id=thread_id,
        output_dir=output_dir,
    )
    return document
```

### 6.8 Metadata Extension

Video chunks stored in ChromaDB use the same metadata schema with additional fields:

```python
metadata = {
    # Existing fields (unchanged)
    "document_id": doc_id,
    "document_title": title,
    "page_no": segment_index,       # Scene/segment number
    "file_name": file_name,
    "user_id": user_id,
    "thread_id": thread_id,
    "chunk_index": chunk_idx,
    "entities": "Entity1,Entity2",
    "entity_types": "PERSON,ORG",

    # New video-specific fields (stored as metadata, used for display)
    "content_type": "video",        # Distinguishes from "text" documents
    "start_time": "5.23",           # Segment start (string for ChromaDB)
    "end_time": "45.67",            # Segment end
}
```

The `content_type` field enables the frontend to render video-specific source citations (with timestamps) while the retrieval pipeline treats them identically to text chunks.

---

## 7. Dependencies

### 7.1 New Python Packages

```
# Core video processing
faster-whisper>=1.0.0              # Speech-to-text (CTranslate2 backend)
scenedetect[opencv]>=0.6.0         # Scene detection
opencv-python-headless>=4.8.0      # Video frame manipulation (headless — no GUI)
decord>=0.6.0                      # GPU-accelerated video decoding (optional)

# Phase 3: Speaker diarization
pyannote.audio>=3.1.0              # Speaker diarization (optional, requires HF token)
whisperx>=3.1.0                    # Combined transcription + diarization (optional)
```

### 7.2 System Dependencies

```
# FFmpeg — required for audio extraction
# Usually already available in Docker. If not:
apt-get install ffmpeg              # Debian/Ubuntu
# or
conda install -c conda-forge ffmpeg # Conda
```

### 7.3 Ollama Models

```bash
# Pull the video VLM
ollama pull qwen2.5-vl:7b
```

---

## 8. Testing Strategy

### 8.1 Unit Tests

```python
# tests/unit/test_video_parser.py

@pytest.mark.unit
class TestAudioExtraction:
    def test_extract_audio_produces_wav(self, sample_video):
        """Audio extraction produces valid 16kHz mono WAV."""

    def test_extract_audio_handles_no_audio_track(self, silent_video):
        """Gracefully handles videos with no audio."""

@pytest.mark.unit
class TestSceneDetection:
    def test_detects_scene_boundaries(self, multi_scene_video):
        """Detects correct number of scene changes."""

    def test_single_scene_fallback(self, static_video):
        """Returns single scene for static/uniform videos."""

    def test_keyframe_extraction(self, multi_scene_video):
        """Extracts one keyframe per scene minimum."""

    def test_blurry_frame_filtering(self):
        """Skips blurry frames below quality threshold."""

@pytest.mark.unit
class TestTranscript:
    def test_time_range_extraction(self):
        """get_text_for_timerange returns correct segments."""

    def test_full_text_assembly(self):
        """full_text concatenates all segments."""

@pytest.mark.unit
class TestVideoDocument:
    def test_video_produces_document(self):
        """parse_video returns Document with correct structure."""

    def test_pages_have_timestamps(self):
        """Each page text starts with timestamp range."""

    def test_document_type_is_video(self):
        """Document.type == 'video'."""
```

### 8.2 Integration Tests

```python
# tests/integration/test_video_pipeline.py

@pytest.mark.integration
class TestVideoIngestion:
    async def test_video_indexed_in_chromadb(self, processed_video):
        """Video chunks appear in ChromaDB with correct metadata."""

    async def test_video_in_bm25_index(self, processed_video):
        """Video transcript text appears in BM25 index."""

    async def test_video_retrieval(self, processed_video):
        """Queries about video content retrieve video chunks."""

    async def test_mixed_retrieval(self, video_and_pdf_thread):
        """Cross-document queries retrieve both video and PDF chunks."""
```

### 8.3 Test Fixtures

```python
# tests/conftest.py — add video fixtures

@pytest.fixture
def sample_video(tmp_path):
    """Create a minimal test video (5 seconds, with audio)."""
    # Use ffmpeg to generate a test video
    video_path = tmp_path / "test.mp4"
    subprocess.run([
        "ffmpeg", "-f", "lavfi", "-i",
        "testsrc=duration=5:size=640x480:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=5",
        "-c:v", "libx264", "-c:a", "aac",
        "-y", str(video_path)
    ], check=True, capture_output=True)
    return video_path
```

---

## 9. Implementation Phases

### Phase 1: Audio Intelligence (Weeks 1-2)

**Goal**: Transcribe video audio, index transcripts, enable Q&A.

| Task | File(s) | Effort |
|------|---------|--------|
| Add `VIDEO_EXTENSIONS` | `core/parsers/extensions.py` | Small |
| Add video constants | `core/constants.py` | Small |
| Add Whisper config | `core/config.py` | Small |
| Implement `audio.py` | `core/parsers/audio.py` (new) | Medium |
| Implement basic `video.py` (transcript-only) | `core/parsers/video.py` (new) | Medium |
| Integrate in `main.py` parser | `core/parsers/main.py` | Small |
| Add progress events | `app/routes/upload.py` | Small |
| Install dependencies | `requirements.txt` | Small |
| Pull Whisper model | Ollama / pip | Small |
| Unit + integration tests | `tests/` | Medium |
| Frontend: video upload support | `frontend/` | Medium |

**Deliverable**: Users can upload videos, audio is transcribed and indexed, Q&A works on transcript content.

### Phase 2: Visual Understanding (Weeks 3-4)

**Goal**: Add keyframe extraction and VLM descriptions.

| Task | File(s) | Effort |
|------|---------|--------|
| Implement `scene_detect.py` | `core/parsers/scene_detect.py` (new) | Medium |
| Implement `video_vlm.py` | `core/parsers/video_vlm.py` (new) | Medium |
| Update `video.py` for full pipeline | `core/parsers/video.py` | Medium |
| Pull video VLM model | Ollama | Small |
| Add model manager (optional) | `core/services/model_manager.py` (new) | Medium |
| Update metadata for video chunks | `core/embeddings/vectorstore.py` | Small |
| Frontend: keyframe thumbnails | `frontend/` | Medium |
| Tests | `tests/` | Medium |

**Deliverable**: Full video processing with visual + audio content, scene-based segmentation.

### Phase 3: Speaker Intelligence (Weeks 5-6)

**Goal**: Add speaker diarization and speaker-aware queries.

| Task | File(s) | Effort |
|------|---------|--------|
| Add diarization to `audio.py` | `core/parsers/audio.py` | Medium |
| Speaker labels in transcript chunks | `core/parsers/video.py` | Medium |
| Speaker metadata in ChromaDB | `core/embeddings/vectorstore.py` | Small |
| Frontend: transcript panel with speakers | `frontend/` | Large |
| Frontend: speaker label assignment | `frontend/` | Medium |
| Tests | `tests/` | Medium |

**Deliverable**: Speaker-labeled transcripts, speaker-aware queries.

### Phase 4: Polish & Advanced Features (Weeks 7-8)

**Goal**: Full integration with Studio features, timeline navigation.

| Task | File(s) | Effort |
|------|---------|--------|
| Video content in mind maps | `core/studio_features/mind_map.py` | Small |
| Video content in summaries | `core/studio_features/summarizer.py` | Small |
| Video content in insights | `core/studio_features/insights.py` | Small |
| Video content in roadmaps | `core/studio_features/strategic_roadmap.py`, etc. | Small |
| Frontend: timeline navigation | `frontend/` | Large |
| Frontend: embedded video player | `frontend/` | Large |
| Performance optimization | Various | Medium |
| Documentation | `CLAUDE.md`, README | Small |

---

## 10. Monitoring & Observability

### 10.1 Metrics to Track

| Metric | How | Alert Threshold |
|--------|-----|-----------------|
| Video processing time | Log per-stage timing | >2 min/minute of video |
| Whisper model load time | Log on load | >30 seconds |
| VLM model load time | Log on load | >60 seconds |
| VRAM usage during processing | `nvidia-smi` polling | >45GB |
| Query latency (video threads) | Compare to non-video baseline | >10% increase |
| Transcription WER | Spot-check sample | >10% on clear audio |
| Failed video processing | Error logs | Any |

### 10.2 Progress Events (Socket.IO)

Extend existing progress event pattern:

```python
# Events emitted during video processing:
f"{user_id}/progress": {"message": "Extracting audio from {title}..."}
f"{user_id}/progress": {"message": "Detecting scenes in {title}..."}
f"{user_id}/progress": {"message": "Transcribing audio ({language})..."}
f"{user_id}/progress": {"message": "Analyzing {n} video frames..."}
f"{user_id}/progress": {"message": "Indexing video content..."}
f"{user_id}/progress": {"message": "Video {title} ready: {n} segments, {duration}"}
```

---

## 11. Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| **VLM + text LLM VRAM conflict** | Medium | High | Time-multiplexed loading; Ollama `keep_alive` management; explicit model unload before loading another |
| **Long processing for large videos** | High | Medium | Background processing; incremental availability (audio first); progress streaming; configurable limits |
| **Poor transcription on noisy audio** | Medium | Medium | VAD filtering; confidence reporting; allow re-processing; future: denoising pre-processor |
| **FFmpeg not available in environment** | Low | High | Add to Dockerfile; check on startup; clear error message |
| **Scene detection misses boundaries** | Low | Low | Threshold tuning; uniform sampling fallback for long scenes |
| **ChromaDB performance with more chunks** | Low | Low | Video chunks use same schema; no collection changes; existing performance optimizations apply |
| **Disk space for keyframes** | Low | Low | JPEG at 85% quality (~50-100KB each); configurable cleanup after indexing |

---

## 12. Future Enhancements (Beyond Phase 4)

| Enhancement | Description | Complexity |
|------------|-------------|------------|
| **Visual similarity search** | Add `nomic-embed-vision-v1.5` for frame embeddings, enable "find frames like this" queries | Medium |
| **Real-time video ingestion** | Process streaming video (e.g., live meeting recording) | High |
| **Multi-language transcription** | Language detection + per-segment language switching | Low (Whisper supports 99 languages natively) |
| **Video summarization cards** | Generate visual summary with key frames + text | Medium |
| **Action recognition** | Detect specific actions (e.g., "person presenting", "whiteboard writing") | High |
| **Audio event detection** | Detect non-speech audio events (applause, music, alarms) | Medium |
| **Video-to-video search** | Find similar scenes across different videos | High |
| **Subtitle/caption extraction** | Extract embedded subtitles (SRT/VTT tracks) | Low |
| **Slide change detection** | Specialized detection for presentation videos | Medium |
