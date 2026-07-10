# CodeReflex

Feedback-loop-centric coding agent harness. Wraps an LLM to write, validate, and self-correct Python code until tests pass or retry budget exhausts.

## Project Intro

CodeReflex implements `Agent = LLM + Harness`. The LLM decides the next action; the harness handles tool dispatch, guardrails, feedback validation, and memory. The feedback loop is the structural spine: after every `write_file`, the harness runs pytest + ruff + mypy, classifies failures, and injects structured feedback so the LLM can self-correct.

## Installation

```bash
cd 作业
pip install -e ".[dev,validators]"
```

## Running

### Local

```bash
# 1. Set up API key (stored in OS keyring)
python -m codereflex.cli setup

# 2. Run the WebUI server
python -m codereflex.cli run --project /path/to/your/python/project --port 8000
```

Open http://localhost:8000

### Docker

```bash
docker build -t codereflex ./作业
docker run -p 8000:8000 -e OPENAI_API_KEY=sk-... -v /path/to/project:/workspace codereflex
```

## API Key Security

- **Local**: stored in OS keyring (Windows Credential Manager / macOS Keychain / Linux Secret Service). First run `codereflex setup` with hidden input. `status` shows set/unset without echoing the key.
- **Docker**: pass via `-e OPENAI_API_KEY=...` at `docker run`. **Known risk**: environment variables are plaintext and visible to processes in the container. This is an accepted tradeoff for containerized deployment.
- **`.env` fallback** (local dev only, gitignored): plaintext, loaded via `python-dotenv`. Documented risk.

Never commit real keys. The repo self-checks `.env`, history, and config files before commit.

## Distribution Commands

```bash
# Build Docker image
docker build -t codereflex ./作业

# Run
docker run -p 8000:8000 -e OPENAI_API_KEY=sk-... codereflex
```

## Directory Structure

```
作业/
  pyproject.toml
  codereflex/
    models.py          # data models + enums
    config.py          # YAML config loading
    credentials.py     # keyring + env credential store
    agent.py           # AgentLoop main loop
    cli.py             # CLI entry
    llm/client.py      # LLMClient + MockLLMClient
    tools/             # ToolDispatcher + file/shell tools
    guardrail/         # Guardrail + HITL state machine
    feedback/          # Validators + FailureClassifier + FeedbackLoop
    memory/            # ContextWindow + DecisionLog
    web/               # FastAPI + SSE WebUI
  tests/               # mock-LLM unit tests + fixtures
  demos/               # mechanism demo
  Dockerfile
  .gitlab-ci.yml
```

## Security Boundaries

- **Path sandboxing**: all file operations restricted to `allowed_paths`; `..` traversal resolved and denied.
- **Dangerous command interception**: `rm -rf`, `drop`, `git push --force`, `curl|sh` patterns intercepted → HITL approval required.
- **Credential isolation**: keys never in source, git, or logs. Log sanitization strips key-like strings.
- **Retry budget + convergence detection**: prevents infinite feedback loops.

## Known Limitations

- Single concurrent session (MVP).
- Target project must be Python with pytest/ruff/mypy.
- Docker deployment: env var key is plaintext (accepted tradeoff).
- Free-tier deployment (Render/Fly.io) may sleep on inactivity.
