# src/logic/info_fetcher.py
# -- ملف يحتوي على كلاس جلب المعلومات --
# -- Modified to ensure thumbnail URLs are part of the fetched info --

import yt_dlp
import traceback
import threading
from typing import Callable, Dict, Any, Optional, List

from .exceptions import DownloadCancelled

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
    Class responsible for fetching video/playlist information using yt-dlp,
    including thumbnail URLs.
    """

    def __init__(
        self,
        url: str,
        cancel_event: threading.Event,
        success_callback: Callable[[Dict[str, Any]], None],
        error_callback: Callable[[str], None],
        status_callback: Callable[[str], None],
        progress_callback: Callable[[float], None],
        finished_callback: Callable[[], None],
    ):
        self.url: str = url
        self.cancel_event: threading.Event = cancel_event
        self.success_callback: Callable[[Dict[str, Any]], None] = success_callback
        self.error_callback: Callable[[str], None] = error_callback
        self.status_callback: Callable[[str], None] = status_callback
        self.progress_callback: Callable[[float], None] = progress_callback
        self.finished_callback: Callable[[], None] = finished_callback

    def _check_cancel(self, stage: str = "") -> None:
        if self.cancel_event.is_set():
            raise DownloadCancelled(f"{STATUS_FETCH_CANCELLED} {stage}.")

    def _fetch_info_core(self) -> None:
        self.status_callback(STATUS_FETCHING)
        self.progress_callback(0.0)
        self._check_cancel("before starting fetch")

        ydl_opts: Dict[str, Any] = {
            "quiet": True,
            "nocheckcertificate": True,
            "extract_flat": "in_playlist",
            "playlistend": 500,
            "ignoreerrors": True,
            "forcejson": True,
            "skip_download": True,
            # Ensure thumbnails are not skipped by default yt-dlp behavior for flat extract.
            # However, 'thumbnail' key is usually present even with extract_flat for the main playlist/video.
            # For individual playlist entries, more detailed fetching might be needed if flat extract is too aggressive.
            # 'writethumbnail': True, # This would download them, not what we want.
            # We just need the URL.
        }

        info_dict: Optional[Dict[str, Any]] = None
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self._check_cancel("before calling extract_info")
                info_dict = ydl.extract_info(self.url, download=False)
                self._check_cancel("after calling extract_info")

        except yt_dlp.utils.DownloadError as e:
            error_message: str = str(e)
            partial_info: Optional[Dict[str, Any]] = None
            if "ERROR:" in error_message:
                error_message = error_message.split("ERROR:")[-1].strip()
            if getattr(e, "partial", False):
                partial_info = getattr(e, "data", None)
            if partial_info:
                print(f"InfoFetcher yt-dlp DownloadError with partial data: {e}")
                self._process_and_callback_info(
                    partial_info
                )  # Process even partial info
            else:
                print(f"InfoFetcher yt-dlp DownloadError: {e}")
                self.error_callback(f"{ERROR_FETCH_PREFIX}: {error_message}")
            return

        except DownloadCancelled:
            raise
        except Exception as e:
            self._log_unexpected_error(e, "during yt-dlp info extraction")
            self.error_callback(f"{ERROR_UNEXPECTED_FETCH}: {type(e).__name__}")
            return

        self._process_and_callback_info(info_dict)

    def _process_and_callback_info(self, info_dict: Optional[Dict[str, Any]]) -> None:
        """
        Processes the fetched info_dict (handles playlists, extracts thumbnails)
        and calls the appropriate success or error callback.
        """
        if not info_dict:
            print("InfoFetcher: No information dictionary returned.")
            self.error_callback(ERROR_INVALID_URL)
            return

        # Ensure 'thumbnail' key or 'thumbnails' list exists and select one.
        # yt-dlp usually provides 'thumbnail' (single URL) or 'thumbnails' (list of dicts).
        def get_best_thumbnail_url(item_info: Dict[str, Any]) -> Optional[str]:
            if not item_info:
                return None
            if "thumbnail" in item_info and isinstance(item_info["thumbnail"], str):
                return item_info["thumbnail"]
            if "thumbnails" in item_info and isinstance(item_info["thumbnails"], list):
                # Prefer higher resolution if multiple thumbnails are available
                # For simplicity, take the last one, often the largest.
                # Or iterate and find one with specific width/height if needed.
                for thumb_info in reversed(item_info["thumbnails"]):
                    if isinstance(thumb_info, dict) and "url" in thumb_info:
                        return thumb_info["url"]
            return None

        # Add/update thumbnail_url for the main item
        info_dict["thumbnail_url"] = get_best_thumbnail_url(info_dict)

        if "entries" in info_dict and isinstance(info_dict["entries"], list):
            valid_entries: List[Dict[str, Any]] = []
            for entry in info_dict["entries"]:
                if isinstance(entry, dict):
                    # Add/update thumbnail_url for each entry in the playlist
                    entry["thumbnail_url"] = get_best_thumbnail_url(entry)
                    valid_entries.append(entry)

            if not valid_entries and info_dict.get("extractor_key") == "YoutubeTab":
                print("InfoFetcher: YouTube playlist seems empty or private.")
                self.error_callback(ERROR_EMPTY_PLAYLIST)
                return
            info_dict["entries"] = valid_entries

        # Debug: print extracted thumbnail URLs
        # print(f"Main thumbnail URL: {info_dict.get('thumbnail_url')}")
        # if "entries" in info_dict:
        #     for i, entry in enumerate(info_dict["entries"]):
        #         print(f"Entry {i} thumbnail URL: {entry.get('thumbnail_url')}")

        self.status_callback(STATUS_FETCHED_SUCCESS)
        self.progress_callback(1.0)
        self.success_callback(info_dict)

    def run(self) -> None:
        try:
            self._fetch_info_core()
        except DownloadCancelled as e:
            self.status_callback(str(e) or STATUS_FETCH_CANCELLED)
            print(f"InfoFetcher Run: Caught {e}")
        except Exception as e:
            self._log_unexpected_error(e, "in main run loop")
            self.error_callback(f"{ERROR_UNEXPECTED_FETCH}: {type(e).__name__}")
        finally:
            print("InfoFetcher: Reached finally block, calling finished_callback.")
            self.finished_callback()

    def _log_unexpected_error(self, e: Exception, context: str) -> None:
        print(f"--- UNEXPECTED ERROR ({context}) ---")
        traceback.print_exc()
        print("------------------------------------")
