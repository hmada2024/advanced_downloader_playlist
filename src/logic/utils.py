# src/logic/utils.py
# -- ملف يحتوي على دوال مساعدة عامة للمنطق --
# Purpose: Contains general helper functions for the logic part.

import sys
import re
import os  # Required for path operations
from pathlib import Path
from typing import Optional, Union

# Import yt_dlp specific utils carefully
try:
    import yt_dlp.utils as yt_dlp_utils
except ImportError:
    print("Warning: yt-dlp not found, ffmpeg detection might be limited.")
    yt_dlp_utils = None

# --- Constants ---
TEMP_FOLDER_NAME = "ASF_TEMP"  # اسم المجلد المؤقت


def find_ffmpeg() -> Optional[str]:
    """
    يبحث عن الملف التنفيذي لـ FFmpeg.
    Priority is given to the bundled executable, then the system PATH.
    Returns:
        Optional[str]: Path to ffmpeg.exe if found, else None.
    """
    base_path: Path
    try:
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            base_path = Path(sys._MEIPASS)
        elif getattr(sys, "frozen", False):
            base_path = Path(sys.executable).parent
        else:
            # Running as script: Assuming utils.py is in src/logic, go up 3 levels
            base_path = Path(__file__).resolve().parent.parent.parent
            # print(f"Script mode base path: {base_path}") # Debug
    except Exception as e:
        print(f"Error determining base path: {e}")
        base_path = Path(".")

    # 1. Check bundled version
    bundled_ffmpeg_path = base_path / "ffmpeg_bin" / "ffmpeg.exe"
    # print(f"Checking bundled ffmpeg: {bundled_ffmpeg_path}") # Debug
    if bundled_ffmpeg_path.is_file():
        # Also check for ffprobe companion
        bundled_ffprobe_path = bundled_ffmpeg_path.with_name("ffprobe.exe")
        if bundled_ffprobe_path.is_file():
            print(f"Found bundled ffmpeg and ffprobe in: {bundled_ffmpeg_path.parent}")
        else:
            print(
                f"Warning: Found bundled ffmpeg but not ffprobe at {bundled_ffprobe_path}"
            )
        return str(bundled_ffmpeg_path)
    # 2. Check system PATH via yt_dlp utils
    print(
        f"Bundled ffmpeg not found at '{bundled_ffmpeg_path}'. Checking system PATH..."
    )
    if yt_dlp_utils:
        try:
            ffmpeg_path_in_env = yt_dlp_utils.ffmpeg_executable()
            if ffmpeg_path_in_env and Path(ffmpeg_path_in_env).is_file():
                ffprobe_env_path = Path(ffmpeg_path_in_env).parent / "ffprobe.exe"
                if ffprobe_env_path.is_file():
                    print(
                        f"Using ffmpeg and ffprobe from PATH: {Path(ffmpeg_path_in_env).parent}"
                    )
                else:
                    print(
                        f"Warning: Found ffmpeg in PATH ({ffmpeg_path_in_env}), but ffprobe missing nearby."
                    )
                return ffmpeg_path_in_env
        except Exception as e:
            print(f"Error checking for ffmpeg in PATH via yt-dlp: {e}")

    # 3. Not found
    print("Warning: ffmpeg/ffprobe not found in bundle or system PATH.")
    return None


# <<< إضافة: دالة للحصول على وإنشاء المجلد المؤقت >>>
def get_temp_dir() -> Optional[Path]:
    """
    يحصل على مسار المجلد المؤقت المخصص للتطبيق وينشئه إذا لم يكن موجودًا.
    يقع المجلد المؤقت داخل مجلد المستخدم الرئيسي.

    Returns:
        Optional[Path]: كائن Path للمجلد المؤقت، أو None إذا فشل الإنشاء.
    """
    try:
        # الحصول على مجلد المستخدم الرئيسي
        user_home = Path.home()
        if not user_home.is_dir():
            print(f"Error: Cannot find user home directory: {user_home}")
            return None

        # تحديد مسار المجلد المؤقت
        temp_dir_path = user_home / TEMP_FOLDER_NAME

        # إنشاء المجلد إذا لم يكن موجودًا (مع المجلدات الأصلية إذا لزم الأمر)
        temp_dir_path.mkdir(parents=True, exist_ok=True)

        print(f"Using temporary directory: {temp_dir_path}")
        return temp_dir_path

    except OSError as e:
        print(f"Error creating temporary directory '{temp_dir_path}': {e}")
        return None
    except Exception as e:
        print(f"Unexpected error getting temporary directory: {e}")
        return None


def clean_filename(filename: Optional[str]) -> str:
    """
    ينظف اسم الملف بإزالة الأحرف غير الصالحة واستبدال أخرى.
    Cleans a filename by removing invalid characters and replacing others.

    Args:
        filename (Optional[str]): The original filename.

    Returns:
        str: The cleaned filename. Returns "downloaded_file" if empty or None input.
    """
    INVALID_FILENAME_CHARS_REGEX = r'[\\/*?:"<>|]'
    REPLACEMENT_CHAR = ""
    FALLBACK_FILENAME = "downloaded_file"

    if not filename:
        return FALLBACK_FILENAME

    cleaned = re.sub(INVALID_FILENAME_CHARS_REGEX, REPLACEMENT_CHAR, filename)
    cleaned = cleaned.replace(":", " -")  # Replace colons separately
    cleaned = re.sub(r"\s+", " ", cleaned).strip()  # Replace multiple spaces and strip
    cleaned = cleaned.rstrip(". ")  # Remove trailing dots/spaces

    return cleaned or FALLBACK_FILENAME
