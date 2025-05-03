# src/downloader.py
# -- ملف يحتوي على كلاس التحميل الرئيسي --

import os
import yt_dlp
import sys
from pathlib import Path
import traceback
import time
import humanize
import contextlib
import re
import logging  # <-- إضافة استيراد logging

from .exceptions import DownloadCancelled
from .logic_utils import clean_filename


class Downloader:
    """Class responsible for downloading and processing video/audio using yt-dlp."""

    def __init__(
        self,
        url,
        save_path,
        format_choice,
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
        self.format_choice = format_choice
        self.is_playlist = is_playlist
        self.playlist_items = playlist_items
        self.selected_items_count = selected_items_count
        self.total_playlist_count = total_playlist_count
        self.ffmpeg_path = ffmpeg_path
        self.cancel_event = cancel_event
        self.status_callback = status_callback
        self.progress_callback = progress_callback
        self.finished_callback = finished_callback

        self._current_processing_playlist_idx_display = 1
        self._last_hook_playlist_index = 0
        self._processed_selected_count = 0
        logging.debug("Downloader initialized.")

    def _check_cancel(self, stage=""):
        """Checks for cancellation request and raises if requested."""
        if self.cancel_event.is_set():
            logging.info(f"Downloader: Cancellation detected {stage}.")
            raise DownloadCancelled(f"Download cancelled {stage}.")

    def _my_hook(self, d):
        """Progress hook for yt-dlp."""
        try:
            self._check_cancel("during progress hook")
        except DownloadCancelled as e:
            raise yt_dlp.utils.DownloadCancelled(str(e)) from e

        status = d.get("status")
        info_dict = d.get("info_dict", {})
        hook_playlist_index = info_dict.get("playlist_index")

        # استخدام logging.debug للخطافات لأنها تتكرر كثيراً
        # logging.debug(f"Downloader Hook: Status='{status}', Playlist Index='{hook_playlist_index}', Data: {d}")

        if (
            self.is_playlist
            and hook_playlist_index is not None
            and hook_playlist_index > self._last_hook_playlist_index
        ):
            logging.debug(
                f"Downloader Hook: Playlist index changed from {self._last_hook_playlist_index} to {hook_playlist_index}"
            )
            self._current_processing_playlist_idx_display = hook_playlist_index
            self._last_hook_playlist_index = hook_playlist_index

        if status == "finished":
            if filepath := info_dict.get("filepath") or d.get("filename"):
                self._update_status_on_finish_or_process(
                    filepath, info_dict, is_final=False
                )
            else:
                logging.debug(
                    "Downloader Hook: Status 'finished' but no filepath found in hook data."
                )
                self.status_callback("Processing...")
            self.progress_callback(1.0)

        elif status == "downloading":
            downloaded_bytes = d.get("downloaded_bytes")
            if downloaded_bytes is not None:
                self._format_and_display_download_status(d, downloaded_bytes)
            else:
                # تسجيل تحذير إذا كانت بيانات التحميل غير متوقعة
                logging.warning(
                    f"Downloader Hook: Status 'downloading' but 'downloaded_bytes' missing. Data: {d}"
                )
                self.status_callback(f"Status: {d.get('status', 'Connecting')}...")

        elif status == "error":
            error_info = d.get("error", "Unknown yt-dlp error")
            logging.error(f"Downloader Hook: yt-dlp reported error: {error_info}")
            self.status_callback("Error during download/processing reported by yt-dlp.")

    def _format_and_display_download_status(self, d, downloaded_bytes):
        """Formats and displays the status message during download."""
    def _format_and_display_download_status(self, d, downloaded_bytes):
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
            self._extracted_from__format_and_display_download_status_14(status_lines)
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
                eta_str = f"{int(round(eta))}s"  # أبسط Shorter
        status_lines.append(f"Speed: {speed_str} | ETA: {eta_str}")

        status_msg = "\n".join(status_lines)
        self.status_callback(status_msg)

    # TODO Rename this here and in `_format_and_display_download_status`
    def _extracted_from__format_and_display_download_status_14(self, status_lines):
        current_absolute_index = self._current_processing_playlist_idx_display
        total_absolute_str = (
            f"of {self.total_playlist_count}"
            if self.total_playlist_count > 0
            else ""
        )
        status_lines.append(f"Video {current_absolute_index} {total_absolute_str}")

        index_in_selection = min(
            self._processed_selected_count + 1, self.selected_items_count
        )
        remaining_in_selection = max(
            0, self.selected_items_count - self._processed_selected_count
        )
        status_lines.append(
            f"Selected: {index_in_selection} of {self.selected_items_count} ({remaining_in_selection} remaining)"
        )
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
            logging.debug(
                f"Downloader: Item finished processing: {display_name} (Processed count: {self._processed_selected_count})"
            )
        else:
            status_msg = f"Processing: {display_name}..."
            logging.debug(
                f"Downloader: Item processing started/intermediate: {display_name}"
            )

        self.status_callback(status_msg)

    def _postprocessor_hook(self, d):
        """Postprocessor hook for yt-dlp."""
        status = d.get("status")
        postprocessor_name = d.get("postprocessor")
        # استخدام logging.debug للخطافات
        logging.debug(
            f"Downloader PP Hook: Status='{status}', PP='{postprocessor_name}', Data: {d.get('info_dict', {}).get('filepath', 'N/A')}"
        )

        if status == "finished":
            info_dict = d.get("info_dict", {})
            final_filepath = info_dict.get("filepath")

            if not final_filepath or not Path(final_filepath).is_file():
                logging.error(
                    f"Downloader PP Hook Error: Final file path '{final_filepath}' not found or missing after PP '{postprocessor_name}'."
                )
                # self.status_callback(f"Error: Postprocessing failed for {postprocessor_name}")
                return

            logging.info(
                f"Downloader PP Hook: Postprocessor '{postprocessor_name}' finished. Final file confirmed at '{final_filepath}'."
            )
            self._update_status_on_finish_or_process(
                final_filepath, info_dict, is_final=True
            )

            # --- Final Renaming Logic ---
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
                logging.info(
                    f"Downloader PP Hook: Attempting rename: '{current_basename}' -> '{target_basename}'"
                )
                try:
                    expected_final_path_obj.rename(new_final_filepath_obj)
                    logging.info(
                        f"Downloader PP Hook: Rename successful: '{new_final_filepath_obj}'"
                    )
                except OSError as e:
                    logging.error(
                        f"Downloader PP Hook: OSError during rename for '{current_basename}': {e}"
                    )
                    self.status_callback(
                        f"Warning: Could not rename '{current_basename}' due to OS error."
                    )
            else:
                logging.debug(
                    f"Downloader PP Hook: Filename '{current_basename}' already correct. No rename needed."
                )

        elif status == "started":
            logging.debug(
                f"Downloader PP Hook: Postprocessor '{postprocessor_name}' started."
            )

    def _build_format_string(self):
        """Builds the complex format string for yt-dlp."""
        output_ext = "mp4"
        postprocessors = []
        final_format_string = None

        logging.debug(
            f"Downloader: Building format string for choice: '{self.format_choice}'"
        )

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
                logging.debug(
                    "Downloader: Selecting best audio for MP3 conversion (FFmpeg found)."
                )
            else:
                # تسجيل تحذير بدلاً من print
                logging.warning(
                    "Downloader: MP3 requested but FFmpeg not found. Downloading best audio format available. Output may not be MP3."
                )
                output_ext = None
            logging.debug(
                f"Downloader: Audio mode selected. Format: '{final_format_string}', Target Ext: {output_ext}"
            )

        else:
            height_limit = None
            if match := re.search(r"\b(\d{3,4})p\b", self.format_choice):
                height_limit = int(match[1])
                logging.debug(f"Downloader: Found height limit: {height_limit}p")
            else:
                logging.warning(
                    f"Downloader: Could not parse height from format choice '{self.format_choice}'. Falling back to default 720p."
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
            logging.debug(
                f"Downloader: Video mode selected. Limit: {height_limit}p, Format: '{final_format_string}', Target Ext: {output_ext}"
            )

        return final_format_string, output_ext, postprocessors

    def _download_core(self):
        """Executes the core download process using yt-dlp."""
        logging.info("Downloader: Starting core download process.")
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
        logging.debug(f"Downloader: Output template: {outtmpl_pattern}")

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
            # 'writethumbnail': True,
            # 'skip_download': True, # Debug only
        }

        if self.ffmpeg_path:
            ydl_opts["ffmpeg_location"] = self.ffmpeg_path
            logging.debug(
                f"Downloader: FFmpeg location set in options: {self.ffmpeg_path}"
            )
        elif core_postprocessors:
            logging.warning(
                "Downloader: FFmpeg needed for postprocessing but not found/set. Process might fail or produce unexpected output."
            )
            self.status_callback(
                "Warning: FFmpeg needed for conversion but not found. Process might fail."
            )

        if self.is_playlist and self.playlist_items:
            ydl_opts["playlist_items"] = self.playlist_items
            logging.debug(
                f"Downloader: Playlist items set in options: {self.playlist_items}"
            )

        if final_format_string:
            ydl_opts["format"] = final_format_string
        elif "format" in ydl_opts:
            # حالة نادرة: إذا لم يتم تحديد صيغة ولم يكن هناك صيغة صوت فقط
            logging.warning(
                "Downloader: No specific format string determined, removing default format key if present."
            )
            del ydl_opts["format"]

        # استخدام logging.debug لطباعة الخيارات لأنها قد تكون طويلة جداً
        logging.debug(f"Downloader: Final yt-dlp options: {ydl_opts}")
        self.status_callback("Starting download...")
        self.progress_callback(0)

        self._check_cancel("right before calling ydl.download()")

        try:
            logging.info("Downloader: Calling ydl.download()...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
            logging.info("Downloader: ydl.download() completed.")
            self._check_cancel("immediately after ydl.download() finished")

        except yt_dlp.utils.DownloadCancelled as e:
            logging.info(f"Downloader: Download cancelled by yt-dlp hook/check: {e}")
            raise DownloadCancelled(str(e)) from e
        except yt_dlp.utils.DownloadError as dl_err:
            error_message = str(dl_err).split("ERROR:")[-1].strip()
            logging.error(
                f"Downloader: yt-dlp DownloadError during download execution: {dl_err}"
            )
            self.status_callback(f"Download Error: {error_message}")
            # لا ترمي خطأ، انتهت العملية (بفشل) Don't raise, operation finished (failed)
        except Exception as e:
            # استخدام logging.exception لتسجيل الخطأ مع تتبع كامل
            logging.exception(
                "Downloader: Unexpected error during yt-dlp download execution."
            )
            self.status_callback(f"Unexpected Error ({type(e).__name__})! Check logs.")
            # لا ترمي خطأ، انتهت العملية (بفشل) Don't raise, operation finished (failed)

    def run(self):
        """Main entry point to run the download process."""
        logging.debug("Downloader: run() method started.")
        try:
            self._download_core()
        except DownloadCancelled as e:
            # تم تسجيل الإلغاء، فقط أبلغ المستخدم Cancellation logged, just inform user
            self.status_callback(str(e))
        except Exception as e:
            # أخطاء فادحة غير متوقعة خارج _download_core Fatal unexpected errors outside _download_core
            logging.exception("Downloader: FATAL UNEXPECTED error in run() method.")
            self.status_callback(
                f"Critical Unexpected Error ({type(e).__name__})! Check logs."
            )
        finally:
            logging.debug(
                "Downloader: Reached finally block, calling finished_callback."
            )
            self.finished_callback()

    # دالة _log_unexpected_error لم تعد ضرورية لأننا نستخدم logging.exception
    # def _log_unexpected_error(self, e, context=""): ... removed ...
