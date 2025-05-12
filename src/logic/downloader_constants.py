# src/logic/downloader_constants.py
# -- ملف يحتوي على الثوابت المستخدمة في عملية التحميل --

from typing import Set

# --- Status Messages ---
STATUS_STARTING_DOWNLOAD: str = "Starting download..."
STATUS_CONNECTING: str = "Connecting..."
STATUS_PROCESSING: str = "Processing..."
STATUS_PROCESSING_FILE: str = "Processing downloaded file..."
STATUS_FINISHED_PREFIX: str = (
    "Finished: "  # لا يزال مفيدًا للرسائل القديمة أو الخطافات الأخرى
)
STATUS_PROCESSING_PREFIX: str = "Processing: "
STATUS_ERROR_PREFIX: str = "Download Error: "
STATUS_ERROR_YT_DLP: str = "Error during download/processing reported by yt-dlp."
STATUS_WARNING_FFMPEG_MISSING: str = (
    "Warning: FFmpeg needed but not found. Conversion/Merging might fail."
)
STATUS_WARNING_FFPROBE_MISSING: str = (
    "Warning: ffprobe.exe might be missing. Some features may not work."
)
STATUS_RENAME_FAILED_WARNING: str = (
    "Warning: Could not rename '{filename}'. Error: {error}"
)
STATUS_ORGANIZE_FILES: str = "Organizing final files..."  # English
STATUS_UNEXPECTED_ERROR: str = (
    "Unexpected Error ({error_type})! Check logs/console for details."
)
STATUS_FINAL_PROCESSING: str = "Final processing..."  # English
STATUS_DOWNLOAD_CANCELLED: str = "Download Cancelled."

# --- Postprocessor Names (match yt-dlp internal names) ---
PP_NAME_MERGER: str = "FFmpegMerger"
PP_NAME_EXTRACT_AUDIO: str = "FFmpegExtractAudio"
PP_NAME_CONVERT_VIDEO: str = "FFmpegVideoConvertor"
PP_NAME_MOVE_FILES: str = "MoveFiles"

# --- Postprocessor Status Messages (English) ---
PP_STATUS_MERGING: str = "Merging video and audio..."
PP_STATUS_CONVERTING_MP3: str = "Converting to MP3..."
PP_STATUS_EXTRACTING_AUDIO: str = "Extracting audio ({codec})..."
PP_STATUS_CONVERTING_VIDEO: str = "Converting video format..."
PP_STATUS_PROCESSING_GENERIC_PP: str = "Processing via {pp_name}..."


# --- Filename Constants ---
DEFAULT_CLEANED_FILENAME: str = "downloaded_file"


# --- File Extensions ---
FINAL_MEDIA_EXTENSIONS: Set[str] = {
    ".mp4",
    ".mp3",
    ".mkv",
    ".webm",
    ".opus",
    ".ogg",
    ".m4a",
    ".flv",
    ".avi",
    ".wav",
    ".aac",
    ".mov",
    ".wmv",
}

# --- Format Choices ---
FORMAT_AUDIO_MP3: str = "Download Audio Only (MP3)"

# --- Core Status Constants ---
STATUS_COMPLETED: str = "Completed"  # <<< تمت إضافة هذا الثابت
