# src/logic/downloader_utils.py
# -- ملف يحتوي على دوال مساعدة لعملية التحميل --

import re
import traceback
from typing import Callable, Dict, Any, Optional, List, Tuple, Union
from pathlib import Path
import threading  # For Event type hint

# --- Imports from current package (using relative imports) ---
# Use '.' to import from the same directory (logic)
from .exceptions import DownloadCancelled
from .downloader_constants import (
    FORMAT_AUDIO_MP3,
    PP_NAME_EXTRACT_AUDIO,
    STATUS_WARNING_FFMPEG_MISSING,
    STATUS_UNEXPECTED_ERROR,
)


def check_cancel(cancel_event: threading.Event, stage: str = "") -> None:
    """يتحقق من طلب الإلغاء ويطلق استثناءً إذا طُلب."""
    """Checks for cancellation request and raises if requested."""
    if cancel_event.is_set():
        raise DownloadCancelled(f"Download cancelled {stage}.")


def log_unexpected_error(
    e: Exception, status_callback: Callable[[str], None], context: str = ""
) -> None:
    """يسجل الأخطاء غير المتوقعة ويعرض رسالة عامة للمستخدم."""
    """Logs unexpected errors and displays a generic message to the user."""
    print(f"--- UNEXPECTED ERROR ({context}) ---")
    traceback.print_exc()
    print("------------------------------------")
    status_callback(STATUS_UNEXPECTED_ERROR.format(error_type=type(e).__name__))
    print(f"Unexpected Error during download ({context}): {e}")


def build_format_string(
    format_choice: str, ffmpeg_path: Optional[str]
) -> Tuple[Optional[str], Optional[str], List[Dict[str, Any]]]:
    """يبني سلسلة الصيغة المعقدة لـ yt-dlp بناءً على اختيار الجودة للمستخدم."""
    """Builds the complex format string for yt-dlp based on the user's quality choice."""
    output_ext_hint: Optional[str] = "mp4"  # الامتداد الافتراضي المتوقع للفيديو
    postprocessors: List[Dict[str, Any]] = []  # قائمة المعالجات اللاحقة
    final_format_string: Optional[str] = None  # سلسلة الصيغة النهائية

    print(f"BuildFormat: Received format choice: '{format_choice}'")

    # حالة تحميل الصوت فقط (MP3)
    if format_choice == FORMAT_AUDIO_MP3:
        # اختيار أفضل صوت متاح، مع تفضيل opus أو m4a كمدخلات للتحويل
        final_format_string = "bestaudio[ext=opus]/bestaudio[ext=m4a]/ba/best"
        output_ext_hint = "mp3"  # الامتداد المستهدف هو MP3
        if ffmpeg_path:  # إذا كان FFmpeg متاحًا
            # إضافة معالج لاحق لاستخراج الصوت وتحويله إلى MP3
            postprocessors.append(
                {
                    "key": PP_NAME_EXTRACT_AUDIO,
                    "preferredcodec": "mp3",
                    "preferredquality": "192",  # جودة MP3 (يمكن تغييرها)
                }
            )
            print(
                "BuildFormat: Selecting best audio for MP3 conversion (FFmpeg found)."
            )
        else:  # إذا لم يكن FFmpeg متاحًا
            print(f"BuildFormat Warning: {STATUS_WARNING_FFMPEG_MISSING}")
            output_ext_hint = None  # لا يمكن ضمان MP3، اترك yt-dlp يختار الامتداد
        print(
            f"BuildFormat: Audio mode. Format: '{final_format_string}', Target Ext Hint: {output_ext_hint}"
        )

    # حالة تحميل الفيديو (مع الصوت إن أمكن)
    else:
        height_limit: Optional[int] = None  # حد الارتفاع (مثل 720)
        # محاولة استخراج حد الارتفاع من اسم الصيغة المختارة (مثل "... up to 720p")
        if match := re.search(r"\b(\d{3,4})p\b", format_choice):
            try:
                height_limit = int(match[1])  # الحصول على الرقم من نتيجة البحث
                print(f"BuildFormat: Found height limit: {height_limit}p")
            except (ValueError, IndexError):
                print(
                    f"BuildFormat Warning: Could not parse height from match object '{match}'."
                )
                height_limit = None  # التعامل معه كأن لم يتم العثور على حد

        if not height_limit:  # إذا لم يتم تحديد أو استخراج حد للارتفاع
            print(
                f"BuildFormat Info: Could not parse specific height from '{format_choice}'. Using best available."
            )

        # بناء سلسلة الصيغة للفيديو
        # الأولوية لـ mp4 ثم webm، مع محاولة دمج أفضل فيديو (bv) وأفضل صوت (ba)
        # وفي حالة الفشل، يتم اختيار أفضل صيغة متاحة (b) بالامتداد المحدد
        format_parts: List[str] = [
            "bv[ext=mp4]+ba[ext=m4a]/b[ext=mp4]",  # أفضل فيديو mp4 + أفضل صوت m4a / أفضل mp4 شامل
            "bv[ext=webm]+ba[ext=opus]/b[ext=webm]",  # أفضل فيديو webm + أفضل صوت opus / أفضل webm شامل
            "bv+ba/b",  # أفضل فيديو + أفضل صوت (أي امتداد) / أفضل شامل (أي امتداد)
        ]

        # إذا كان هناك حد للارتفاع، قم بإضافته كفلتر
        if height_limit:
            height_filter = f"[height<={height_limit}]"  # فلتر الارتفاع لـ yt-dlp
            # إعادة بناء قائمة الصيغ مع تطبيق الفلتر
            format_parts = [
                f"bv{height_filter}[ext=mp4]+ba[ext=m4a]/b{height_filter}[ext=mp4]",
                f"bv{height_filter}[ext=webm]+ba[ext=opus]/b{height_filter}[ext=webm]",
                f"bv{height_filter}+ba/b{height_filter}",
                f"b{height_filter}[ext=mp4]",  # كخيار احتياطي: أفضل صيغة شاملة بالارتفاع المحدد وامتداد mp4
                f"b{height_filter}[ext=webm]",  # كخيار احتياطي: أفضل صيغة شاملة بالارتفاع المحدد وامتداد webm
                f"b{height_filter}",  # كخيار احتياطي: أفضل صيغة شاملة بالارتفاع المحدد (أي امتداد)
            ]
        else:  # إذا لم يكن هناك حد للارتفاع، أضف خيارات احتياطية لأفضل جودة شاملة
            format_parts.extend(["b[ext=mp4]", "b[ext=webm]", "b"])

        final_format_string = "/".join(format_parts)  # دمج أجزاء الصيغة بشرطة مائلة
        output_ext_hint = "mp4"  # الامتداد المفضل للفيديو المدمج
        postprocessors = (
            []
        )  # لا حاجة لمعالجات لاحقة أساسية هنا (الدمج يتم بواسطة yt-dlp)
        print(
            f"BuildFormat: Video mode. Limit: {height_limit or 'None'}p, Format: '{final_format_string}', Target Ext Hint: {output_ext_hint}"
        )

    return final_format_string, output_ext_hint, postprocessors
