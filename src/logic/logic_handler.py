# src/logic/logic_handler.py
# -- ملف يحتوي على الكلاس المنسق لعمليات المنطق --
# -- Fixed import, using STATUS_COMPLETED from downloader_constants --

import threading
import time
import traceback
import uuid
from collections import deque
from typing import Callable, Dict, Any, Optional, Union

# --- Imports from current package (using relative imports) ---
from .info_fetcher import InfoFetcher
from .downloader import Downloader
from .utils import find_ffmpeg
from .exceptions import DownloadCancelled
# --- Import QueueTab statuses for internal logic ---
from ..ui.queue_tab import (
    STATUS_PENDING,
    STATUS_RUNNING,
    STATUS_COMPLETED,
    STATUS_ERROR,
    STATUS_CANCELLED,
    STATUS_CANCELLING,
    STATUS_DOWNLOADING,
    STATUS_PROCESSING,
    STATUS_PENDING, STATUS_RUNNING, # Removed STATUS_COMPLETED import from here
    STATUS_ERROR, STATUS_CANCELLED, STATUS_CANCELLING,
STATUS_DOWNLOADING, STATUS_PROCESSING
)
# --- Import constants from downloader_constants ---
from .downloader_constants import (
    STATUS_ERROR_PREFIX,
    STATUS_COMPLETED, # <<< استيراد مباشر الآن
    STATUS_DOWNLOAD_CANCELLED,
    # Add other constants if needed, e.g., STATUS_PROCESSING_PREFIX
)


# --- Constants ---
ERROR_OPERATION_IN_PROGRESS = "Error: Fetch Info is already in progress."
ERROR_URL_EMPTY = "URL cannot be empty."
ERROR_URL_PATH_REQUIRED = "Error: URL and Save Path are required for download task."
WARNING_FFMPEG_NOT_FOUND = "LogicHandler Warning: FFmpeg not found."
LOG_INFO_FETCH_START = "LogicHandler: Starting info fetch..."
LOG_DOWNLOAD_TASK_ADD = "LogicHandler: Adding download task to queue..."
LOG_WORKER_START = "LogicHandler: Worker thread started."
LOG_WORKER_STOP = "LogicHandler: Worker thread stopped."
LOG_WORKER_NEXT_TASK = "LogicHandler: Worker processing next task: {task_id}"
LOG_WORKER_WAITING = "LogicHandler: Worker waiting for tasks..."
LOG_CANCEL_REQUESTED = "LogicHandler: Cancellation requested for task: {task_id}"
LOG_CANCEL_PENDING = "LogicHandler: Cancelling pending task: {task_id}"
LOG_CANCEL_RUNNING = "LogicHandler: Signalling running task to cancel: {task_id}"
LOG_NO_TASK_TO_CANCEL = "LogicHandler: Task {task_id} not found or already finished."


class LogicHandler:
    """
    Coordinates between the GUI and background operations (info fetching and download queue).
    Manages a sequential download queue, threads, and task-specific cancellation requests.
    """

    def __init__(
        self,
        status_callback_main: Callable[[str], None],
        progress_callback_main: Callable[[float], None],
        finished_callback_main: Callable[[], None],
        info_success_callback: Callable[[Dict[str, Any]], None],
        info_error_callback: Callable[[str], None],
        queue_callbacks: Dict[str, Callable],
    ):
        """Initializes the logic handler with queue management."""
        self.status_callback_main = status_callback_main
        self.progress_callback_main = progress_callback_main
        self.finished_callback_main = finished_callback_main
        self.info_success_callback = info_success_callback
        self.info_error_callback = info_error_callback

        # --- Queue UI Callbacks ---
        self.queue_add_task_callback = queue_callbacks.get('add')
        self.queue_update_task_display_callback = queue_callbacks.get('update_display')
        self.queue_update_progress_callback = queue_callbacks.get('update_progress')
        self.queue_remove_task_callback = queue_callbacks.get('remove')

        # --- FFmpeg ---
        self.ffmpeg_path: Optional[str] = find_ffmpeg()
        if not self.ffmpeg_path: print(WARNING_FFMPEG_NOT_FOUND)

        # --- Queue Management ---
        self.tasks_info: Dict[str, Dict[str, Any]] = {}
        self.pending_tasks: deque[str] = deque()
        self.running_task_id: Optional[str] = None
        self.queue_lock = threading.Lock()
        self._stop_worker_event = threading.Event()

        # --- Active Operation Tracking ---
        self.fetch_info_cancel_event = threading.Event()
        self.fetch_info_thread: Optional[threading.Thread] = None

        # --- Start the Download Worker Thread ---
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

    # --- Worker Thread Logic ---
    def _worker_loop(self) -> None:
        """The main loop for the sequential download worker thread."""
        print(LOG_WORKER_START)
        while not self._stop_worker_event.is_set():
            next_task_id: Optional[str] = None
            task_details: Optional[Dict[str, Any]] = None

            with self.queue_lock:
                if not self.running_task_id and self.pending_tasks:
                    next_task_id = self.pending_tasks.popleft()
                    self.running_task_id = next_task_id
                    task_details = self.tasks_info.get(next_task_id)
                    if task_details:
                        task_details['status'] = STATUS_RUNNING
                        if self.queue_update_task_display_callback:
                             self.queue_update_task_display_callback(next_task_id, STATUS_RUNNING)

            if next_task_id and task_details:
                print(LOG_WORKER_NEXT_TASK.format(task_id=next_task_id))
                downloader_instance = None
                # <<< استخدام STATUS_COMPLETED المستورد من downloader_constants >>>
                task_final_status: str = STATUS_ERROR # Default to error
                error_msg: str = "Unknown error during execution"

                try:
                    task_cancel_event = task_details.get('cancel_event')
                    if not isinstance(task_cancel_event, threading.Event):
                         raise ValueError("Invalid cancel_event found for task.")

                    downloader_instance = Downloader(
                        task_id=next_task_id, url=task_details['url'], save_path=task_details['save_path'],
                        format_choice=task_details['format_choice'], is_playlist=task_details['is_playlist'],
                        playlist_items=task_details['playlist_items'], selected_items_count=task_details['selected_count'],
                        total_playlist_count=task_details['total_count'], ffmpeg_path=self.ffmpeg_path,
                        cancel_event=task_cancel_event, status_callback=self._get_task_status_updater(next_task_id),
                        progress_callback=self._get_task_progress_updater(next_task_id), finished_callback=lambda: None,
                    )
                    downloader_instance.run()

                    if task_cancel_event.is_set():
                        task_final_status = STATUS_CANCELLED
                        error_msg = ""
                    else:
                        with self.queue_lock:
                             last_error = self.tasks_info[next_task_id].get('error_message')
                             internal_status = self.tasks_info[next_task_id].get('status')
                        if last_error:
                             task_final_status = STATUS_ERROR; error_msg = last_error
                        elif internal_status == STATUS_ERROR:
                             task_final_status = STATUS_ERROR; error_msg = "Download failed (check logs)"
                        else:
                             # <<< استخدام STATUS_COMPLETED المستورد من downloader_constants >>>
                             task_final_status = STATUS_COMPLETED
                             error_msg = ""

                except DownloadCancelled as dc_e:
                    print(f"Worker caught DownloadCancelled for task {next_task_id}: {dc_e}")
                    task_final_status = STATUS_CANCELLED; error_msg = ""
                except Exception as e:
                    print(f"--- Worker Error Processing Task {next_task_id} ---"); traceback.print_exc(); print("---")
                    task_final_status = STATUS_ERROR; error_msg = f"{type(e).__name__}: {e}"
                    self._update_task_info(next_task_id, status=task_final_status, error_message=error_msg)
                finally:
                    print(f"Worker finished task {next_task_id} with status: {task_final_status}")
                    self._update_task_info(next_task_id, status=task_final_status, progress=1.0 if task_final_status == STATUS_COMPLETED else None, error_message=error_msg if task_final_status == STATUS_ERROR else None)
                    with self.queue_lock: self.running_task_id = None
                    if self.queue_update_task_display_callback:
                         # <<< تعديل لعرض رسالة الخطأ بشكل صحيح >>>
                         display_msg = task_final_status if task_final_status != STATUS_ERROR else f"Error: {error_msg}"
                         self.queue_update_task_display_callback(next_task_id, display_msg)
            else:
                time.sleep(0.5)
        print(LOG_WORKER_STOP)

    # --- Callback Wrappers ---
    def _get_task_status_updater(self, task_id: str) -> Callable[[str], None]:
        """Returns a status callback that passes the raw message and updates internal state."""
        def updater(raw_message: str) -> None:
            internal_status = STATUS_PROCESSING # Default
            error_message = None
            # <<< استخدام STATUS_COMPLETED المستورد >>>
            if raw_message.startswith(f"{STATUS_COMPLETED}:"):
                internal_status = STATUS_COMPLETED # Mark as completed internally
            elif raw_message.startswith(STATUS_DOWNLOADING):
                 internal_status = STATUS_DOWNLOADING
            elif raw_message.startswith(STATUS_ERROR_PREFIX):
                 internal_status = STATUS_ERROR
                 error_message = raw_message.split(STATUS_ERROR_PREFIX, 1)[-1]
            elif raw_message == STATUS_DOWNLOAD_CANCELLED:
                internal_status = STATUS_CANCELLING

            # Update internal task info
            # <<< تعديل: لا تقم بتغيير الحالة إلى Completed هنا، العامل هو من يحدد الحالة النهائية >>>
            if internal_status != STATUS_COMPLETED:
                 self._update_task_info(task_id, status=internal_status, error_message=error_message)
            elif error_message: # حالة الخطأ
                 self._update_task_info(task_id, status=STATUS_ERROR, error_message=error_message)
            # else: لا تحدّث الحالة إلى Completed هنا


            # Pass the RAW message to the Queue Tab UI callback
            if self.queue_update_task_display_callback:
                self.queue_update_task_display_callback(task_id, raw_message)

        return updater

    # --- (باقي الدوال في LogicHandler تبقى كما هي من الإصدار السابق) ---
    # _get_task_progress_updater, _update_task_info, start_info_fetch,
    # add_download_task, get_queue_size, get_finished_task_ids,
    # prune_finished_tasks, cancel_task, cancel_fetch_info, shutdown, __del__
    def _get_task_progress_updater(self, task_id: str) -> Callable[[float], None]:
        """Returns a progress callback function that includes the task_id."""
        def updater(value: float) -> None:
            self._update_task_info(task_id, progress=value)
            if self.queue_update_progress_callback:
                self.queue_update_progress_callback(task_id, value)
        return updater

    def _update_task_info(self, task_id: str, **kwargs) -> None:
        """Safely updates the internal tasks_info dictionary."""
        with self.queue_lock:
            if task_id in self.tasks_info:
                # <<< استخدام STATUS_COMPLETED المستورد >>>
                current_status = self.tasks_info[task_id].get('status')
                is_final = current_status in [STATUS_COMPLETED, STATUS_ERROR, STATUS_CANCELLED]
                if not is_final or kwargs.get('force_update') or 'error_message' in kwargs: # Allow updating error msg even if final
                    if 'error_message' in kwargs and kwargs['error_message'] is None and self.tasks_info[task_id].get('error_message'):
                        del kwargs['error_message']
                    self.tasks_info[task_id].update(kwargs)

    def start_info_fetch(self, url: str) -> None:
        """Starts the information fetching process (not queued)."""
        if not url:
            self.info_error_callback(ERROR_URL_EMPTY); self.finished_callback_main(); return
        if self.fetch_info_thread and self.fetch_info_thread.is_alive():
            self.status_callback_main(ERROR_OPERATION_IN_PROGRESS); self.finished_callback_main(); return
        print(LOG_INFO_FETCH_START)
        self.fetch_info_cancel_event.clear()
        fetcher_instance = InfoFetcher(
            url=url, cancel_event=self.fetch_info_cancel_event,
            success_callback=self.info_success_callback, error_callback=self.info_error_callback,
            status_callback=self.status_callback_main, progress_callback=self.progress_callback_main,
            finished_callback=self.finished_callback_main,
        )
        self.fetch_info_thread = threading.Thread(target=fetcher_instance.run, daemon=True); self.fetch_info_thread.start()

    def add_download_task(self, url: str, save_path: str, format_choice: str, is_playlist: bool,
                          playlist_items: Optional[str], selected_items_count: int,
                          total_playlist_count: int, title: str) -> Optional[str]:
        """Adds a new download task to the queue."""
        if not url or not save_path:
            self.status_callback_main(ERROR_URL_PATH_REQUIRED); return None
        task_id = str(uuid.uuid4())
        task_details = {
            'id': task_id, 'url': url, 'save_path': save_path, 'format_choice': format_choice,
            'is_playlist': is_playlist, 'playlist_items': playlist_items,
            'selected_count': selected_items_count, 'total_count': total_playlist_count,
            'title': title or "Untitled Download", 'status': STATUS_PENDING, 'progress': 0.0,
            'cancel_event': threading.Event(), 'error_message': None,
        }
        with self.queue_lock:
            self.tasks_info[task_id] = task_details; self.pending_tasks.append(task_id)
            print(f"{LOG_DOWNLOAD_TASK_ADD} ID: {task_id}, Title: {task_details['title']}")
        if self.queue_add_task_callback: self.queue_add_task_callback(task_id, task_details['title'], STATUS_PENDING)
        return task_id

    def get_queue_size(self) -> int:
        """Returns the current number of tasks (pending + running)."""
        with self.queue_lock: size = len(self.pending_tasks) + (1 if self.running_task_id else 0)
        return size

    def get_finished_task_ids(self) -> list[str]:
        """Returns a list of task IDs that are in a final state."""
        finished_ids = []
        with self.queue_lock:
            finished_ids.extend(
                task_id
                for task_id, info in self.tasks_info.items()
                if info.get('status')
                in [STATUS_COMPLETED, STATUS_ERROR, STATUS_CANCELLED]
            )
        return finished_ids

    def prune_finished_tasks(self, task_ids: list[str]) -> None:
        """Removes finished task data from internal memory."""
        with self.queue_lock:
            count = 0
            for task_id in task_ids:
                if task_id in self.tasks_info:
                    # <<< استخدام STATUS_COMPLETED المستورد >>>
                    if self.tasks_info[task_id].get('status') in [STATUS_COMPLETED, STATUS_ERROR, STATUS_CANCELLED]:
                       try: del self.tasks_info[task_id]; count += 1
                       except KeyError: pass # Handle potential race condition if removed between check and del
                    else: print(f"LogicHandler Warning: Attempted to prune non-finished task {task_id}")
            print(f"LogicHandler: Pruned data for {count} finished tasks.")

    def cancel_task(self, task_id: str) -> None:
        """Requests cancellation of a specific download task."""
        print(LOG_CANCEL_REQUESTED.format(task_id=task_id))
        task_cancelled = False
        with self.queue_lock:
            task_info = self.tasks_info.get(task_id);
            if not task_info: print(LOG_NO_TASK_TO_CANCEL.format(task_id=task_id)); return
            status = task_info['status']
            cancel_event = task_info.get('cancel_event')
            if status == STATUS_PENDING:
                print(LOG_CANCEL_PENDING.format(task_id=task_id))
                try: self.pending_tasks.remove(task_id)
                except ValueError: print(f"LogicHandler Warning: Task {task_id} not in pending deque.")
                task_info['status'] = STATUS_CANCELLED; task_cancelled = True
                if self.queue_update_task_display_callback: self.queue_update_task_display_callback(task_id, STATUS_CANCELLED)
            elif status in [STATUS_RUNNING, STATUS_DOWNLOADING, STATUS_PROCESSING]:
                print(LOG_CANCEL_RUNNING.format(task_id=task_id))
                if isinstance(cancel_event, threading.Event):
                    task_info['status'] = STATUS_CANCELLING; cancel_event.set(); task_cancelled = True
                    if self.queue_update_task_display_callback: self.queue_update_task_display_callback(task_id, STATUS_CANCELLING)
                else:
                    print(f"LogicHandler Error: Invalid cancel_event for running task {task_id}")
                    task_info['status'] = STATUS_ERROR
                    task_info['error_message'] = "Internal cancel error"
                    if self.queue_update_task_display_callback:
                        self.queue_update_task_display_callback(
                            task_id, "Error: Internal cancel error"
                        )
            elif status in [STATUS_COMPLETED, STATUS_ERROR, STATUS_CANCELLED, STATUS_CANCELLING]:
                 print(f"LogicHandler Info: Task {task_id} already {status}.")
            else: print(f"LogicHandler Warning: Unknown status '{status}' for task {task_id} during cancel.")
        if task_cancelled: self.status_callback_main(f"Cancellation requested for task {task_id}.")

    def cancel_fetch_info(self) -> None:
         """Cancels an ongoing Fetch Info operation."""
         if self.fetch_info_thread and self.fetch_info_thread.is_alive():
             print("LogicHandler: Cancelling Fetch Info operation.")
             self.status_callback_main("Cancelling Fetch Info...")
             self.fetch_info_cancel_event.set()
         else: print("LogicHandler: No Fetch Info operation running to cancel.")

    def shutdown(self) -> None:
        """Signals the worker thread to stop and waits for it."""
        print("LogicHandler: Shutdown requested.")
        self._stop_worker_event.set()
        with self.queue_lock:
            if self.running_task_id and self.running_task_id in self.tasks_info: # Check existence
                 print(f"LogicHandler: Cancelling running task {self.running_task_id} during shutdown.")
                 cancel_event = self.tasks_info[self.running_task_id].get('cancel_event')
                 if isinstance(cancel_event, threading.Event): cancel_event.set()
        if self.worker_thread and self.worker_thread.is_alive():
            print("LogicHandler: Waiting for worker thread to finish...")
            self.worker_thread.join(timeout=5.0)
            if self.worker_thread.is_alive(): print("LogicHandler Warning: Worker thread did not stop gracefully.")
        print("LogicHandler: Shutdown complete.")

    def __del__(self): self.shutdown()