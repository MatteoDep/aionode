# aionode

Lightweight asyncio task tracking as call tree and DAG.

## Installation

```bash
pip install aionode
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
    root = asyncio.create_task(aionode.node(pipeline)(), name="pipeline")
    await root
    for info in aionode.walk_dag():
        print(f"{info.name}: {info.status} ({info.duration():.2f}s)")

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

### `walk_tree` / `walk_dag`

Iterate over tracked tasks after they have been created.

```python
# DFS pre-order through the call tree (parent → children)
for info in aionode.walk_tree():
    print(info.name, info.status)

# Topological order over the DAG (deps → dependents)
for info in aionode.walk_dag():
    print(info.name, info.status)
```

Both accept an optional `root` argument (an `asyncio.Task` or task id). Passing `None` (the default) includes all tasks in the current event loop.

### `sync_node(name, auto_progress=True)`

Track sync code blocks as child nodes in the task tree — without spawning extra threads. Use inside functions running in a `make_async` thread.

```python
@aionode.make_async
def compute_pipeline(state):
    with aionode.sync_node("extract"):
        extract(state)
    with aionode.sync_node("transform"):
        transform(state)
    with aionode.sync_node("load"):
        load(state)

# Each block appears as a named child in walk_tree() with its own timing.
```

`sync_node` can also be used directly inside async `node`-wrapped code for lightweight sync blocks. Be aware that the wrapped code runs on the event loop thread and blocks other coroutines — keep it short, or use `make_async` to offload to a thread.

Also works as a decorator:

```python
@aionode.sync_node
def extract(state):
    ...

# Or with a custom/parameterized name:
@aionode.sync_node(name="compute_{table}")
def process(table: str, state):
    ...
```

### Task Inspection

```python
task_id = await aionode.get_task_id(asyncio_task)
info = aionode.get_task_info(task_id)

info.status        # TaskStatus: WAITING, RUNNING, DONE, FAILED, CANCELLED
info.duration()    # Elapsed seconds
info.name          # Task name
info.deps          # Upstream dependency IDs
info.dependents    # Downstream dependent IDs
info.logs          # Accumulated log output

await aionode.log("processing record 42")  # Append to current task's logs

# Get TaskInfo for the currently running tracked task
info = aionode.current_task_info()
```

## API Reference

| Function | Description |
|---|---|
| `node(func, wait_for, track, auto_progress)` | Wrap an async function as a DAG node |
| `resolve(awaitable)` | Mark an awaitable to be resolved as a node argument |
| `get_task_id(task, timeout)` | Get the task ID for an asyncio.Task |
| `get_task_info(task_id)` | Get TaskInfo by ID |
| `current_task_info()` | Get TaskInfo for the currently running tracked task |
| `remove_task(task_id)` | Remove a task and its descendants |
| `log(value, end)` | Append to the current task's logs |
| `sync_node(name, auto_progress)` | Track a sync block or function as a child node |
| `make_async(func)` | Run a sync function in a thread |
| `make_async_generator(gen)` | Async iterate a sync iterator via threads |
| `walk_tree(root)` | DFS pre-order through the call tree |
| `walk_dag(root)` | Topological order over the DAG |
