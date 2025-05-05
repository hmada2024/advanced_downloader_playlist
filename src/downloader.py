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
from .exceptions import DownloadCancelled
from .logic_utils import clean_filename


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
            # Propagate cancellation in a way yt-dlp understands
            raise yt_dlp.utils.DownloadCancelled(str(e)) from e

        status = d.get("status")
        info_dict = d.get("info_dict", {})
        hook_playlist_index = info_dict.get("playlist_index")

        # Update current item index for playlist status display
        if (
            self.is_playlist
            and hook_playlist_index is not None
            and hook_playlist_index > self._last_hook_playlist_index
        ):
            self._current_processing_playlist_idx_display = hook_playlist_index
            self._last_hook_playlist_index = hook_playlist_index

        if status == "finished":
            # When download part finishes (before postprocessing potentially)
            if filepath := info_dict.get("filepath") or d.get("filename"):
                # Update status to show it's processing the downloaded file
                self._update_status_on_finish_or_process(
                    filepath, info_dict, is_final=False
                )
            else:
                # Fallback status if filepath isn't available immediately
                self.status_callback("Processing downloaded file...")
            # Set progress to 100% for the download part
            self.progress_callback(1.0)

        elif status == "downloading":
            downloaded_bytes = d.get("downloaded_bytes")
            if downloaded_bytes is not None:
                self._format_and_display_download_status(d, downloaded_bytes)
            else:
                # Status before bytes are known (e.g., connecting)
                self.status_callback(f"Status: {d.get('status', 'Connecting')}...")

        elif status == "error":
            self.status_callback("Error during download/processing reported by yt-dlp.")
            print(
                f"yt-dlp hook reported error: {d.get('error', 'Unknown yt-dlp error')}"
            )
        # Note: We don't handle 'postprocessing' status here directly,
        # as the postprocessor hook is more specific for that.

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
                # Format ETA more nicely (e.g., "1 minute 30 seconds")
                # eta_str = humanize.precisedelta(timedelta(seconds=int(round(eta))), minimum_unit="seconds")
                # Simple seconds is often preferred for downloads:
                eta_str = f"{int(round(eta))} seconds remaining"

        status_lines.append(f"Speed: {speed_str} | ETA: {eta_str}")

        status_msg = "\n".join(status_lines)
        self.status_callback(status_msg)

    def _format_playlist_progress_status(self, status_lines):
        """Formats the status lines related to playlist progress."""
        current_absolute_index = self._current_processing_playlist_idx_display
        total_absolute_str = (
            f"out of {self.total_playlist_count} total"
            if self.total_playlist_count > 0
            else ""
        )
        status_lines.append(f"Video {current_absolute_index} {total_absolute_str}")

        # Calculate index within the *selected* items more accurately
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
        # Check if the extension looks like a final video/audio format
        final_ext_present = any(
            base_filename.lower().endswith(ext)
            for ext in [
                ".mp4",
                ".mp3",
                ".mkv",
                ".webm",
                ".opus",
                ".ogg",
                ".m4a",
                ".flv",
                ".avi",
            ]
        )

        title = info_dict.get("title")
        # Clean the title or fallback to the raw filename if title is missing
        display_name = clean_filename(title or base_filename)

        # Add playlist index prefix if applicable *and* we are finishing the final file
        playlist_index = info_dict.get("playlist_index")
        if self.is_playlist and playlist_index is not None and is_final:
            display_name = f"{playlist_index}. {display_name}"
        elif (
            not title
        ):  # If title was missing, maybe keep the original name if it's final
            display_name = base_filename

        if is_final and final_ext_present:
            # Only increment processed count when the *final* file processing is done
            self._processed_selected_count += 1
            status_msg = f"Finished: {display_name}"
        else:
            # If not final, or extension is temporary (like .part), show 'Processing'
            status_msg = f"Processing: {display_name}..."

        self.status_callback(status_msg)

    def _postprocessor_hook(self, d):
        """
        خطاف ما بعد المعالجة لـ yt-dlp، يُستدعى عند بدء وانتهاء عمليات المعالجة (مثل الدمج، تحويل الصوت).
        Postprocessor hook for yt-dlp, called when postprocessing operations start and finish (e.g., merging, audio conversion).
        """
        status = d.get("status")
        postprocessor_name = d.get("postprocessor")
        info_dict = d.get("info_dict", {})  # Get info_dict early

        # --- START: Phase 2 - Improved Feedback ---
        if status == "started":
            print(f"Postprocessor Hook: '{postprocessor_name}' started.")
            # Provide user feedback based on the postprocessor name
            if postprocessor_name == "FFmpegMerger":
                self.status_callback(
                    "جاري دمج الفيديو والصوت..."
                )  # Merging video and audio...
            elif postprocessor_name == "FFmpegExtractAudio":
                # Check the target codec if available in info_dict or options
                target_codec = info_dict.get("postprocessor_args", {}).get(
                    "preferredcodec", ""
                )
                if target_codec == "mp3":
                    self.status_callback(
                        "جاري التحويل إلى MP3..."
                    )  # Converting to MP3...
                else:
                    self.status_callback(
                        f"جاري استخراج الصوت ({target_codec or '...'})..."
                    )  # Extracting audio...
            elif postprocessor_name == "FFmpegVideoConvertor":
                self.status_callback(
                    "جاري تحويل صيغة الفيديو..."
                )  # Converting video format...
            elif postprocessor_name == "MoveFiles":  # yt-dlp internal step
                self.status_callback(
                    "جاري تنظيم الملفات النهائية..."
                )  # Organizing final files...
            elif postprocessor_name:  # Generic message for other postprocessors
                self.status_callback(
                    f"جاري المعالجة بواسطة {postprocessor_name}..."
                )  # Processing via {name}...
            else:
                self.status_callback("جاري المعالجة النهائية...")  # Final processing...

        # --- END: Phase 2 - Improved Feedback ---

        elif status == "finished":
            # Logic for handling rename after *all* postprocessing is done
            final_filepath = info_dict.get("filepath")
            print(
                f"Postprocessor Hook: Status='{status}', PP='{postprocessor_name}', Final Path='{final_filepath}'"
            )

            if not final_filepath or not Path(final_filepath).is_file():
                print(
                    f"Postprocessor Error: Final file path '{final_filepath}' not found or missing after postprocessing '{postprocessor_name}'."
                )
                # Maybe add a warning callback?
                # self.status_callback(f"Warning: Final file missing after {postprocessor_name}")
                return  # Cannot proceed if final file is missing

            print(
                f"Postprocessor Hook: Final file confirmed at '{final_filepath}'. Proceeding with status update/rename."
            )
            # Update status to "Finished: ..." after successful postprocessing step
            # Pass is_final=True here
            self._update_status_on_finish_or_process(
                final_filepath, info_dict, is_final=True
            )

            # --- Renaming Logic (Can be kept as is or refined) ---
            # This part handles renaming based on title/playlist index *after*
            # yt-dlp thinks it's done with the file.

            expected_final_path_obj = Path(final_filepath)
            current_basename = expected_final_path_obj.name
            target_basename = current_basename  # Start with current name

            # Get info needed for target name
            base_title = info_dict.get("title", "Untitled")
            # Get the actual extension from the final file path
            base_ext = expected_final_path_obj.suffix  # Includes the dot (e.g., '.mp4')
            playlist_index = info_dict.get("playlist_index")

            # Construct the desired target filename
            if self.is_playlist and playlist_index is not None:
                # Format: "1. Video Title.mp4"
                target_basename_no_ext = f"{playlist_index}. {base_title}"
            else:
                target_basename_no_ext = base_title

            # Clean the base name part
            cleaned_target_basename_no_ext = clean_filename(target_basename_no_ext)
            # Combine cleaned name with original extension
            target_basename = f"{cleaned_target_basename_no_ext}{base_ext}"

            if target_basename != current_basename:
                new_final_filepath_obj = expected_final_path_obj.with_name(
                    target_basename
                )
                print(
                    f"Postprocessor: Attempting rename: '{current_basename}' -> '{target_basename}' in dir '{expected_final_path_obj.parent}'"
                )
                try:
                    # Add a small delay before rename, sometimes helps with file locks
                    time.sleep(0.2)
                    expected_final_path_obj.rename(new_final_filepath_obj)
                    print(
                        f"Postprocessor: Rename successful: '{new_final_filepath_obj}'"
                    )
                    # Optionally update status after rename (might be too quick to notice)
                    # self.status_callback(f"Renamed to: {target_basename}")
                except OSError as e:
                    print(
                        f"Postprocessor Error during rename for '{current_basename}' -> '{target_basename}': {e}"
                    )
                    # Inform user about rename failure
                    self.status_callback(
                        f"Warning: Could not rename '{current_basename}'. Error: {e}"
                    )
            else:
                print(
                    f"Postprocessor: Filename '{current_basename}' already correct or cleaned to be the same. No rename needed."
                )

    def _build_format_string(self):
        """
        يبني سلسلة الصيغة المعقدة لـ yt-dlp بناءً على اختيار المستخدم العام للجودة.
        Builds the complex format string for yt-dlp based on the user's general quality choice.
        Returns:
            tuple: (final_format_string, output_ext, postprocessors_list)
        """
        output_ext = "mp4"  # Default extension
        postprocessors = []
        final_format_string = None

        print(f"BuildFormat: Received format choice: '{self.format_choice}'")

        if self.format_choice == "Download Audio Only (MP3)":
            # Prioritize opus or m4a for conversion if possible, fallback to best audio
            final_format_string = (
                "bestaudio[ext=opus]/bestaudio[ext=m4a]/bestaudio/best"
            )
            output_ext = "mp3"  # Target extension
            if self.ffmpeg_path:
                # Configure FFmpeg for MP3 extraction
                postprocessors.append(
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",  # Standard MP3 quality
                    }
                )
                print(
                    "BuildFormat: Selecting best audio for MP3 conversion (FFmpeg found)."
                )
            else:
                # Warn if MP3 is requested but FFmpeg is missing
                print(
                    "BuildFormat Warning: MP3 requested but FFmpeg not found. Downloading best audio format available directly."
                )
                output_ext = None  # Let yt-dlp decide the extension if no conversion
            print(
                f"BuildFormat: Audio mode. Format: '{final_format_string}', Target Ext: {output_ext}"
            )

        else:  # Video format requested
            height_limit = None
            # Extract height limit (e.g., "1080p", "720p")
            if match := re.search(r"\b(\d{3,4})p\b", self.format_choice):
                height_limit = int(match[1])
                print(f"BuildFormat: Found height limit: {height_limit}p")
            else:
                print(
                    f"BuildFormat Warning: Could not parse height from format choice '{self.format_choice}'. Falling back to default 720p."
                )
                height_limit = 720  # Default height limit if parsing fails

            # Build a robust format selection string for video
            # Prioritize MP4 container, then WebM, fallback to best
            # Prefer separate video+audio for higher quality, then merged formats
            final_format_string = (
                f"bestvideo[height<={height_limit}][ext=mp4]+bestaudio[ext=m4a]/mp4/"  # Best MP4 video + M4A audio -> MP4
                f"bestvideo[height<={height_limit}][ext=webm]+bestaudio[ext=opus]/webm/"  # Best WebM video + Opus audio -> WebM (often higher quality)
                f"bestvideo[height<={height_limit}]+bestaudio/"  # Best available separate video + audio -> default container (usually MP4 or MKV)
                f"best[height<={height_limit}][ext=mp4]/"  # Best pre-merged MP4 up to limit
                f"best[height<={height_limit}][ext=webm]/"  # Best pre-merged WebM up to limit
                f"best[height<={height_limit}]"  # Absolute fallback: best overall format up to limit
            )
            output_ext = (
                "mp4"  # Default target extension (yt-dlp might merge to mkv if needed)
            )
            # No specific postprocessors needed here unless forcing container,
            # yt-dlp's merge_output_format handles merging usually.
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
        # Reset internal state variables for this download run
        self._current_processing_playlist_idx_display = 1
        self._last_hook_playlist_index = 0
        self._processed_selected_count = 0

        self._check_cancel("before starting download")

        # Build output template - Ensure directory exists or handle error
        try:
            Path(self.save_path).mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print(f"Error creating save directory '{self.save_path}': {e}")
            self.status_callback(f"Error: Cannot create save directory: {e}")
            # No point continuing if save path is invalid
            return  # Exit the download process

        # Define output filename pattern
        # Use a temporary placeholder for index if not a playlist initially
        # The postprocessor hook handles the final renaming including index
        if self.is_playlist:
            # Let postprocessor handle index prefix for cleanliness
            outtmpl_pattern = os.path.join(self.save_path, "%(title)s.%(ext)s")
        else:
            outtmpl_pattern = os.path.join(self.save_path, "%(title)s.%(ext)s")

        # Get format string, extension hint, and postprocessors
        final_format_string, output_ext_hint, core_postprocessors = (
            self._build_format_string()
        )

        # Configure yt-dlp options
        ydl_opts = {
            "progress_hooks": [self._my_hook],
            "postprocessor_hooks": [self._postprocessor_hook],
            "outtmpl": outtmpl_pattern,
            "nocheckcertificate": True,  # Avoid SSL verification issues
            "ignoreerrors": self.is_playlist,  # Continue playlist download on individual errors
            "merge_output_format": "mp4",  # Prefer MP4 container when merging
            "postprocessors": core_postprocessors,  # Add postprocessors (e.g., for MP3)
            "restrictfilenames": False,  # Allow Unicode characters, handled by clean_filename later
            "keepvideo": False,  # Don't keep separate video/audio files after merge
            "retries": 5,  # Retry downloads a few times
            "fragment_retries": 5,  # Retry fragments as well
            # 'quiet': True, # Uncomment to suppress yt-dlp console output (except errors)
            # 'verbose': True, # Uncomment for detailed yt-dlp debugging output
        }

        # Set FFmpeg location if found
        if self.ffmpeg_path:
            ydl_opts["ffmpeg_location"] = self.ffmpeg_path
            print(f"Downloader: Using FFmpeg from: {self.ffmpeg_path}")
            # --- Phase 2 Check ---
            # Check if ffprobe likely exists alongside ffmpeg
            ffprobe_path = Path(self.ffmpeg_path).parent / "ffprobe.exe"
            if not ffprobe_path.is_file():
                print(
                    "Downloader Warning: ffmpeg.exe found, but ffprobe.exe might be missing nearby. Some operations could fail."
                )
                # Optional: Add a status callback warning?
                # self.status_callback("Warning: ffprobe.exe might be missing. Some features may not work.")
            # --- End Phase 2 Check ---
        elif core_postprocessors:  # Warn if postprocessing needed but no FFmpeg
            self.status_callback(
                "Warning: FFmpeg needed for format conversion but not found. Process might fail or download original format."
            )

        # Add playlist items if applicable
        if self.is_playlist and self.playlist_items:
            ydl_opts["playlist_items"] = self.playlist_items

        # Add the format selection string
        if final_format_string:
            ydl_opts["format"] = final_format_string
        # Ensure 'format' key is removed if no specific format string was built
        # (though _build_format_string should always return one)
        elif "format" in ydl_opts:
            del ydl_opts["format"]

        print("\n--- Final yt-dlp options ---")
        # Pretty print for easier debugging in console
        import json

        print(
            json.dumps(ydl_opts, indent=2, default=str)
        )  # Use default=str for non-serializable items like callables
        print("----------------------------\n")

        self.status_callback("Starting download...")
        self.progress_callback(0)  # Reset progress bar

        self._check_cancel("right before calling ydl.download()")

        # Execute the download
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # This is the blocking call where download happens
                ydl.download([self.url])
            # Check for cancellation immediately after download finishes
            # (useful if cancelled during final postprocessing steps not covered by hooks)
            self._check_cancel("immediately after ydl.download() finished")

        # Handle specific yt-dlp cancellation exception
        except yt_dlp.utils.DownloadCancelled as e:
            # Re-raise our custom exception for consistent handling upstream
            raise DownloadCancelled(str(e)) from e
        # Handle general yt-dlp download errors
        except yt_dlp.utils.DownloadError as dl_err:
            # Extract a cleaner error message if possible
            error_message = str(dl_err)
            if "ERROR:" in error_message:
                error_message = error_message.split("ERROR:")[-1].strip()
            print(f"Downloader yt-dlp DownloadError: {dl_err}")
            # Display the error to the user
            self.status_callback(f"Download Error: {error_message}")
            # Note: We don't re-raise here, allowing finished_callback to run
        # Handle any other unexpected exceptions during download
        except Exception as e:
            # Log the full traceback for debugging
            self._log_unexpected_error(e, "during yt-dlp download execution")
            # Note: finished_callback will still run in the finally block

    def run(self):
        """
        نقطة الدخول الرئيسية لتشغيل عملية التحميل.
        Main entry point to run the download process.
        Handles exceptions and ensures the finished_callback is always called.
        """
        start_time = time.time()
        try:
            self._download_core()
            # If _download_core completes without error, check for cancellation *again*
            # before declaring implicit success (as cancellation might happen in postprocessor cleanup)
            self._check_cancel("after _download_core completed")
            # If no exception occurred and not cancelled, assume success for status update
            # (The final status might have been set by postprocessor hook already)
            # We rely on the finished_callback to trigger UI state change
            print("Downloader: _download_core completed without raising exceptions.")

        except DownloadCancelled as e:
            self.status_callback(
                str(e) or "Download Cancelled."
            )  # Provide default message
            print(f"Downloader Run: Caught DownloadCancelled: {e}")
        except Exception as e:  # Catch any other unexpected errors from _download_core
            # Logging is handled inside _download_core or _log_unexpected_error
            print(f"Downloader Run: Caught unexpected exception: {e}")
            # Ensure an error status is shown if not already set by _download_core
            if "Error" not in self.status_callback.__self__.status_label.cget(
                "text"
            ):  # Rough check
                self.status_callback(f"Unexpected Error: {type(e).__name__}")
        finally:
            end_time = time.time()
            print(
                f"Downloader: Reached finally block after {end_time - start_time:.2f} seconds. Calling finished_callback."
            )
            # Crucially, always call finished_callback to signal completion (success, error, or cancel)
            # The UI state manager will then determine the correct UI state based on the final status message.
            self.finished_callback()

    def _log_unexpected_error(self, e, context=""):
        """يسجل الأخطاء غير المتوقعة ويعرض رسالة عامة للمستخدم."""
        """Logs unexpected errors and displays a generic message to the user."""
        print(f"--- UNEXPECTED ERROR ({context}) ---")
        traceback.print_exc()
        print("------------------------------------")
        # Display a user-friendly generic error message via status callback
        self.status_callback(
            f"Unexpected Error ({type(e).__name__})! Check logs/console for details."
        )
        # Also print the error to console for easier debugging
        print(f"Unexpected Error during download ({context}): {e}")
