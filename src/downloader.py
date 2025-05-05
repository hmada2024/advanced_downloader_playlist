# src/downloader.py
# -- ملف يحتوي على كلاس التحميل الرئيسي --
# Purpose: Contains the main Downloader class responsible for the download process.

import os
import sys
import traceback
import time
import humanize
import contextlib
import re
import json  # For pretty printing options
from pathlib import Path
from typing import (
    Callable,
    Dict,
    Any,
    Optional,
    List,
    Tuple,
    Union,
)  # Added typing imports
import threading  # For Event type hinting if needed, though Any is often simpler

import yt_dlp  # Import the library
from yt_dlp.utils import (  # Import specific exceptions/utils
    DownloadCancelled as YtdlpDownloadCancelled,
    DownloadError as YtdlpDownloadError,
    ExtractorError as YtdlpExtractorError,
)

# Imports from current package
from .exceptions import DownloadCancelled  # Our custom exception
from .logic_utils import clean_filename

# --- Constants ---
# Status Messages
STATUS_STARTING_DOWNLOAD = "Starting download..."
STATUS_CONNECTING = "Connecting..."
STATUS_PROCESSING = "Processing..."
STATUS_PROCESSING_FILE = "Processing downloaded file..."
STATUS_FINISHED_PREFIX = "Finished: "
STATUS_PROCESSING_PREFIX = "Processing: "
STATUS_ERROR_PREFIX = "Download Error: "
# *** FIX 1: Renamed constant to a valid identifier ***
STATUS_ERROR_YT_DLP = "Error during download/processing reported by yt-dlp."
STATUS_WARNING_FFMPEG_MISSING = "Warning: FFmpeg needed for conversion but not found. Process might fail or download original format."
STATUS_WARNING_FFPROBE_MISSING = (
    "Warning: ffprobe.exe might be missing. Some features may not work."
)
STATUS_RENAME_FAILED_WARNING = "Warning: Could not rename '{filename}'. Error: {error}"
STATUS_ORGANIZE_FILES = "جاري تنظيم الملفات النهائية..."  # Organizing final files...
STATUS_UNEXPECTED_ERROR = (
    "Unexpected Error ({error_type})! Check logs/console for details."
)

# Postprocessor Names (match yt-dlp internal names)
PP_NAME_MERGER = "FFmpegMerger"
PP_NAME_EXTRACT_AUDIO = "FFmpegExtractAudio"
PP_NAME_CONVERT_VIDEO = "FFmpegVideoConvertor"
PP_NAME_MOVE_FILES = "MoveFiles"  # Internal yt-dlp postprocessor

# Postprocessor Status Messages (Arabic versions from Phase 2)
PP_STATUS_MERGING = "جاري دمج الفيديو والصوت..."  # Merging video and audio...
PP_STATUS_CONVERTING_MP3 = "جاري التحويل إلى MP3..."  # Converting to MP3...
PP_STATUS_EXTRACTING_AUDIO = (
    "جاري استخراج الصوت ({codec})..."  # Extracting audio ({codec})...
)
PP_STATUS_CONVERTING_VIDEO = "جاري تحويل صيغة الفيديو..."  # Converting video format...
PP_STATUS_PROCESSING_GENERIC_PP = (
    "جاري المعالجة بواسطة {pp_name}..."  # Processing via {pp_name}...
)
# *** FIX 3: Ensure constant is defined and used correctly ***
STATUS_FINAL_PROCESSING = (
    "جاري المعالجة النهائية..."  # Final processing... (Defined correctly here)
)

# Default fallback filename if cleaning results in empty string
DEFAULT_CLEANED_FILENAME = "downloaded_file"

# Common video/audio extensions for status checks
FINAL_MEDIA_EXTENSIONS = {
    ".mp4",
    ".mp3",
    ".mkv",
    ".webm",
    ".opus",
    ".ogg",
    ".m4a",
    ".flv",
    ".avi",
    ".wav",
}


class Downloader:
    """
    كلاس مسؤول عن عملية تحميل الفيديو/الصوت ومعالجته باستخدام yt-dlp.
    Class responsible for downloading and processing video/audio using yt-dlp.
    """

    def __init__(
        self,
        url: str,
        save_path: str,
        format_choice: str,
        is_playlist: bool,
        playlist_items: Optional[str],  # Comma-separated indices or None
        selected_items_count: int,
        total_playlist_count: int,
        ffmpeg_path: Optional[str],
        cancel_event: Any,  # Use Any or threading.Event
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
        self.cancel_event = cancel_event  # Type hint: Any or threading.Event
        self.status_callback: Callable[[str], None] = status_callback
        self.progress_callback: Callable[[float], None] = progress_callback
        self.finished_callback: Callable[[], None] = finished_callback

        # Internal state for playlist progress tracking
        self._current_processing_playlist_idx_display: int = 1
        self._last_hook_playlist_index: int = 0
        self._processed_selected_count: int = 0

    def _check_cancel(self, stage: str = "") -> None:
        """Checks for cancellation request and raises if requested."""
        if self.cancel_event.is_set():
            raise DownloadCancelled(f"Download cancelled {stage}.")

    def _my_hook(self, d: Dict[str, Any]) -> None:
        """
        Progress hook for yt-dlp, called periodically during download and processing.
        Args:
            d (Dict[str, Any]): The dictionary passed by yt-dlp containing status information.
        Raises:
            YtdlpDownloadCancelled: To signal cancellation back to yt-dlp if our event is set.
        """
        try:
            self._check_cancel("during progress hook")
        except DownloadCancelled as e:
            raise YtdlpDownloadCancelled(str(e)) from e

        status: Optional[str] = d.get("status")
        info_dict: Dict[str, Any] = d.get("info_dict", {})
        hook_playlist_index: Optional[int] = info_dict.get("playlist_index")

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
                self.status_callback(STATUS_PROCESSING_FILE)
            self.progress_callback(1.0)

        elif status == "downloading":
            downloaded_bytes: Optional[int] = d.get("downloaded_bytes")
            if downloaded_bytes is not None:
                self._format_and_display_download_status(d, downloaded_bytes)
            else:
                self.status_callback(STATUS_CONNECTING)

        elif status == "error":
            # *** FIX 2: Use the corrected constant name ***
            self.status_callback(STATUS_ERROR_YT_DLP)
            print(
                f"yt-dlp hook reported error: {d.get('error', 'Unknown yt-dlp error')}"
            )

    def _format_and_display_download_status(
        self, d: Dict[str, Any], downloaded_bytes: int
    ) -> None:
        """Formats and displays the status message during download."""
        total_bytes: Optional[int] = d.get("total_bytes") or d.get(
            "total_bytes_estimate"
        )
        progress: float = 0.0
        percentage_str: str = "0.0%"
        if total_bytes and total_bytes > 0:
            progress = max(0.0, min(1.0, downloaded_bytes / total_bytes))
            percentage_str = f"{progress:.1%}"

        self.progress_callback(progress)

        status_lines: List[str] = []

        if self.is_playlist:
            self._format_playlist_progress_status(status_lines)
        else:
            status_lines.append("Downloading Video")

        downloaded_size_str: str = humanize.naturalsize(downloaded_bytes, binary=True)
        total_size_str: str = (
            humanize.naturalsize(total_bytes, binary=True)
            if total_bytes
            else "Unknown size"
        )
        status_lines.append(
            f"Progress: {percentage_str} ({downloaded_size_str} / {total_size_str})"
        )

        speed: Optional[float] = d.get("speed")
        speed_str: str = (
            f"{humanize.naturalsize(speed, binary=True, gnu=True)}/s"
            if speed
            else "Calculating..."
        )
        eta: Optional[Union[int, float]] = d.get("eta")
        eta_str: str = "Calculating..."
        with contextlib.suppress(TypeError, ValueError):
            if eta is not None and isinstance(eta, (int, float)) and eta >= 0:
                eta_str = f"{int(round(eta))} seconds remaining"

        status_lines.append(f"Speed: {speed_str} | ETA: {eta_str}")

        status_msg: str = "\n".join(status_lines)
        self.status_callback(status_msg)

    def _format_playlist_progress_status(self, status_lines: List[str]) -> None:
        """Formats the status lines related to playlist progress."""
        current_absolute_index: int = self._current_processing_playlist_idx_display
        total_absolute_str: str = (
            f"out of {self.total_playlist_count} total"
            if self.total_playlist_count > 0
            else ""
        )
        status_lines.append(f"Video {current_absolute_index} {total_absolute_str}")

        index_in_selection: int = self._processed_selected_count + 1
        index_in_selection = min(index_in_selection, self.selected_items_count)
        remaining_in_selection: int = max(
            0, self.selected_items_count - self._processed_selected_count
        )
        status_lines.append(
            f"Selected: {index_in_selection} of {self.selected_items_count} ({remaining_in_selection} remaining)"
        )

    def _update_status_on_finish_or_process(
        self, filepath: str, info_dict: Dict[str, Any], is_final: bool = False
    ) -> None:
        """Updates status message when a file finishes downloading or final processing."""
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
            status_msg = f"{STATUS_FINISHED_PREFIX}{display_name}"
        else:
            status_msg = f"{STATUS_PROCESSING_PREFIX}{display_name}..."

        self.status_callback(status_msg)

    def _postprocessor_hook(self, d: Dict[str, Any]) -> None:
        """Postprocessor hook for yt-dlp. Called for events during postprocessing."""
        status: Optional[str] = d.get("status")
        postprocessor_name: Optional[str] = d.get("postprocessor")
        info_dict: Dict[str, Any] = d.get("info_dict", {})

        if status == "started":
            print(f"Postprocessor Hook: '{postprocessor_name}' started.")
            # *** FIX 3: Ensure constant STATUS_FINAL_PROCESSING is used correctly ***
            status_message: str = STATUS_FINAL_PROCESSING  # Default message

            if postprocessor_name == PP_NAME_MERGER:
                status_message = PP_STATUS_MERGING
            elif postprocessor_name == PP_NAME_EXTRACT_AUDIO:
                target_codec: str = "audio"
                pp_args: Dict[str, Any] = info_dict.get("postprocessor_args", {})
                if isinstance(pp_args, dict):
                    target_codec = pp_args.get("preferredcodec", target_codec)

                if target_codec == "mp3":
                    status_message = PP_STATUS_CONVERTING_MP3
                else:
                    status_message = PP_STATUS_EXTRACTING_AUDIO.format(
                        codec=target_codec
                    )
            elif postprocessor_name == PP_NAME_CONVERT_VIDEO:
                status_message = PP_STATUS_CONVERTING_VIDEO
            elif postprocessor_name == PP_NAME_MOVE_FILES:
                status_message = STATUS_ORGANIZE_FILES
            elif postprocessor_name:
                status_message = PP_STATUS_PROCESSING_GENERIC_PP.format(
                    pp_name=postprocessor_name
                )

            self.status_callback(status_message)

        elif status == "finished":
            final_filepath: Optional[str] = info_dict.get("filepath")
            print(
                f"Postprocessor Hook: Status='{status}', PP='{postprocessor_name}', Final Path='{final_filepath}'"
            )

            if not final_filepath or not Path(final_filepath).is_file():
                print(
                    f"Postprocessor Error: Final file path '{final_filepath}' not found after '{postprocessor_name}'."
                )
                return

            print(
                f"Postprocessor Hook: Final file confirmed at '{final_filepath}'. Updating status/rename."
            )
            self._update_status_on_finish_or_process(
                final_filepath, info_dict, is_final=True
            )

            # --- Final Renaming Logic ---
            expected_final_path_obj: Path = Path(final_filepath)
            current_basename: str = expected_final_path_obj.name

            base_title: str = info_dict.get("title", "Untitled")
            base_ext: str = expected_final_path_obj.suffix
            playlist_index: Optional[int] = info_dict.get("playlist_index")

            target_basename_no_ext: str
            if self.is_playlist and playlist_index is not None:
                target_basename_no_ext = f"{playlist_index}. {base_title}"
            else:
                target_basename_no_ext = base_title

            cleaned_target_basename_no_ext: str = clean_filename(target_basename_no_ext)
            target_basename: str = f"{cleaned_target_basename_no_ext}{base_ext}"

            if target_basename != current_basename:
                new_final_filepath_obj: Path = expected_final_path_obj.with_name(
                    target_basename
                )
                print(
                    f"Postprocessor: Attempting rename: '{current_basename}' -> '{target_basename}'"
                )
                try:
                    time.sleep(0.2)
                    expected_final_path_obj.rename(new_final_filepath_obj)
                    print(
                        f"Postprocessor: Rename successful: '{new_final_filepath_obj}'"
                    )
                except OSError as e:
                    print(f"Postprocessor Error during rename: {e}")
                    self.status_callback(
                        STATUS_RENAME_FAILED_WARNING.format(
                            filename=current_basename, error=e
                        )
                    )
            else:
                print(
                    f"Postprocessor: Filename '{current_basename}' already correct. No rename needed."
                )

    def _build_format_string(
        self,
    ) -> Tuple[Optional[str], Optional[str], List[Dict[str, Any]]]:
        """Builds the complex format string for yt-dlp based on the user's quality choice."""
        output_ext_hint: Optional[str] = "mp4"
        postprocessors: List[Dict[str, Any]] = []
        final_format_string: Optional[str] = None

        print(f"BuildFormat: Received format choice: '{self.format_choice}'")

        if self.format_choice == "Download Audio Only (MP3)":
            final_format_string = "bestaudio[ext=opus]/bestaudio[ext=m4a]/ba/best"
            output_ext_hint = "mp3"
            if self.ffmpeg_path:
                postprocessors.append(
                    {
                        "key": PP_NAME_EXTRACT_AUDIO,
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                )
                print(
                    "BuildFormat: Selecting best audio for MP3 conversion (FFmpeg found)."
                )
            else:
                print(f"BuildFormat Warning: {STATUS_WARNING_FFMPEG_MISSING}")
                output_ext_hint = None
            print(
                f"BuildFormat: Audio mode. Format: '{final_format_string}', Target Ext Hint: {output_ext_hint}"
            )

        else:
            height_limit: Optional[int] = None
            # *** FIX 4: Apply Sourcery suggestions for re.search and group access ***
            if match := re.search(r"\b(\d{3,4})p\b", self.format_choice):
                try:
                    # Use match[1] instead of match.group(1)
                    height_limit = int(match[1])
                    print(f"BuildFormat: Found height limit: {height_limit}p")
                except (ValueError, IndexError):
                    print(
                        f"BuildFormat Warning: Could not parse height from match object '{match}'."
                    )
                    height_limit = None  # Treat as if no match found

            if not height_limit:
                print(
                    f"BuildFormat Info: Could not parse specific height from '{self.format_choice}'. Using best available."
                )

            format_parts: List[str] = [
                "bv[ext=mp4]+ba[ext=m4a]/b[ext=mp4]",
                "bv[ext=webm]+ba[ext=opus]/b[ext=webm]",
                "bv+ba/b",
            ]

            if height_limit:
                height_filter = f"[height<={height_limit}]"
                format_parts = [
                    f"bv{height_filter}[ext=mp4]+ba[ext=m4a]/b{height_filter}[ext=mp4]",
                    f"bv{height_filter}[ext=webm]+ba[ext=opus]/b{height_filter}[ext=webm]",
                    f"bv{height_filter}+ba/b{height_filter}",
                    f"b{height_filter}[ext=mp4]",
                    f"b{height_filter}[ext=webm]",
                    f"b{height_filter}",
                ]
            else:
                format_parts.extend(["b[ext=mp4]", "b[ext=webm]", "b"])

            final_format_string = "/".join(format_parts)
            output_ext_hint = "mp4"
            postprocessors = []
            print(
                f"BuildFormat: Video mode. Limit: {height_limit or 'None'}p, Format: '{final_format_string}', Target Ext Hint: {output_ext_hint}"
            )

        return final_format_string, output_ext_hint, postprocessors

    def _download_core(self) -> None:
        """Executes the core download process using yt-dlp."""
        self._current_processing_playlist_idx_display = 1
        self._last_hook_playlist_index = 0
        self._processed_selected_count = 0

        self._check_cancel("before starting download")

        save_path_obj: Path = Path(self.save_path)
        try:
            save_path_obj.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print(f"Error creating save directory '{self.save_path}': {e}")
            self.status_callback(f"Error: Cannot create save directory: {e}")
            raise

        outtmpl_pattern: str = str(save_path_obj / "%(title)s.%(ext)s")

        final_format_string, output_ext_hint, core_postprocessors = (
            self._build_format_string()
        )

        ydl_opts: Dict[str, Any] = {
            "progress_hooks": [self._my_hook],
            "postprocessor_hooks": [self._postprocessor_hook],
            "outtmpl": outtmpl_pattern,
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

        if self.ffmpeg_path:
            ydl_opts["ffmpeg_location"] = self.ffmpeg_path
            print(f"Downloader: Using FFmpeg from: {self.ffmpeg_path}")
            ffprobe_path: Path = Path(self.ffmpeg_path).parent / "ffprobe.exe"
            if not ffprobe_path.is_file():
                print(f"Downloader Warning: ffprobe.exe missing at {ffprobe_path}.")
                self.status_callback(STATUS_WARNING_FFPROBE_MISSING)
        elif core_postprocessors:
            self.status_callback(STATUS_WARNING_FFMPEG_MISSING)

        if self.is_playlist and self.playlist_items:
            ydl_opts["playlist_items"] = self.playlist_items

        if final_format_string:
            ydl_opts["format"] = final_format_string
        elif "format" in ydl_opts:
            del ydl_opts["format"]

        print("\n--- Final yt-dlp options ---")
        print(json.dumps(ydl_opts, indent=2, default=str))
        print("----------------------------\n")

        self.status_callback(STATUS_STARTING_DOWNLOAD)
        self.progress_callback(0.0)

        self._check_cancel("right before calling ydl.download()")

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
            self._check_cancel("immediately after ydl.download() finished")

        except YtdlpDownloadCancelled as e:
            raise DownloadCancelled(
                str(e) or "Download cancelled by yt-dlp hook."
            ) from e
        except (YtdlpDownloadError, YtdlpExtractorError) as dl_err:
            error_message: str = str(dl_err)
            if "ERROR:" in error_message:
                error_message = error_message.split("ERROR:")[-1].strip()
            print(f"Downloader yt-dlp Error: {dl_err}")
            self.status_callback(f"{STATUS_ERROR_PREFIX}{error_message}")
        except DownloadCancelled:
            raise
        except Exception as e:
            self._log_unexpected_error(e, "during yt-dlp download execution")
            raise

    def run(self) -> None:
        """Main entry point to run the download process."""
        start_time: float = time.time()
        try:
            self._download_core()
            self._check_cancel("after _download_core completed")
            print("Downloader: _download_core completed without raising exceptions.")

        except DownloadCancelled as e:
            cancel_msg = str(e) or "Download Cancelled."
            self.status_callback(cancel_msg)
            print(f"Downloader Run: Caught DownloadCancelled: {e}")
        except Exception as e:
            print(
                f"Downloader Run: Caught unexpected exception: {type(e).__name__}: {e}"
            )
            if not isinstance(e, (YtdlpDownloadError, YtdlpExtractorError)):
                self._log_unexpected_error(e, "in main run loop")

        finally:
            end_time: float = time.time()
            print(
                f"Downloader: Reached finally block after {end_time - start_time:.2f} seconds. Calling finished_callback."
            )
            self.finished_callback()

    def _log_unexpected_error(self, e: Exception, context: str = "") -> None:
        """Logs unexpected errors and displays a generic message to the user."""
        print(f"--- UNEXPECTED ERROR ({context}) ---")
        traceback.print_exc()
        print("------------------------------------")
        self.status_callback(
            STATUS_UNEXPECTED_ERROR.format(error_type=type(e).__name__)
        )
        print(f"Unexpected Error during download ({context}): {e}")
