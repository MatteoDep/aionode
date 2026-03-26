# aionode

Lightweight asyncio task tracking with dependency graphs and progress rendering.

## Installation

```bash
pip install aionode
```

For Rich table rendering:

```bash
pip install aionode[viz]
```

## Quick Start

```python
import asyncio
import aionode

async def fetch_data() -> list[int]:
    await asyncio.sleep(1)
    return list(range(100))

async def process(data: list[int]) -> int:
    await asyncio.sleep(0.5)
    return sum(data)

async def pipeline() -> None:
    async with asyncio.TaskGroup() as tg:
        fetch = tg.create_task(aionode.node(fetch_data)(), name="fetch")
        tg.create_task(aionode.node(process)(aionode.resolve(fetch)), name="process")

async def main() -> None:
    root = asyncio.create_task(aionode.track(pipeline)(), name="pipeline")
    root_id = await aionode.get_task_id(root)
    graph = aionode.TaskGraph(root_id=root_id)

    await aionode.watch(graph, interval=0.3)
    await root

asyncio.run(main())
```

## Core Concepts

### `node(func, wait_for=[], track=True, auto_progress=True)`

Wraps an async function as a DAG node. Use `resolve()` to pass awaitables as arguments — they are gathered concurrently before the function is called. Sync functions must be wrapped with `make_async` first.

```python
# Async function — pass upstream tasks with resolve()
fetch = tg.create_task(aionode.node(fetch_data)(), name="fetch")
process_task = tg.create_task(aionode.node(process)(aionode.resolve(fetch)), name="process")

# Sync function — wrap with make_async first
summarize = tg.create_task(
    aionode.node(aionode.make_async(my_sync_fn))(aionode.resolve(process_task)),
    name="summarize",
)

# Side-only dependency (no value passed): use wait_for
task_b = tg.create_task(aionode.node(cleanup, wait_for=[fetch])(), name="cleanup")
```

### `resolve(awaitable)`

Marks an awaitable to be resolved before being passed as an argument to `node()`. This preserves type information — the type checker sees `resolve(task: Task[T])` as returning `T`.

```python
result = await aionode.node(process)(aionode.resolve(upstream_task))
```

### `track(func, start=True)`

Tracks a coroutine by registering it in the task graph. Use this for the root task or tasks that don't need `node()`'s dependency resolution.

```python
root = asyncio.create_task(aionode.track(my_coro)(), name="root")
```

### `TaskGraph`

Query the dependency graph:

```python
graph = aionode.TaskGraph(root_id=root_id)

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
renderer = aionode.get_render()

# Force plain text
renderer = aionode.get_render(rich=False)

# Live-updating display
await aionode.watch(graph, interval=0.5, renderer=renderer)
```

### Task Inspection

```python
task_id = await aionode.get_task_id(asyncio_task)
info = aionode.get_task(task_id)

info.status        # TaskStatus: WAITING, RUNNING, DONE, FAILED, CANCELLED
info.duration()    # Elapsed seconds
info.description   # Task name
info.deps          # Upstream dependency IDs
info.dependents    # Downstream dependent IDs
info.logs          # Accumulated log output

await aionode.log("processing record 42")  # Append to current task's logs
```

## API Reference

| Function | Description |
|---|---|
| `node(func, wait_for, track, auto_progress)` | Wrap an async function as a DAG node |
| `resolve(awaitable)` | Mark an awaitable to be resolved as a node argument |
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
