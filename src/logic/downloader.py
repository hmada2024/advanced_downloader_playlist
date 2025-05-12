# src/logic/downloader.py
# -- ملف يحتوي على كلاس التحميل الرئيسي المنسق --
# -- Ensure STATUS_COMPLETED from downloader_constants is used --

import os
import sys
import traceback
import time
import json
from pathlib import Path
from typing import Callable, Dict, Any, Optional, List, Tuple, Union
import threading

import yt_dlp
from yt_dlp.utils import (
    DownloadCancelled as YtdlpDownloadCancelled,
    DownloadError as YtdlpDownloadError,
    ExtractorError as YtdlpExtractorError,
)

# --- Imports from current package ---
from .exceptions import DownloadCancelled
from .utils import clean_filename, get_temp_dir

# <<< استيراد محدد للثوابت المستخدمة >>>
from .downloader_constants import (
    STATUS_STARTING_DOWNLOAD,
    STATUS_ERROR_PREFIX,
    STATUS_COMPLETED,
    STATUS_PROCESSING_PREFIX,
    STATUS_WARNING_FFMPEG_MISSING,
    STATUS_DOWNLOAD_CANCELLED,
    FINAL_MEDIA_EXTENSIONS,
    # PP_NAME_*, PP_STATUS_* etc. if needed by hooks
)
from .downloader_hooks import ProgressHookHandler, PostprocessorHookHandler
from .downloader_utils import build_format_string, check_cancel, log_unexpected_error


class Downloader:
    """
    Coordinates a single download task, directs output to a temp folder.
    Uses task-specific cancel_event and reports status/progress with task_id.
    """

    def __init__(
        self,
        task_id: str,
        url: str,
        save_path: str,
        format_choice: str,
        is_playlist: bool,
        playlist_items: Optional[str],
        selected_items_count: int,
        total_playlist_count: int,
        ffmpeg_path: Optional[str],
        cancel_event: threading.Event,
        status_callback: Callable[[str], None],
        progress_callback: Callable[[float], None],
        finished_callback: Callable[[], None],
    ):
        self.task_id: str = task_id
        self.url: str = url
        self.save_path: str = save_path
        self.format_choice: str = format_choice
        self.is_playlist: bool = is_playlist
        self.playlist_items: Optional[str] = playlist_items
        self.selected_items_count: int = selected_items_count
        self.total_playlist_count: int = total_playlist_count
        self.ffmpeg_path: Optional[str] = ffmpeg_path
        self.cancel_event: threading.Event = cancel_event
        self.status_callback: Callable[[str], None] = status_callback
        self.progress_callback: Callable[[float], None] = progress_callback
        self.finished_callback: Callable[[], None] = finished_callback

        self.temp_dir_path: Optional[Path] = get_temp_dir()
        if not self.temp_dir_path:
            self.status_callback(
                f"{STATUS_ERROR_PREFIX}Could not create/access temporary directory!"
            )
            print(
                f"Downloader Warning (Task {self.task_id}): Failed to get temporary directory."
            )

        # --- Internal State Tracking ---
        self._current_processing_playlist_idx_display: int = 1
        self._last_hook_playlist_index: int = 0
        self._processed_selected_count: int = 0
        self.last_error_message: Optional[str] = None

        # --- Initialize Hooks ---
        self.progress_handler = ProgressHookHandler(
            downloader=self,
            status_callback=self.status_callback,
            progress_callback=self.progress_callback,
        )
        self.postprocessor_handler = PostprocessorHookHandler(downloader=self)

        print(f"Downloader instance initialized for task {self.task_id}.")
        if self.temp_dir_path:
            print(
                f"Downloader (Task {self.task_id}): Using temp path: {self.temp_dir_path}"
            )

    def _update_status_on_finish_or_process(
        self, filepath: str, info_dict: Dict[str, Any], is_final: bool = False
    ) -> None:
        """Updates status message and increments processed count."""
        base_filename: str = os.path.basename(filepath)
        file_path_obj = Path(filepath)
        file_ext_lower: str = file_path_obj.suffix.lower()
        final_ext_present: bool = file_ext_lower in FINAL_MEDIA_EXTENSIONS

        title: Optional[str] = info_dict.get("title")
        display_name: str = clean_filename(title or base_filename)
        playlist_index: Optional[int] = info_dict.get("playlist_index")

        if self.is_playlist and playlist_index is not None and is_final:
            display_name = clean_filename(f"{playlist_index}. {display_name}")
        elif not title:
            display_name = base_filename

        status_msg: str
        if is_final and final_ext_present:
            self._processed_selected_count += 1
            # <<< استخدام الثابت الصحيح من downloader_constants >>>
            status_msg = f"{STATUS_COMPLETED}: {display_name}"
        else:
            status_msg = f"{STATUS_PROCESSING_PREFIX}{display_name}..."

        self.status_callback(status_msg)
        if is_final:
            print(
                f"Downloader Internal Status (Task {self.task_id}): Finalized '{display_name}' (Counter: {self._processed_selected_count})"
            )

    # --- (باقي الدوال _download_core و run تبقى كما هي من الإصدار السابق) ---
    def _download_core(self) -> None:
        """Executes the core download, directing output to the temp directory."""
        self._current_processing_playlist_idx_display = 1
        self._last_hook_playlist_index = 0
        self._processed_selected_count = 0
        self.last_error_message = None
        check_cancel(
            self.cancel_event, f"(Task {self.task_id}) before starting download"
        )
        save_path_obj: Path = Path(self.save_path)
        try:
            save_path_obj.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            err_msg = f"Cannot create final save directory: {e}"
            self.status_callback(f"{STATUS_ERROR_PREFIX}{err_msg}")
            self.last_error_message = err_msg
            raise
        final_format_string, output_ext_hint, core_postprocessors = build_format_string(
            self.format_choice, self.ffmpeg_path
        )
        ydl_opts: Dict[str, Any] = {
            "progress_hooks": [self.progress_handler.hook],
            "postprocessor_hooks": [self.postprocessor_handler.hook],
            "nocheckcertificate": True,
            "ignoreerrors": self.is_playlist,
            "merge_output_format": output_ext_hint or "mp4",
            "postprocessors": core_postprocessors,
            "restrictfilenames": False,
            "keepvideo": False,
            "retries": 5,
            "fragment_retries": 5,
            "concurrent_fragment_downloads": 4,
        }
        if self.temp_dir_path and self.temp_dir_path.is_dir():
            outtmpl_pattern = str(self.temp_dir_path / "%(title)s.%(ext)s")
        else:
            outtmpl_pattern = str(save_path_obj / "%(title)s.%(ext)s")
            print(
                f"Downloader Warning (Task {self.task_id}): Using final path template."
            )
            self.temp_dir_path = None
        ydl_opts["outtmpl"] = outtmpl_pattern
        if self.ffmpeg_path:
            ydl_opts["ffmpeg_location"] = self.ffmpeg_path
        elif core_postprocessors:
            self.status_callback(STATUS_WARNING_FFMPEG_MISSING)
        if self.is_playlist and self.playlist_items:
            ydl_opts["playlist_items"] = self.playlist_items
        if final_format_string:
            ydl_opts["format"] = final_format_string
        elif "format" in ydl_opts:
            del ydl_opts["format"]
        print(f"\n--- Final yt-dlp options (Task {self.task_id}) ---")
        print(json.dumps(ydl_opts, indent=2, default=str))
        print("---\n")
        self.status_callback(STATUS_STARTING_DOWNLOAD)
        self.progress_callback(0.0)
        check_cancel(
            self.cancel_event,
            f"(Task {self.task_id}) right before calling ydl.download()",
        )
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
            check_cancel(
                self.cancel_event,
                f"(Task {self.task_id}) immediately after ydl.download() finished",
            )
        except YtdlpDownloadCancelled as e:
            raise DownloadCancelled(str(e) or "Download cancelled by hook.") from e
        except (YtdlpDownloadError, YtdlpExtractorError) as dl_err:
            error_message = str(dl_err)
            print(f"Downloader yt-dlp Error (Task {self.task_id}): {dl_err}")
            if "ERROR:" in error_message:
                error_message = error_message.split("ERROR:")[-1].strip()
            self.last_error_message = error_message
            self.status_callback(f"{STATUS_ERROR_PREFIX}{error_message}")
        except DownloadCancelled:
            raise
        except Exception as e:
            log_unexpected_error(
                e,
                self.status_callback,
                f"during yt-dlp download execution (Task {self.task_id})",
            )
            self.last_error_message = f"Unexpected Error: {type(e).__name__}"

    def run(self) -> None:
        """Main entry point for running the download task."""
        start_time = time.time()
        was_cancelled = False
        try:
            self._download_core()
            check_cancel(
                self.cancel_event,
                f"(Task {self.task_id}) after _download_core completed",
            )
            print(f"Downloader (Task {self.task_id}): _download_core completed.")
            if not self.cancel_event.is_set() and not self.last_error_message:
                all_processed = (
                    self._processed_selected_count >= self.selected_items_count
                )
                if all_processed:
                    self.progress_callback(1.0)
                    print(
                        f"Downloader (Task {self.task_id}): Run completed successfully."
                    )
                else:
                    print(
                        f"Downloader Warning (Task {self.task_id}): Processed {self._processed_selected_count}/{self.selected_items_count} items."
                    )
        except DownloadCancelled as e:
            was_cancelled = True
            cancel_msg = str(e) or STATUS_DOWNLOAD_CANCELLED
            self.status_callback(cancel_msg)
            print(
                f"Downloader Run (Task {self.task_id}): Caught DownloadCancelled: {e}"
            )
        except Exception as e:
            print(
                f"Downloader Run (Task {self.task_id}): Caught unexpected exception: {type(e).__name__}: {e}"
            )
            if not self.last_error_message:
                self.last_error_message = f"Unexpected Error: {type(e).__name__}"
                log_unexpected_error(
                    e, self.status_callback, f"in main run loop (Task {self.task_id})"
                )
                self.status_callback(f"{STATUS_ERROR_PREFIX}{self.last_error_message}")
        finally:
            end_time = time.time()
            print(
                f"Downloader (Task {self.task_id}): Reached finally block after {end_time - start_time:.2f}s. Cancelled={was_cancelled}, Error='{self.last_error_message}'"
            )
            self.finished_callback()
