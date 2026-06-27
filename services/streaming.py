"""ContextVar bridge: lets sync graph thread push tokens to the async WebSocket loop."""
import asyncio
from contextvars import ContextVar

_token_queue: ContextVar[asyncio.Queue | None] = ContextVar("token_queue", default=None)
_main_loop: ContextVar[asyncio.AbstractEventLoop | None] = ContextVar("main_loop", default=None)


def setup_streaming(queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
    _token_queue.set(queue)
    _main_loop.set(loop)


def emit_token(delta: str):
    """Called from the sync executor thread to enqueue a token for the WebSocket."""
    q = _token_queue.get()
    loop = _main_loop.get()
    if q is not None and loop is not None and not loop.is_closed():
        try:
            q.put_nowait(delta)
        except asyncio.QueueFull:
            pass


def clear_streaming():
    _token_queue.set(None)
    _main_loop.set(None)
