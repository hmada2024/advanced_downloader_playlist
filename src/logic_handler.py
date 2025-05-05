# src/logic_handler.py
# -- ملف يحتوي على الكلاس المنسق لعمليات المنطق --
# Purpose: Contains the coordinating class for logic operations.

import threading
from typing import Callable, Dict, Any, Optional  # Added typing imports

# Imports from current package
from .info_fetcher import InfoFetcher
from .downloader import Downloader
from .logic_utils import find_ffmpeg
from .exceptions import DownloadCancelled

# --- Constants ---
ERROR_OPERATION_IN_PROGRESS = "Error: Another operation is already in progress."
ERROR_URL_EMPTY = "URL cannot be empty."
ERROR_URL_PATH_REQUIRED = "Error: URL and Save Path are required."
WARNING_FFMPEG_NOT_FOUND = "LogicHandler Warning: FFmpeg not found. Some operations like MP3 conversion might fail."
LOG_INFO_FETCH_START = "LogicHandler: Starting info fetch..."
LOG_DOWNLOAD_START = "LogicHandler: Starting download..."
LOG_CANCEL_REQUESTED = "LogicHandler: Cancellation requested."
LOG_NO_OPERATION_TO_CANCEL = "LogicHandler: No operation running to cancel."


class LogicHandler:
    """
    ينسق بين الواجهة الرسومية وعمليات الخلفية (جلب المعلومات والتحميل).
    Coordinates between the GUI and background operations (info fetching and downloading).
    يدير الخيوط وطلبات الإلغاء.
    Manages threads and cancellation requests.
    """

    def __init__(
        self,
        status_callback: Callable[[str], None],
        progress_callback: Callable[[float], None],
        finished_callback: Callable[[], None],
        info_success_callback: Callable[[Dict[str, Any]], None],
        info_error_callback: Callable[[str], None],
    ):
        """
        تهيئة منسق المنطق.
        Initializes the logic handler.

        Args:
            status_callback (Callable[[str], None]): لتحديث رسالة الحالة في الواجهة.
            progress_callback (Callable[[float], None]): لتحديث شريط التقدم.
            finished_callback (Callable[[], None]): للإعلام بانتهاء المهمة.
            info_success_callback (Callable[[Dict[str, Any]], None]): لنجاح جلب المعلومات مع البيانات.
            info_error_callback (Callable[[str], None]): لفشل جلب المعلومات مع رسالة خطأ.
        """
        self.status_callback: Callable[[str], None] = status_callback
        self.progress_callback: Callable[[float], None] = progress_callback
        self.finished_callback: Callable[[], None] = finished_callback
        self.info_success_callback: Callable[[Dict[str, Any]], None] = (
            info_success_callback
        )
        self.info_error_callback: Callable[[str], None] = info_error_callback

        # --- FFmpeg Handling ---
        # Find FFmpeg path on initialization
        self.ffmpeg_path: Optional[str] = find_ffmpeg()
        if not self.ffmpeg_path:
            print(WARNING_FFMPEG_NOT_FOUND)
            # Optionally call status_callback to inform UI?
            # self.status_callback(WARNING_FFMPEG_NOT_FOUND)

        # --- Threading Management ---
        # Event object to signal cancellation across threads
        self.cancel_event: threading.Event = threading.Event()
        # Reference to the currently active background thread (if any)
        self.current_thread: Optional[threading.Thread] = None

    def _is_operation_running(self) -> bool:
        """
        يتحقق مما إذا كانت هناك عملية (خيط) نشطة حاليًا.
        Checks if an operation (thread) is currently active.

        Returns:
            bool: True إذا كان هناك خيط نشط، وإلا False.
        """
        if self.current_thread and self.current_thread.is_alive():
            # Inform the user if they try to start a new operation while one is running
            self.status_callback(ERROR_OPERATION_IN_PROGRESS)
            return True
        return False

    def start_info_fetch(self, url: str) -> None:
        """
        يبدأ عملية جلب المعلومات في خيط منفصل.
        Starts the information fetching process in a separate thread.

        Args:
            url (str): The URL to fetch information from.
        """
        if not url:
            self.info_error_callback(ERROR_URL_EMPTY)  # Report specific error
            self.finished_callback()  # Ensure finished is called even on input error
            return
        if self._is_operation_running():
            self.finished_callback()  # Also call finished if operation blocked
            return

        print(LOG_INFO_FETCH_START)
        self.cancel_event.clear()  # Reset cancellation flag for the new operation

        # Create an instance of the InfoFetcher class
        fetcher_instance = InfoFetcher(
            url=url,
            cancel_event=self.cancel_event,
            success_callback=self.info_success_callback,
            error_callback=self.info_error_callback,
            status_callback=self.status_callback,
            progress_callback=self.progress_callback,
            finished_callback=self.finished_callback,  # Pass our *own* finished callback
        )
        # Create and start the background thread
        self.current_thread = threading.Thread(target=fetcher_instance.run, daemon=True)
        self.current_thread.start()

    def start_download(
        self,
        url: str,
        save_path: str,
        format_choice: str,
        is_playlist: bool,
        playlist_items: Optional[str],  # Can be None
        selected_items_count: int,
        total_playlist_count: int,
    ) -> None:
        """
        يبدأ عملية التحميل في خيط منفصل.
        Starts the download process in a separate thread.

        Args:
            url (str): The video/playlist URL.
            save_path (str): The directory to save files in.
            format_choice (str): The user's selected format/quality option.
            is_playlist (bool): Whether the download should be treated as a playlist.
            playlist_items (Optional[str]): Comma-separated string of selected item indices, or None.
            selected_items_count (int): Number of items selected for download.
            total_playlist_count (int): Total number of items in the fetched playlist info.
        """
        if not url or not save_path:
            self.status_callback(ERROR_URL_PATH_REQUIRED)
            self.finished_callback()
            return
        if self._is_operation_running():
            self.finished_callback()
            return

        print(
            f"{LOG_DOWNLOAD_START} Playlist: {is_playlist}, "
            f"Selected: {selected_items_count}, Total: {total_playlist_count}, "
            f"Format Choice: '{format_choice}'"
        )
        self.cancel_event.clear()  # Reset cancellation flag

        # Create an instance of the Downloader class
        downloader_instance = Downloader(
            url=url,
            save_path=save_path,
            format_choice=format_choice,
            is_playlist=is_playlist,
            playlist_items=playlist_items,
            selected_items_count=selected_items_count,
            total_playlist_count=total_playlist_count,
            ffmpeg_path=self.ffmpeg_path,
            cancel_event=self.cancel_event,
            status_callback=self.status_callback,
            progress_callback=self.progress_callback,
            finished_callback=self.finished_callback,  # Pass our finished callback
        )
        # Create and start the background thread
        self.current_thread = threading.Thread(
            target=downloader_instance.run, daemon=True
        )
        self.current_thread.start()

    def cancel_operation(self) -> None:
        """
        يطلب إلغاء العملية النشطة حاليًا (إذا وجدت).
        Requests cancellation of the currently active operation (if any).
        Sets the cancel_event, which should be checked by the running task.
        """
        if self.current_thread and self.current_thread.is_alive():
            print(LOG_CANCEL_REQUESTED)
            self.status_callback("Cancellation requested...")  # Give immediate feedback
            self.cancel_event.set()  # Signal the background thread to stop
        else:
            print(LOG_NO_OPERATION_TO_CANCEL)
            # Maybe update status if no operation was running?
            # self.status_callback("No operation running to cancel.")
