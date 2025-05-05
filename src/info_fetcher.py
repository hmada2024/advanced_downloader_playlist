# src/info_fetcher.py
# -- ملف يحتوي على كلاس جلب المعلومات --
# Purpose: Contains the InfoFetcher class responsible for fetching metadata.

import yt_dlp
import traceback
from .exceptions import (
    DownloadCancelled,
)  # <-- تم التعديل: إزالة الشرطة السفلية


class InfoFetcher:
    """
    كلاس مسؤول عن عملية جلب معلومات الفيديو/قائمة التشغيل باستخدام yt-dlp.
    Class responsible for fetching video/playlist information using yt-dlp.
    """

    def __init__(
        self,
        url,
        cancel_event,
        success_callback,
        error_callback,
        status_callback,
        progress_callback,
        finished_callback,
    ):
        self.url = url
        self.cancel_event = cancel_event
        self.success_callback = success_callback
        self.error_callback = error_callback
        self.status_callback = status_callback
        self.progress_callback = progress_callback
        self.finished_callback = finished_callback

    def _check_cancel(self, stage=""):
        """
        يتحقق مما إذا كان قد تم طلب الإلغاء ويطلق استثناءً إذا كان الأمر كذلك.
        Checks if cancellation has been requested and raises an exception if so.
        """
        if self.cancel_event.is_set():
            raise DownloadCancelled(f"Info fetch cancelled {stage}.")

    def _fetch_info_core(self):
        """
        ينفذ عملية جلب المعلومات الأساسية باستخدام yt-dlp.
        Executes the core information fetching process using yt-dlp.
        """
        self.status_callback("Fetching information...")
        self.progress_callback(0)
        self._check_cancel("before starting fetch")

        ydl_opts = {
            "quiet": True,
            "nocheckcertificate": True,
            "extract_flat": "in_playlist",
            "playlistend": 500,
            "ignoreerrors": True,
            "forcejson": True,
            "skip_download": True,
        }

        info_dict = None
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self._check_cancel("before calling extract_info")
                info_dict = ydl.extract_info(self.url, download=False)
                self._check_cancel("after calling extract_info")

        except yt_dlp.utils.DownloadError as e:
            error_message = str(e)
            partial_info = None
            if "ERROR:" in error_message:
                error_message = error_message.split("ERROR:")[-1].strip()

            if getattr(e, "partial", False):
                partial_info = getattr(e, "data", None)

            if partial_info:
                print(f"InfoFetcher yt-dlp DownloadError with partial data: {e}")
                self.success_callback(partial_info)
            else:
                print(f"InfoFetcher yt-dlp DownloadError: {e}")
                self.error_callback(error_message)
            return

        except DownloadCancelled:
            raise
        except Exception as e:
            self._log_unexpected_error(e, "InfoFetcher Unexpected Error")
            return

        if info_dict:
            if "entries" in info_dict and isinstance(info_dict["entries"], list):
                valid_entries = [entry for entry in info_dict["entries"] if entry]
                if not valid_entries and info_dict.get("extractor_key") == "YoutubeTab":
                    print("InfoFetcher: YouTube playlist seems empty or private.")
                    self.error_callback(
                        "Playlist is empty, private, or could not be accessed."
                    )
                    return
                info_dict["entries"] = valid_entries

            self.status_callback("Information fetched successfully.")
            self.progress_callback(1.0)
            self.success_callback(info_dict)
        else:
            print(
                "InfoFetcher: No information dictionary returned (URL might be invalid)."
            )
            self.error_callback(
                "Could not retrieve information (URL might be invalid or video unavailable)."
            )

    def run(self):
        """
        نقطة الدخول لتشغيل عملية جلب المعلومات في خيط منفصل.
        Entry point to run the info fetching process in a separate thread.
        Handles exceptions and ensures the finished_callback is always called.
        """
        try:
            self._fetch_info_core()
        except DownloadCancelled as e:
            self.status_callback(str(e))
            print(e)
        except Exception as e:
            self._log_unexpected_error(e, "InfoFetcher FATAL UNEXPECTED Error in run")
        finally:
            print("InfoFetcher: Reached finally block, calling finished_callback.")
            self.finished_callback()

    def _log_unexpected_error(self, e, context):
        """Logs unexpected errors."""
        print(f"--- {context} ---")
        traceback.print_exc()
        print("------------------------------------")
        self.error_callback(f"An unexpected error occurred: {type(e).__name__}")
