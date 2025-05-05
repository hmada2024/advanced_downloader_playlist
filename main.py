# main.py (الآن في المجلد الجذر للمشروع)
# -- ملف نقطة الدخول الرئيسي لتشغيل التطبيق --
# Purpose: Main entry point script to run the application.

import sys
import os
from pathlib import Path
from typing import Optional

# --- Import Core Application Classes ---
# <<<--- التعديل هنا: إضافة 'src.' قبل الوحدات الفرعية --->>>
try:
    # استيراد من الحزمة 'src'
    from src.ui.interface import UserInterface # تأكد من اسم الملف الصحيح (interface.py)
    from src.logic.logic_handler import LogicHandler
except ImportError as e:
    # Handle import errors, maybe provide guidance if run from wrong directory
    print(f"Import Error: {e}")
    # تعديل رسالة الخطأ لتناسب الحالة
    print(
        "Import Error. Ensure you are running 'python main.py' from the project's root directory"
        " (the one containing 'main.py' and the 'src' folder)"
        " and that the 'src' package and its subpackages ('ui', 'logic', 'components')"
        " contain necessary '__init__.py' files."
    )
    sys.exit(1) # Exit if core components can't be imported


# --- Optional High DPI Awareness (Windows) ---
# (الكود الخاص بـ set_high_dpi_awareness يبقى كما هو إذا كنت تستخدمه)
# ...

# --- Main Execution Block ---
if __name__ == "__main__":
    # --- Optional: Enable High DPI ---
    # set_high_dpi_awareness() # Uncomment this line if needed

    # --- Determine Application Path (for bundled resources like ffmpeg) ---
    # (الكود الخاص بتحديد المسار يبقى كما هو)
    # ...

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
    logic: LogicHandler = LogicHandler(
        status_callback=app.update_status,
        progress_callback=app.update_progress,
        finished_callback=app.on_task_finished,
        info_success_callback=app.on_info_success,
        info_error_callback=app.on_info_error,
    )

    # 5. Link the Logic Handler instance back to the UI instance
    app.logic = logic

    # --- Run the Application ---
    print("Starting application main loop...")
    app.mainloop()
    print("Application main loop finished.")