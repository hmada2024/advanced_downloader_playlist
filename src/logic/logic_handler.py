# src/logic/logic_handler.py
# -- ملف يحتوي على الكلاس المنسق لعمليات المنطق --
# -- MAJOR REWORK: Implements sequential download queue --

import threading
import time
import traceback
import uuid
from collections import deque
from typing import Callable, Dict, Any, Optional, Union

from src.logic.downloader_constants import STATUS_DOWNLOAD_CANCELLED, STATUS_ERROR_PREFIX, STATUS_PROCESSING_PREFIX

# --- Imports from current package (using relative imports) ---
from .info_fetcher import InfoFetcher
from .downloader import Downloader
from .utils import find_ffmpeg
from .exceptions import DownloadCancelled

# Import QueueTab statuses
from ..ui.queue_tab import (
    STATUS_PENDING,
    STATUS_RUNNING,
    STATUS_COMPLETED,
    STATUS_ERROR,
    STATUS_CANCELLED,
    STATUS_CANCELLING,
    STATUS_DOWNLOADING,
    STATUS_PROCESSING,
)

# --- Constants ---
ERROR_OPERATION_IN_PROGRESS = (
    "Error: Fetch Info is already in progress."  # Only for fetch now
)
ERROR_URL_EMPTY = "URL cannot be empty."
ERROR_URL_PATH_REQUIRED = "Error: URL and Save Path are required for download task."
WARNING_FFMPEG_NOT_FOUND = "LogicHandler Warning: FFmpeg not found. Some operations like MP3 conversion might fail."
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


# --- Task Data Structure (using dict for flexibility) ---
# Keys: 'id', 'url', 'save_path', 'format_choice', 'is_playlist',
#       'playlist_items', 'selected_count', 'total_count', 'title',
#       'status', 'progress', 'cancel_event', 'error_message'


class LogicHandler:
    """
    ينسق بين الواجهة الرسومية وعمليات الخلفية (جلب المعلومات وقائمة انتظار التحميل).
    Coordinates between the GUI and background operations (info fetching and download queue).
    يدير قائمة انتظار تحميل تسلسلية وخيوط وطلبات الإلغاء الخاصة بالمهام.
    Manages a sequential download queue, threads, and task-specific cancellation requests.
    """

    def __init__(
        self,
        # --- UI Callbacks (names indicate target) ---
        status_callback_main: Callable[[str], None],  # For general status (bottom bar)
        progress_callback_main: Callable[
            [float], None
        ],  # For general progress (bottom bar - maybe for fetch?)
        finished_callback_main: Callable[[], None],  # For Fetch Info finish signal
        info_success_callback: Callable[
            [Dict[str, Any]], None
        ],  # For Fetch Info success
        info_error_callback: Callable[[str], None],  # For Fetch Info error
        # --- Callbacks specifically for the Queue Tab ---
        queue_add_task_callback: Callable[
            [str, str, str], None
        ],  # task_id, title, status
        queue_update_status_callback: Callable[
            [str, str, str], None
        ],  # task_id, status, details
        queue_update_progress_callback: Callable[[str, float], None],  # task_id, value
        queue_remove_task_callback: Callable[[str], None],  # task_id (optional)
    ):
        """
        Initializes the logic handler with queue management.
        """
        # --- Main UI Callbacks ---
        self.status_callback_main = status_callback_main
        self.progress_callback_main = progress_callback_main
        self.finished_callback_main = (
            finished_callback_main  # Primarily for Fetch Info now
        )
        self.info_success_callback = info_success_callback
        self.info_error_callback = info_error_callback

        # --- Queue UI Callbacks ---
        self.queue_add_task_callback = queue_add_task_callback
        self.queue_update_status_callback = queue_update_status_callback
        self.queue_update_progress_callback = queue_update_progress_callback
        self.queue_remove_task_callback = queue_remove_task_callback  # If needed

        # --- FFmpeg ---
        self.ffmpeg_path: Optional[str] = find_ffmpeg()
        if not self.ffmpeg_path:
            print(WARNING_FFMPEG_NOT_FOUND)
            # self.status_callback_main(WARNING_FFMPEG_NOT_FOUND) # Optional UI feedback

        # --- Queue Management ---
        self.tasks_info: Dict[str, Dict[str, Any]] = (
            {}
        )  # Stores details of all tasks (pending, running, finished)
        self.pending_tasks: deque[str] = deque()  # Queue of task IDs waiting to be run
        self.running_task_id: Optional[str] = (
            None  # ID of the task currently being processed by the worker
        )
        self.queue_lock = (
            threading.Lock()
        )  # Protects access to tasks_info, pending_tasks, running_task_id
        self._stop_worker_event = (
            threading.Event()
        )  # Signal for the worker thread to exit gracefully

        # --- Active Operation Tracking (Primarily for Fetch Info now) ---
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
                # Check if we can run a new task
                if not self.running_task_id and self.pending_tasks:
                    next_task_id = self.pending_tasks.popleft()
                    self.running_task_id = next_task_id
                    task_details = self.tasks_info.get(next_task_id)
                    if task_details:
                        task_details["status"] = STATUS_RUNNING
                        # Notify UI immediately that task is starting
                        self.queue_update_status_callback(
                            next_task_id, STATUS_RUNNING, ""
                        )

            if next_task_id and task_details:
                print(LOG_WORKER_NEXT_TASK.format(task_id=next_task_id))
                downloader_instance = None
                task_final_status = STATUS_ERROR  # Assume error unless proven otherwise
                error_msg = "Unknown error during execution"

                try:
                    # Prepare task-specific cancel event from stored details
                    task_cancel_event = task_details.get("cancel_event")
                    if not isinstance(task_cancel_event, threading.Event):
                        raise ValueError("Invalid cancel_event found for task.")

                    # Create downloader instance
                    downloader_instance = Downloader(
                        task_id=next_task_id,  # Pass task ID
                        url=task_details["url"],
                        save_path=task_details["save_path"],
                        format_choice=task_details["format_choice"],
                        is_playlist=task_details["is_playlist"],
                        playlist_items=task_details["playlist_items"],
                        selected_items_count=task_details["selected_count"],
                        total_playlist_count=task_details["total_count"],
                        ffmpeg_path=self.ffmpeg_path,
                        cancel_event=task_cancel_event,  # Pass task-specific event
                        # --- Pass WRAPPED callbacks ---
                        status_callback=self._get_task_status_updater(next_task_id),
                        progress_callback=self._get_task_progress_updater(next_task_id),
                        finished_callback=lambda: None,  # Finished callback is handled by worker loop
                    )

                    # --- Run the download directly in this worker thread ---
                    # This blocks the worker until the download is done/cancelled/errors out
                    downloader_instance.run()

                    # Check if cancellation was the reason it stopped
                    if task_cancel_event.is_set():
                        task_final_status = STATUS_CANCELLED
                        error_msg = ""
                    else:
                        # If not cancelled, assume success for now (Downloader might have set error status via callback)
                        with self.queue_lock:  # Check final status set by downloader
                            if self.tasks_info[next_task_id]["status"] != STATUS_ERROR:
                                task_final_status = STATUS_COMPLETED
                                error_msg = ""
                            else:
                                # Error status was already set by a callback
                                task_final_status = STATUS_ERROR
                                error_msg = self.tasks_info[next_task_id].get(
                                    "error_message", "Download failed"
                                )

                except DownloadCancelled as dc_e:
                    print(
                        f"Worker caught DownloadCancelled for task {next_task_id}: {dc_e}"
                    )
                    task_final_status = STATUS_CANCELLED
                    error_msg = ""
                except Exception as e:
                    print(f"--- Worker Error Processing Task {next_task_id} ---")
                    traceback.print_exc()
                    print("---------------------------------------------")
                    task_final_status = STATUS_ERROR
                    error_msg = f"{type(e).__name__}: {e}"
                    # Update status immediately in case of crash
                    self._update_task_info(
                        next_task_id, status=task_final_status, error_message=error_msg
                    )
                finally:
                    # --- Task finished (completed, error, or cancelled) ---
                    print(
                        f"Worker finished task {next_task_id} with status: {task_final_status}"
                    )
                    # Update final status and reset running task ID
                    self._update_task_info(
                        next_task_id,
                        status=task_final_status,
                        progress=1.0 if task_final_status == STATUS_COMPLETED else None,
                        error_message=(
                            error_msg if task_final_status == STATUS_ERROR else ""
                        ),
                    )
                    with self.queue_lock:
                        self.running_task_id = None  # Allow next task to be picked up
                        # Optionally, notify UI about the final status again
                        self.queue_update_status_callback(
                            next_task_id,
                            task_final_status,
                            error_msg if task_final_status == STATUS_ERROR else "",
                        )

            else:
                # No task to run, wait a bit
                # print(LOG_WORKER_WAITING) # Can be noisy
                time.sleep(0.5)

        print(LOG_WORKER_STOP)

    # --- Callback Wrappers (to include task_id) ---

    def _get_task_status_updater(self, task_id: str) -> Callable[[str], None]:
        """Returns a status callback function that includes the task_id."""

        def updater(message: str) -> None:
            # Determine status and details from message if possible
            status = STATUS_PROCESSING  # Default
            details = message
            if message.startswith(STATUS_DOWNLOADING):  # e.g., "Downloading (50.1%)"
                status = STATUS_DOWNLOADING
                details = message.split("(")[-1].split(")")[0]  # Extract percentage
            elif message.startswith(STATUS_PROCESSING_PREFIX):
                status = STATUS_PROCESSING
                details = message.split(STATUS_PROCESSING_PREFIX)[-1]
            elif message.startswith(f"{STATUS_COMPLETED}:"):  # Hook uses "Completed: filename"
                status = STATUS_PROCESSING  # Still processing until worker loop marks COMPLETED
                details = message.split(":", 1)[-1].strip()
            elif message.startswith(STATUS_ERROR_PREFIX):
                status = STATUS_ERROR
                details = message.split(STATUS_ERROR_PREFIX)[-1]
            elif message == STATUS_DOWNLOAD_CANCELLED:
                status = STATUS_CANCELLING  # Intermediate state
                details = ""

            # Update internal state and notify Queue UI
            self._update_task_info(
                task_id,
                status=status,
                error_message=details if status == STATUS_ERROR else None,
            )
            self.queue_update_status_callback(task_id, status, details)

        return updater

    def _get_task_progress_updater(self, task_id: str) -> Callable[[float], None]:
        """Returns a progress callback function that includes the task_id."""

        def updater(value: float) -> None:
            # Update internal state and notify Queue UI
            self._update_task_info(task_id, progress=value)
            self.queue_update_progress_callback(task_id, value)

        return updater

    # --- Thread-Safe Task Info Update ---
    def _update_task_info(self, task_id: str, **kwargs) -> None:
        """Safely updates the internal tasks_info dictionary."""
        with self.queue_lock:
            if task_id in self.tasks_info:
                # Only update if status is not already final (unless forced)
                current_status = self.tasks_info[task_id].get("status")
                is_final = current_status in [
                    STATUS_COMPLETED,
                    STATUS_ERROR,
                    STATUS_CANCELLED,
                ]
                if not is_final or kwargs.get("force_update"):
                    self.tasks_info[task_id].update(kwargs)
            # else: # Task might have been removed or cancelled very quickly
            # print(f"LogicHandler Info: Task {task_id} not found for update (might be finished/removed).")

    # --- Public Methods for UI Interaction ---

    def start_info_fetch(self, url: str) -> None:
        """Starts the information fetching process (not queued)."""
        if not url:
            self.info_error_callback(ERROR_URL_EMPTY)
            self.finished_callback_main()  # Signal fetch 'finish' even on input error
            return
        # Check if fetch info is already running
        if self.fetch_info_thread and self.fetch_info_thread.is_alive():
            self.status_callback_main(ERROR_OPERATION_IN_PROGRESS)
            self.finished_callback_main()
            return

        print(LOG_INFO_FETCH_START)
        self.fetch_info_cancel_event.clear()

        fetcher_instance = InfoFetcher(
            url=url,
            cancel_event=self.fetch_info_cancel_event,
            success_callback=self.info_success_callback,
            error_callback=self.info_error_callback,
            status_callback=self.status_callback_main,  # Use main status bar
            progress_callback=self.progress_callback_main,  # Use main progress bar
            finished_callback=self.finished_callback_main,  # Use main finished signal
        )
        self.fetch_info_thread = threading.Thread(
            target=fetcher_instance.run, daemon=True
        )
        self.fetch_info_thread.start()

    def add_download_task(
        self,
        url: str,
        save_path: str,
        format_choice: str,
        is_playlist: bool,
        playlist_items: Optional[str],
        selected_items_count: int,
        total_playlist_count: int,
        title: str,  # Get title from fetched info
    ) -> Optional[str]:
        """Adds a new download task to the queue."""
        if not url or not save_path:
            self.status_callback_main(
                ERROR_URL_PATH_REQUIRED
            )  # Show error on main status
            return None

        task_id = str(uuid.uuid4())  # Generate unique ID
        task_details = {
            "id": task_id,
            "url": url,
            "save_path": save_path,
            "format_choice": format_choice,
            "is_playlist": is_playlist,
            "playlist_items": playlist_items,
            "selected_count": selected_items_count,
            "total_count": total_playlist_count,
            "title": title or "Untitled Download",
            "status": STATUS_PENDING,
            "progress": 0.0,
            "cancel_event": threading.Event(),  # Create a specific cancel event
            "error_message": None,
        }

        with self.queue_lock:
            self.tasks_info[task_id] = task_details
            self.pending_tasks.append(task_id)
            print(
                f"{LOG_DOWNLOAD_TASK_ADD} ID: {task_id}, Title: {task_details['title']}"
            )

        # Notify the QueueTab UI to add the task
        self.queue_add_task_callback(task_id, task_details["title"], STATUS_PENDING)
        self.status_callback_main(
            f"Task '{task_details['title'][:30]}...' added to queue."
        )  # Update main status briefly
        return task_id

    def cancel_task(self, task_id: str) -> None:
        """Requests cancellation of a specific download task."""
        print(LOG_CANCEL_REQUESTED.format(task_id=task_id))
        task_cancelled = False
        with self.queue_lock:
            task_info = self.tasks_info.get(task_id)
            if not task_info:
                print(LOG_NO_TASK_TO_CANCEL.format(task_id=task_id))
                return

            status = task_info["status"]
            cancel_event = task_info.get("cancel_event")

            if status == STATUS_PENDING:
                print(LOG_CANCEL_PENDING.format(task_id=task_id))
                try:
                    # Create a new list/deque without the cancelled task ID
                    new_pending = deque(
                        tid for tid in self.pending_tasks if tid != task_id
                    )
                    self.pending_tasks = new_pending
                except ValueError:
                    print(
                        f"LogicHandler Warning: Task {task_id} not found in pending_tasks deque during cancel."
                    )
                task_info["status"] = STATUS_CANCELLED
                task_cancelled = True
                # Notify UI about cancellation
                self.queue_update_status_callback(task_id, STATUS_CANCELLED, "")

            elif status in [STATUS_RUNNING, STATUS_DOWNLOADING, STATUS_PROCESSING]:
                print(LOG_CANCEL_RUNNING.format(task_id=task_id))
                if isinstance(cancel_event, threading.Event):
                    task_info["status"] = STATUS_CANCELLING  # Intermediate state
                    cancel_event.set()  # Signal the Downloader instance
                    task_cancelled = True
                    # Notify UI
                    self.queue_update_status_callback(task_id, STATUS_CANCELLING, "")
                else:
                    print(
                        f"LogicHandler Error: Invalid cancel_event for running task {task_id}"
                    )
                    task_info["status"] = STATUS_ERROR
                    task_info["error_message"] = "Internal error during cancel"
                    self.queue_update_status_callback(
                        task_id, STATUS_ERROR, "Internal cancel error"
                    )

            elif status in [
                STATUS_COMPLETED,
                STATUS_ERROR,
                STATUS_CANCELLED,
                STATUS_CANCELLING,
            ]:
                print(
                    f"LogicHandler Info: Task {task_id} is already in a final state ({status}). Cannot cancel."
                )
            else:
                print(
                    f"LogicHandler Warning: Unknown status '{status}' for task {task_id} during cancel."
                )

        if task_cancelled:
            self.status_callback_main(
                f"Cancellation requested for task {task_id}."
            )  # Optional main status update

    def cancel_fetch_info(self) -> None:
        """Cancels an ongoing Fetch Info operation."""
        if self.fetch_info_thread and self.fetch_info_thread.is_alive():
            print("LogicHandler: Cancelling Fetch Info operation.")
            self.status_callback_main("Cancellation requested for Fetch Info...")
            self.fetch_info_cancel_event.set()
        else:
            print("LogicHandler: No Fetch Info operation running to cancel.")

    def shutdown(self) -> None:
        """Signals the worker thread to stop and waits for it."""
        print("LogicHandler: Shutdown requested.")
        self._stop_worker_event.set()
        # Cancel any running task during shutdown
        with self.queue_lock:
            if self.running_task_id:
                print(
                    f"LogicHandler: Cancelling running task {self.running_task_id} during shutdown."
                )
                cancel_event = self.tasks_info[self.running_task_id].get("cancel_event")
                if isinstance(cancel_event, threading.Event):
                    cancel_event.set()

        if self.worker_thread and self.worker_thread.is_alive():
            print("LogicHandler: Waiting for worker thread to finish...")
            self.worker_thread.join(timeout=5.0)  # Wait max 5 seconds
            if self.worker_thread.is_alive():
                print("LogicHandler Warning: Worker thread did not stop gracefully.")
        print("LogicHandler: Shutdown complete.")

    def __del__(self):
        # Attempt graceful shutdown when the object is garbage collected
        self.shutdown()
