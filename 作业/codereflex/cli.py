from __future__ import annotations
import argparse
import sys


def main():
    parser = argparse.ArgumentParser(prog="codereflex", description="CodeReflex coding agent harness")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("setup", help="Set up API credentials")
    run_p = sub.add_parser("run", help="Run the agent server")
    run_p.add_argument("--config", default=None, help="Path to config YAML")
    run_p.add_argument("--project", default=".", help="Target project path")
    run_p.add_argument("--port", type=int, default=8000)

    args = parser.parse_args()

    if args.command == "setup":
        from codereflex.credentials import CredentialStore
        store = CredentialStore()
        store.setup_interactive("OPENAI_API_KEY")
    elif args.command == "run":
        _run_server(args.config, args.project, args.port)
    else:
        parser.print_help()


def _run_server(config_path: str | None, project_path: str, port: int):
    from codereflex.config import load_config
    from codereflex.credentials import CredentialStore
    from codereflex.web.app import create_app
    import uvicorn

    cfg = load_config(config_path)
    store = CredentialStore()
    api_key = store.get("OPENAI_API_KEY")
    if not api_key:
        print("No API key found. Run 'codereflex setup' first.")
        sys.exit(1)

    from codereflex.llm.client import LLMClient
    from codereflex.tools.base import ToolDispatcher
    from codereflex.tools.file_tools import ReadFile, WriteFile, ListDir
    from codereflex.tools.shell_tool import RunShell
    from codereflex.guardrail.guardrail import Guardrail
    from codereflex.guardrail.hitl import HITLController
    from codereflex.feedback.validators import ValidatorPipeline, PytestValidator, RuffValidator, MypyValidator, Validator
    from codereflex.feedback.feedback_loop import FeedbackLoop
    from codereflex.memory.session import ContextWindow
    from codereflex.agent import AgentLoop
    from codereflex.models import ActionType

    llm = LLMClient(cfg.llm_base_url, api_key)
    disp = ToolDispatcher(allowed_paths=[project_path])
    disp.register(ActionType.READ_FILE, ReadFile(allowed_paths=[project_path]))
    disp.register(ActionType.WRITE_FILE, WriteFile(allowed_paths=[project_path]))
    disp.register(ActionType.LIST_DIR, ListDir(allowed_paths=[project_path]))
    disp.register(ActionType.RUN_SHELL, RunShell())
    validators: list[Validator] = []
    if "pytest" in cfg.validators:
        validators.append(PytestValidator())
    if "ruff" in cfg.validators:
        validators.append(RuffValidator())
    if "mypy" in cfg.validators:
        validators.append(MypyValidator())
    loop = AgentLoop(
        llm_client=llm, dispatcher=disp,
        guardrail=Guardrail(cfg.dangerous_patterns, cfg.allowed_paths),
        hitl=HITLController(),
        feedback_loop=FeedbackLoop(ValidatorPipeline(validators), cfg),
        context_window=ContextWindow(), config=cfg, project_path=project_path,
    )
    app = create_app(loop, cfg)
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
