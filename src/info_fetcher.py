# src/info_fetcher.py
# -- ملف يحتوي على كلاس جلب المعلومات --
# Purpose: Contains the InfoFetcher class responsible for fetching metadata.

import yt_dlp
import traceback
from typing import Callable, Dict, Any, Optional, List  # Added typing imports

from .exceptions import DownloadCancelled

# --- Constants ---
STATUS_FETCHING = "Fetching information..."
STATUS_FETCHED_SUCCESS = "Information fetched successfully."
STATUS_FETCH_CANCELLED = "Info fetch cancelled"
ERROR_FETCH_PREFIX = "Could not fetch information"
ERROR_EMPTY_PLAYLIST = "Playlist is empty, private, or could not be accessed."
ERROR_INVALID_URL = (
    "Could not retrieve information (URL might be invalid or video unavailable)."
)
ERROR_UNEXPECTED_FETCH = "An unexpected error occurred during info fetch"


class InfoFetcher:
    """
    كلاس مسؤول عن عملية جلب معلومات الفيديو/قائمة التشغيل باستخدام yt-dlp.
    Class responsible for fetching video/playlist information using yt-dlp.
    """

    def __init__(
        self,
        url: str,
        cancel_event: Any,  # threading.Event is tricky for typing stub files, use Any for simplicity
        success_callback: Callable[[Dict[str, Any]], None],
        error_callback: Callable[[str], None],
        status_callback: Callable[[str], None],
        progress_callback: Callable[[float], None],
        finished_callback: Callable[[], None],
    ):
        """
        Initializes the InfoFetcher.

        Args:
            url (str): The URL to fetch information from.
            cancel_event (Any): A threading.Event object to signal cancellation.
            success_callback (Callable[[Dict[str, Any]], None]): Callback on success, receives info dict.
            error_callback (Callable[[str], None]): Callback on error, receives error message.
            status_callback (Callable[[str], None]): Callback for status updates.
            progress_callback (Callable[[float], None]): Callback for progress updates (0.0 to 1.0).
            finished_callback (Callable[[], None]): Callback when the operation finishes (success, error, or cancel).
        """
        self.url: str = url
        self.cancel_event = (
            cancel_event  # Keep as Any or use 'threading.Event' if typing stubs allow
        )
        self.success_callback: Callable[[Dict[str, Any]], None] = success_callback
        self.error_callback: Callable[[str], None] = error_callback
        self.status_callback: Callable[[str], None] = status_callback
        self.progress_callback: Callable[[float], None] = progress_callback
        self.finished_callback: Callable[[], None] = finished_callback

    def _check_cancel(self, stage: str = "") -> None:
        """
        يتحقق مما إذا كان قد تم طلب الإلغاء ويطلق استثناءً إذا كان الأمر كذلك.
        Checks if cancellation has been requested and raises an exception if so.

        Args:
            stage (str): Optional context string for the cancellation message.

        Raises:
            DownloadCancelled: If the cancel_event is set.
        """
        if self.cancel_event.is_set():
            raise DownloadCancelled(f"{STATUS_FETCH_CANCELLED} {stage}.")

    def _fetch_info_core(self) -> None:
        """
        ينفذ عملية جلب المعلومات الأساسية باستخدام yt-dlp.
        Executes the core information fetching process using yt-dlp.
        """
        self.status_callback(STATUS_FETCHING)
        self.progress_callback(0.0)
        self._check_cancel("before starting fetch")

        # yt-dlp options for fetching info
        ydl_opts: Dict[str, Any] = {
            "quiet": True,  # Suppress console output from yt-dlp itself
            "nocheckcertificate": True,  # Ignore SSL certificate errors
            "extract_flat": "in_playlist",  # Avoid extracting full info for every item in playlist initially
            "playlistend": 500,  # Limit number of playlist entries fetched (adjust if needed)
            "ignoreerrors": True,  # Try to continue fetching even if some playlist items fail
            "forcejson": True,  # Ensure the output is JSON (though extract_info returns dict)
            "skip_download": True,  # Crucial: only fetch info, don't download
            # 'dump_single_json': True, # Alternative way to get JSON, but extract_info is more direct
        }

        info_dict: Optional[Dict[str, Any]] = None
        try:
            # Use yt-dlp as a context manager
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self._check_cancel("before calling extract_info")
                # The core call to get metadata
                info_dict = ydl.extract_info(self.url, download=False)
                self._check_cancel("after calling extract_info")

        except yt_dlp.utils.DownloadError as e:
            # Handle errors specifically from yt-dlp's download/extraction process
            error_message: str = str(e)
            partial_info: Optional[Dict[str, Any]] = None

            # Try to extract a cleaner error message
            if "ERROR:" in error_message:
                error_message = error_message.split("ERROR:")[-1].strip()

            # Check if yt-dlp provided partial data despite the error
            if getattr(e, "partial", False):
                partial_info = getattr(e, "data", None)  # type: ignore # yt-dlp attributes might not be in stubs

            if partial_info:
                # If we got partial data (e.g., playlist info but some items failed), treat as success
                print(f"InfoFetcher yt-dlp DownloadError with partial data: {e}")
                self.success_callback(partial_info)  # Send the partial data
            else:
                # If no partial data, report the error
                print(f"InfoFetcher yt-dlp DownloadError: {e}")
                self.error_callback(f"{ERROR_FETCH_PREFIX}: {error_message}")
            return  # Exit core function after handling DownloadError

        except DownloadCancelled:
            # Re-raise cancellation to be caught by the run() method
            raise
        except Exception as e:
            # Catch any other unexpected exceptions
            self._log_unexpected_error(e, "during yt-dlp info extraction")
            # Report a generic error to the user
            self.error_callback(f"{ERROR_UNEXPECTED_FETCH}: {type(e).__name__}")
            return  # Exit core function after handling unexpected error

        # --- Process successfully fetched info ---
        if info_dict:
            # Handle playlists: filter out potentially null entries yt-dlp might return
            if "entries" in info_dict and isinstance(info_dict["entries"], list):
                valid_entries: List[Dict[str, Any]] = [
                    entry for entry in info_dict["entries"] if isinstance(entry, dict)
                ]
                # Specific check for empty/private YouTube playlists
                # yt-dlp might return an empty 'entries' list for these
                if not valid_entries and info_dict.get("extractor_key") == "YoutubeTab":
                    print("InfoFetcher: YouTube playlist seems empty or private.")
                    self.error_callback(ERROR_EMPTY_PLAYLIST)
                    return  # Exit, report as error

                info_dict["entries"] = valid_entries  # Update with filtered list

            # If everything looks okay, report success
            self.status_callback(STATUS_FETCHED_SUCCESS)
            self.progress_callback(1.0)  # Signal completion
            self.success_callback(info_dict)  # Send the full info dict
        else:
            # Handle the case where yt-dlp returned None or an empty dict unexpectedly
            print(
                "InfoFetcher: No information dictionary returned (URL might be invalid or extractor failed silently)."
            )
            self.error_callback(ERROR_INVALID_URL)

    def run(self) -> None:
        """
        نقطة الدخول لتشغيل عملية جلب المعلومات في خيط منفصل.
        Entry point to run the info fetching process in a separate thread.
        Handles exceptions and ensures the finished_callback is always called.
        """
        try:
            self._fetch_info_core()
        except DownloadCancelled as e:
            # If cancellation was raised from _fetch_info_core
            self.status_callback(
                str(e) or STATUS_FETCH_CANCELLED
            )  # Use exception message or default
            print(f"InfoFetcher Run: Caught {e}")
        except Exception as e:
            # Catch any unexpected errors not handled within _fetch_info_core
            self._log_unexpected_error(e, "in main run loop")
            # Ensure an error status is set if not already done
            self.error_callback(f"{ERROR_UNEXPECTED_FETCH}: {type(e).__name__}")
        finally:
            # This block executes regardless of exceptions
            print("InfoFetcher: Reached finally block, calling finished_callback.")
            # Always call finished_callback to signal the LogicHandler/UI the task is done
            self.finished_callback()

    def _log_unexpected_error(self, e: Exception, context: str) -> None:
        """Logs unexpected errors."""
        print(f"--- UNEXPECTED ERROR ({context}) ---")
        traceback.print_exc()  # Print full traceback to console/log
        print("------------------------------------")
        # Avoid calling error_callback here if it was already called in _fetch_info_core
        # The run method's except block handles the final user notification if needed.
