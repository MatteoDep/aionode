import asyncio
import inspect
from collections.abc import Awaitable
from typing import Any


def awaitify(func: Any, /, *wait_for: Awaitable, track: bool = True, auto_progress: bool = True) -> Any:
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        if track:
            from aiotask import _init_task_info, _start_task
            await _init_task_info(start=False, auto_progress=auto_progress)
            _start = _start_task
        else:
            async def _start():
                pass

        try:
            if wait_for:
                await asyncio.gather(*wait_for)
            resolved_args = [await a if inspect.isawaitable(a) else a for a in args]
            resolved_kwargs = {k: (await v if inspect.isawaitable(v) else v) for k, v in kwargs.items()}
        except Exception as e:
            msg = "Failed while waiting to start."
            raise RuntimeError(msg) from e

        await _start()

        result = func(*resolved_args, **resolved_kwargs)
        return await result if inspect.isawaitable(result) else result

    return wrapper
