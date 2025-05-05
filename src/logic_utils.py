# src/logic_utils.py
# -- ملف يحتوي على دوال مساعدة عامة للمنطق --
# Purpose: Contains general helper functions for the logic part.

import sys
import re
from pathlib import Path
from typing import Optional, Union  # Added Union for type hinting

# Import yt_dlp specific utils carefully to avoid circular dependencies if refactored
try:
    import yt_dlp.utils as yt_dlp_utils
except ImportError:
    # Fallback or logging if yt_dlp is not installed, though it's a requirement
    print("Warning: yt-dlp not found, ffmpeg detection might be limited.")
    yt_dlp_utils = None


def find_ffmpeg() -> Optional[str]:
    """
    يبحث عن الملف التنفيذي لـ FFmpeg.
    Looks for the FFmpeg executable.
    الأولوية للملف المضمن في مجلد ffmpeg_bin، ثم لمتغيرات البيئة PATH.
    Priority is given to the bundled executable in ffmpeg_bin, then the system PATH.

    Returns:
        Optional[str]: مسار FFmpeg إذا وجد، وإلا None. Path to ffmpeg if found, else None.
    """
    base_path: Path
    try:
        # Determine base path correctly for both running script and bundled app
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            # Running as a PyInstaller bundle
            base_path = Path(sys._MEIPASS)
        elif getattr(sys, "frozen", False):
            # Running as a bundled executable (not using _MEIPASS?)
            base_path = Path(sys.executable).parent
        else:
            # Running as a script
            base_path = (
                Path(__file__).resolve().parent.parent
            )  # Assumes src is one level down from root
    except Exception as e:
        print(f"Error determining base path: {e}")
        base_path = Path(".")  # Fallback to current directory

    # 1. Check for bundled version relative to base path
    bundled_ffmpeg_path: Path = base_path / "ffmpeg_bin" / "ffmpeg.exe"
    bundled_ffprobe_path: Path = (
        base_path / "ffmpeg_bin" / "ffprobe.exe"
    )  # Also check ffprobe

    if bundled_ffmpeg_path.is_file():
        if bundled_ffprobe_path.is_file():
            print(f"Found bundled ffmpeg and ffprobe in: {bundled_ffmpeg_path.parent}")
        else:
            print(
                f"Found bundled ffmpeg: {bundled_ffmpeg_path}, but ffprobe might be missing."
            )
        return str(bundled_ffmpeg_path)  # Return path to ffmpeg.exe
    # 2. If not bundled, check the system PATH using yt_dlp's utility if available
    print(
        f"Bundled ffmpeg not found or incomplete at '{bundled_ffmpeg_path.parent}'. Checking system PATH..."
    )
    if yt_dlp_utils:
        try:
            # Use yt-dlp's function to find ffmpeg in PATH
            ffmpeg_path_in_env: Optional[str] = yt_dlp_utils.ffmpeg_executable()
            if ffmpeg_path_in_env and Path(ffmpeg_path_in_env).is_file():
                # Check if ffprobe is also accessible near the found ffmpeg
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

    # 3. If neither bundled nor found in PATH
    print("Warning: ffmpeg/ffprobe not found in bundle or system PATH.")
    return None


# Use Union[str, None] or Optional[str] for filename parameter
def clean_filename(filename: Optional[str]) -> str:
    """
    ينظف اسم الملف بإزالة الأحرف غير الصالحة واستبدال أخرى.
    Cleans a filename by removing invalid characters and replacing others.

    Args:
        filename (Optional[str]): اسم الملف الأصلي. The original filename.

    Returns:
        str: اسم الملف المنظف. The cleaned filename.
             Returns "downloaded_file" if the cleaned name is empty or input is None.
    """
    # --- Constants for filename cleaning ---
    INVALID_FILENAME_CHARS_REGEX = r'[\\/*?:"<>|]'
    REPLACEMENT_CHAR = ""  # Replace invalid chars with nothing
    FALLBACK_FILENAME = "downloaded_file"
    # --------------------------------------

    if not filename:
        return FALLBACK_FILENAME

    # Remove invalid characters using regex
    cleaned: str = re.sub(INVALID_FILENAME_CHARS_REGEX, REPLACEMENT_CHAR, filename)
    # Replace colons separately (often used in timestamps)
    cleaned = cleaned.replace(":", " -")
    # Replace multiple spaces with a single space and strip leading/trailing whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    # Remove trailing dots and spaces which can cause issues on Windows
    cleaned = cleaned.rstrip(". ")

    # Return the cleaned name, or fallback if it became empty
    return cleaned or FALLBACK_FILENAME
