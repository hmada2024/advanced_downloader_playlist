# src/logic/link_fetcher.py
# -- كلاس لجلب روابط التحميل المباشرة لقائمة تشغيل --
# Purpose: Class to fetch direct download links for a playlist using yt-dlp subprocess.

import subprocess
import threading
import traceback
from typing import Callable, List, Optional, Dict, Any

# --- Imports from current package (using relative imports) ---
from .exceptions import DownloadCancelled
from .downloader_utils import build_format_string, check_cancel, log_unexpected_error


class LinkFetcher:
    """
    مسؤول عن جلب روابط التحميل المباشرة لقائمة تشغيل باستخدام yt-dlp كعملية فرعية.
    Responsible for fetching direct download links for a playlist using yt-dlp as a subprocess.
    """

    def __init__(
        self,
        playlist_url: str,
        format_choice: str,
        ffmpeg_path: Optional[str],
        cancel_event: threading.Event,
        success_callback: Callable[[List[str]], None],
        error_callback: Callable[[str], None],
        status_callback: Callable[[str], None],
        finished_callback: Callable[[], None],
    ):
        """
        تهيئة LinkFetcher.
        Args:
            playlist_url (str): رابط قائمة التشغيل.
            format_choice (str): اختيار الصيغة من الواجهة.
            ffmpeg_path (Optional[str]): المسار إلى ffmpeg.exe (قد تحتاجه yt-dlp داخليًا).
            cancel_event (threading.Event): كائن للإشارة إلى الإلغاء.
            success_callback (Callable[[List[str]], None]): كولباك للنجاح، يستقبل قائمة الروابط.
            error_callback (Callable[[str], None]): كولباك للخطأ، يستقبل رسالة الخطأ.
            status_callback (Callable[[str], None]): كولباك لتحديث الحالة.
            finished_callback (Callable[[], None]): كولباك عند انتهاء العملية.
        """
        self.playlist_url: str = playlist_url
        self.format_choice: str = format_choice
        self.ffmpeg_path: Optional[str] = ffmpeg_path
        self.cancel_event: threading.Event = cancel_event
        self.success_callback: Callable[[List[str]], None] = success_callback
        self.error_callback: Callable[[str], None] = error_callback
        self.status_callback: Callable[[str], None] = status_callback
        self.finished_callback: Callable[[], None] = finished_callback
        print(
            f"LinkFetcher initialized for URL: {playlist_url}, Format: {format_choice}"
        )

    def _get_links_core(self) -> None:
        """
        ينفذ عملية جلب الروابط الأساسية باستخدام yt-dlp subprocess.
        Executes the core link fetching process using yt-dlp subprocess.
        """
        self.status_callback("Preparing to fetch links...")
        check_cancel(self.cancel_event, "before building format")

        # بناء سلسلة الصيغة لـ yt-dlp
        format_selector, _, _ = build_format_string(
            self.format_choice, self.ffmpeg_path
        )

        if not format_selector:
            self.error_callback("Could not determine format selector for yt-dlp.")
            return

        self.status_callback(f"Fetching links (Format: {self.format_choice})...")
        print(f"LinkFetcher: Using format selector: {format_selector}")

        command: List[str] = [
            "yt-dlp",
            "--ignore-errors",  # تجاهل أخطاء الفيديو الفردي في القائمة
            "--no-check-certificate",  # تجاهل مشاكل شهادة SSL المحتملة
            "-g",  # الخيار الأساسي: الحصول على الروابط المباشرة فقط
            "--format",
            format_selector,  # تحديد الصيغة/الجودة المطلوبة
            # يمكنك إضافة خيارات أخرى هنا إذا لزم الأمر مثل --playlist-items
            self.playlist_url,  # رابط قائمة التشغيل
        ]

        # إضافة مسار FFmpeg إذا كان متاحاً (قد تحتاجه yt-dlp حتى لجلب الروابط أحياناً)
        if self.ffmpeg_path:
            command.extend(["--ffmpeg-location", self.ffmpeg_path])
            print(f"LinkFetcher: Providing ffmpeg path: {self.ffmpeg_path}")

        print(f"LinkFetcher: Running command: {' '.join(command)}")

        try:
            # التحقق من الإلغاء قبل بدء العملية الفرعية
            check_cancel(self.cancel_event, "before running subprocess")

            # تشغيل yt-dlp كعملية فرعية
            result = subprocess.run(
                command,
                capture_output=True,  # التقاط المخرجات القياسية والخطأ
                text=True,  # التعامل مع المخرجات كنص
                check=True,  # إطلاق استثناء إذا كان كود الخروج غير صفر
                encoding="utf-8",  # تحديد الترميز لضمان قراءة صحيحة
                errors="ignore",  # تجاهل أخطاء الترميز المحتملة في المخرجات
                # إضافة startupinfo لمنع ظهور نافذة موجه الأوامر على ويندوز
                startupinfo=(
                    subprocess.STARTUPINFO(
                        wShowWindow=subprocess.SW_HIDE,
                        dwFlags=subprocess.STARTF_USESHOWWINDOW,
                    )
                    if hasattr(subprocess, "STARTUPINFO")
                    else None
                ),  # Windows specific hide console
            )

            # التحقق من الإلغاء بعد انتهاء العملية الفرعية
            check_cancel(self.cancel_event, "after subprocess finished")

            # معالجة المخرجات
            links_output = result.stdout.strip()
            if not links_output:
                # إذا كان المخرج فارغًا ولكن العملية نجحت، قد تكون القائمة فارغة أو خاصة
                self.error_callback(
                    "yt-dlp returned successfully but found no links. Playlist might be empty, private, or requires login."
                )
                return

            links_list: List[str] = links_output.splitlines()

            # إزالة أي أسطر فارغة محتملة
            links_list = [link for link in links_list if link.strip()]

            if not links_list:
                raise ValueError(
                    "yt-dlp did not return any valid links after filtering."
                )

            print(f"LinkFetcher: Successfully fetched {len(links_list)} links.")
            self.success_callback(links_list)  # استدعاء كولباك النجاح مع قائمة الروابط

        except subprocess.CalledProcessError as e:
            # حدث خطأ أثناء تنفيذ yt-dlp (كود خروج غير صفر)
            error_output = e.stderr.strip() if e.stderr else "No error output captured."
            # محاولة استخراج رسالة خطأ أوضح
            clean_error = error_output
            if "ERROR:" in error_output:
                clean_error = error_output.split("ERROR:", 1)[-1].strip()
            print(
                f"LinkFetcher Error (CalledProcessError): {e}\nStderr:\n{error_output}"
            )
            self.error_callback(f"yt-dlp Error: {clean_error}")

        except FileNotFoundError:
            # لم يتم العثور على الملف التنفيذي لـ yt-dlp
            print(
                "LinkFetcher Error: 'yt-dlp' command not found. Is it installed and in PATH?"
            )
            self.error_callback(
                "'yt-dlp' command not found. Please ensure it is installed and accessible."
            )

        except DownloadCancelled:
            # تم طلب الإلغاء
            raise  # إعادة إطلاق الاستثناء ليتم التقاطه في run()

        except Exception as e:
            # أي أخطاء أخرى غير متوقعة
            log_unexpected_error(
                e, self.error_callback, "during link fetching subprocess"
            )
            raise  # إعادة إطلاق للسماح لـ finally في run بالعمل

    def run(self) -> None:
        """
        نقطة الدخول لتشغيل عملية جلب الروابط في خيط منفصل.
        Entry point to run the link fetching process in a separate thread.
        Handles exceptions and ensures the finished_callback is always called.
        """
        try:
            self._get_links_core()
        except DownloadCancelled as e:
            # إذا تم طلب الإلغاء
            cancel_msg = str(e) or "Link fetching cancelled."
            self.status_callback(cancel_msg)
            print(f"LinkFetcher Run: Caught DownloadCancelled: {e}")
        except Exception as e:
            # التقاط أي أخطاء غير متوقعة لم يتم التعامل معها في _get_links_core
            # يتم استدعاء error_callback بالفعل بواسطة log_unexpected_error
            print(
                f"LinkFetcher Run: Caught unexpected exception in run: {type(e).__name__}: {e}"
            )
            # لا نرفع الخطأ مرة أخرى هنا، فقط نضمن استدعاء finished_callback
        finally:
            # هذا البلوك يتم تنفيذه دائمًا
            print("LinkFetcher: Reached finally block, calling finished_callback.")
            self.finished_callback()
