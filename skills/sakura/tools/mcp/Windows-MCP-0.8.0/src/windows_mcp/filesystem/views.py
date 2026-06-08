"""
Data models and constants for filesystem operations.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

# Maximum file size for read operations (10 MB)
MAX_READ_SIZE = 10 * 1024 * 1024
# Maximum number of results for list/search operations
MAX_RESULTS = 500


@dataclass
class File:
    path: str
    type: str
    size: int
    created: datetime
    modified: datetime
    accessed: datetime
    read_only: bool
    extension: Optional[str] = None
    link_target: Optional[str] = None
    contents_files: Optional[int] = None
    contents_dirs: Optional[int] = None

    def to_string(self) -> str:
        lines = [
            f'Path: {self.path}',
            f'Type: {self.type}',
            f'Size: {format_size(self.size)} ({self.size:,} bytes)',
            f'Created: {self.created.strftime("%Y-%m-%d %H:%M:%S")}',
            f'Modified: {self.modified.strftime("%Y-%m-%d %H:%M:%S")}',
            f'Accessed: {self.accessed.strftime("%Y-%m-%d %H:%M:%S")}',
            f'Read-only: {self.read_only}',
        ]

        if self.contents_files is not None and self.contents_dirs is not None:
            lines.append(f'Contents: {self.contents_files} files, {self.contents_dirs} directories')

        if self.extension is not None:
            lines.append(f'Extension: {self.extension}')

        if self.link_target is not None:
            lines.append(f'Link target: {self.link_target}')

        return '\n'.join(lines)


@dataclass
class Directory:
    name: str
    is_dir: bool
    size: int = 0

    def to_string(self, relative_path: str | None = None) -> str:
        entry_type = 'DIR ' if self.is_dir else 'FILE'
        size_str = format_size(self.size) if not self.is_dir else ''
        display = relative_path or self.name
        return f'  [{entry_type}] {display}  {size_str}'


def format_size(size_bytes: int) -> str:
    """Format bytes into a human-readable string."""
    if size_bytes < 1024:
        return f'{size_bytes} B'
    elif size_bytes < 1024 ** 2:
        return f'{size_bytes / 1024:.1f} KB'
    elif size_bytes < 1024 ** 3:
        return f'{size_bytes / (1024 ** 2):.1f} MB'
    else:
        return f'{size_bytes / (1024 ** 3):.1f} GB'
