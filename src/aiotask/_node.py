import asyncio
import functools
import inspect
from collections.abc import Awaitable, Callable, Coroutine, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class _Resolved[T]:
    awaitable: Awaitable[T]


def resolve[T](awaitable: Awaitable[T]) -> T:
    return _Resolved(awaitable)  # type: ignore[return-value]


def node[**P, R](
    func: Callable[P, Coroutine[Any, Any, R]],
    /,
    wait_for: Sequence[Awaitable[Any]] | None = None,
    track: bool = True,
    auto_progress: bool = True,
) -> Callable[P, Coroutine[Any, Any, R]]:
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        if track:
            from aiotask import _init_task_info, _start_task

            await _init_task_info(start=False, auto_progress=auto_progress)
            _start = _start_task
        else:

            async def _start() -> None:
                pass

        # Identify _Resolved positions
        resolved_arg_idxs = [(i, a) for i, a in enumerate(args) if isinstance(a, _Resolved)]
        resolved_kwarg_keys = [(k, v) for k, v in kwargs.items() if isinstance(v, _Resolved)]
        all_awaitables = (
            [a.awaitable for _, a in resolved_arg_idxs]
            + [v.awaitable for _, v in resolved_kwarg_keys]
            + list(wait_for or [])
        )

        try:
            if all_awaitables:
                results = await asyncio.gather(*all_awaitables)
                n_args = len(resolved_arg_idxs)
                n_kw = len(resolved_kwarg_keys)
                arg_results = list(results[:n_args])
                kwarg_results = list(results[n_args : n_args + n_kw])
                # results[n_args + n_kw:] are wait_for results — discarded
            else:
                arg_results, kwarg_results = [], []
        except Exception as e:
            msg = "Failed while waiting to start."
            raise RuntimeError(msg) from e

        # Rebuild args/kwargs with resolved values
        resolved_args = list(args)
        for (i, _), val in zip(resolved_arg_idxs, arg_results, strict=True):
            resolved_args[i] = val
        resolved_kwargs = dict(kwargs)
        for (k, _), val in zip(resolved_kwarg_keys, kwarg_results, strict=True):
            resolved_kwargs[k] = val

        if track:
            from aiotask import _get_state, _register_dep, _task_id

            state = _get_state()
            our_id = _task_id.get()
            dep_tasks: list[asyncio.Task] = (
                [a.awaitable for _, a in resolved_arg_idxs if isinstance(a.awaitable, asyncio.Task)]
                + [v.awaitable for _, v in resolved_kwarg_keys if isinstance(v.awaitable, asyncio.Task)]
                + [d for d in (wait_for or []) if isinstance(d, asyncio.Task)]
            )
            for dep_task in dep_tasks:
                if dep_task in state.task_ids:
                    await _register_dep(our_id, state.task_ids[dep_task])

        await _start()

        result = func(*resolved_args, **resolved_kwargs)
        return await result if inspect.isawaitable(result) else result

    return wrapper
