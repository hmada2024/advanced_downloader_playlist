# src/logic/downloader_hooks.py
# -- ملف يحتوي على كلاسات معالجة الـ Hooks لعملية التحميل --

import os
import time
import humanize
import contextlib
from pathlib import Path
from typing import Callable, Dict, Any, Optional, List, Union, TYPE_CHECKING
import threading  # For Event type hinting

# Import exceptions and utils from yt-dlp
from yt_dlp.utils import DownloadCancelled as YtdlpDownloadCancelled

# --- Imports from current package (using relative imports) ---
# Use '.' to import from the same directory (logic)
from .exceptions import DownloadCancelled
from .utils import clean_filename  # Changed from logic_utils
from .downloader_constants import *  # Import all constants
from .downloader_utils import check_cancel  # Import check_cancel utility

# Conditional import for type hinting Downloader to avoid circular dependency
if TYPE_CHECKING:
    from .downloader import Downloader  # Use relative import here too


class ProgressHookHandler:
    """كلاس لمعالجة الـ progress_hooks من yt-dlp."""

    def __init__(
        self,
        downloader: "Downloader",  # Use string literal for type hint
        status_callback: Callable[[str], None],
        progress_callback: Callable[[float], None],
    ):
        """
        تهيئة معالج خطاف التقدم.
        Args:
            downloader: نسخة من كلاس Downloader الرئيسي للوصول إلى حالته.
            status_callback: دالة لتحديث رسالة الحالة.
            progress_callback: دالة لتحديث شريط التقدم.
        """
        self.downloader: "Downloader" = downloader
        self.status_callback: Callable[[str], None] = status_callback
        self.progress_callback: Callable[[float], None] = progress_callback

    def hook(self, d: Dict[str, Any]) -> None:
        """
        الدالة التي يتم استدعاؤها بواسطة yt-dlp كـ progress_hook.
        Args:
            d (Dict[str, Any]): القاموس الذي يمرره yt-dlp بمعلومات الحالة.
        Raises:
            YtdlpDownloadCancelled: لإرسال إشارة الإلغاء إلى yt-dlp إذا تم تعيين حدث الإلغاء لدينا.
        """
        try:
            # استخدام دالة check_cancel المنفصلة
            check_cancel(self.downloader.cancel_event, "during progress hook")
        except DownloadCancelled as e:
            raise YtdlpDownloadCancelled(str(e)) from e

        status: Optional[str] = d.get("status")
        info_dict: Dict[str, Any] = d.get("info_dict", {})
        hook_playlist_index: Optional[int] = info_dict.get("playlist_index")

        # تحديث مؤشر قائمة التشغيل الحالي إذا كنا في وضع قائمة التشغيل والفهرس تغير
        if (
            self.downloader.is_playlist
            and hook_playlist_index is not None
            and hook_playlist_index
            > self.downloader._last_hook_playlist_index  # Access via downloader instance
        ):
            # Access and update state via downloader instance
            self.downloader._current_processing_playlist_idx_display = (
                hook_playlist_index
            )
            self.downloader._last_hook_playlist_index = hook_playlist_index

        # --- معالجة الحالات المختلفة ---
        if status == "finished":
            # تم الانتهاء من تنزيل ملف (قد يكون مؤقتًا قبل المعالجة)
            # استخدم التعبير المسمى لتبسيط الشرط
            if filepath := info_dict.get("filepath") or d.get("filename"):
                # استدعاء الدالة الموجودة في Downloader الرئيسي لتحديث الحالة
                self.downloader._update_status_on_finish_or_process(
                    filepath,
                    info_dict,
                    is_final=False,  # is_final=False لأن هذا قد لا يكون الملف النهائي
                )
            else:
                # في حالة عدم وجود مسار ملف لسبب ما
                self.status_callback(STATUS_PROCESSING_FILE)
            self.progress_callback(1.0)  # تعيين التقدم إلى 100% عند الانتهاء (مؤقتًا)

        elif status == "downloading":
            # جاري التنزيل
            downloaded_bytes: Optional[int] = d.get("downloaded_bytes")
            if downloaded_bytes is not None:
                # تنسيق وعرض حالة التنزيل التفصيلية
                self._format_and_display_download_status(d, downloaded_bytes)
            else:
                # إذا لم تتوفر بايتات التنزيل، فقد يكون لا يزال يتصل
                self.status_callback(STATUS_CONNECTING)

        elif status == "error":
            # حدث خطأ أبلغ عنه yt-dlp
            self.status_callback(STATUS_ERROR_YT_DLP)
            print(
                f"yt-dlp hook reported error: {d.get('error', 'Unknown yt-dlp error')}"
            )

    def _format_and_display_download_status(
        self, d: Dict[str, Any], downloaded_bytes: int
    ) -> None:
        """تنسيق وعرض رسالة الحالة أثناء التنزيل."""
        # الحصول على الحجم الكلي (الفعلي أو المقدر)
        total_bytes: Optional[int] = d.get("total_bytes") or d.get(
            "total_bytes_estimate"
        )
        progress: float = 0.0
        percentage_str: str = "0.0%"
        if total_bytes and total_bytes > 0:  # تأكد من أن الحجم الكلي موجب
            progress = max(
                0.0, min(1.0, downloaded_bytes / total_bytes)
            )  # حساب النسبة المئوية (بين 0 و 1)
            percentage_str = f"{progress:.1%}"  # تنسيق النسبة المئوية

        self.progress_callback(progress)  # تحديث شريط التقدم

        status_lines: List[str] = []  # قائمة لتجميع أسطر رسالة الحالة

        # إضافة معلومات قائمة التشغيل إذا كانت ذات صلة
        if self.downloader.is_playlist:  # Access via downloader instance
            self._format_playlist_progress_status(status_lines)
        else:
            status_lines.append("Downloading Video")  # رسالة بسيطة للفيديو الفردي

        # تنسيق حجم الملف المحمل والحجم الكلي
        downloaded_size_str: str = humanize.naturalsize(downloaded_bytes, binary=True)
        total_size_str: str = (
            humanize.naturalsize(total_bytes, binary=True)
            if total_bytes
            else "Unknown size"
        )
        status_lines.append(
            f"Progress: {percentage_str} ({downloaded_size_str} / {total_size_str})"
        )

        # تنسيق السرعة والوقت المتبقي المقدر (ETA)
        speed: Optional[float] = d.get("speed")
        speed_str: str = (
            f"{humanize.naturalsize(speed, binary=True, gnu=True)}/s"  # استخدام gnu=True لإظهار B/s, KiB/s, إلخ.
            if speed
            else "Calculating..."
        )
        eta: Optional[Union[int, float]] = d.get("eta")
        eta_str: str = "Calculating..."
        with contextlib.suppress(
            TypeError, ValueError
        ):  # تجاهل الأخطاء إذا كان eta غير صالح
            if eta is not None and isinstance(eta, (int, float)) and eta >= 0:
                eta_str = (
                    f"{int(round(eta))} seconds remaining"  # تقريب ETA إلى أقرب ثانية
                )

        status_lines.append(f"Speed: {speed_str} | ETA: {eta_str}")

        # دمج الأسطر في رسالة واحدة وتحديث الواجهة
        status_msg: str = "\n".join(status_lines)
        self.status_callback(status_msg)

    def _format_playlist_progress_status(self, status_lines: List[str]) -> None:
        """تنسيق أسطر الحالة المتعلقة بتقدم قائمة التشغيل."""
        # Access state via downloader instance
        current_absolute_index: int = (
            self.downloader._current_processing_playlist_idx_display
        )
        total_absolute_str: str = (
            f"out of {self.downloader.total_playlist_count} total"
            if self.downloader.total_playlist_count > 0
            else ""
        )
        status_lines.append(f"Video {current_absolute_index} {total_absolute_str}")

        index_in_selection: int = self.downloader._processed_selected_count + 1
        index_in_selection = min(
            index_in_selection, self.downloader.selected_items_count
        )
        remaining_in_selection: int = max(
            0,
            self.downloader.selected_items_count
            - self.downloader._processed_selected_count,
        )
        status_lines.append(
            f"Selected: {index_in_selection} of {self.downloader.selected_items_count} ({remaining_in_selection} remaining)"
        )


class PostprocessorHookHandler:
    """كلاس لمعالجة الـ postprocessor_hooks من yt-dlp."""

    def __init__(self, downloader: "Downloader"):
        """
        تهيئة معالج خطاف المعالج اللاحق.
        Args:
            downloader: نسخة من كلاس Downloader الرئيسي للوصول إلى حالته ودواله.
        """
        self.downloader: "Downloader" = downloader

    def hook(self, d: Dict[str, Any]) -> None:
        """خطاف المعالج اللاحق لـ yt-dlp. يتم استدعاؤه للأحداث أثناء المعالجة اللاحقة."""
        """Postprocessor hook for yt-dlp. Called for events during postprocessing."""
        status: Optional[str] = d.get("status")
        postprocessor_name: Optional[str] = d.get("postprocessor")
        info_dict: Dict[str, Any] = d.get(
            "info_dict", {}
        )  # معلومات حول الملف قيد المعالجة

        # إذا بدأت مرحلة معالجة لاحقة
        if status == "started":
            print(f"Postprocessor Hook: '{postprocessor_name}' started.")
            status_message: str = STATUS_FINAL_PROCESSING  # رسالة افتراضية

            # تحديد رسالة حالة أكثر تحديدًا بناءً على اسم المعالج
            if postprocessor_name == PP_NAME_MERGER:
                status_message = PP_STATUS_MERGING
            elif postprocessor_name == PP_NAME_EXTRACT_AUDIO:
                target_codec: str = "audio"  # الترميز الافتراضي
                # محاولة الحصول على الترميز المستهدف من خيارات المعالج
                pp_args: Dict[str, Any] = info_dict.get("postprocessor_args", {})
                if isinstance(pp_args, dict):
                    target_codec = pp_args.get("preferredcodec", target_codec)

                if target_codec == "mp3":  # حالة خاصة لـ MP3
                    status_message = PP_STATUS_CONVERTING_MP3
                else:
                    status_message = PP_STATUS_EXTRACTING_AUDIO.format(
                        codec=target_codec
                    )
            elif postprocessor_name == PP_NAME_CONVERT_VIDEO:
                status_message = PP_STATUS_CONVERTING_VIDEO
            elif (
                postprocessor_name == PP_NAME_MOVE_FILES
            ):  # معالج داخلي لـ yt-dlp لنقل الملفات
                status_message = STATUS_ORGANIZE_FILES
            elif postprocessor_name:  # معالج آخر غير معروف
                status_message = PP_STATUS_PROCESSING_GENERIC_PP.format(
                    pp_name=postprocessor_name
                )

            # تحديث رسالة الحالة في الواجهة
            self.downloader.status_callback(
                status_message
            )  # Access callback via downloader

        # إذا انتهت مرحلة معالجة لاحقة
        elif status == "finished":
            # الحصول على المسار النهائي للملف بعد المعالجة
            final_filepath: Optional[str] = info_dict.get("filepath")
            print(
                f"Postprocessor Hook: Status='{status}', PP='{postprocessor_name}', Final Path='{final_filepath}'"
            )

            # التحقق من وجود الملف النهائي فعليًا
            if not final_filepath or not Path(final_filepath).is_file():
                print(
                    f"Postprocessor Error: Final file path '{final_filepath}' not found after '{postprocessor_name}'."
                )
                # يمكن إضافة تحديث للحالة هنا للإبلاغ عن خطأ داخلي
                return  # الخروج إذا لم يتم العثور على الملف

            print(
                f"Postprocessor Hook: Final file confirmed at '{final_filepath}'. Updating status/rename."
            )
            # تحديث الحالة للإشارة إلى اسم الملف النهائي (الذي تم إنشاؤه للتو)
            # is_final=True لأنه من المفترض أن يكون هذا هو الملف النهائي لهذه الخطوة
            self.downloader._update_status_on_finish_or_process(
                final_filepath, info_dict, is_final=True
            )

            # --- منطق إعادة التسمية النهائي ---
            # يهدف إلى تسمية الملف بالشكل المطلوب (مثل: "1. Title.mp4")
            expected_final_path_obj: Path = Path(
                final_filepath
            )  # كائن المسار للملف الحالي
            current_basename: str = (
                expected_final_path_obj.name
            )  # اسم الملف الحالي مع الامتداد

            # الحصول على المعلومات اللازمة للاسم المستهدف
            base_title: str = info_dict.get("title", "Untitled")  # عنوان الفيديو الأصلي
            base_ext: str = expected_final_path_obj.suffix  # امتداد الملف الحالي
            playlist_index: Optional[int] = info_dict.get(
                "playlist_index"
            )  # فهرس قائمة التشغيل (إذا كان متاحًا)

            # بناء الاسم المستهدف بدون امتداد
            target_basename_no_ext: str
            if (
                self.downloader.is_playlist and playlist_index is not None
            ):  # Access via downloader
                # في حالة قائمة التشغيل، أضف الفهرس إلى العنوان
                target_basename_no_ext = f"{playlist_index}. {base_title}"
            else:
                # في حالة الفيديو الفردي، استخدم العنوان فقط
                target_basename_no_ext = base_title

            # تنظيف الاسم المستهدف من الأحرف غير الصالحة
            cleaned_target_basename_no_ext: str = clean_filename(target_basename_no_ext)
            # إضافة الامتداد للاسم المستهدف النظيف
            target_basename: str = f"{cleaned_target_basename_no_ext}{base_ext}"

            # إذا كان الاسم المستهدف يختلف عن الاسم الحالي، قم بإعادة التسمية
            if target_basename != current_basename:
                new_final_filepath_obj: Path = expected_final_path_obj.with_name(
                    target_basename
                )
                print(
                    f"Postprocessor: Attempting rename: '{current_basename}' -> '{target_basename}'"
                )
                try:
                    time.sleep(0.2)  # إعطاء وقت بسيط للنظام للتأكد من إغلاق الملف
                    expected_final_path_obj.rename(
                        new_final_filepath_obj
                    )  # تنفيذ إعادة التسمية
                    print(
                        f"Postprocessor: Rename successful: '{new_final_filepath_obj}'"
                    )
                except OSError as e:  # التعامل مع أخطاء إعادة التسمية المحتملة
                    print(f"Postprocessor Error during rename: {e}")
                    # إبلاغ المستخدم بالخطأ عبر رسالة الحالة
                    self.downloader.status_callback(  # Access via downloader
                        STATUS_RENAME_FAILED_WARNING.format(
                            filename=current_basename, error=e
                        )
                    )
            else:  # إذا كان الاسم الحالي هو نفسه الاسم المستهدف
                print(
                    f"Postprocessor: Filename '{current_basename}' already correct. No rename needed."
                )
