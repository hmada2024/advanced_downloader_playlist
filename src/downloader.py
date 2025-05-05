# src/downloader.py
# -- ملف يحتوي على كلاس التحميل الرئيسي --
# Purpose: Contains the main Downloader class responsible for the download process.

import os
import yt_dlp
import sys
from pathlib import Path
import traceback
import time
import humanize
import contextlib
import re  # لاستخراج الدقة من خيار الجودة To extract resolution from quality choice

# الاستيرادات من الحزمة الحالية Imports from current package
from .exceptions import DownloadCancelled  # <-- تم التعديل: إزالة الشرطة السفلية
from .logic_utils import clean_filename  # <-- تم التعديل: إزالة الشرطة السفلية


class Downloader:
    """
    كلاس مسؤول عن عملية تحميل الفيديو/الصوت ومعالجته باستخدام yt-dlp.
    Class responsible for downloading and processing video/audio using yt-dlp.
    """

    def __init__(
        self,
        url,
        save_path,
        format_choice,  # الخيار العام من القائمة المنسدلة العلوية General choice from top dropdown
        is_playlist,
        playlist_items,
        selected_items_count,
        total_playlist_count,
        ffmpeg_path,
        cancel_event,
        status_callback,
        progress_callback,
        finished_callback,
    ):
        self.url = url
        self.save_path = save_path
        self.format_choice = format_choice  # تخزين الخيار العام Store general choice
        self.is_playlist = is_playlist
        self.playlist_items = playlist_items
        self.selected_items_count = selected_items_count
        self.total_playlist_count = total_playlist_count
        self.ffmpeg_path = ffmpeg_path
        self.cancel_event = cancel_event
        self.status_callback = status_callback
        self.progress_callback = progress_callback
        self.finished_callback = finished_callback

        # متغيرات داخلية لتتبع حالة تقدم القائمة Internal variables for tracking playlist progress status
        self._current_processing_playlist_idx_display = (
            1  # فهرس العنصر المطلق للعرض Absolute item index for display
        )
        self._last_hook_playlist_index = (
            0  # آخر فهرس تم الإبلاغ عنه من yt-dlp Last index reported by yt-dlp
        )
        self._processed_selected_count = 0  # عداد العناصر التي تمت معالجتها من التحديد Counter for processed selected items

    def _check_cancel(self, stage=""):
        """يتحقق من طلب الإلغاء ويرفع استثناءً إذا تم طلبه."""
        """Checks for cancellation request and raises if requested."""
        if self.cancel_event.is_set():
            raise DownloadCancelled(f"Download cancelled {stage}.")

    def _my_hook(self, d):
        """
        خطاف التقدم لـ yt-dlp، يُستدعى بشكل دوري أثناء التحميل والمعالجة.
        Progress hook for yt-dlp, called periodically during download and processing.
        """
        try:
            self._check_cancel("during progress hook")
        except DownloadCancelled as e:
            raise yt_dlp.utils.DownloadCancelled(str(e)) from e

        status = d.get("status")
        info_dict = d.get("info_dict", {})
        hook_playlist_index = info_dict.get("playlist_index")

        if (
            self.is_playlist
            and hook_playlist_index is not None
            and hook_playlist_index > self._last_hook_playlist_index
        ):
            self._current_processing_playlist_idx_display = hook_playlist_index
            self._last_hook_playlist_index = hook_playlist_index

        if status == "finished":
            if filepath := info_dict.get("filepath") or d.get("filename"):
                self._update_status_on_finish_or_process(
                    filepath, info_dict, is_final=False
                )
            else:
                self.status_callback("Processing...")
            self.progress_callback(1.0)

        elif status == "downloading":
            downloaded_bytes = d.get("downloaded_bytes")
            if downloaded_bytes is not None:
                self._format_and_display_download_status(d, downloaded_bytes)
            else:
                self.status_callback(f"Status: {d.get('status', 'Connecting')}...")

        elif status == "error":
            self.status_callback("Error during download/processing reported by yt-dlp.")
            print(
                f"yt-dlp hook reported error: {d.get('error', 'Unknown yt-dlp error')}"
            )

    def _format_and_display_download_status(self, d, downloaded_bytes):
        """تنسيق وعرض رسالة الحالة أثناء التحميل."""
        """Formats and displays the status message during download."""
        total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate")
        progress = 0.0
        percentage_str = "0.0%"
        if total_bytes and total_bytes > 0:
            progress = max(0.0, min(1.0, downloaded_bytes / total_bytes))
            percentage_str = f"{progress:.1%}"

        self.progress_callback(progress)

        status_lines = []

        if self.is_playlist:
            # <-- تم التعديل: استدعاء الدالة بالاسم الجديد
            self._format_playlist_progress_status(status_lines)
        else:
            status_lines.append("Downloading Video")

        downloaded_size_str = humanize.naturalsize(downloaded_bytes, binary=True)
        total_size_str = (
            humanize.naturalsize(total_bytes, binary=True)
            if total_bytes
            else "Unknown size"
        )
        status_lines.append(
            f"Progress: {percentage_str} ({downloaded_size_str} / {total_size_str})"
        )

        speed = d.get("speed")
        speed_str = (
            f"{humanize.naturalsize(speed, binary=True, gnu=True)}/s"
            if speed
            else "Calculating..."
        )
        eta = d.get("eta")
        eta_str = "Calculating..."
        with contextlib.suppress(TypeError, ValueError):
            if eta is not None and isinstance(eta, (int, float)) and eta >= 0:
                eta_str = f"{int(round(eta))} seconds remaining"
        status_lines.append(f"Speed: {speed_str} | ETA: {eta_str}")

        status_msg = "\n".join(status_lines)
        self.status_callback(status_msg)

    # <-- تم التعديل: إعادة تسمية الدالة هنا
    def _format_playlist_progress_status(self, status_lines):
        """Formats the status lines related to playlist progress."""
        current_absolute_index = self._current_processing_playlist_idx_display
        total_absolute_str = (
            f"out of {self.total_playlist_count} total"
            if self.total_playlist_count > 0
            else ""
        )
        status_lines.append(f"Video {current_absolute_index} {total_absolute_str}")

        index_in_selection = self._processed_selected_count + 1
        index_in_selection = min(index_in_selection, self.selected_items_count)
        remaining_in_selection = max(
            0, self.selected_items_count - self._processed_selected_count
        )
        status_lines.append(
            f"Selected: {index_in_selection} of {self.selected_items_count} ({remaining_in_selection} remaining)"
        )

    def _update_status_on_finish_or_process(self, filepath, info_dict, is_final=False):
        """تحديث رسالة الحالة عند انتهاء تحميل ملف أو معالجته النهائية."""
        """Updates status message when a file finishes downloading or final processing."""
        base_filename = os.path.basename(filepath)
        final_ext_present = any(
            base_filename.lower().endswith(ext)
            for ext in [".mp4", ".mp3", ".mkv", ".webm", ".opus", ".ogg"]
        )

        title = info_dict.get("title")
        display_name = clean_filename(title or base_filename)

        if is_final and final_ext_present:
            status_msg = f"Finished: {display_name}"
            self._processed_selected_count += 1
        else:
            status_msg = f"Processing: {display_name}..."

        self.status_callback(status_msg)

    def _postprocessor_hook(self, d):
        """
        خطاف ما بعد المعالجة لـ yt-dlp، يُستدعى عند بدء وانتهاء عمليات المعالجة (مثل الدمج، تحويل الصوت).
        Postprocessor hook for yt-dlp, called when postprocessing operations start and finish (e.g., merging, audio conversion).
        """
        status = d.get("status")
        postprocessor_name = d.get("postprocessor")
        print(f"Postprocessor Hook: Status='{status}', PP='{postprocessor_name}'")

        if status == "finished":
            info_dict = d.get("info_dict", {})
            final_filepath = info_dict.get("filepath")

            if not final_filepath or not Path(final_filepath).is_file():
                print(
                    f"Postprocessor Error: Final file path '{final_filepath}' not found or missing after postprocessing '{postprocessor_name}'."
                )
                return

            print(
                f"Postprocessor Hook: Final file confirmed at '{final_filepath}'. Proceeding with rename/cleanup."
            )
            self._update_status_on_finish_or_process(
                final_filepath, info_dict, is_final=True
            )

            expected_final_path_obj = Path(final_filepath)
            current_basename = expected_final_path_obj.name
            target_basename = current_basename

            base_title = info_dict.get("title", "Untitled")
            base_ext = expected_final_path_obj.suffix.lstrip(".")
            playlist_index = info_dict.get("playlist_index")

            if self.is_playlist and playlist_index is not None:
                target_basename = f"{playlist_index}. {base_title}.{base_ext}"
            else:
                target_basename = f"{base_title}.{base_ext}"

            target_basename = clean_filename(target_basename)

            if target_basename != current_basename:
                new_final_filepath_obj = expected_final_path_obj.with_name(
                    target_basename
                )
                print(
                    f"Postprocessor: Attempting rename: '{current_basename}' -> '{target_basename}'"
                )
                try:
                    expected_final_path_obj.rename(new_final_filepath_obj)
                    print(
                        f"Postprocessor: Rename successful: '{new_final_filepath_obj}'"
                    )
                except OSError as e:
                    print(
                        f"Postprocessor Error during rename for '{current_basename}': {e}"
                    )
                    self.status_callback(
                        f"Warning: Could not rename '{current_basename}' due to OS error."
                    )
            else:
                print(
                    f"Postprocessor: Filename '{current_basename}' already correct. No rename needed."
                )

        elif status == "started":
            print(f"Postprocessor Hook: '{postprocessor_name}' started.")

    def _build_format_string(self):
        """
        يبني سلسلة الصيغة المعقدة لـ yt-dlp بناءً على اختيار المستخدم العام للجودة.
        Builds the complex format string for yt-dlp based on the user's general quality choice.
        Returns:
            tuple: (final_format_string, output_ext, postprocessors_list)
        """
        output_ext = "mp4"
        postprocessors = []
        final_format_string = None

        print(f"BuildFormat: Received format choice: '{self.format_choice}'")

        if self.format_choice == "Download Audio Only (MP3)":
            final_format_string = "bestaudio/best"
            output_ext = "mp3"
            if self.ffmpeg_path:
                postprocessors.append(
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                )
                print(
                    "BuildFormat: Selecting best audio for MP3 conversion (FFmpeg found)."
                )
            else:
                print(
                    "BuildFormat Warning: MP3 requested but FFmpeg not found. Downloading best audio format available."
                )
                output_ext = None
            print(
                f"BuildFormat: Audio mode. Format: '{final_format_string}', Target Ext: {output_ext}"
            )

        else:
            height_limit = None
            if match := re.search(r"\b(\d{3,4})p\b", self.format_choice):
                height_limit = int(match[1])
                print(f"BuildFormat: Found height limit: {height_limit}p")
            else:
                print(
                    f"BuildFormat Warning: Could not parse height from format choice '{self.format_choice}'. Falling back to default 720p."
                )
                height_limit = 720

            final_format_string = (
                f"bestvideo[height<={height_limit}][ext=mp4]+bestaudio[ext=m4a]/"
                f"bestvideo[height<={height_limit}]+bestaudio/"
                f"best[height<={height_limit}][ext=mp4]/"
                f"best[height<={height_limit}]"
            )
            output_ext = "mp4"
            postprocessors = []
            print(
                f"BuildFormat: Video mode. Limit: {height_limit}p, Format: '{final_format_string}', Target Ext: {output_ext}"
            )

        return final_format_string, output_ext, postprocessors

    def _download_core(self):
        """
        ينفذ عملية التحميل الأساسية باستخدام yt-dlp.
        Executes the core download process using yt-dlp.
        """
        self._current_processing_playlist_idx_display = 1
        self._last_hook_playlist_index = 0
        self._processed_selected_count = 0

        self._check_cancel("before starting download")

        if self.is_playlist:
            outtmpl_pattern = os.path.join(
                self.save_path, "%(playlist_index)s. %(title)s.%(ext)s"
            )
        else:
            outtmpl_pattern = os.path.join(self.save_path, "%(title)s.%(ext)s")

        final_format_string, output_ext_hint, core_postprocessors = (
            self._build_format_string()
        )

        ydl_opts = {
            "progress_hooks": [self._my_hook],
            "postprocessor_hooks": [self._postprocessor_hook],
            "outtmpl": outtmpl_pattern,
            "nocheckcertificate": True,
            "ignoreerrors": self.is_playlist,
            "merge_output_format": "mp4",
            "postprocessors": core_postprocessors,
            "restrictfilenames": False,
            "keepvideo": False,
        }

        if self.ffmpeg_path:
            ydl_opts["ffmpeg_location"] = self.ffmpeg_path
        elif core_postprocessors:
            self.status_callback(
                "Warning: FFmpeg needed for conversion but not found. Process might fail."
            )

        if self.is_playlist and self.playlist_items:
            ydl_opts["playlist_items"] = self.playlist_items

        if final_format_string:
            ydl_opts["format"] = final_format_string
        elif "format" in ydl_opts:
            del ydl_opts["format"]

        print("Final yt-dlp options:", ydl_opts)
        self.status_callback("Starting download...")
        self.progress_callback(0)

        self._check_cancel("right before calling ydl.download()")

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
            self._check_cancel("immediately after ydl.download() finished")

        except yt_dlp.utils.DownloadCancelled as e:
            raise DownloadCancelled(str(e)) from e
        except yt_dlp.utils.DownloadError as dl_err:
            error_message = str(dl_err).split("ERROR:")[-1].strip()
            print(f"Downloader yt-dlp DownloadError: {dl_err}")
            self.status_callback(f"Download Error: {error_message}")
        except Exception as e:
            self._log_unexpected_error(e, "during yt-dlp download execution")

    def run(self):
        """
        نقطة الدخول الرئيسية لتشغيل عملية التحميل.
        Main entry point to run the download process.
        Handles exceptions and ensures the finished_callback is always called.
        """
        try:
            self._download_core()
        except DownloadCancelled as e:
            self.status_callback(str(e))
            print(e)
        except Exception as e:
            self._log_unexpected_error(e, "in main run loop")
        finally:
            print("Downloader: Reached finally block, calling finished_callback.")
            self.finished_callback()

    def _log_unexpected_error(self, e, context=""):
        """يسجل الأخطاء غير المتوقعة."""
        """Logs unexpected errors."""
        print(f"--- UNEXPECTED ERROR ({context}) ---")
        traceback.print_exc()
        print("------------------------------------")
        self.status_callback(
            f"Unexpected Error ({type(e).__name__})! Check logs for details."
        )
        print(f"Unexpected Error during download ({context}): {e}")
