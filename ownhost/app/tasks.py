"""Ejecuta llamadas de red fuera del hilo de la interfaz para que no se congele."""

from typing import Any, Callable

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal


class _Signals(QObject):
    done = Signal(object)
    failed = Signal(str)
    progress = Signal(str)


class _Job(QRunnable):
    def __init__(self, fn: Callable[..., Any], with_progress: bool):
        super().__init__()
        self.fn = fn
        self.with_progress = with_progress
        self.signals = _Signals()

    def run(self) -> None:
        try:
            try:
                result = self.fn(self.signals.progress.emit) if self.with_progress else self.fn()
            except Exception as e:  # noqa: BLE001 - se muestra al usuario
                self.signals.failed.emit(str(e))
                return
            self.signals.done.emit(result)
        except RuntimeError:
            pass  # la app se cerró mientras la tarea seguía en curso


_alive: set[_Signals] = set()


def _start(fn, with_progress, on_done, on_error, on_progress=None) -> None:
    job = _Job(fn, with_progress)
    signals = job.signals
    _alive.add(signals)
    queued = Qt.ConnectionType.QueuedConnection
    if on_done:
        signals.done.connect(on_done, queued)
    if on_error:
        signals.failed.connect(on_error, queued)
    if on_progress:
        signals.progress.connect(on_progress, queued)
    signals.done.connect(lambda _: _alive.discard(signals), queued)
    signals.failed.connect(lambda _: _alive.discard(signals), queued)
    QThreadPool.globalInstance().start(job)


def run_async(fn: Callable[[], Any], on_done: Callable[[Any], None] | None = None,
              on_error: Callable[[str], None] | None = None) -> None:
    _start(fn, False, on_done, on_error)


def run_with_progress(fn: Callable[[Callable[[str], None]], Any], on_progress: Callable[[str], None],
                      on_done: Callable[[Any], None] | None = None,
                      on_error: Callable[[str], None] | None = None) -> None:
    """Como run_async, pero `fn` recibe una función para informar del progreso."""
    _start(fn, True, on_done, on_error, on_progress)
