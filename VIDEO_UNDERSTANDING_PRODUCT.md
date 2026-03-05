# Video Understanding — Product Plan

## Executive Summary

This document outlines the product strategy for adding video understanding capabilities to PRISM. The goal is to enable users to upload video files (lectures, meetings, presentations, training materials, interviews) and ask natural-language questions about their content — just as they do today with PDFs, spreadsheets, and presentations.

The approach follows PRISM's existing philosophy: **ingest at upload time, answer at query time**. Videos are decomposed into visual scenes and audio transcripts during upload, converting them into the same text+metadata format that the existing RAG pipeline already handles. This means every existing feature — hybrid retrieval, cross-document synthesis, mind maps, insights, roadmaps — works with video content from day one.

### Constraints

| Constraint | Detail |
|-----------|--------|
| **GPU** | 48GB VRAM (NVIDIA A6000) |
| **LLM Access** | Local only — no external API calls |
| **Latency** | ≤10% impact on current retrieval and inference performance |

---

## 1. User Value Proposition

### 1.1 What Users Can Do Today (Without Video)

- Upload PDFs, spreadsheets, presentations, images
- Ask questions and get cited, grounded answers
- Generate mind maps, summaries, insights, roadmaps
- Query spreadsheet data using natural language
- Synthesize knowledge across multiple documents

### 1.2 What Users Will Be Able to Do (With Video)

Everything above, **plus**:

| Capability | Example |
|-----------|---------|
| **Upload videos** alongside other documents | Upload a training video + its reference PDF and ask questions across both |
| **Ask about video content** | *"What was discussed about Q3 revenue in the board meeting recording?"* |
| **Search across audio transcripts** | *"Find all mentions of 'compliance deadline' across the uploaded videos"* |
| **Understand visual content** | *"What does the architecture diagram shown at 14:30 describe?"* |
| **Cross-modal synthesis** | *"Compare the strategy outlined in the presentation video with the written report"* |
| **Speaker-aware queries** | *"What did Speaker 2 say about the budget?"* |
| **Temporal navigation** | Answers include timestamps — *"At 5:23, the presenter discusses..."* |
| **Video + document synthesis** | Mind maps, summaries, and insights that incorporate video content |

### 1.3 Target Use Cases

| Use Case | Description | Priority |
|----------|------------|----------|
| **Lecture/Training Analysis** | Upload recorded lectures, ask questions, generate study materials | High |
| **Meeting Intelligence** | Upload meeting recordings, extract action items, decisions, who-said-what | High |
| **Presentation Review** | Upload recorded presentations, analyze slide content + narration | High |
| **Interview Analysis** | Upload interview recordings, extract key themes and speaker positions | Medium |
| **Video Documentation** | Upload product demos or tutorials, make them searchable | Medium |
| **Compliance Review** | Upload recorded procedures, verify against written policies | Medium |

---

## 2. User Experience Design

### 2.1 Upload Experience

The video upload experience mirrors the existing document upload:

```
┌─────────────────────────────────────────────────┐
│  Thread: Q3 Strategy Review                      │
│                                                  │
│  Documents:                                      │
│  ├── Q3_Report.pdf          ✓ Ready              │
│  ├── Financials.xlsx        ✓ Ready              │
│  ├── Board_Meeting.mp4      ⟳ Processing (67%)   │
│  │   ├── Extracting audio...     ✓               │
│  │   ├── Transcribing speech...  ✓               │
│  │   ├── Analyzing video frames... ⟳             │
│  │   └── Indexing content...     ○               │
│  └── Strategy_Deck.pptx    ✓ Ready              │
│                                                  │
│  [+ Upload Files]                                │
└─────────────────────────────────────────────────┘
```

Key UX decisions:
- **Progress transparency**: Video processing takes longer than text documents. The UI shows granular progress via Socket.IO events (audio extraction → transcription → frame analysis → indexing)
- **Incremental availability**: Audio transcript is indexed first, so users can start asking transcript-based questions while visual analysis is still processing
- **File size guidance**: UI shows estimated processing time based on video duration
- **Supported formats**: MP4, AVI, MOV, MKV, WebM (clearly listed in the upload dialog)

### 2.2 Query Experience

Once a video is processed, the query experience is identical to the current system. Users simply ask questions:

**Example interaction**:
```
User: "What were the three main priorities discussed in the board meeting?"

PRISM: Based on the board meeting recording (Board_Meeting.mp4):

The three main priorities discussed were:

1. **Revenue Growth** (discussed at 5:23-8:45): The CFO presented
   Q3 targets of 15% YoY growth, emphasizing APAC expansion...

2. **Cost Optimization** (discussed at 12:10-15:30): The COO
   outlined a plan to reduce operational costs by 8%...

3. **Product Launch** (discussed at 20:15-24:00): The VP Product
   presented the timeline for the v3.0 launch...

Sources:
├── Board_Meeting.mp4, Segment 3 (5:23-8:45)
├── Board_Meeting.mp4, Segment 6 (12:10-15:30)
└── Board_Meeting.mp4, Segment 9 (20:15-24:00)

Confidence: High
```

### 2.3 Source Attribution for Video

Video sources include temporal information that text documents don't have:

| Source Type | Attribution Format |
|------------|-------------------|
| PDF | *Report.pdf, Page 5* |
| Spreadsheet | *Data.xlsx, Sheet "Revenue"* |
| **Video** | *Meeting.mp4, Segment 3 (5:23-8:45)* |
| **Video (speaker)** | *Meeting.mp4, Speaker 2 at 12:10* |

### 2.4 Video-Specific UI Components

| Component | Description | Priority |
|-----------|------------|----------|
| **Video Segment Viewer** | When clicking a video source, show the keyframe thumbnail + transcript for that segment | Phase 2 |
| **Transcript Panel** | Full searchable transcript with speaker labels and timestamps | Phase 2 |
| **Timeline View** | Visual timeline showing which segments were referenced in the answer | Phase 3 |
| **Video Player Integration** | Embedded player that jumps to cited timestamps | Phase 3 |

---

## 3. Feature Scope — Phased Rollout

### Phase 1: Audio Intelligence (MVP)

**Goal**: Make video speech searchable and queryable.

| Feature | Detail |
|---------|--------|
| Video upload (MP4, AVI, MOV, MKV, WebM) | Upload alongside existing document types |
| Audio extraction | Extract audio track from video |
| Speech-to-text transcription | High-accuracy, word-level timestamps |
| Transcript chunking & indexing | Temporal chunks indexed in ChromaDB + BM25 |
| Q&A over transcripts | Full RAG pipeline works with transcript content |
| Progress streaming | Real-time status via Socket.IO |
| Source citations with timestamps | "Meeting.mp4, 5:23-8:45" |

**User value**: Users can upload meeting recordings, lectures, interviews and ask questions about what was said. This alone covers the majority of video Q&A use cases.

**GPU budget**: ~3GB additional (faster-whisper).

### Phase 2: Visual Understanding

**Goal**: Understand what's shown in the video, not just what's said.

| Feature | Detail |
|---------|--------|
| Scene detection & keyframe extraction | Automatic detection of scene changes |
| Visual content description | VLM describes each keyframe (diagrams, slides, whiteboards) |
| OCR from video frames | Extract text from slides, screen recordings, whiteboard content |
| Merged visual + audio context | Each segment combines transcript + visual description + OCR |
| Cross-modal Q&A | "What does the diagram at 14:30 show?" |
| Keyframe thumbnails in sources | Visual preview when clicking video sources |

**User value**: Users can ask about visual content — diagrams, slides, demonstrations — not just speech.

**GPU budget**: ~15GB additional during ingestion (VLM). Zero additional at query time.

### Phase 3: Speaker Intelligence

**Goal**: Know who said what.

| Feature | Detail |
|---------|--------|
| Speaker diarization | Identify distinct speakers in recordings |
| Speaker-attributed transcript | "Speaker 1: ... Speaker 2: ..." |
| Speaker-aware queries | "What did Speaker 2 say about the budget?" |
| Speaker labels (manual) | Users can assign names to detected speakers |
| Transcript panel with speakers | Searchable, speaker-labeled transcript view |

**User value**: Critical for meeting recordings, interviews, panel discussions, debates.

**GPU budget**: ~1-2GB additional (pyannote.audio).

### Phase 4: Advanced Video Features

**Goal**: Full integration with Studio features and advanced capabilities.

| Feature | Detail |
|---------|--------|
| Video mind maps | Mind maps generated from video content |
| Video summarization | Per-video and global summaries including video content |
| Video insights | Insights extraction from video content |
| Cross-video synthesis | Find patterns across multiple video recordings |
| Timeline navigation | Click timestamps in answers to jump to video position |
| Embedded video player | Play referenced segments directly in the UI |

---

## 4. How Video Fits Into Existing Features

### 4.1 Existing RAG Pipeline

Video content flows through the **same RAG pipeline** as all other documents:

```
                    ┌─── PDF ────┐
                    ├─── Excel ──┤
 Current:           ├─── PPTX ──┼──→ Document Model ──→ Chunk ──→ Embed ──→ ChromaDB
                    ├─── Image ──┤                                            ↓
                    └─── MD ─────┘                                      Retrieve → LLM
                                                                              ↑
 New:               └─── Video ──┘──→ Document Model ──→ Chunk ──→ Embed ──→ ChromaDB
                         (scenes     (same format as     (same     (same
                          become      PDF pages)         chunker)  embedder)
                          "pages")
```

No changes to the retrieval, re-ranking, CRAG, or generation pipeline.

### 4.2 Cross-Document Synthesis

Because video segments are stored as regular document chunks in ChromaDB, cross-document synthesis works automatically:

- *"Compare the strategy in the video presentation with the written report"*
- *"Do the financial figures in the spreadsheet match what was discussed in the meeting?"*
- *"Create a mind map combining insights from the whitepaper, the training video, and the Q3 deck"*

### 4.3 Query Decomposition

The existing decomposition engine naturally handles video-related complex queries:

- *"What were the key takeaways from the three training videos?"* → decomposes into per-video sub-queries → combines answers
- *"Compare what Speaker 1 and Speaker 2 said about the product roadmap"* → decomposes into per-speaker sub-queries

### 4.4 Studio Features Integration

| Feature | Video Integration |
|---------|------------------|
| **Mind Maps** | Video content included in node generation |
| **Summarization** | Per-video and global summaries |
| **Word Clouds** | Video transcript text included in TF-IDF |
| **Insights** | Video content analyzed for strengths, improvements, etc. |
| **Roadmaps** | Video content can inform strategic/technical roadmaps |

### 4.5 Spreadsheet + Video Queries

Combined queries work naturally:

- *"The training video mentioned a target of 15% growth. What does the Q3 spreadsheet show for actual growth?"*
- The agent decomposes this: video retrieval for the target + SQL query for actual data

---

## 5. Agentic Architecture — Video Extension

### 5.1 Current Agent Flow

```
Retriever → Evaluator → Generate → Router → Action
```

### 5.2 How Video Changes the Agent

**No changes to the core agent graph are needed for Phases 1-2.**

Video content is already text (transcripts + visual descriptions) by the time the agent processes it. The agent sees video content as regular document chunks with video-specific metadata (timestamps, segment numbers).

The only agent-level change is in Phase 3+ where the router may optionally select a **video-specific analysis** action for queries that explicitly request temporal or speaker-level analysis.

### 5.3 Video-Aware Routing (Phase 3+)

```
Router decisions (extended):
├─→ answer                   # Standard: answer from retrieved chunks
├─→ web_search               # External: search the web
├─→ sql_query                # Spreadsheet: execute SQL
├─→ document_summarizer      # Summary: load per-doc summary
├─→ global_summarizer        # Summary: load global summary
├─→ video_temporal_analysis  # NEW: timestamp-specific video Q&A
└─→ failure → self_knowledge # Fallback
```

---

## 6. Performance Expectations

### 6.1 Ingestion Performance

| Video Duration | Phase 1 (Audio Only) | Phase 2 (Audio + Visual) |
|---------------|---------------------|-------------------------|
| 5 minutes | ~30 seconds | ~2 minutes |
| 30 minutes | ~2 minutes | ~8 minutes |
| 1 hour | ~4 minutes | ~15 minutes |
| 2 hours | ~8 minutes | ~30 minutes |

Notes:
- These are estimates based on faster-whisper (4-8x realtime) + VLM processing
- Processing happens in the background; users can continue other work
- Audio transcript is indexed first, enabling early querying while visual analysis completes

### 6.2 Query Performance

| Metric | Without Video | With Video | Impact |
|--------|-------------|------------|--------|
| Retrieval latency | Baseline | Baseline | **0% impact** — same ChromaDB + BM25 |
| Re-ranking latency | Baseline | +0-2% | Marginal — slightly more chunks from video |
| LLM inference | Baseline | +0% | Same model, same prompts |
| Total query time | Baseline | **<5% total** | Well within the 10% constraint |

The key insight: video processing happens entirely at **upload time**. At query time, video content is already text in ChromaDB — the retrieval pipeline doesn't know or care that the text came from a video.

---

## 7. Supported Video Formats

| Format | Extension | Container | Notes |
|--------|-----------|-----------|-------|
| MP4 | `.mp4` | MPEG-4 Part 14 | Most common, widely supported |
| AVI | `.avi` | Audio Video Interleave | Legacy format, full support |
| MOV | `.mov` | QuickTime | Apple ecosystem |
| MKV | `.mkv` | Matroska | Open format, supports all codecs |
| WebM | `.webm` | WebM | Web-optimized (VP8/VP9/AV1) |

### Video Codec Support

All codecs supported by FFmpeg + NVIDIA NVDEC hardware decoding:
- H.264 (AVC) — most common
- H.265 (HEVC) — modern, efficient
- VP9 — YouTube/WebM standard
- AV1 — newest, most efficient

### Practical Limits

| Parameter | Recommended Limit | Reason |
|-----------|-------------------|--------|
| Max file size | 2GB | Disk and processing time |
| Max duration | 4 hours | Processing time and chunk volume |
| Min resolution | 360p | OCR/VLM quality below this is poor |
| Max resolution | 4K | Downsampled to 1080p for processing |
| Audio requirement | Optional | Silent videos processed as visual-only |

---

## 8. Privacy & Security Considerations

| Concern | Mitigation |
|---------|-----------|
| Video files contain sensitive meetings | All processing is local (GPU). No cloud APIs used. Videos stored on-premises only |
| Speaker identification is PII | Speaker labels are numerical by default ("Speaker 1"). Named labels are user-assigned and stored locally |
| Video files are large | Original files can be deleted after processing (configurable retention policy) |
| Transcripts may contain confidential speech | Same isolation as document text — per-user, per-thread, JWT-protected |

---

## 9. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Transcript accuracy** | ≥95% WER on clear English audio | Sample verification against manual transcripts |
| **Visual description quality** | Correctly describes key visual elements in ≥80% of keyframes | Manual evaluation on test set |
| **Query relevance** | Same confidence scores as text-document queries | A/B comparison of confidence distributions |
| **Processing throughput** | 1 minute of video processed in ≤30 seconds (Phase 1) | Automated benchmarking |
| **Query latency impact** | ≤5% increase in p95 query latency | Load testing before/after |
| **User adoption** | ≥30% of threads include at least one video within 3 months | Usage analytics |

---

## 10. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Long video processing frustrates users | High | Medium | Granular progress UI, incremental availability (audio first), estimated time display |
| Poor audio quality → bad transcripts | Medium | High | Show confidence indicators, allow transcript editing in Phase 3+, offer re-processing with different settings |
| Users upload very long videos (4+ hours) | Medium | Low | Set configurable limits, show estimated time before upload |
| VLM struggles with complex diagrams | Medium | Medium | Fall back to OCR text + transcript context; iterative VLM prompt improvement |
| GPU contention during video processing | Low | Medium | Time-multiplexed model loading; video processing queued as background task |
| Users expect real-time video playback in UI | Low | Low | Phase 3+ feature; clearly communicated as future capability |
