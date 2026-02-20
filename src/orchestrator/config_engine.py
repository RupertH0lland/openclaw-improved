"""Config engine - orchestrator can propose config changes (sandboxed)."""
import yaml
from pathlib import Path


class ConfigEngine:
    """Propose and apply config changes. Writes to pending/ for approval."""

    def __init__(self, project_root: Path):
        self.root = project_root
        self.config_dir = project_root / "config"
        self.pending_dir = project_root / "config" / "pending"
        self.pending_dir.mkdir(parents=True, exist_ok=True)

    def propose(self, config_file: str, changes: dict) -> Path:
        """Write proposed changes to pending/. Returns path to pending file."""
        src = self.config_dir / config_file
        if not src.exists():
            raise FileNotFoundError(f"Config not found: {config_file}")
        with open(src, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        for key, value in changes.items():
            keys = key.split(".")
            d = data
            for k in keys[:-1]:
                d = d.setdefault(k, {})
            d[keys[-1]] = value
        pending_path = self.pending_dir / config_file
        with open(pending_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False)
        return pending_path

    def apply_pending(self, config_file: str) -> bool:
        """Apply pending config. Returns True if applied."""
        pending = self.pending_dir / config_file
        target = self.config_dir / config_file
        if not pending.exists():
            return False
        target.write_text(pending.read_text(), encoding="utf-8")
        pending.unlink()
        return True


def load_skills(project_root: Path) -> list[dict]:
    """Load skill configs from skills/ directory."""
    skills_dir = project_root / "skills"
    if not skills_dir.exists():
        return []
    skills = []
    for path in skills_dir.glob("*.yaml"):
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        data["_path"] = str(path)
        skills.append(data)
    return skills
