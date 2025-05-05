# src/downloader.py
# -- ملف يحتوي على كلاس التحميل الرئيسي المنسق --
# Purpose: Contains the main coordinating Downloader class.

import os
import sys
import traceback
import time
import json
from pathlib import Path
from typing import Callable, Dict, Any, Optional, List, Tuple, Union
import threading

import yt_dlp
from yt_dlp.utils import (
    DownloadCancelled as YtdlpDownloadCancelled,
    DownloadError as YtdlpDownloadError,
    ExtractorError as YtdlpExtractorError,
)

# Imports from current package
from .exceptions import DownloadCancelled
from .logic_utils import (
    clean_filename,
)  # Keep clean_filename accessible if needed by _update_status
from .downloader_constants import *  # استيراد جميع الثوابت
from .downloader_hooks import (
    ProgressHookHandler,
    PostprocessorHookHandler,
)  # استيراد معالجات الـ Hooks
from .downloader_utils import (
    build_format_string,
    check_cancel,
    log_unexpected_error,
)  # استيراد الدوال المساعدة


class Downloader:
    """
    كلاس مسؤول عن تنسيق عملية تحميل الفيديو/الصوت ومعالجته باستخدام yt-dlp.
    Class responsible for coordinating the download and processing of video/audio using yt-dlp.
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
        cancel_event: threading.Event,  # Use threading.Event type hint
        status_callback: Callable[[str], None],
        progress_callback: Callable[[float], None],
        finished_callback: Callable[[], None],
    ):
        # --- تخزين الوسائط الأساسية ---
        self.url: str = url
        self.save_path: str = save_path
        self.format_choice: str = format_choice
        self.is_playlist: bool = is_playlist
        self.playlist_items: Optional[str] = playlist_items
        self.selected_items_count: int = selected_items_count
        self.total_playlist_count: int = total_playlist_count
        self.ffmpeg_path: Optional[str] = ffmpeg_path
        self.cancel_event: threading.Event = cancel_event
        # --- تخزين الكول باكات ---
        self.status_callback: Callable[[str], None] = status_callback
        self.progress_callback: Callable[[float], None] = progress_callback
        self.finished_callback: Callable[[], None] = finished_callback

        # --- تهيئة الحالة الداخلية لتتبع قائمة التشغيل ---
        self._current_processing_playlist_idx_display: int = (
            1  # فهرس العرض الحالي (يبدأ من 1)
        )
        self._last_hook_playlist_index: int = 0  # آخر فهرس تم تلقيه من hook
        self._processed_selected_count: int = 0  # عدد العناصر المحددة التي تمت معالجتها

        # --- تهيئة معالجات الـ Hooks ---
        # تمرير نسخة من Downloader ('self') للسماح للـ handlers بالوصول للحالة والكول باكات
        self.progress_handler = ProgressHookHandler(
            downloader=self,
            status_callback=self.status_callback,
            progress_callback=self.progress_callback,
        )
        self.postprocessor_handler = PostprocessorHookHandler(downloader=self)

        print("Downloader instance initialized.")

    # --- دالة تحديث الحالة عند انتهاء ملف (تبقى هنا لأنها تعدل حالة Downloader) ---
    def _update_status_on_finish_or_process(
        self, filepath: str, info_dict: Dict[str, Any], is_final: bool = False
    ) -> None:
        """تحديث رسالة الحالة عند انتهاء تنزيل ملف أو معالجته النهائية."""
        """Updates status message when a file finishes downloading or final processing."""
        base_filename: str = os.path.basename(filepath)  # الحصول على اسم الملف فقط
        file_path_obj = Path(filepath)
        file_ext_lower: str = (
            file_path_obj.suffix.lower()
        )  # الحصول على الامتداد بأحرف صغيرة

        # التحقق مما إذا كان الامتداد هو أحد الامتدادات النهائية الشائعة
        final_ext_present: bool = file_ext_lower in FINAL_MEDIA_EXTENSIONS

        # الحصول على العنوان وتنظيفه لعرضه
        title: Optional[str] = info_dict.get("title")
        # استخدام clean_filename لتنظيف العنوان أو اسم الملف الأساسي
        display_name: str = clean_filename(title or base_filename)

        # إضافة فهرس قائمة التشغيل للاسم المعروض إذا كان ملفًا نهائيًا في قائمة تشغيل
        playlist_index: Optional[int] = info_dict.get("playlist_index")
        if self.is_playlist and playlist_index is not None and is_final:
            display_name = clean_filename(f"{playlist_index}. {display_name}")
        elif not title:  # إذا لم يكن هناك عنوان، استخدم اسم الملف الأصلي كاسم معروض
            display_name = base_filename

        status_msg: str
        # إذا كان هذا هو الملف النهائي (is_final=True) ويحتوي على امتداد وسائط معروف
        if is_final and final_ext_present:
            self._processed_selected_count += 1  # زيادة عداد العناصر المعالجة
            status_msg = f"{STATUS_FINISHED_PREFIX}{display_name}"  # رسالة الانتهاء
        else:
            # إذا كان ملفًا مؤقتًا أو قيد المعالجة
            status_msg = (
                f"{STATUS_PROCESSING_PREFIX}{display_name}..."  # رسالة المعالجة
            )

        self.status_callback(status_msg)  # إرسال رسالة الحالة إلى الواجهة

    def _download_core(self) -> None:
        """تنفيذ عملية التحميل الأساسية باستخدام yt-dlp."""
        """Executes the core download process using yt-dlp."""
        # إعادة تعيين الحالة الداخلية لتتبع قائمة التشغيل عند بدء تحميل جديد
        self._current_processing_playlist_idx_display = 1
        self._last_hook_playlist_index = 0
        self._processed_selected_count = 0

        # التحقق من الإلغاء قبل البدء
        check_cancel(self.cancel_event, "before starting download")

        # --- إعداد مسار الحفظ ---
        save_path_obj: Path = Path(self.save_path)
        try:
            # إنشاء مجلد الحفظ إذا لم يكن موجودًا (مع إنشاء المجلدات الأصلية)
            save_path_obj.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print(f"Error creating save directory '{self.save_path}': {e}")
            self.status_callback(f"Error: Cannot create save directory: {e}")
            raise  # إيقاف التنفيذ إذا تعذر إنشاء المجلد

        # --- بناء نمط اسم الملف الناتج لـ yt-dlp ---
        # %(title)s سيتم استبداله بعنوان الفيديو، و %(ext)s بالامتداد
        # استخدام صيغة قديمة لـ outtmpl، قد نحتاج لمراجعتها لاحقًا لتجنب مشاكل إعادة التسمية
        outtmpl_pattern: str = str(save_path_obj / "%(title)s.%(ext)s")

        # --- بناء سلسلة الصيغة والمعالجات اللاحقة باستخدام الدالة المساعدة ---
        final_format_string, output_ext_hint, core_postprocessors = build_format_string(
            self.format_choice, self.ffmpeg_path
        )

        # --- بناء قاموس خيارات yt-dlp (ydl_opts) ---
        ydl_opts: Dict[str, Any] = {
            # استخدام الـ hooks من الـ handlers المهيأة
            "progress_hooks": [self.progress_handler.hook],
            "postprocessor_hooks": [self.postprocessor_handler.hook],
            "outtmpl": outtmpl_pattern,  # نمط اسم الملف الناتج
            "nocheckcertificate": True,  # تجاهل أخطاء شهادة SSL
            "ignoreerrors": self.is_playlist,  # تجاهل الأخطاء الفردية في قائمة التشغيل للمتابعة
            "merge_output_format": output_ext_hint
            or "mp4",  # الامتداد المفضل بعد الدمج
            "postprocessors": core_postprocessors,  # المعالجات اللاحقة (مثل تحويل MP3)
            "restrictfilenames": False,  # السماح بأحرف أكثر في أسماء الملفات (نتحكم بها بـ clean_filename)
            "keepvideo": False,  # عدم الاحتفاظ بملفات الفيديو/الصوت المنفصلة بعد الدمج
            "retries": 5,  # عدد محاولات إعادة الاتصال
            "fragment_retries": 5,  # عدد محاولات إعادة تحميل الأجزاء (لصيغ مثل HLS/DASH)
            "concurrent_fragment_downloads": 4,  # عدد الأجزاء التي يتم تحميلها بالتوازي
            # 'writethumbnail': True, # خيار لإضافة الصورة المصغرة (اختياري)
            # 'embedthumbnail': True, # خيار لتضمين الصورة المصغرة في الميتا بيانات (يتطلب ffmpeg)
        }

        # إضافة مسار FFmpeg إذا كان متاحًا والتحقق من ffprobe
        if self.ffmpeg_path:
            ydl_opts["ffmpeg_location"] = self.ffmpeg_path
            print(f"Downloader: Using FFmpeg from: {self.ffmpeg_path}")
            # التحقق من وجود ffprobe.exe في نفس مجلد ffmpeg.exe
            ffprobe_path: Path = Path(self.ffmpeg_path).parent / "ffprobe.exe"
            if not ffprobe_path.is_file():
                print(f"Downloader Warning: ffprobe.exe missing at {ffprobe_path}.")
                self.status_callback(STATUS_WARNING_FFPROBE_MISSING)
        elif (
            core_postprocessors
        ):  # إذا كانت هناك معالجات تتطلب FFmpeg ولم يتم العثور عليه
            self.status_callback(STATUS_WARNING_FFMPEG_MISSING)

        # تحديد عناصر قائمة التشغيل المحددة (إذا كانت قائمة تشغيل وتم تحديد عناصر)
        if self.is_playlist and self.playlist_items:
            ydl_opts["playlist_items"] = self.playlist_items

        # تعيين سلسلة الصيغة إذا تم بناؤها
        if final_format_string:
            ydl_opts["format"] = final_format_string
        elif (
            "format" in ydl_opts
        ):  # التأكد من إزالة أي صيغة قديمة إذا لم نقم ببناء واحدة جديدة
            del ydl_opts["format"]

        # طباعة الخيارات النهائية لأغراض التصحيح
        print("\n--- Final yt-dlp options ---")
        # استخدام json.dumps لطباعة القاموس بشكل مقروء
        print(
            json.dumps(ydl_opts, indent=2, default=str)
        )  # default=str لمعالجة أنواع غير قابلة للتسلسل
        print("----------------------------\n")

        # تحديث الحالة والتقدم قبل بدء التنزيل الفعلي
        self.status_callback(STATUS_STARTING_DOWNLOAD)
        self.progress_callback(0.0)

        # التحقق مرة أخرى من الإلغاء قبل استدعاء yt-dlp مباشرة
        check_cancel(self.cancel_event, "right before calling ydl.download()")

        # --- تنفيذ التنزيل باستخدام yt-dlp ---
        try:
            # استخدام yt-dlp كمدير سياق لضمان التنظيف
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])  # بدء عملية التنزيل للرابط المحدد
            # التحقق من الإلغاء فور انتهاء التنزيل (قد يتم الإلغاء أثناء المعالجة اللاحقة)
            check_cancel(self.cancel_event, "immediately after ydl.download() finished")

        # --- معالجة الاستثناءات (الأخطاء) ---
        except YtdlpDownloadCancelled as e:
            # إذا تم إلغاء العملية بواسطة خطاف yt-dlp (بسبب حدث الإلغاء لدينا)
            raise DownloadCancelled(
                str(e) or "Download cancelled by yt-dlp hook."
            ) from e
        except (YtdlpDownloadError, YtdlpExtractorError) as dl_err:
            # أخطاء التنزيل أو الاستخراج من yt-dlp
            error_message: str = str(dl_err)
            # محاولة تنظيف رسالة الخطأ
            if "ERROR:" in error_message:
                error_message = error_message.split("ERROR:")[-1].strip()
            print(f"Downloader yt-dlp Error: {dl_err}")
            self.status_callback(
                f"{STATUS_ERROR_PREFIX}{error_message}"
            )  # إبلاغ المستخدم بالخطأ
            # لا نرفع الخطأ هنا مرة أخرى، فقط نعرضه للمستخدم ونسمح للدالة بالانتهاء
        except DownloadCancelled:
            # إذا تم الإلغاء بواسطة check_cancel مباشرة
            raise  # إعادة إطلاق الاستثناء ليتم التقاطه في run()
        except Exception as e:
            # أي أخطاء أخرى غير متوقعة
            # استخدام الدالة المساعدة لتسجيل الخطأ وإبلاغ المستخدم
            log_unexpected_error(
                e, self.status_callback, "during yt-dlp download execution"
            )
            raise  # إعادة إطلاق الاستثناء ليتم التقاطه في run()

    def run(self) -> None:
        """نقطة الدخول الرئيسية لتشغيل عملية التحميل."""
        """Main entry point to run the download process."""
        start_time: float = time.time()  # تسجيل وقت البدء
        try:
            self._download_core()  # تشغيل جوهر عملية التحميل
            # التحقق من الإلغاء بعد اكتمال _download_core (للتأكد من عدم حدوث إلغاء في النهاية)
            check_cancel(self.cancel_event, "after _download_core completed")
            print("Downloader: _download_core completed without raising exceptions.")

        except DownloadCancelled as e:
            # التقاط استثناء الإلغاء
            cancel_msg = (
                str(e) or STATUS_DOWNLOAD_CANCELLED
            )  # استخدام رسالة الاستثناء أو رسالة افتراضية
            self.status_callback(cancel_msg)  # تحديث الحالة برسالة الإلغاء
            print(f"Downloader Run: Caught DownloadCancelled: {e}")
        except Exception as e:
            # التقاط أي استثناءات أخرى غير متوقعة لم يتم التعامل معها في _download_core
            print(
                f"Downloader Run: Caught unexpected exception: {type(e).__name__}: {e}"
            )
            # تسجيل الخطأ إذا لم يكن خطأ تنزيل معروفًا تم التعامل معه بالفعل
            if not isinstance(e, (YtdlpDownloadError, YtdlpExtractorError)):
                # استخدام الدالة المساعدة لتسجيل الخطأ وإبلاغ المستخدم
                log_unexpected_error(e, self.status_callback, "in main run loop")
            # لا نرفع الخطأ هنا، فقط تم تسجيله وإبلاغ المستخدم

        finally:
            # هذا البلوك يتم تنفيذه دائمًا، سواء حدث خطأ أم لا
            end_time: float = time.time()  # تسجيل وقت الانتهاء
            print(
                f"Downloader: Reached finally block after {end_time - start_time:.2f} seconds. Calling finished_callback."
            )
            # استدعاء الكول باك للإشارة إلى انتهاء المهمة (للواجهة أو LogicHandler)
            self.finished_callback()
