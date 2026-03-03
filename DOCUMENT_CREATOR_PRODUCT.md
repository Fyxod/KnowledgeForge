# PRISM Document Creator — Product Specification

## Executive Summary

The **Interactive Document Creator** extends PRISM from a knowledge analysis platform into a knowledge **synthesis and delivery** platform. Users will be able to transform their uploaded documents and AI-generated insights into polished, export-ready documents — presentations (PPTX), reports (DOCX), and formatted PDFs — through an interactive, iterative workflow powered by local LLMs.

This feature bridges the gap between PRISM's existing analytical capabilities (insights, roadmaps, analyses, mind maps) and the final deliverable that enterprise users need: a shareable, professionally formatted document grounded in their source materials.

---

## 1. Problem Statement

### Current Gap

PRISM excels at **understanding and analyzing** documents:
- It answers questions grounded in uploaded source material
- It generates insights, roadmaps, SWOT analyses, and mind maps
- It provides confidence scores and source attribution

However, users currently cannot transform this intelligence into **outbound deliverables**:
- A manager who uploads project reports cannot generate a summary presentation for stakeholders
- A researcher who uploads papers cannot produce a synthesis report
- An analyst who receives insights cannot export a polished brief without manual effort

### User Need

Enterprise users need a **document creation workflow** that:
1. Uses their uploaded knowledge base as source material
2. Generates structured, multi-section documents (not just Q&A answers)
3. Allows iterative refinement at the section level
4. Exports in standard business formats (PPTX, DOCX, PDF)
5. Runs entirely on local infrastructure (no cloud APIs)

---

## 2. Core Value Proposition

| Dimension | What Document Creator Delivers |
|-----------|-------------------------------|
| **Knowledge-Grounded Generation** | Documents are synthesized from uploaded source materials via RAG, not hallucinated from general knowledge |
| **Interactive Iteration** | Users refine at the outline and section level — no need to regenerate entire documents |
| **Multi-Format Export** | One workflow produces PPTX, DOCX, or PDF — choose the format at export time |
| **Enterprise Privacy** | Entire pipeline runs on local Ollama LLMs — no data leaves the organization |
| **Integrated Workflow** | Works within existing PRISM threads — same documents, same knowledge base, same workspace |

---

## 3. User Workflow

### 3.1 High-Level Flow

```
┌─────────────────────────────────────────────────────────────┐
│  1. INITIATE                                                 │
│  User opens Document Creator from thread workspace           │
│  Selects source documents (specific docs or all)             │
│  Chooses document type, audience, and tone                   │
│  Optionally provides custom instructions                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  2. OUTLINE GENERATION                                       │
│  System generates a structured outline with section titles,  │
│  descriptions, and suggested content types                   │
│  User reviews, reorders, adds, removes, or edits sections    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  3. CONTENT GENERATION                                       │
│  System generates content section-by-section                 │
│  Each section uses targeted RAG retrieval from source docs    │
│  Real-time progress shown as sections complete                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  4. REVIEW & ITERATE                                         │
│  User reviews each section in a preview pane                 │
│  Can approve, regenerate, or provide feedback per section    │
│  Can regenerate individual sections without affecting others │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  5. EXPORT                                                   │
│  User selects output format (PPTX / DOCX / PDF)             │
│  System assembles and renders the final document             │
│  File is downloaded to user's machine                        │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Detailed User Journey

#### Step 1: Initiation

The user opens the Document Creator from their thread workspace (same location as existing Insights, Roadmap, Analysis features). They are presented with:

- **Source Selection**: Choose specific documents or "All Documents" in the thread
- **Document Type**: Presentation, Report, Brief, Technical Specification, Executive Summary
- **Target Audience**: Executive, Technical, General
- **Tone**: Formal, Professional, Conversational, Academic
- **Length Guidance**: Short (5-8 sections), Medium (8-15 sections), Detailed (15-25 sections)
- **Custom Instructions** (optional): Free-text guidance (e.g., "Focus on financial metrics", "Include comparison tables")

#### Step 2: Outline Review

The system generates a structured outline showing:
- Document title and subtitle
- Ordered list of sections with:
  - Section title
  - Brief description of intended content (1-2 sentences)
  - Suggested content format (prose, bullet points, table, mixed)
  - Relevant source documents that will feed this section

**User interactions on the outline:**
| Action | Description |
|--------|-------------|
| **Reorder** | Drag sections to change sequence |
| **Add Section** | Insert a new section with title and description |
| **Remove Section** | Delete a section from the outline |
| **Edit Section** | Modify title, description, or content format |
| **Add Guidance** | Attach specific instructions to a section |
| **Approve** | Accept the outline and proceed to generation |

#### Step 3: Content Generation

Once the outline is approved, the system generates content section-by-section:
- Each section uses **per-section RAG retrieval** — the system queries the vector store with section-specific search terms
- A **document context object** maintains consistency across sections (terminology, tone, narrative flow)
- Progress is streamed in real-time via Socket.IO:
  - "Generating section 1 of 12: Executive Summary..."
  - "Generating section 2 of 12: Market Analysis..."
  - Estimated time remaining based on per-section generation speed

#### Step 4: Review & Iteration

After generation completes, the user sees a **preview pane** with the full document rendered as HTML. For each section, the user can:

| Action | Description |
|--------|-------------|
| **Approve** | Mark section as final |
| **Regenerate** | Generate a new version of this section (keeping the same outline spec) |
| **Regenerate with Feedback** | Provide text feedback and regenerate (e.g., "Make this more concise", "Add more data points") |
| **Edit Directly** | Minor text edits in the preview (for small fixes) |

**Key UX principle**: Section-level iteration means the user never waits for the entire document to regenerate. Only the targeted section is reprocessed (5-15 seconds per section on local LLM).

**Version History**: Each section maintains a generation history. Users can cycle through previous versions of a section and select the best one — inspired by the worklet-gen iteration model where each field tracks multiple versions with a selected index.

#### Step 5: Export

Once satisfied, the user exports in their chosen format:

| Format | Best For |
|--------|----------|
| **PPTX (PowerPoint)** | Presentations, stakeholder updates, visual summaries |
| **DOCX (Word)** | Reports, technical documentation, editable drafts |
| **PDF** | Final deliverables, print-ready documents, archives |

The exported document uses a **professional template** with consistent branding, typography, and layout. Users can download and further customize in their native application (PowerPoint, Word, etc.).

---

## 4. Document Types & Templates

### 4.1 Supported Document Types

| Type | Description | Typical Sections | Best Output Format |
|------|-------------|-------------------|--------------------|
| **Presentation** | Visual slide deck for stakeholders | Title, Overview, Key Findings, Analysis, Recommendations, Next Steps | PPTX |
| **Executive Summary** | Concise brief for decision-makers | Context, Key Findings, Impact, Recommendations | DOCX, PDF |
| **Technical Report** | Detailed analysis document | Abstract, Methodology, Findings, Analysis, Conclusion, Appendix | DOCX, PDF |
| **Research Brief** | Synthesis of multiple sources | Background, Literature Review, Synthesis, Gaps, Future Directions | DOCX, PDF |
| **Project Proposal** | Structured project pitch | Problem, Approach, Deliverables, Timeline, Resources, Risks | PPTX, DOCX |
| **Comparison Report** | Side-by-side analysis | Introduction, Criteria, Comparison Matrix, Analysis, Recommendation | DOCX, PDF |

### 4.2 Template System

Each document type has a **default professional template** that defines:
- Layout structure (slide layouts for PPTX, heading styles for DOCX, HTML/CSS for PDF)
- Color scheme (aligned with PRISM's existing UI palette)
- Typography (professional font selections)
- Header/footer with document metadata
- Placeholder positions for content, tables, and visuals

Templates are stored as actual document files (`.pptx`, `.docx` templates, `.html`/`.css` for PDF) — not generated code. This makes them easy to customize and brand.

---

## 5. RAG-Grounded Generation

### 5.1 How Source Documents Feed Generation

Unlike generic AI document generators, PRISM's Document Creator is **grounded in the user's uploaded knowledge base**:

```
Source Documents (uploaded to thread)
        │
        ▼
  ┌─ Per-Section Retrieval ─┐
  │  Section: "Market Analysis"        →  Retrieve chunks about markets, competition
  │  Section: "Technical Architecture"  →  Retrieve chunks about tech, systems
  │  Section: "Risk Assessment"         →  Retrieve chunks about risks, challenges
  └────────────────────────────────────┘
        │
        ▼
  LLM generates each section using retrieved context
  Sources are tracked per section for attribution
```

### 5.2 Source Attribution

Every section in the generated document includes:
- **Source indicators** showing which uploaded documents contributed
- **Page references** for traceability
- Users can verify any generated claim against original sources

### 5.3 Coverage Awareness

After outline generation, the system checks which source documents contribute to which sections. If any uploaded document is not represented in the outline, the user is alerted:

> "Note: 'Financial Report Q3.xlsx' is not referenced in any section. Would you like to add a section covering this data?"

---

## 6. Integration with Existing PRISM Features

### 6.1 Leverage Existing Outputs

The Document Creator can incorporate outputs from other PRISM Studio features:

| Existing Feature | Integration |
|-----------------|-------------|
| **Insights** | "Include extracted insights as a section" |
| **Strategic Roadmap** | "Include the generated roadmap as a section" |
| **Technical Analysis** | "Include the analysis findings" |
| **Mind Map** | "Include a summary of the mind map structure" |
| **Summaries** | "Use document summaries as section starting points" |
| **Spreadsheet Data** | "Include SQL query results as tables" |

### 6.2 Thread Context

The Document Creator lives within a thread workspace:
- Uses the same document collection as Q&A and other features
- Respects **Thread Instructions** (e.g., "Always use metric units")
- Can reference chat history for context
- Generated documents are stored in the thread's data directory

### 6.3 Future: Chat-Initiated Generation

In a later phase, users could initiate document creation from the chat interface:
> "Create a presentation summarizing the key findings from all uploaded reports"

The agent would detect the document-generation intent and route to the Document Creator pipeline.

---

## 7. Iterative Refinement Model

### 7.1 Inspiration from worklet-gen

The iteration model is inspired by the worklet-gen project's approach to iterative content refinement, adapted for document sections:

**worklet-gen Pattern** (adapted):
- Each content field maintains a **version history** (array of generated values)
- A **selected index** indicates the currently chosen version
- Users can generate new versions, compare, and select the best one
- Field-level iteration means changing one field doesn't affect others

**Document Creator Adaptation**:
- Each **section** (not field) maintains a version history
- Users can:
  - Generate alternative versions of a section
  - Compare versions side-by-side
  - Select the best version per section
  - Provide feedback to guide the next iteration
- Section-level changes don't cascade to other sections (unless explicitly requested)

### 7.2 Enhancement Mode

Beyond section-level iteration, users can trigger a **whole-document enhancement**:
- Provide an instruction (e.g., "Make the entire document more concise", "Add executive framing")
- The system regenerates all non-approved sections with the enhancement instruction applied
- Approved/locked sections remain unchanged

---

## 8. Operating Constraints & Privacy

| Constraint | How Document Creator Handles It |
|-----------|-------------------------------|
| **No external LLM APIs** | Entire pipeline runs on local Ollama (Qwen3-14B on A6000 GPU) |
| **48GB VRAM limit** | Section-by-section generation (not whole-document) keeps per-call VRAM reasonable |
| **Context window limits** | Sliding context pattern: outline + previous section summary + per-section RAG chunks |
| **Data privacy** | Generated documents stay on local storage; no cloud processing |
| **Offline capable** | No internet dependency for core generation pipeline |

---

## 9. User Interface Specification

### 9.1 Entry Point

The Document Creator is accessed from the thread workspace, alongside existing Studio Features (Insights, Roadmap, Analysis). A new "Create Document" button appears in the feature panel.

### 9.2 Views (Modal Flow)

The UI follows PRISM's existing 4-view modal pattern:

| View | Content |
|------|---------|
| **Configure** | Source document selection, document type picker, audience/tone selectors, custom instructions textarea |
| **Outline Editor** | Editable outline with drag-to-reorder, add/remove/edit sections, source coverage indicator |
| **Generation Progress** | Per-section progress bar, section-by-section status, estimated time remaining |
| **Review & Export** | HTML preview with per-section approve/regenerate/feedback controls, version history, format selector, download button |

### 9.3 Preview Rendering

The preview pane renders the generated document as styled HTML:
- **For Presentations**: Slide cards with layout previews
- **For Reports/Briefs**: Paginated document view with headings, body text, tables
- **For PDF**: Faithful representation of the final PDF layout

### 9.4 Section Interaction Controls

Each section in the preview has a floating toolbar:
```
┌─────────────────────────────────────────┐
│  Section 3: Market Analysis              │
│  ┌─────────────────────────────────────┐ │
│  │  ✓ Approve  │  ↺ Regenerate  │  ✎ Edit  │  📋 Versions (3)  │
│  └─────────────────────────────────────┘ │
│                                          │
│  [Section content rendered here...]      │
│                                          │
└─────────────────────────────────────────┘
```

---

## 10. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Generation Time** | < 2 minutes for a 10-section document | Backend performance monitoring |
| **Iteration Time** | < 15 seconds per section regeneration | Backend performance monitoring |
| **Export Quality** | Professional-grade formatting in all 3 formats | User feedback / design review |
| **Source Grounding** | > 80% of generated content traceable to source documents | Automated source coverage check |
| **User Satisfaction** | Users can produce a usable deliverable in < 10 minutes | User testing sessions |

---

## 11. Phased Rollout

### Phase 1: Core Generation (MVP)
- Document type: Report (DOCX) only
- Single-pass generation (outline → content → export)
- Basic outline editing (add/remove/reorder sections)
- DOCX export with default template

### Phase 2: Multi-Format + Iteration
- Add PPTX and PDF export formats
- Section-level iteration with feedback
- Version history per section
- Template selection

### Phase 3: Advanced Features
- Incorporate existing PRISM outputs (insights, roadmaps) as sections
- Enhancement mode (whole-document refinement)
- Chat-initiated document creation
- Direct text editing in preview
- Custom templates upload

---

## 12. Relationship to worklet-gen

The [worklet-gen](https://github.com/bugslayer01/worklet-gen) project provides validated patterns that are adapted (not copied) for Document Creator:

| worklet-gen Concept | Document Creator Adaptation |
|--------------------|----------------------------|
| **Pipeline**: Process → Extract → Search → Generate → References → Rank → Generate Files | **Pipeline**: Configure → RAG Retrieve → Outline → Section Generation → Review → Assemble → Export |
| **Field-level iteration** with version history and selected index | **Section-level iteration** with version history and selected version |
| **Worklet enhancement** (whole-object refinement with instructions) | **Document enhancement** (whole-document refinement with instructions) |
| **Keywords/domains approval** before generation | **Outline approval** before section generation |
| **WebSocket status updates** during pipeline execution | **Socket.IO progress streaming** during generation |
| **Structured LLM output** via Pydantic schemas | **Same pattern** using PRISM's `invoke_llm()` + Pydantic schemas |
| **Separate iteration prompts** per field type | **Separate iteration prompts** per section with context injection |

**What is NOT adopted from worklet-gen:**
- Web scraping and Tavily-based content extraction (PRISM uses its own RAG pipeline)
- Google Scholar / GitHub reference searching (not relevant for document generation)
- Selenium-based web interactions
- The specific worklet data model (replaced by document section model)
- External LLM API fallbacks (constraint: local-only)

---

## 13. Competitive Context

### How this compares to existing tools

| Tool | Approach | PRISM Advantage |
|------|----------|-----------------|
| **Gamma.app** | Cloud-based AI presentation generator | PRISM runs locally; grounded in user's own documents |
| **Beautiful.ai** | Template-driven presentation design | PRISM synthesizes from uploaded knowledge, not generic templates |
| **Tome** | AI-first presentation creation | PRISM's RAG grounding ensures factual accuracy from source materials |
| **ChatGPT + export** | General LLM → manual document creation | PRISM provides structured, iterative workflow with professional templates |
| **Google Slides AI** | Cloud-only, Google ecosystem | PRISM is enterprise-private, format-agnostic |

**PRISM's unique position**: The only tool that combines **enterprise-private local LLM inference** with **RAG-grounded document generation** from the user's own uploaded knowledge base, with **interactive iterative refinement** and **multi-format export**.
