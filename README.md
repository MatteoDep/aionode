# aiotask

Lightweight asyncio task tracking with dependency graphs and progress rendering.

## Installation

```bash
pip install aiotask
```

For Rich table rendering:

```bash
pip install aiotask[viz]
```

## Quick Start

```python
import asyncio
import aiotask

async def fetch_data() -> list[int]:
    await asyncio.sleep(1)
    return list(range(100))

async def process(data: list[int]) -> int:
    await asyncio.sleep(0.5)
    return sum(data)

async def pipeline() -> None:
    async with asyncio.TaskGroup() as tg:
        fetch = tg.create_task(aiotask.node(fetch_data)(), name="fetch")
        tg.create_task(aiotask.node(process, deps=[fetch])(fetch), name="process")

async def main() -> None:
    root = asyncio.create_task(aiotask.track(pipeline)(), name="pipeline")
    root_id = await aiotask.get_task_id(root)
    graph = aiotask.TaskGraph(root_id=root_id)

    await aiotask.watch(graph, interval=0.3)
    await root

asyncio.run(main())
```

## Core Concepts

### `node(func, deps=[], track=True, auto_progress=True)`

Wraps a sync or async function as a DAG node. Awaitable arguments are resolved automatically before calling the function.

```python
# Sync function — wrapped transparently
result = await aiotask.node(lambda x, y: x + y)(task_a, task_b)

# With explicit dependencies
task_b = tg.create_task(aiotask.node(process, deps=[task_a])(task_a), name="process")
```

### `track(func, start=True)`

Tracks a coroutine by registering it in the task graph. Use this for the root task or tasks that don't need `node()`'s dependency resolution.

```python
root = asyncio.create_task(aiotask.track(my_coro)(), name="root")
```

### `TaskGraph`

Query the dependency graph:

```python
graph = aiotask.TaskGraph(root_id=root_id)

graph.nodes()            # All tasks in topological order
graph.roots()            # Tasks with no upstream deps
graph.leaves()           # Tasks with no downstream dependents
graph.upstream(task_id)  # Transitive upstream deps
graph.downstream(task_id)  # Transitive downstream dependents
graph.summary()          # {TaskStatus: count}
graph.critical_path()    # Longest-duration path
```

### Rendering

```python
# Auto-detect Rich or fall back to ANSI text
renderer = aiotask.get_render()

# Force plain text
renderer = aiotask.get_render(rich=False)

# Live-updating display
await aiotask.watch(graph, interval=0.5, renderer=renderer)
```

### Task Inspection

```python
task_id = await aiotask.get_task_id(asyncio_task)
info = aiotask.get_task(task_id)

info.status        # TaskStatus: WAITING, RUNNING, DONE, FAILED, CANCELLED
info.duration()    # Elapsed seconds
info.description   # Task name
info.deps          # Upstream dependency IDs
info.dependents    # Downstream dependent IDs
info.logs          # Accumulated log output

await aiotask.log("processing record 42")  # Append to current task's logs
```

## API Reference

| Function | Description |
|---|---|
| `node(func, deps, track, auto_progress)` | Wrap a function as a DAG node |
| `track(func, start)` | Track a coroutine in the task graph |
| `get_task_id(task, timeout)` | Get the task ID for an asyncio.Task |
| `get_task(task_id)` | Get TaskInfo by ID |
| `remove_task(task_id)` | Remove a task and its descendants |
| `log(value, end)` | Append to the current task's logs |
| `make_async(func)` | Run a sync function in a thread |
| `make_async_generator(gen)` | Async iterate a sync iterator via threads |
| `TaskGraph(root_id)` | Create a graph view rooted at a task |
| `TaskGraph.from_task(task)` | Create a graph from an asyncio.Task |
| `TaskGraph.current()` | Graph over all tasks in the current loop |
| `get_render(rich, bar_width, ...)` | Get a configured render function |
| `watch(graph, interval, renderer)` | Live-render until all tasks finish |
