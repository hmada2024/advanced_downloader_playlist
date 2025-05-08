# src/logic/utils.py
# -- ملف يحتوي على دوال مساعدة عامة للمنطق --
# -- Added image loading and processing utilities --

import sys
import re
import os
from pathlib import Path
from typing import Optional, Union, Callable, Any
import threading # For image loading thread

# Import yt_dlp specific utils carefully
try:
    import yt_dlp.utils as yt_dlp_utils
except ImportError:
    print("Warning: yt-dlp not found, ffmpeg detection might be limited.")
    yt_dlp_utils = None

# --- Third-party imports for image handling ---
try:
    from PIL import Image, ImageTk
    import customtkinter as ctk # For CTkImage
    import requests # For fetching images
    from io import BytesIO # For handling image data in memory
except ImportError as e:
    print(f"Error importing image handling libraries: {e}. Thumbnails will not work.")
    print("Please install Pillow and requests: pip install Pillow requests")
    Image = None
    ImageTk = None
    ctk = None
    requests = None
    BytesIO = None


# --- Constants ---
TEMP_FOLDER_NAME = "ASF_TEMP"  # اسم المجلد المؤقت
DEFAULT_THUMBNAIL_SIZE = (120, 67) # حجم مناسب للصور المصغرة (e.g., 16:9 ratio)
# يمكنك إنشاء صورة placeholder صغيرة بصيغة PNG أو GIF وحفظها في المشروع
# مثلاً في 'src/ui/assets/placeholder_thumbnail.png'
PLACEHOLDER_IMAGE_PATH = Path(__file__).parent.parent / "ui" / "assets" / "placeholder_thumbnail.png" # مسار افتراضي
# إذا لم يكن لديك placeholder.png حاليًا، يمكنك تجاهل هذا الجزء مؤقتًا أو استخدام None
# وسنتعامل مع الحالة التي لا يوجد فيها placeholder في الكود.

_placeholder_ctk_image: Optional[Any] = None # لتخزين الصورة المؤقتة المحملة

def get_placeholder_ctk_image(size: tuple = DEFAULT_THUMBNAIL_SIZE) -> Optional[Any]:
    """
    Loads and returns the placeholder CTkImage, resized to the given size.
    Caches the loaded image to avoid reloading.
    """
    global _placeholder_ctk_image
    if not ctk or not Image: # Ensure libraries are loaded
        return None

    # For simplicity, we'll just return a simple CTkImage if placeholder doesn't exist
    # Or you can create a dummy one on the fly (less ideal for visual appeal)
    # For now, let's assume we might not have a placeholder image file.
    # A better approach would be to bundle a placeholder image.
    # If you add a placeholder image, uncomment the loading logic.

    # if _placeholder_ctk_image is None:
    #     try:
    #         if PLACEHOLDER_IMAGE_PATH.is_file():
    #             pil_image = Image.open(PLACEHOLDER_IMAGE_PATH)
    #             _placeholder_ctk_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=size)
    #         else:
    #             print(f"Placeholder image not found at: {PLACEHOLDER_IMAGE_PATH}")
    #             # Create a dummy dark gray image if placeholder not found
    #             pil_image = Image.new("RGB", size, (60, 60, 60)) # Dark gray
    #             _placeholder_ctk_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=size)
    #     except Exception as e:
    #         print(f"Error loading or creating placeholder image: {e}")
    #         return None # Fallback to no image

    # Simple fallback: just create a CTkImage of a certain color if no actual placeholder
    try:
        pil_image = Image.new("RGB", size, (50, 50, 50)) # Dark gray as placeholder
        return ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=size)
    except Exception:
        return None


    # If using a file and caching:
    # if _placeholder_ctk_image and _placeholder_ctk_image.cget("size") == size:
    #     return _placeholder_ctk_image
    # elif _placeholder_ctk_image: # Size changed, reload
    #      _placeholder_ctk_image = None # Force reload
    #      return get_placeholder_ctk_image(size)
    # return _placeholder_ctk_image


def load_image_from_url_async(
    url: str,
    callback: Callable[[Optional[Any]], None], # CTkImage or None
    target_widget: Optional[Any] = None, # The CTk widget to update (e.g., CTkLabel)
    target_size: tuple = DEFAULT_THUMBNAIL_SIZE,
    user_agent: str = "AdvancedSpiderFetch/1.0"
) -> None:
    """
    Loads an image from a URL asynchronously in a separate thread.
    Resizes it, creates a CTkImage, and calls the callback.

    Args:
        url (str): The URL of the image.
        callback (Callable[[Optional[Any]], None]): Function to call with the CTkImage or None.
        target_widget (Optional[Any]): The CTk widget (e.g., CTkLabel) that will display the image.
                                       Used with widget.after to schedule UI updates.
        target_size (tuple): The desired (width, height) for the image.
        user_agent (str): User agent for the request.
    """
    if not Image or not requests or not BytesIO or not ctk:
        print("Image libraries not available. Cannot load image.")
        if target_widget and hasattr(target_widget, 'after'):
            target_widget.after(0, lambda: callback(get_placeholder_ctk_image(target_size)))
        else:
            callback(get_placeholder_ctk_image(target_size))
        return

    def _load_image_thread():
        ctk_image: Optional[Any] = None
        try:
            headers = {'User-Agent': user_agent}
            response = requests.get(url, stream=True, timeout=10, headers=headers)
            response.raise_for_status() # Raise an exception for bad status codes
            
            image_data = BytesIO(response.content)
            pil_image = Image.open(image_data)
            
            # Resize while maintaining aspect ratio (optional, simple resize for now)
            # For better aspect ratio preservation:
            # pil_image.thumbnail(target_size, Image.Resampling.LANCZOS)
            # If you need exact size, you might need to crop or pad after thumbnail.
            # For simplicity, we'll use resize which might distort.
            pil_image_resized = pil_image.resize(target_size, Image.Resampling.LANCZOS)

            # Convert to RGBA if it's P mode with transparency (common for GIFs/PNGs from web)
            if pil_image_resized.mode == 'P' and 'transparency' in pil_image_resized.info:
                 pil_image_resized = pil_image_resized.convert('RGBA')
            elif pil_image_resized.mode not in ['RGB', 'RGBA']:
                 pil_image_resized = pil_image_resized.convert('RGB')


            ctk_image = ctk.CTkImage(
                light_image=pil_image_resized,
                dark_image=pil_image_resized, # Use the same for both themes for simplicity
                size=target_size
            )
            # print(f"Successfully loaded and processed image from: {url}")
        except requests.exceptions.RequestException as e:
            print(f"Error fetching image from {url}: {e}")
        except Image.UnidentifiedImageError:
            print(f"Error: Cannot identify image file from {url}. Not a valid image format or corrupt.")
        except Exception as e:
            print(f"Unexpected error loading image {url}: {e}")
            import traceback
            traceback.print_exc()

        # Schedule the callback to be run in the main Tkinter thread
        if target_widget and hasattr(target_widget, 'after'):
            # If image loading failed, ctk_image will be None, send placeholder
            final_image_to_show = ctk_image or get_placeholder_ctk_image(target_size)
            target_widget.after(0, lambda: callback(final_image_to_show))
        else: # Fallback if no target_widget for .after()
            callback(ctk_image or get_placeholder_ctk_image(target_size))

    threading.Thread(target=_load_image_thread, daemon=True).start()


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
            base_path = Path(__file__).resolve().parent.parent.parent
    except Exception as e:
        print(f"Error determining base path: {e}")
        base_path = Path(".")

    bundled_ffmpeg_path = base_path / "ffmpeg_bin" / "ffmpeg.exe"
    if bundled_ffmpeg_path.is_file():
        bundled_ffprobe_path = bundled_ffmpeg_path.with_name("ffprobe.exe")
        if bundled_ffprobe_path.is_file():
            print(f"Found bundled ffmpeg and ffprobe in: {bundled_ffmpeg_path.parent}")
        else:
            print(
                f"Warning: Found bundled ffmpeg but not ffprobe at {bundled_ffprobe_path}"
            )
        return str(bundled_ffmpeg_path)
    
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

    print("Warning: ffmpeg/ffprobe not found in bundle or system PATH.")
    return None


def get_temp_dir() -> Optional[Path]:
    """
    يحصل على مسار المجلد المؤقت المخصص للتطبيق وينشئه إذا لم يكن موجودًا.
    يقع المجلد المؤقت داخل مجلد المستخدم الرئيسي.

    Returns:
        Optional[Path]: كائن Path للمجلد المؤقت، أو None إذا فشل الإنشاء.
    """
    try:
        user_home = Path.home()
        if not user_home.is_dir():
            print(f"Error: Cannot find user home directory: {user_home}")
            return None
        temp_dir_path = user_home / TEMP_FOLDER_NAME
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
    cleaned = cleaned.replace(":", " -")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = cleaned.rstrip(". ")

    return cleaned or FALLBACK_FILENAME