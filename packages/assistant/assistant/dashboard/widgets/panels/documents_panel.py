"""
Documents panel for file browsing and preview.

Browse, search, and preview documents with semantic search support.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from rich.text import Text
from .panel_base import PanelBase


@dataclass
class Document:
    """Represents a document."""
    path: Path
    name: str
    size: int
    modified: datetime
    file_type: str
    starred: bool = False

    @classmethod
    def from_path(cls, path: Path) -> "Document":
        """Create Document from file path."""
        stat = path.stat()
        return cls(
            path=path,
            name=path.name,
            size=stat.st_size,
            modified=datetime.fromtimestamp(stat.st_mtime),
            file_type=path.suffix[1:] if path.suffix else "file"
        )

    def size_str(self) -> str:
        """Get human-readable file size."""
        size = self.size
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}TB"

    def get_icon(self) -> str:
        """Get icon for file type."""
        icons = {
            "py": "🐍",
            "js": "📜",
            "ts": "📘",
            "md": "📝",
            "txt": "📄",
            "pdf": "📕",
            "json": "📊",
            "yaml": "⚙️",
            "yml": "⚙️",
            "toml": "⚙️",
            "csv": "📊",
            "xlsx": "📊",
            "png": "🖼️",
            "jpg": "🖼️",
            "svg": "🎨",
            "zip": "📦",
            "tar": "📦",
            "gz": "📦",
        }
        return icons.get(self.file_type, "📄")


class DocumentsPanel(PanelBase):
    """
    Documents panel for file browsing.

    Features:
    - File browser (tree view)
    - Search bar (filename search)
    - Recent files list
    - Starred documents
    - File type filtering
    - Quick file preview
    """

    def __init__(
        self,
        root_dir: Optional[Path] = None,
        **kwargs
    ):
        """
        Initialize documents panel.

        Args:
            root_dir: Root directory to browse (defaults to home)
        """
        super().__init__(
            panel_id="documents",
            title="Documents",
            min_width=35,
            min_height=10,
            **kwargs
        )
        self.root_dir = root_dir or Path.home()
        self.current_dir = self.root_dir
        self.documents: List[Document] = []
        self.starred_docs: List[Document] = []
        self.search_query = ""
        self.view_mode = "list"  # list, starred, recent
        self.file_type_filter: Optional[str] = None

        # Load initial documents
        self._load_documents()

    def _load_documents(self):
        """Load documents from current directory."""
        try:
            self.documents = []
            if not self.current_dir.exists() or not self.current_dir.is_dir():
                return

            for item in sorted(self.current_dir.iterdir()):
                # Skip hidden files
                if item.name.startswith("."):
                    continue

                # Only show files (not directories for now)
                if item.is_file():
                    try:
                        doc = Document.from_path(item)
                        self.documents.append(doc)
                    except (PermissionError, OSError):
                        continue

            self.refresh()

        except (PermissionError, OSError):
            self.documents = []

    def search(self, query: str):
        """
        Search documents by filename.

        Args:
            query: Search query
        """
        self.search_query = query.lower()
        self.refresh()

    def toggle_star(self, document: Document):
        """
        Toggle starred status of document.

        Args:
            document: Document to star/unstar
        """
        document.starred = not document.starred
        if document.starred and document not in self.starred_docs:
            self.starred_docs.append(document)
        elif not document.starred and document in self.starred_docs:
            self.starred_docs.remove(document)

        # Update notification count (starred docs)
        self.set_notification_count(len(self.starred_docs))
        self.refresh()

    def change_directory(self, path: Path):
        """
        Change current directory.

        Args:
            path: New directory path
        """
        if path.is_dir():
            self.current_dir = path
            self._load_documents()

    def _get_filtered_documents(self) -> List[Document]:
        """
        Get documents filtered by current settings.

        Returns:
            Filtered document list
        """
        # Select base list
        if self.view_mode == "starred":
            docs = self.starred_docs
        else:
            docs = self.documents

        # Apply search filter
        if self.search_query:
            docs = [d for d in docs if self.search_query in d.name.lower()]

        # Apply file type filter
        if self.file_type_filter:
            docs = [d for d in docs if d.file_type == self.file_type_filter]

        # Sort by modified time (newest first) for recent view
        if self.view_mode == "recent":
            docs = sorted(docs, key=lambda d: d.modified, reverse=True)[:10]

        return docs

    def render_content(self) -> Text:
        """
        Render documents list.

        Returns:
            Rich Text with documents
        """
        result = Text()

        # Calculate available space
        widget_width = max(self.size.width, self.min_width)
        widget_height = max(self.size.height, self.min_height)
        content_width = widget_width - 4  # Account for borders
        available_lines = widget_height - 2  # Account for borders

        # Header: current directory or view mode
        if self.view_mode == "starred":
            header = "⭐ Starred Documents"
        elif self.view_mode == "recent":
            header = "🕐 Recent Files"
        else:
            # Show current directory (truncate if too long)
            dir_str = str(self.current_dir)
            max_dir_len = content_width - 4
            if len(dir_str) > max_dir_len:
                dir_str = "..." + dir_str[-(max_dir_len - 3):]
            header = f"📁 {dir_str}"

        result.append(header + "\n", style="bold cyan")
        lines_used = 1

        # Search bar (if active)
        if self.search_query:
            if lines_used < available_lines:
                result.append(f"🔍 Search: {self.search_query}\n", style="yellow")
                lines_used += 1

        # Separator
        if lines_used < available_lines:
            result.append("─" * content_width + "\n", style="dim cyan")
            lines_used += 1

        documents = self._get_filtered_documents()

        if not documents:
            # Show empty state
            if lines_used < available_lines:
                result.append("\n")
                lines_used += 1
            if lines_used < available_lines:
                if self.search_query:
                    result.append("  No matching documents\n", style="dim white")
                else:
                    result.append("  No documents found\n", style="dim white")
                lines_used += 1
        else:
            # Render documents
            for doc in documents:
                if lines_used >= available_lines:
                    break

                # Icon and name
                icon = doc.get_icon()
                star = "⭐" if doc.starred else "  "

                # Truncate filename if needed
                max_name_len = content_width - 20  # Space for icon, star, size, etc.
                name = doc.name
                if len(name) > max_name_len:
                    name = name[:max_name_len - 3] + "..."

                # Size and date
                size_str = doc.size_str()
                date_str = doc.modified.strftime("%m/%d")

                # Build line
                line = f"{star}{icon} {name}"

                # Pad and add size/date
                info_str = f"{size_str} {date_str}"
                padding = content_width - len(line) - len(info_str) - 1
                if padding > 0:
                    line += " " * padding + " " + info_str
                else:
                    line += " " + info_str

                result.append(line + "\n", style="white")
                lines_used += 1

        # Fill remaining space
        while lines_used < available_lines:
            result.append("\n")
            lines_used += 1

        return result

    def handle_voice_command(self, command: str, args: Dict[str, Any]) -> bool:
        """
        Handle voice command directed to documents panel.

        Args:
            command: Command name
            args: Command arguments

        Returns:
            True if command was handled
        """
        # Handle base commands
        if super().handle_voice_command(command, args):
            return True

        # Documents-specific commands
        if command == "search files":
            query = args.get("query", "")
            self.search(query)
            return True

        elif command == "clear search":
            self.search("")
            return True

        elif command == "show starred":
            self.view_mode = "starred"
            self.refresh()
            return True

        elif command == "show recent":
            self.view_mode = "recent"
            self.refresh()
            return True

        elif command == "show all":
            self.view_mode = "list"
            self.refresh()
            return True

        elif command == "go up":
            parent = self.current_dir.parent
            if parent != self.current_dir:  # Not at root
                self.change_directory(parent)
            return True

        elif command == "go home":
            self.change_directory(self.root_dir)
            return True

        return False

    def get_panel_info(self) -> Dict[str, Any]:
        """
        Get panel information for debugging.

        Returns:
            Dict with panel state
        """
        info = super().get_panel_info()
        info.update({
            "document_count": len(self.documents),
            "starred_count": len(self.starred_docs),
            "current_dir": str(self.current_dir),
            "view_mode": self.view_mode,
            "search_query": self.search_query,
        })
        return info
