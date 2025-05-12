# src/logic/downloader.py
# -- ملف يحتوي على كلاس التحميل الرئيسي المنسق --
# -- Modified to accept task_id and task-specific cancel_event --
# -- Calls back status/progress with task_id --

import os
import sys
import traceback
import time
import json

# import shutil # No longer needed here
from pathlib import Path
from typing import Callable, Dict, Any, Optional, List, Tuple, Union
import threading

import yt_dlp
from yt_dlp.utils import (
    DownloadCancelled as YtdlpDownloadCancelled,
    DownloadError as YtdlpDownloadError,
    ExtractorError as YtdlpExtractorError,
)

from src.ui.queue_tab import STATUS_COMPLETED

# --- Imports from current package ---
from .exceptions import DownloadCancelled
from .utils import clean_filename, get_temp_dir
from .downloader_constants import *
from .downloader_hooks import ProgressHookHandler, PostprocessorHookHandler
from .downloader_utils import build_format_string, check_cancel, log_unexpected_error


class Downloader:
    """
    ينسق عملية تحميل مهمة واحدة، ويوجهها إلى مجلد مؤقت.
    يستخدم cancel_event خاص بالمهمة ويبلغ الحالة/التقدم مع task_id.
    """

    def __init__(
        self,
        # --- Task Identification ---
        task_id: str,
        # --- Download Parameters ---
        url: str,
        save_path: str,
        format_choice: str,
        is_playlist: bool,
        playlist_items: Optional[str],
        selected_items_count: int,
        total_playlist_count: int,
        ffmpeg_path: Optional[str],
        # --- Task-Specific Control & Callbacks ---
        cancel_event: threading.Event,  # Task-specific cancellation event
        status_callback: Callable[
            [str], None
        ],  # Wrapped callback expecting only message
        progress_callback: Callable[
            [float], None
        ],  # Wrapped callback expecting only value
        finished_callback: Callable[[], None],  # Wrapped callback (often no-op now)
    ):
        self.task_id: str = task_id  # Store task ID
        self.url: str = url
        self.save_path: str = save_path
        self.format_choice: str = format_choice
        self.is_playlist: bool = is_playlist
        self.playlist_items: Optional[str] = playlist_items
        self.selected_items_count: int = selected_items_count
        self.total_playlist_count: int = total_playlist_count
        self.ffmpeg_path: Optional[str] = ffmpeg_path
        self.cancel_event: threading.Event = cancel_event  # Use the passed event
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

        # --- Internal State Tracking (Remains the Same) ---
        self._current_processing_playlist_idx_display: int = 1
        self._last_hook_playlist_index: int = 0
        self._processed_selected_count: int = 0
        self.last_error_message: Optional[str] = None  # Store last error

        # --- Initialize Hooks ---
        # Pass self (the Downloader instance) to hooks so they can access instance variables like cancel_event
        self.progress_handler = ProgressHookHandler(
            downloader=self,  # Pass self
            status_callback=self.status_callback,
            progress_callback=self.progress_callback,
        )
        self.postprocessor_handler = PostprocessorHookHandler(
            downloader=self  # Pass self
        )

        print(f"Downloader instance initialized for task {self.task_id}.")
        if self.temp_dir_path:
            print(
                f"Downloader (Task {self.task_id}): Using temp path: {self.temp_dir_path}"
            )

    def _update_status_on_finish_or_process(
        self, filepath: str, info_dict: Dict[str, Any], is_final: bool = False
    ) -> None:
        """Updates status message and increments processed count."""
        # --- Logic remains the same ---
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
            # Use "Completed: " prefix for the hook to signal final move success
            status_msg = f"{STATUS_COMPLETED}: {display_name}"
        else:
            status_msg = f"{STATUS_PROCESSING_PREFIX}{display_name}..."

        # Send status update via callback
        self.status_callback(status_msg)

        if is_final:
            print(
                f"Downloader Internal Status (Task {self.task_id}): Finalized '{display_name}' (Counter: {self._processed_selected_count})"
            )

    def _download_core(self) -> None:
        """Executes the core download, directing output to the temp directory."""
        # Reset state for this run
        self._current_processing_playlist_idx_display = 1
        self._last_hook_playlist_index = 0
        self._processed_selected_count = 0
        self.last_error_message = None  # Clear last error

        check_cancel(
            self.cancel_event, f"(Task {self.task_id}) before starting download"
        )

        save_path_obj: Path = Path(self.save_path)
        try:
            save_path_obj.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            err_msg = f"Error: Cannot create final save directory: {e}"
            self.status_callback(f"{STATUS_ERROR_PREFIX}{err_msg}")
            self.last_error_message = err_msg
            raise  # Propagate error

        # --- Build yt-dlp options (logic remains the same) ---
        final_format_string, output_ext_hint, core_postprocessors = build_format_string(
            self.format_choice, self.ffmpeg_path
        )

        ydl_opts: Dict[str, Any] = {
            "progress_hooks": [self.progress_handler.hook],
            "postprocessor_hooks": [self.postprocessor_handler.hook],
            "nocheckcertificate": True,
            "ignoreerrors": self.is_playlist,  # Continue playlist even if one item fails
            "merge_output_format": output_ext_hint or "mp4",
            "postprocessors": core_postprocessors,
            "restrictfilenames": False,
            "keepvideo": False,
            "retries": 5,
            "fragment_retries": 5,
            "concurrent_fragment_downloads": 4,
            # Custom user agent?
            # 'http_headers': {'User-Agent': 'Mozilla/5.0 ...'}
        }

        # Set output template to temporary directory
        if self.temp_dir_path and self.temp_dir_path.is_dir():
            # Use a subfolder per task in temp dir to avoid collisions? Maybe overkill if sequential.
            # task_temp_dir = self.temp_dir_path / self.task_id
            # task_temp_dir.mkdir(exist_ok=True)
            # outtmpl_pattern = str(task_temp_dir / "%(title)s.%(ext)s")
            # For simplicity with sequential, just use main temp dir:
            outtmpl_pattern = str(self.temp_dir_path / "%(title)s.%(ext)s")
            print(
                f"Downloader (Task {self.task_id}): Setting output template to temp dir: {outtmpl_pattern}"
            )
        else:
            # Fallback to final path if temp dir fails (less ideal)
            outtmpl_pattern = str(save_path_obj / "%(title)s.%(ext)s")
            print(
                f"Downloader Warning (Task {self.task_id}): Using final path template as temp dir unavailable: {outtmpl_pattern}"
            )
            self.temp_dir_path = None  # Ensure consistency

        ydl_opts["outtmpl"] = outtmpl_pattern

        # Add ffmpeg path if available
        if self.ffmpeg_path:
            ydl_opts["ffmpeg_location"] = self.ffmpeg_path
            # Check ffprobe? (Handled by utils.find_ffmpeg implicitly)
        elif core_postprocessors:
            self.status_callback(STATUS_WARNING_FFMPEG_MISSING)

        # Playlist items selection
        if self.is_playlist and self.playlist_items:
            ydl_opts["playlist_items"] = self.playlist_items
        # Format selection string
        if final_format_string:
            ydl_opts["format"] = final_format_string
        elif "format" in ydl_opts:  # Ensure no default format lingers if not needed
            del ydl_opts["format"]

        print(f"\n--- Final yt-dlp options (Task {self.task_id}) ---")
        print(json.dumps(ydl_opts, indent=2, default=str))
        print("---------------------------------------------\n")

        # --- Start Download ---
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
            # Let the main run() handle DownloadCancelled exception type
            raise DownloadCancelled(
                str(e) or "Download cancelled by yt-dlp hook."
            ) from e
        except (YtdlpDownloadError, YtdlpExtractorError) as dl_err:
            error_message: str = str(dl_err)
            print(f"Downloader yt-dlp Error (Task {self.task_id}): {dl_err}")
            if "ERROR:" in error_message:
                error_message = error_message.split("ERROR:")[-1].strip()
            self.last_error_message = error_message  # Store error for worker
            self.status_callback(f"{STATUS_ERROR_PREFIX}{error_message}")
            # Don't re-raise here, let run() finish, worker checks last_error_message
        except DownloadCancelled:
            # If check_cancel raised it
            raise
        except Exception as e:
            log_unexpected_error(
                e,
                self.status_callback,
                f"during yt-dlp download execution (Task {self.task_id})",
            )
            self.last_error_message = f"Unexpected Error: {type(e).__name__}"
            # Don't re-raise, let run() finish
        finally:
            # Clean up task-specific temp files? Not strictly necessary if using main temp.
            pass

    def run(self) -> None:
        """
        Main entry point for running the download task. Handles exceptions.
        The LogicHandler worker thread calls this method.
        """
        start_time: float = time.time()
        was_cancelled = False

        try:
            self._download_core()  # Execute the download
            check_cancel(
                self.cancel_event,
                f"(Task {self.task_id}) after _download_core completed",
            )
            print(f"Downloader (Task {self.task_id}): _download_core completed.")

            # Set final progress if successful and not cancelled during core execution
            if not self.cancel_event.is_set() and not self.last_error_message:
                # Check if all selected items were processed (relevant for playlists)
                all_processed = (
                    self._processed_selected_count >= self.selected_items_count
                )
                if all_processed:
                    self.progress_callback(1.0)
                    # Final status is set by the last successful hook or worker loop
                    print(
                        f"Downloader (Task {self.task_id}): Run completed successfully."
                    )
                else:
                    # Might happen if ignoreerrors=True and some items failed silently
                    print(
                        f"Downloader Warning (Task {self.task_id}): Run finished, but processed count ({self._processed_selected_count}) < selected count ({self.selected_items_count})."
                    )
                    # Set status to error or warning? Let worker decide based on last_error_message.

        except DownloadCancelled as e:
            was_cancelled = True
            cancel_msg = str(e) or STATUS_DOWNLOAD_CANCELLED
            self.status_callback(cancel_msg)  # Report cancellation status
            print(
                f"Downloader Run (Task {self.task_id}): Caught DownloadCancelled: {e}"
            )
            # No need to set last_error_message, worker knows it was cancelled

        except Exception as e:
            # Should ideally be caught within _download_core, but catch here as fallback
            print(
                f"Downloader Run (Task {self.task_id}): Caught unexpected exception: {type(e).__name__}: {e}"
            )
            if not self.last_error_message:  # Set error if not already set by core
                self.last_error_message = f"Unexpected Error: {type(e).__name__}"
                log_unexpected_error(
                    e, self.status_callback, f"in main run loop (Task {self.task_id})"
                )
                self.status_callback(f"{STATUS_ERROR_PREFIX}{self.last_error_message}")

        finally:
            end_time: float = time.time()
            print(
                f"Downloader (Task {self.task_id}): Reached finally block after {end_time - start_time:.2f} seconds. Cancelled={was_cancelled}, Error='{self.last_error_message}'"
            )
            # Cleanup logic (if any) could go here

            # Call the (often no-op) finished callback passed by LogicHandler
            # The worker loop handles the *real* task completion logic.
            self.finished_callback()
