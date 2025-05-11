import collections
import dataclasses
import enum
import statistics
import threading
import time
from typing import Sequence, Type

from .display import *
from .encoding import *
from .flow import *

__all__ = [
    'WorkerStatus', 'BaseWorker', 'WorkerSession'
]

class WorkerStatus(enum.IntEnum):
    """Lower statuses have higher priority.
    
    Less than 0 means the worker aborted.
    """
    ABORT_FINISHED = -3,
    ABORT_ERROR = -2,
    ABORT_USER = -1,
    NOT_STARTED = 0,
    WORKING = 1,
    FINISHED_ALL_WORK = 2

class BaseWorker[T](threading.Thread):
    def __init__(self, id: int):
        super(BaseWorker, self).__init__()

        self.id = id
        self._status: WorkerStatus = WorkerStatus.NOT_STARTED
        self._work: Sequence[T]|None = None
        self._work_index: int = 0

        # Stats
        self.work_execution_times = collections.deque(maxlen=10)

    @property
    def status(self) -> WorkerStatus:
        return self._status
    @property
    def work(self) -> Sequence[T]|None:
        return self._work
    @property
    def work_index(self) -> int:
        return self._work_index

    def prepare(self, work: Sequence[T], start_index: int = 0):
        """Must be called before starting the worker.
        
        Once the worker starts, it will work on the elements of `work`
        starting from `start_index` and the status will be set to `WORKING`.

        When there's no more work to do, the status will be set to `FINISHED_ALL_WORK`.

        If an exception is raised while working, the status will be set to `ABORT_ERROR`
        and the worker will abort.

        If `abort()` is called while working, the status will be set to `ABORT_USER`
        and the worker will abort.
        """
        if not 0 <= start_index < len(work):
            raise ValueError('Invalid start index', start_index)
        if self._status == WorkerStatus.WORKING:
            raise Exception('Can\'t call prepare while working', self.id)

        self._work = work
        self._work_index = start_index
        self.work_execution_times.clear()

    def abort(self):
        """Sets the status to `ABORT_USER` (only if it's `WORKING`)
        and waits for the worker to exit.
        """
        if self._status == WorkerStatus.WORKING:
            self._status = WorkerStatus.ABORT_USER
        
        printed = False
        while self.is_alive():
            if not printed:
                info(f'Waiting for worker {self.id} to exit')
                printed = True

            time.sleep(0.1)

    def run(self):
        if self._work is None:
            raise Exception('prepare() must be called before starting the worker', self.id)

        id_s = str(self.id).zfill(2)
        self._status = WorkerStatus.WORKING
        last_time = time.time()
        while self._status == WorkerStatus.WORKING:
            if len(self._work) <= self._work_index:
                info(f'[w{id_s}] Finished all work')
                self._status = WorkerStatus.FINISHED_ALL_WORK
                break

            try:
                if self._do_work(self._work[self._work_index]):
                    success(f'[w{id_s}] Finished work earlier')
                    self._status = WorkerStatus.ABORT_FINISHED
                    break
            except Exception as e:
                error(f'[w{id_s}] Abort: {e}')
                self._status = WorkerStatus.ABORT_ERROR
                break

            now = time.time()
            self.work_execution_times.append(now - last_time)
            last_time = now
            self._work_index += 1

    def _do_work(self, elem: T) -> bool:
        """Must be implemented by subclasses.
        
        Optionally return `True` to abort and set the status to
        `ABORT_FINISHED` to signal that the worker was able to
        finish earlier. This is used by the `WorkerSession` class.
        """
        raise NotImplementedError()

@dataclasses.dataclass(init=False)
class WorkerSession[T, W: BaseWorker[T]](Serializable):
    """Facilitates the management of multiple workers working on the same work.

    This class is prepared to be stored in a `ObjectsFile` to save the
    progress of the workers.
    """
    work_hash: str
    workers_checkpoints: list[int]

    def __init__(self, work_hash: str, workers_checkpoints: list[int]):
        """The length of `workers_checkpoints` will be the amount of
        workers that are going to be used.

        If you don't have any checkpoints saved and want to use 4 workers,
        pass a list with 4 zeros.

        `work_hash` is optional and only meant to be used by third-party
        scripts to identify if this session corresponds to the work they're doing
        and can resume it from the checkpoints.
        """
        self.work_hash = work_hash
        self.workers_checkpoints = workers_checkpoints

    def run(self, worker_type: Type[W], work: Sequence[T]) -> tuple[WorkerStatus, list[W]]:
        """Prepares & starts the workers to work on the given work,
        starting from the checkpoints saved on this session.
        
        Returns a tuple with the final status and the list of workers.

        The final status will be `ABORT_X` if any worker aborted or
        the user did so through the keyboard interrupt.
        Otherwise, it will be `FINISHED_ALL_WORK` when all workers finished
        doing all the work.
        """
        if len(self.workers_checkpoints) == 0:
            raise Exception('No workers checkpoints loaded')
        if len(work) == 0:
            raise Exception('No work given')
        
        workers_num = len(self.workers_checkpoints)
        # Split work between workers
        work_dic: dict[int, list[T]] = {}
        worker_i = 0
        for e in work:
            work_dic.setdefault(worker_i % workers_num, []).append(e)
            worker_i += 1

        # Create & start workers
        workers: list[W] = []
        debug(f'Begin worker session ({workers_num} workers)')
        for i in range(workers_num):
            worker = worker_type(i)
            workers.append(worker)

            worker.prepare(work_dic[i], self.workers_checkpoints[i])
            worker.start()

        global_status: WorkerStatus|None = None
        last_stats_print = time.time()
        try:
            while 1:
                time.sleep(0.2)
                global_status = None
                work_per_second = 0
                total_work_done = 0

                # Handle stats & worker-initiated aborts
                for w in workers:
                    # Lower statuses have higher priority
                    if global_status is None or w.status < global_status:
                        global_status = w.status

                    total_work_done += w.work_index
                    self.workers_checkpoints[w.id] = w.work_index
                    if len(w.work_execution_times) > 0:
                        average = statistics.mean(w.work_execution_times)
                        work_per_second += 1 / average
                
                # Either a worker aborted (status < 0) or all workers finished all work
                if global_status < 0 or global_status == WorkerStatus.FINISHED_ALL_WORK:
                    break

                # Print stats every 4 seconds & save progress
                if time.time() - last_stats_print >= 4:
                    last_stats_print = time.time()

                    progress = total_work_done / len(work) * 100
                    work_per_second = work_per_second or 0.0001
                    remaining = (len(work) - total_work_done) / work_per_second / 60
                    info(
                        f'[darkgray]Progress: [0]{round(progress)}% '
                        f'[darkgray]Work p/second: [0]{round(work_per_second, 2)} '
                        f'[darkgray]Remaining time: [0]{round(remaining, 1)}m'
                    )
        except KeyboardInterrupt:
            global_status = WorkerStatus.ABORT_USER

        # Signal abort to all workers
        for w in workers:
            w._status = WorkerStatus.ABORT_USER
        # Wait for all workers to exit
        for w in workers:
            info(f'Waiting for w{w.id} to exit')
            w.join()

        return global_status, workers