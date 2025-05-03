# src/logic_utils.py
# -- ملف يحتوي على دوال مساعدة عامة للمنطق --

import sys
from pathlib import Path
import re
import yt_dlp
import logging  # <-- إضافة استيراد logging


def find_ffmpeg():
    """Looks for the FFmpeg executable."""
    logging.debug("Attempting to find FFmpeg executable...")
    try:
        if getattr(sys, "frozen", False):
            base_path = Path(sys.executable).parent
            logging.debug(f"Running frozen, base path: {base_path}")
        else:
            # مستوى واحد للأعلى من logic_utils.py للوصول إلى جذر المشروع
            base_path = Path(__file__).resolve().parent.parent
            logging.debug(f"Running as script, base path: {base_path}")
    except Exception as e:
        logging.error(f"Error determining base path in find_ffmpeg: {e}")
        base_path = Path(".")

    # Check for bundled version
    bundled_path = base_path / "ffmpeg_bin" / "ffmpeg.exe"
    logging.debug(f"Checking for bundled ffmpeg at: {bundled_path}")
    if bundled_path.is_file():
        logging.info(f"Found bundled ffmpeg: {bundled_path}")
        return str(bundled_path)
    else:
        # Check the system PATH
        logging.debug(f"Bundled ffmpeg not found. Checking system PATH...")
        try:
            # استخدام دالة yt-dlp للبحث في PATH
            ffmpeg_path_in_env = yt_dlp.utils.ffmpeg_executable()
            if ffmpeg_path_in_env and Path(ffmpeg_path_in_env).is_file():
                # التأكد من أنه ليس مجرد اسم الملف Ensure it's not just the filename
                if (
                    Path(ffmpeg_path_in_env).is_absolute()
                    or os.path.sep in ffmpeg_path_in_env
                ):
                    logging.info(f"Using ffmpeg from system PATH: {ffmpeg_path_in_env}")
                    return ffmpeg_path_in_env
                else:
                    logging.warning(
                        f"yt_dlp.utils.ffmpeg_executable() returned non-path: {ffmpeg_path_in_env}. Ignoring."
                    )
            else:
                logging.debug("ffmpeg not found in system PATH by yt_dlp.")

        except Exception as e:
            # قد يحدث خطأ إذا لم يتمكن yt-dlp من تنفيذ الأوامر
            logging.error(f"Error checking for ffmpeg in PATH using yt-dlp: {e}")

        # إذا لم يتم العثور عليه في أي مكان
        logging.warning("ffmpeg executable not found in bundle or system PATH.")
        return None


def clean_filename(filename):
    """Cleans a filename by removing invalid characters and replacing others."""
    if not filename:
        return "downloaded_file"

    # إزالة الأحرف غير المسموح بها في ويندوز + أحرف التحكم
    cleaned = re.sub(r'[\\/*?:"<>|\x00-\x1f\x7f]', "", filename)
    # استبدال النقطتين بـ " - "
    cleaned = cleaned.replace(":", " -")
    # استبدال المسافات المتعددة بمسافة واحدة
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    # إزالة النقاط أو المسافات الزائدة في النهاية والبداية
    cleaned = cleaned.strip(". ")

    final_name = cleaned or "downloaded_file"
    # تسجيل فقط إذا تم التغيير أو كان فارغاً
    if final_name != filename or not filename:
        logging.debug(f"Cleaned filename: '{filename}' -> '{final_name}'")
    return final_name
