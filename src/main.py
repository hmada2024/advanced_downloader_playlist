# src/main.py
# -- ملف نقطة الدخول الرئيسي لتشغيل التطبيق --
# Purpose: Main entry point script to run the application.

import sys
import os
from pathlib import Path
from typing import Optional

# --- Import Core Application Classes ---
# Ensure correct import paths now that main.py is inside src
try:
    # <<<--- التعديل هنا: إزالة 'src.' واستخدام استيراد مباشر للوحدات الشقيقة --->>>
    from ui.interface import UserInterface  # كان اسمه interface.py, تم تصحيحه هنا
    from logic.logic_handler import LogicHandler
except ImportError as e:
    # Handle import errors, maybe provide guidance if run from wrong directory
    print(f"Import Error: {e}")
    # تعديل رسالة الخطأ لتناسب الحالة الجديدة
    print(
        "Import Error. Ensure you are running this script correctly"
        " (e.g., using 'python -m src.main' from the project root)"
        " and all necessary __init__.py files exist in 'src' and its subdirectories ('ui', 'logic', 'components')."
    )
    sys.exit(1)  # Exit if core components can't be imported


# --- Optional High DPI Awareness (Windows) ---
# Uncomment the block below and the call in `if __name__ == "__main__":`
# if you experience blurry UI elements on high-resolution Windows displays.
# Requires 'ctypes' module.
# def set_high_dpi_awareness() -> bool:
#     """Attempts to set high DPI awareness for the application on Windows."""
#     try:
#         from ctypes import windll
#         # Try newer API first (Windows 10 1703+)
#         PROCESS_PER_MONITOR_DPI_AWARE_V2 = 2
#         windll.shcore.SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE_V2)
#         print("High DPI awareness set (Per-Monitor v2).")
#         return True
#     except (ImportError, AttributeError, OSError):
#         print("Could not set Per-Monitor v2 DPI awareness.")
#         try:
#             # Fallback to older API
#             windll.user32.SetProcessDPIAware()
#             print("High DPI awareness set (System Aware).")
#             return True
#         except (ImportError, AttributeError, OSError):
#             print("Could not set System DPI awareness.")
#             return False
#     except Exception as e:
#         print(f"An error occurred while setting DPI awareness: {e}")
#         return False


# --- Main Execution Block ---
if __name__ == "__main__":
    # --- Optional: Enable High DPI ---
    # set_high_dpi_awareness() # Uncomment this line if needed

    # --- Determine Application Path (for bundled resources like ffmpeg) ---
    # This is handled within logic/utils.py now, no specific need here unless
    # accessing other bundled files directly from main.py, which is unlikely.

    # --- Instantiate Application Components ---
    # 1. Create the main UI window instance first. Logic handler is initially None.
    app: UserInterface = UserInterface(logic_handler=None)

    # 2. Determine Default Save Path (User's Downloads folder)
    default_path_to_set: Optional[str] = None
    try:
        # Standard Downloads folder path
        downloads_path: Path = Path.home() / "Downloads"
        if downloads_path.is_dir():  # Check if the directory exists
            default_path_to_set = str(downloads_path)
        else:
            # Fallback to user's home directory if Downloads doesn't exist
            home_path: Path = Path.home()
            if home_path.is_dir():
                default_path_to_set = str(home_path)
                print(
                    f"Warning: 'Downloads' folder not found. Using home directory '{home_path}' as default save path."
                )
            else:
                # Very unlikely case where home directory is also inaccessible
                print(
                    "Warning: Could not find 'Downloads' or Home directory. No default save path set."
                )
    except Exception as e:
        # Catch any errors during path finding (e.g., permissions)
        print(f"Error determining default save path: {e}")

    # 3. Set the default path in the UI *after* the UI is initialized
    if default_path_to_set:
        # Use the dedicated method in the UI class
        app.set_default_save_path(default_path_to_set)

    # 4. Create the Logic Handler instance, passing callback methods from the UI instance
    # These callbacks allow the logic layer (running in background threads)
    # to safely update the UI layer (running in the main thread).
    logic: LogicHandler = LogicHandler(
        status_callback=app.update_status,  # Method from UICallbackHandlerMixin
        progress_callback=app.update_progress,  # Method from UICallbackHandlerMixin
        finished_callback=app.on_task_finished,  # Method from UICallbackHandlerMixin
        info_success_callback=app.on_info_success,  # Method from UICallbackHandlerMixin
        info_error_callback=app.on_info_error,  # Method from UICallbackHandlerMixin
    )

    # 5. Link the Logic Handler instance back to the UI instance
    # Now the UI instance (e.g., in UIActionHandlerMixin) can call methods on `self.logic`
    app.logic = logic

    # --- Run the Application ---
    # Start the main event loop for the Tkinter/CustomTkinter application.
    # This makes the window appear and respond to user interactions.
    print("Starting application main loop...")
    app.mainloop()
    print("Application main loop finished.")
