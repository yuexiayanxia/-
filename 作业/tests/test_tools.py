import tempfile
from pathlib import Path
from codereflex.models import Action, ActionResult, ActionType
from codereflex.tools.base import ToolDispatcher
from codereflex.tools.file_tools import ReadFile, WriteFile, ListDir
from codereflex.tools.shell_tool import RunShell


def test_write_then_read_file():
    with tempfile.TemporaryDirectory() as d:
        disp = ToolDispatcher(allowed_paths=[d])
        disp.register(ActionType.WRITE_FILE, WriteFile(allowed_paths=[d]))
        disp.register(ActionType.READ_FILE, ReadFile(allowed_paths=[d]))
        w = disp.dispatch(Action(ActionType.WRITE_FILE, {"path": f"{d}/x.py", "content": "print(1)"}))
        assert w.success
        r = disp.dispatch(Action(ActionType.READ_FILE, {"path": f"{d}/x.py"}))
        assert r.success
        assert "print(1)" in r.output


def test_read_nonexistent_fails():
    with tempfile.TemporaryDirectory() as d:
        rf = ReadFile(allowed_paths=[d])
        r = rf.execute(Action(ActionType.READ_FILE, {"path": f"{d}/nope.py"}))
        assert not r.success
        assert "not found" in r.error.lower() or "no such" in r.error.lower()


def test_path_traversal_denied():
    with tempfile.TemporaryDirectory() as d:
        wf = WriteFile(allowed_paths=[d])
        r = wf.execute(Action(ActionType.WRITE_FILE, {"path": f"{d}/../../etc/evil", "content": "x"}))
        assert not r.success
        assert "denied" in r.error.lower() or "outside" in r.error.lower()


def test_list_dir():
    with tempfile.TemporaryDirectory() as d:
        Path(d, "a.py").write_text("x")
        Path(d, "b.py").write_text("y")
        ld = ListDir(allowed_paths=[d])
        r = ld.execute(Action(ActionType.LIST_DIR, {"path": d}))
        assert r.success
        assert "a.py" in r.output
        assert "b.py" in r.output


def test_run_shell():
    rs = RunShell(timeout=5)
    r = rs.execute(Action(ActionType.RUN_SHELL, {"cmd": "echo hello"}))
    assert r.success
    assert "hello" in r.output


def test_run_shell_nonzero_exit():
    rs = RunShell(timeout=5)
    r = rs.execute(Action(ActionType.RUN_SHELL, {"cmd": "python -c 'import sys; sys.exit(1)'"}))
    assert not r.success
    assert r.exit_code == 1
