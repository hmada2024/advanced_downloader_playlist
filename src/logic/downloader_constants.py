# src/logic/downloader_constants.py
# -- ملف يحتوي على الثوابت المستخدمة في عملية التحميل --

from typing import Set

# --- Status Messages ---
STATUS_STARTING_DOWNLOAD: str = "Starting download..."
STATUS_CONNECTING: str = "Connecting..."
STATUS_PROCESSING: str = "Processing..."
STATUS_PROCESSING_FILE: str = "Processing downloaded file..."
STATUS_FINISHED_PREFIX: str = "Finished: "
STATUS_PROCESSING_PREFIX: str = "Processing: "
STATUS_ERROR_PREFIX: str = "Download Error: "
STATUS_ERROR_YT_DLP: str = "Error during download/processing reported by yt-dlp."
STATUS_WARNING_FFMPEG_MISSING: str = (
    "Warning: FFmpeg needed for conversion but not found. Process might fail or download original format."
)
STATUS_WARNING_FFPROBE_MISSING: str = (
    "Warning: ffprobe.exe might be missing. Some features may not work."
)
STATUS_RENAME_FAILED_WARNING: str = (
    "Warning: Could not rename '{filename}'. Error: {error}"
)
STATUS_ORGANIZE_FILES: str = "جاري تنظيم الملفات النهائية..."
STATUS_UNEXPECTED_ERROR: str = (
    "Unexpected Error ({error_type})! Check logs/console for details."
)
STATUS_FINAL_PROCESSING: str = "جاري المعالجة النهائية..."
STATUS_DOWNLOAD_CANCELLED: str = "Download Cancelled."  # Added for consistency


# --- Postprocessor Names (match yt-dlp internal names) ---
PP_NAME_MERGER: str = "FFmpegMerger"
PP_NAME_EXTRACT_AUDIO: str = "FFmpegExtractAudio"
PP_NAME_CONVERT_VIDEO: str = "FFmpegVideoConvertor"
PP_NAME_MOVE_FILES: str = "MoveFiles"


# --- Postprocessor Status Messages ---
PP_STATUS_MERGING: str = "جاري دمج الفيديو والصوت..."
PP_STATUS_CONVERTING_MP3: str = "جاري التحويل إلى MP3..."
PP_STATUS_EXTRACTING_AUDIO: str = "جاري استخراج الصوت ({codec})..."
PP_STATUS_CONVERTING_VIDEO: str = "جاري تحويل صيغة الفيديو..."
PP_STATUS_PROCESSING_GENERIC_PP: str = "جاري المعالجة بواسطة {pp_name}..."


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
}

# --- Format Choices (used in utils, but good to keep related constants together) ---
FORMAT_AUDIO_MP3: str = "Download Audio Only (MP3)"
