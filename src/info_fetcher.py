# src/info_fetcher.py
# -- ملف يحتوي على كلاس جلب المعلومات --

import yt_dlp
import traceback
import logging  # <-- إضافة استيراد logging
from .exceptions import DownloadCancelled


class InfoFetcher:
    """Class responsible for fetching video/playlist information using yt-dlp."""

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
        logging.debug("InfoFetcher initialized.")

    def _check_cancel(self, stage=""):
        """Checks if cancellation has been requested and raises an exception if so."""
        if self.cancel_event.is_set():
            logging.info(f"InfoFetcher: Cancellation detected {stage}.")
            raise DownloadCancelled(f"Info fetch cancelled {stage}.")

    def _fetch_info_core(self):
        """Executes the core information fetching process using yt-dlp."""
        logging.info("InfoFetcher: Starting core info fetch.")
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
        logging.debug(f"InfoFetcher: Using yt-dlp options: {ydl_opts}")

        info_dict = None
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logging.info("InfoFetcher: Calling ydl.extract_info().")
                self._check_cancel("before calling extract_info")
                info_dict = ydl.extract_info(self.url, download=False)
                self._check_cancel("after calling extract_info")
                logging.info("InfoFetcher: ydl.extract_info() completed.")

        except yt_dlp.utils.DownloadError as e:
            error_message = str(e)
            partial_info = None
            if "ERROR:" in error_message:
                error_message = error_message.split("ERROR:")[-1].strip()

            if getattr(e, "partial", False):
                partial_info = getattr(e, "data", None)

            if partial_info:
                logging.warning(
                    f"InfoFetcher: yt-dlp DownloadError with partial data: {e}"
                )
                self.success_callback(
                    partial_info
                )  # لا يزال يعتبر نجاحًا جزئيًا Still partial success
            else:
                logging.error(f"InfoFetcher: yt-dlp DownloadError: {e}")
                self.error_callback(error_message)
            return

        except DownloadCancelled:
            # تم تسجيل الإلغاء بالفعل في _check_cancel Cancellation already logged
            raise  # أعد الرمي ليتم التقاطه في run() Re-raise to be caught by run()
        except Exception as e:
            # استخدام logging.exception لتضمين تتبع الخطأ Use logging.exception to include traceback
            logging.exception("InfoFetcher: Unexpected error during core fetch.")
            self.error_callback(f"An unexpected error occurred: {type(e).__name__}")
            return

        # بعد محاولة الجلب
        if info_dict:
            logging.info("InfoFetcher: Information dictionary received.")
            if "entries" in info_dict and isinstance(info_dict["entries"], list):
                logging.debug(
                    f"InfoFetcher: Processing playlist entries (initial count: {len(info_dict['entries'])})."
                )
                valid_entries = [entry for entry in info_dict["entries"] if entry]
                if not valid_entries and info_dict.get("extractor_key") == "YoutubeTab":
                    logging.warning(
                        "InfoFetcher: YouTube playlist seems empty or private (extractor=YoutubeTab)."
                    )
                    self.error_callback(
                        "Playlist is empty, private, or could not be accessed."
                    )
                    return
                info_dict["entries"] = valid_entries
                logging.debug(
                    f"InfoFetcher: Playlist entries cleaned (final count: {len(valid_entries)})."
                )

            self.status_callback("Information fetched successfully.")
            self.progress_callback(1.0)
            logging.info("InfoFetcher: Fetch successful, calling success_callback.")
            self.success_callback(info_dict)
        else:
            # هذا السيناريو قد يحدث إذا لم يرمي yt-dlp خطأً ولكنه أعاد None
            logging.error(
                "InfoFetcher: No information dictionary returned (URL might be invalid or yt-dlp issue)."
            )
            self.error_callback(
                "Could not retrieve information (URL might be invalid or video unavailable)."
            )

    def run(self):
        """Entry point to run the info fetching process."""
        logging.debug("InfoFetcher: run() method started.")
        try:
            self._fetch_info_core()
        except DownloadCancelled as e:
            # لا تحتاج لتسجيل الخطأ هنا، تم تسجيله عند الرمي Don't need to log error here, logged on raise
            self.status_callback(str(e))  # عرض للمستخدم Display to user
        except Exception as e:
            # الأخطاء الفادحة غير المتوقعة Fatal unexpected errors
            logging.exception("InfoFetcher: FATAL UNEXPECTED error in run() method.")
            self.error_callback(
                f"A critical unexpected error occurred: {type(e).__name__}"
            )
        finally:
            logging.debug(
                "InfoFetcher: Reached finally block, calling finished_callback."
            )
            self.finished_callback()
