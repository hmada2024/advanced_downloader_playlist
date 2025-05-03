# src/logic_handler.py
# -- ملف يحتوي على الكلاس المنسق لعمليات المنطق --

import threading
import logging  # <-- إضافة استيراد logging

from .info_fetcher import InfoFetcher
from .downloader import Downloader
from .logic_utils import find_ffmpeg
from .exceptions import DownloadCancelled


class LogicHandler:
    """
    ينسق بين الواجهة الرسومية وعمليات الخلفية (جلب المعلومات والتحميل).
    """

    def __init__(
        self,
        status_callback,
        progress_callback,
        finished_callback,
        info_success_callback,
        info_error_callback,
    ):
        self.status_callback = status_callback
        self.progress_callback = progress_callback
        self.finished_callback = finished_callback
        self.info_success_callback = info_success_callback
        self.info_error_callback = info_error_callback

        logging.info("LogicHandler: Initializing...")
        # البحث عن FFmpeg عند التهيئة
        self.ffmpeg_path = find_ffmpeg()  # find_ffmpeg سيقوم بالتسجيل بنفسه
        if not self.ffmpeg_path:
            # استخدمنا print هنا سابقاً، نحولها لـ warning
            logging.warning(
                "LogicHandler: FFmpeg not found by find_ffmpeg. Some operations like MP3 conversion might fail."
            )
            # يمكنك أيضاً إرسال تحذير للواجهة إذا أردت
            # self.status_callback("Warning: FFmpeg not found. MP3 conversion might fail.")
        else:
            logging.info(f"LogicHandler: FFmpeg path set to: {self.ffmpeg_path}")

        self.cancel_event = threading.Event()
        self.current_thread = None
        logging.info("LogicHandler: Initialization complete.")

    def _is_operation_running(self):
        """Checks if an operation (thread) is currently active."""
        if self.current_thread and self.current_thread.is_alive():
            logging.warning(
                "LogicHandler: Attempted to start new operation while another is running."
            )
            self.status_callback("Error: Another operation is already in progress.")
            return True
        return False

    def start_info_fetch(self, url):
        """Starts the information fetching process in a separate thread."""
        if not url:
            logging.error("LogicHandler: Info fetch start failed - URL is empty.")
            self.info_error_callback("URL cannot be empty.")
            self.finished_callback()
            return
        if self._is_operation_running():
            return

        logging.info(
            f"LogicHandler: Starting info fetch for URL: {url[:50]}..."
        )  # تسجيل جزء من الرابط
        self.cancel_event.clear()

        fetcher_instance = InfoFetcher(
            url=url,
            cancel_event=self.cancel_event,
            success_callback=self.info_success_callback,
            error_callback=self.info_error_callback,
            status_callback=self.status_callback,
            progress_callback=self.progress_callback,
            finished_callback=self.finished_callback,
        )
        self._extracted_from_start_download_25(
            fetcher_instance, "LogicHandler: Info fetch thread started."
        )

    def start_download(
        self,
        url,
        save_path,
        format_choice,
        is_playlist,
        playlist_items,
        selected_items_count,
        total_playlist_count,
    ):
        """Starts the download process in a separate thread."""
        if not url or not save_path:
            logging.error(
                "LogicHandler: Download start failed - URL or Save Path missing."
            )
            self.status_callback("Error: URL and Save Path are required.")
            self.finished_callback()
            return
        if self._is_operation_running():
            return

        log_msg = (
            f"LogicHandler: Starting download...\n"
            f"  URL: {url[:50]}...\n"
            f"  Save Path: {save_path}\n"
            f"  Format Choice: '{format_choice}'\n"
            f"  Is Playlist: {is_playlist}\n"
            f"  Selected Items: {selected_items_count} (String: {playlist_items})\n"
            f"  Total Playlist Count: {total_playlist_count}"
        )
        logging.info(log_msg)
        self.cancel_event.clear()

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
            finished_callback=self.finished_callback,
        )
        self._extracted_from_start_download_25(
            downloader_instance, "LogicHandler: Download thread started."
        )

    # TODO Rename this here and in `start_info_fetch` and `start_download`
    def _extracted_from_start_download_25(self, arg0, arg1):
        self.current_thread = threading.Thread(target=arg0.run, daemon=True)
        self.current_thread.start()
        logging.info(arg1)

    def cancel_operation(self):
        """Requests cancellation of the currently active operation (if any)."""
        if self.current_thread and self.current_thread.is_alive():
            logging.info("LogicHandler: Cancellation requested by UI.")
            self.status_callback("Cancellation requested...")
            self.cancel_event.set()
        else:
            logging.warning(
                "LogicHandler: Cancellation requested, but no operation was running."
            )
