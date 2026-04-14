from abc import ABC, abstractmethod
from typing import List, Optional

from core.document_creator.state import DocumentCreatorConfig, SectionState


class BaseDocumentAssembler(ABC):
    """Base class for format-specific document assembly."""

    @abstractmethod
    async def assemble(
        self,
        title: str,
        subtitle: Optional[str],
        sections: List[SectionState],
        config: DocumentCreatorConfig,
        output_path: str,
    ) -> str:
        """
        Assemble sections into a document file.
        Returns the file path of the generated document.
        """
        ...
