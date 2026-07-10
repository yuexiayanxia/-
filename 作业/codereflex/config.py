from __future__ import annotations
import logging
from dataclasses import dataclass, field
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)


@dataclass
class Config:
    validators: list[str] = field(default_factory=lambda: ["pytest", "ruff", "mypy"])
    retry_budget: int = 5
    allowed_paths: list[str] = field(default_factory=lambda: ["."])
    dangerous_patterns: list[str] = field(default_factory=lambda: [
        "rm -rf", "drop ", "git push --force", "curl.*|.*sh", "wget.*|.*sh",
    ])
    model: str = "gpt-4o-mini"
    llm_base_url: str = "https://api.openai.com/v1"
    convergence_threshold: int = 3
    context_window: int = 20


def load_config(path: str | None) -> Config:
    if path is None:
        return Config()
    p = Path(path)
    if not p.exists():
        logger.warning("Config file %s not found, using defaults", path)
        return Config()
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in config {path}: {e}") from e
    known = {f for f in Config.__dataclass_fields__}
    cfg = Config()
    for k, v in data.items():
        if k in known:
            setattr(cfg, k, v)
        else:
            logger.warning("Unknown config field '%s' ignored", k)
    return cfg
