"""Filesystem tool - read/write files for the orchestrator."""
from pathlib import Path


class FilesystemTool:
    """Safe filesystem operations within configured output and project dirs."""

    def __init__(self, project_root: Path, output_dir: Path):
        self.project_root = Path(project_root)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def read(self, path: str) -> str:
        """Read file content. Path relative to project root."""
        p = self._resolve(path)
        if not p.exists():
            raise FileNotFoundError(f"File not found: {path}")
        if not p.is_file():
            raise ValueError(f"Not a file: {path}")
        return p.read_text(encoding="utf-8", errors="replace")

    def write(self, path: str, content: str) -> str:
        """Write file. Prefer output_dir for new files."""
        p = self._resolve(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return str(p)

    def list_dir(self, path: str = "") -> list[dict]:
        """List directory contents. Returns name, is_dir, size."""
        p = self._resolve(path or ".")
        if not p.exists():
            raise FileNotFoundError(f"Directory not found: {path}")
        if not p.is_dir():
            raise ValueError(f"Not a directory: {path}")
        result = []
        for child in sorted(p.iterdir()):
            result.append({
                "name": child.name,
                "is_dir": child.is_dir(),
                "size": child.stat().st_size if child.is_file() else 0,
            })
        return result

    def _resolve(self, path: str) -> Path:
        """Resolve path; allow output_dir and project_root only."""
        p = Path(path)
        if not p.is_absolute():
            p = self.project_root / p
        p = p.resolve()
        try:
            p.relative_to(self.project_root)
        except ValueError:
            try:
                p.relative_to(self.output_dir)
            except ValueError:
                raise PermissionError(f"Path outside allowed directories: {path}")
        return p
