# src/logic_utils.py
# -- ملف يحتوي على دوال مساعدة عامة للمنطق --
# Purpose: Contains general helper functions for the logic part.

import sys
from pathlib import Path
import re
import yt_dlp.utils  # Needed for find_ffmpeg -> yt_dlp.utils.ffmpeg_executable


def find_ffmpeg():
    """
    يبحث عن الملف التنفيذي لـ FFmpeg.
    Looks for the FFmpeg executable.
    الأولوية للملف المضمن في مجلد ffmpeg_bin، ثم لمتغيرات البيئة PATH.
    Priority is given to the bundled executable in ffmpeg_bin, then the system PATH.

    Returns:
        str | None: مسار FFmpeg إذا وجد، وإلا None. Path to ffmpeg if found, else None.
    """
    try:
        if getattr(sys, "frozen", False):
            base_path = Path(sys.executable).parent
        else:
            # Needs to go up two levels from src/logic_utils.py to project root
            base_path = Path(__file__).resolve().parent.parent
    except Exception as e:
        print(f"Error determining base path: {e}")
        base_path = Path(".")  # Fallback

    # Check for bundled version
    bundled_path = base_path / "ffmpeg_bin" / "ffmpeg.exe"
    if bundled_path.is_file():
        print(f"Found bundled ffmpeg: {bundled_path}")
        return str(bundled_path)
    else:
        # Check the system PATH
        print(f"Bundled ffmpeg not found at '{bundled_path}'. Checking PATH...")
        try:
            # Use yt-dlp's function to check PATH
            ffmpeg_path_in_env = yt_dlp.utils.ffmpeg_executable()
            if ffmpeg_path_in_env and Path(ffmpeg_path_in_env).is_file():
                print(f"Using ffmpeg from PATH: {ffmpeg_path_in_env}")
                return ffmpeg_path_in_env
        except Exception as e:
            print(f"Error checking for ffmpeg in PATH: {e}")

        print("Warning: ffmpeg not found in bundle or system PATH.")
        return None


def clean_filename(filename):
    """
    ينظف اسم الملف بإزالة الأحرف غير الصالحة واستبدال أخرى.
    Cleans a filename by removing invalid characters and replacing others.

    Args:
        filename (str | None): اسم الملف الأصلي. The original filename.

    Returns:
        str: اسم الملف المنظف. The cleaned filename.
             Returns "downloaded_file" if the cleaned name is empty or input is None.
    """
    if not filename:
        return "downloaded_file"

    cleaned = re.sub(r'[\\/*?:"<>|]', "", filename)
    cleaned = cleaned.replace(":", " -")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = cleaned.rstrip(". ")

    return cleaned or "downloaded_file"
