import tempfile
from pathlib import Path
from codereflex.config import Config, load_config


def test_default_config():
    cfg = load_config(None)
    assert cfg.retry_budget == 5
    assert "pytest" in cfg.validators
    assert cfg.model == "gpt-4o-mini"


def test_load_from_yaml():
    yaml_content = """
retry_budget: 3
validators: [pytest, ruff]
allowed_paths: ["/tmp/proj"]
dangerous_patterns: ["rm -rf"]
model: "gpt-4o"
llm_base_url: "https://api.example.com/v1"
convergence_threshold: 2
context_window: 10
"""
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        path = f.name
    cfg = load_config(path)
    assert cfg.retry_budget == 3
    assert cfg.validators == ["pytest", "ruff"]
    assert cfg.allowed_paths == ["/tmp/proj"]
    assert cfg.model == "gpt-4o"


def test_missing_file_uses_defaults():
    cfg = load_config("/nonexistent/path.yaml")
    assert cfg.retry_budget == 5


def test_invalid_yaml_raises():
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        f.write("retry_budget: [unclosed")
        path = f.name
    try:
        load_config(path)
        assert False, "should have raised"
    except Exception:
        assert True
