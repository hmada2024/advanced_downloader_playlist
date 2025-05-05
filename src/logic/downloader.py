# src/logic/downloader.py
# -- ملف يحتوي على كلاس التحميل الرئيسي المنسق --
# -- Simplified run method, move/rename handled in hooks --

import os
import sys
import traceback
import time
import json

# import shutil # <<< إزالة: لم نعد بحاجة إليه هنا
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
from .downloader_constants import *
from .downloader_hooks import ProgressHookHandler, PostprocessorHookHandler
from .downloader_utils import build_format_string, check_cancel, log_unexpected_error


class Downloader:
    """
    ينسق عملية التحميل، ويوجهها إلى مجلد مؤقت. النقل وإعادة التسمية تتم في الخطافات.
    """

    def __init__(
        self,
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
            self.status_callback("Error: Could not create/access temporary directory!")
            print("Downloader Warning: Failed to get temporary directory.")

        # تتبع الحالة الداخلية
        self._current_processing_playlist_idx_display: int = 1
        self._last_hook_playlist_index: int = 0
        self._processed_selected_count: int = 0
        # <<< إزالة: لم نعد بحاجة لتخزين اسم الملف المؤقت أو info_dict هنا >>>
        # self._last_processed_filename_temp: Optional[str] = None
        # self._last_successful_info_dict: Optional[Dict[str, Any]] = None

        # تهيئة الـ Hooks
        self.progress_handler = ProgressHookHandler(
            self, self.status_callback, self.progress_callback
        )
        self.postprocessor_handler = PostprocessorHookHandler(self)

        print("Downloader instance initialized.")
        if self.temp_dir_path:
            print(f"Downloader will use temp path: {self.temp_dir_path}")

    def _update_status_on_finish_or_process(
        self, filepath: str, info_dict: Dict[str, Any], is_final: bool = False
    ) -> None:
        """تحديث رسالة الحالة وزيادة عداد العناصر المكتملة."""
        # --- الكود الأصلي لهذه الدالة يبقى كما هو، لكن بدون تخزين info_dict ---
        base_filename: str = os.path.basename(filepath)
        file_path_obj = Path(filepath)
        file_ext_lower: str = file_path_obj.suffix.lower()
        final_ext_present: bool = file_ext_lower in FINAL_MEDIA_EXTENSIONS

        title: Optional[str] = info_dict.get("title")
        display_name: str = clean_filename(title or base_filename)

        playlist_index: Optional[int] = info_dict.get("playlist_index")
        # if is_final:
        #      # self._last_successful_info_dict = info_dict # Removed storage

        if self.is_playlist and playlist_index is not None and is_final:
            display_name = clean_filename(f"{playlist_index}. {display_name}")
        elif not title:
            display_name = base_filename

        status_msg: str
        if is_final and final_ext_present:
            # <<< هام: زيادة العداد هنا عند اكتمال معالجة الملف بنجاح >>>
            self._processed_selected_count += 1
            status_msg = (
                f"{STATUS_FINISHED_PREFIX}{display_name}"  # Keep this status for UI log
            )
        else:
            status_msg = f"{STATUS_PROCESSING_PREFIX}{display_name}..."

        # لا نرسل رسالة الحالة من هنا إذا كانت final=True، لأن Hook سينقل الملف ويرسل رسالة "Completed"
        if not is_final:
            self.status_callback(status_msg)
        else:
            # Print internal status for debugging
            print(
                f"Downloader Internal Status: {status_msg} (Counter: {self._processed_selected_count})"
            )

    def _download_core(self) -> None:
        """ينفذ التحميل الأساسي، ويوجهه إلى المجلد المؤقت."""
        # --- الكود الأصلي لهذه الدالة يبقى كما هو (يستخدم outtmpl للمجلد المؤقت) ---
        self._current_processing_playlist_idx_display = 1
        self._last_hook_playlist_index = 0
        self._processed_selected_count = 0

        check_cancel(self.cancel_event, "before starting download")

        save_path_obj: Path = Path(self.save_path)
        try:
            save_path_obj.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            self.status_callback(f"Error: Cannot create final save directory: {e}")
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
            print(
                f"Downloader: Setting initial output template to temp dir: {outtmpl_pattern}"
            )
        else:
            outtmpl_pattern = str(save_path_obj / "%(title)s.%(ext)s")
            print(
                f"Downloader Warning: Using final path for output template as temp dir is unavailable: {outtmpl_pattern}"
            )
            self.temp_dir_path = None

        ydl_opts["outtmpl"] = outtmpl_pattern

        if self.ffmpeg_path:
            ydl_opts["ffmpeg_location"] = self.ffmpeg_path
        # ... (check ffprobe) ...
        elif core_postprocessors:
            self.status_callback(STATUS_WARNING_FFMPEG_MISSING)

        if self.is_playlist and self.playlist_items:
            ydl_opts["playlist_items"] = self.playlist_items
        if final_format_string:
            ydl_opts["format"] = final_format_string
        elif "format" in ydl_opts:
            del ydl_opts["format"]

        print("\n--- Final yt-dlp options (Download Core) ---")
        print(json.dumps(ydl_opts, indent=2, default=str))
        print("---------------------------------------------\n")

        self.status_callback(STATUS_STARTING_DOWNLOAD)
        self.progress_callback(0.0)
        check_cancel(self.cancel_event, "right before calling ydl.download()")

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
            check_cancel(self.cancel_event, "immediately after ydl.download() finished")
        except YtdlpDownloadCancelled as e:
            raise DownloadCancelled(
                str(e) or "Download cancelled by yt-dlp hook."
            ) from e
        except (YtdlpDownloadError, YtdlpExtractorError) as dl_err:
            error_message: str = str(dl_err)
            print(f"Downloader yt-dlp Error: {dl_err}")
            if "ERROR:" in error_message:
                error_message = error_message.split("ERROR:")[-1].strip()
            self.status_callback(f"{STATUS_ERROR_PREFIX}{error_message}")
        except DownloadCancelled:
            raise
        except Exception as e:
            log_unexpected_error(
                e, self.status_callback, "during yt-dlp download execution"
            )
            raise

    def run(self) -> None:
        """نقطة الدخول الرئيسية: تنفذ التحميل فقط. النقل يتم في الخطافات."""
        start_time: float = time.time()
        download_exception: Optional[Exception] = None
        was_cancelled = False

        try:
            self._download_core()  # Stage 1: Download to temp directory
            check_cancel(self.cancel_event, "after _download_core completed")
            print("Downloader: _download_core completed without raising exceptions.")

            # --- <<< إزالة: لا يوجد Stage 2 هنا >>> ---

            # <<< تعديل: تعيين التقدم النهائي عند النجاح الكلي >>>
            # Check if cancellation happened *during* _download_core
            if not self.cancel_event.is_set():
                self.progress_callback(1.0)
                # يمكن إرسال رسالة نهائية شاملة هنا إذا أردت،
                # لكن الخطافات ترسل رسائل اكتمال لكل ملف بالفعل.
                # self.status_callback("Playlist download process finished.")

        except DownloadCancelled as e:
            download_exception = e
            was_cancelled = True
            cancel_msg = str(e) or STATUS_DOWNLOAD_CANCELLED
            self.status_callback(cancel_msg)
            print(f"Downloader Run: Caught DownloadCancelled: {e}")
        except Exception as e:
            download_exception = e
            print(
                f"Downloader Run: Caught unexpected exception: {type(e).__name__}: {e}"
            )
            if not isinstance(e, (YtdlpDownloadError, YtdlpExtractorError)):
                log_unexpected_error(e, self.status_callback, "in main run loop")
                self.status_callback(f"Unexpected Error: {type(e).__name__}")

        finally:
            end_time: float = time.time()
            print(
                f"Downloader: Reached finally block after {end_time - start_time:.2f} seconds."
            )
            # لا يوجد تنظيف للمجلد المؤقت هنا تلقائيًا

            print("Downloader: Calling finished_callback.")
            self.finished_callback()  # Always call finished callback
