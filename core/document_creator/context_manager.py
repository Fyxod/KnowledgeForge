from typing import Dict, Optional

from core.document_creator.state import DocumentCreatorState, SectionState


class DocumentContextManager:
    """
    Maintains sliding context across section generation calls.

    Ensures each LLM call receives enough context for coherence
    without exceeding context window limits.

    Budget per section-generation call (~6K-7K tokens):
    - System prompt + instructions:      ~500 tokens
    - Document outline (compact):         ~300-500 tokens
    - Previous section summary:           ~200-300 tokens
    - RAG context for this section:       ~2000-3000 tokens
    - Section spec + user feedback:       ~200-400 tokens
    - Terminology registry:               ~100-200 tokens
    - Style excerpt:                      ~100-200 tokens
    - Output budget:                      ~2000-3000 tokens
    """

    def __init__(self, state: DocumentCreatorState):
        self.state = state

    def get_compact_outline(self) -> str:
        """Compact representation of the full outline (~300 tokens)."""
        lines = []
        if self.state.document_title:
            lines.append(f"Document: {self.state.document_title}")
        if self.state.document_subtitle:
            lines.append(f"Subtitle: {self.state.document_subtitle}")
        lines.append("")
        for i, section in enumerate(self.state.sections, 1):
            lines.append(
                f"{i}. {section.spec.title} [{section.spec.content_format.value}] "
                f"— {section.spec.description}"
            )
        return "\n".join(lines)

    def get_previous_section_summary(self, current_index: int) -> str:
        """Summary of the previous section's content (~200 tokens)."""
        if current_index <= 0:
            return "This is the first section of the document."

        prev_section = self.state.sections[current_index - 1]
        if not prev_section.versions:
            return "Previous section has not been generated yet."

        version = prev_section.versions[prev_section.selected_version_index]
        # Take first 300 characters of content as summary
        content_preview = version.content[:300]
        if len(version.content) > 300:
            content_preview += "..."

        summary = f"Previous section '{prev_section.spec.title}':\n{content_preview}"
        if version.key_takeaway:
            summary += f"\nKey takeaway: {version.key_takeaway}"
        return summary

    def get_terminology_context(self) -> str:
        """Key terms and definitions extracted so far (~100 tokens)."""
        if not self.state.terminology:
            return ""
        lines = ["Key terms used in this document:"]
        for term, definition in list(self.state.terminology.items())[:15]:
            lines.append(f"- {term}: {definition}")
        return "\n".join(lines)

    def update_after_section(self, section_index: int, content: str):
        """Update rolling context after generating a section."""
        # Capture style excerpt from first section
        if section_index == 0 and content:
            # Take first 2-3 sentences as style reference
            sentences = content.split(". ")
            self.state.style_excerpt = ". ".join(sentences[:3])
            if not self.state.style_excerpt.endswith("."):
                self.state.style_excerpt += "."

        # Update narrative summary (last section summary)
        section = self.state.sections[section_index]
        version = section.versions[section.selected_version_index]
        self.state.narrative_summary = (
            f"Last completed section: '{section.spec.title}'. "
            f"Key takeaway: {version.key_takeaway or 'N/A'}"
        )

    def extract_terminology_from_content(self, content: str) -> Dict[str, str]:
        """
        Simple terminology extraction from generated content.
        Looks for patterns like "Term (definition)" or "Term - definition".
        Returns dict of term -> definition.
        """
        import re

        terms = {}
        # Match patterns like "ACRONYM (Full Name)" or "Term (explanation)"
        pattern = r"\b([A-Z]{2,})\s*\(([^)]+)\)"
        for match in re.finditer(pattern, content):
            acronym = match.group(1)
            expansion = match.group(2).strip()
            if len(expansion) > 5:  # Skip very short matches
                terms[acronym] = expansion
        return terms
