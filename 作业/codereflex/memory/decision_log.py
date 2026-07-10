from __future__ import annotations
from pathlib import Path
from codereflex.models import DecisionLogEntry


class DecisionLog:
    def __init__(self, path: Path):
        self._path = Path(path)

    def append(self, entry: DecisionLogEntry) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        line = f"- [{entry.timestamp}] task='{entry.task}' outcome='{entry.outcome}' actions={entry.key_actions}\n"
        with self._path.open("a", encoding="utf-8") as f:
            f.write(line)

    def search(self, keyword: str) -> list[DecisionLogEntry]:
        if not self._path.exists():
            return []
        results = []
        for line in self._path.read_text(encoding="utf-8").splitlines():
            if keyword.lower() in line.lower():
                results.append(self._parse(line))
        return results

    def _parse(self, line: str) -> DecisionLogEntry:
        import re
        m = re.match(r"- \[(.+?)\] task='(.+?)' outcome='(.+?)' actions=(.+)", line)
        if m:
            return DecisionLogEntry(
                timestamp=m.group(1), task=m.group(2), outcome=m.group(3),
                key_actions=m.group(4).strip("[]").split(", "),
            )
        return DecisionLogEntry(timestamp="", task=line, outcome="")
