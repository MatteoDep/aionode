from __future__ import annotations

import asyncio
import os
import sys
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aiotask import TaskInfo, TaskStatus
    from aiotask._graph import TaskGraph

_STATUS_LABEL: dict[str, str] = {
    "waiting to start": "waiting",
    "running": "running",
    "done": "done",
    "failed": "failed",
    "canceled": "canceled",
}

_STATUS_COLOR: dict[str, str] = {
    "waiting to start": "90",  # dark gray
    "running": "33",           # yellow
    "done": "32",              # green
    "failed": "31",            # red
    "canceled": "31",          # red
}

BAR_WIDTH = 10


def _use_color() -> bool:
    try:
        return os.isatty(sys.stdout.fileno())
    except Exception:
        return False


def _ansi(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m"


def _progress_bar(completed: float, total: float | None, width: int = BAR_WIDTH) -> str:
    if total is None or total == 0:
        return "─" * width
    ratio = min(completed / total, 1.0)
    filled = round(ratio * width)
    return "█" * filled + "░" * (width - filled)


def _fmt_duration(info: TaskInfo) -> str:
    if not info.started():
        return "—"
    return f"{info.duration():.1f}s"


def _fmt_node(
    info: TaskInfo,
    graph: TaskGraph,
    prefix: str = "",
    use_color: bool = False,
) -> str:
    status_val = info.status.value
    label = f"[{_STATUS_LABEL.get(status_val, status_val)}]"
    if use_color:
        label = _ansi(label, _STATUS_COLOR.get(status_val, "0"))

    bar = _progress_bar(info.completed, info.total)
    total_str = str(int(info.total)) if info.total is not None else "?"
    progress = f"({int(info.completed)}/{total_str})"
    duration = _fmt_duration(info)

    dep_names: list[str] = []
    for dep_id in info.deps:
        try:
            dep_info = graph.node(dep_id)
            dep_names.append(dep_info.description)
        except Exception:
            pass
    dep_str = f"  ← deps: {', '.join(dep_names)}" if dep_names else ""

    return f"{prefix}{info.description:<10}  {label:<12}  {bar}  {progress:<8}  {duration}{dep_str}"


def render_text(graph: TaskGraph) -> str:
    """Render graph as ANSI text tree."""
    use_color = _use_color()
    nodes = graph.nodes()
    if not nodes:
        return ""

    lines: list[str] = []

    if graph._root_id is not None:
        root_list = [n for n in nodes if n.id == graph._root_id]
        rest = [n for n in nodes if n.id != graph._root_id]
        if root_list:
            lines.append(_fmt_node(root_list[0], graph, use_color=use_color))
            if rest:
                lines.append("│")
            for i, n in enumerate(rest):
                prefix = "└─ " if i == len(rest) - 1 else "├─ "
                lines.append(_fmt_node(n, graph, prefix=prefix, use_color=use_color))
        else:
            for n in nodes:
                lines.append(_fmt_node(n, graph, use_color=use_color))
    else:
        for n in nodes:
            lines.append(_fmt_node(n, graph, use_color=use_color))

    return "\n".join(lines)


def render(graph: TaskGraph, *, rich: bool | None = None) -> str:
    """Render graph, using rich if available (unless rich=False)."""
    if rich is not False:
        try:
            from aiotask._rich_renderer import render_rich

            return render_rich(graph)
        except ImportError:
            pass
    return render_text(graph)


async def watch(
    graph: TaskGraph,
    *,
    interval: float = 0.5,
    renderer: Callable[[TaskGraph], str] | None = None,
) -> None:
    """Redraw graph in-place until all nodes reach a terminal status."""
    from aiotask import TaskStatus

    _TERMINAL = frozenset({TaskStatus.DONE, TaskStatus.FAILED, TaskStatus.CANCELLED})
    render_fn = renderer if renderer is not None else render_text
    last_line_count = 0

    while True:
        output = render_fn(graph)
        line_count = output.count("\n") + 1

        if last_line_count > 0:
            sys.stdout.write(f"\033[{last_line_count}A\033[J")

        sys.stdout.write(output + "\n")
        sys.stdout.flush()
        last_line_count = line_count

        nodes = graph.nodes()
        if nodes and all(n.status in _TERMINAL for n in nodes):
            break

        await asyncio.sleep(interval)
