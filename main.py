# main.py (في المجلد الجذر للمشروع)
# -- ملف نقطة الدخول الرئيسي لتشغيل التطبيق --
# -- Modified to initialize and pass HistoryManager --

import sys
import os
from pathlib import Path
from tkinter import Tk
from typing import Optional

# --- Import Core Application Classes ---
try:
    from src.ui.interface import UserInterface
    from src.logic.logic_handler import LogicHandler
    from src.logic.history_manager import (
        HistoryManager,
    )  # <<< إضافة: استيراد HistoryManager
except ImportError as e:
    print(f"Import Error: {e}")
    print(
        "Import Error. Ensure you are running 'python main.py' from the project's root directory"
        " and that the 'src' package and subpackages contain '__init__.py' files."
    )
    # إضافة مسار src إلى sys.path كحل بديل محتمل إذا لزم الأمر
    # project_root = Path(__file__).resolve().parent
    # src_path = project_root / 'src'
    # if src_path.is_dir():
    #     print(f"Attempting to add {src_path} to sys.path")
    #     sys.path.insert(0, str(project_root))
    #     try:
    #         from src.ui.interface import UserInterface
    #         from src.logic.logic_handler import LogicHandler
    #         from src.logic.history_manager import HistoryManager
    #         print("Import successful after adding path.")
    #     except ImportError:
    #         print("Import still failed after adding path.")
    #         sys.exit(1)
    # else:
    #      print(f"src directory not found at {src_path}")
    #      sys.exit(1)
    sys.exit(1)  # Exit if core components can't be imported


# --- Optional High DPI Awareness (Windows) ---
def set_high_dpi_awareness():
    """Attempts to enable high DPI awareness on Windows."""
    try:
        from ctypes import windll

        windll.shcore.SetProcessDpiAwareness(1)  # Try 1 for system aware
        print("High DPI awareness set (System Aware).")
    except ImportError:
        print(
            "ctypes not available, cannot set DPI awareness."
        )  # Not Windows or ctypes missing
    except AttributeError:
        print(
            "Setting DPI awareness failed (might be older Windows version)."
        )  # Function doesn't exist
    except Exception as e:
        print(f"An unexpected error occurred while setting DPI awareness: {e}")


# --- Main Execution Block ---
if __name__ == "__main__":
    # --- Optional: Enable High DPI ---
    if sys.platform == "win32":  # Only attempt on Windows
        set_high_dpi_awareness()

    # --- Determine Application Path ---
    # (الكود الخاص بتحديد المسار يبقى كما هو إذا كنت تستخدمه)
    # ...

    # --- Instantiate Application Components ---

    # 1. <<< إضافة: إنشاء HistoryManager أولاً >>>
    # سيتم إنشاء ملف قاعدة البيانات في نفس مجلد main.py افتراضيًا
    history_manager = HistoryManager()
    if not history_manager.conn:  # Check if DB connection failed during init
        print("FATAL ERROR: Could not initialize History Database. Exiting.")
        # Optionally show a simple Tkinter error message before exiting
        try:
            import tkinter as tkPillow
            from tkinter import messagebox

            root = Tk.Tk()
            root.withdraw()  # Hide the main empty window
            messagebox.showerror(
                "Initialization Error",
                "Failed to initialize the history database.\nPlease check file permissions or disk space.",
            )
            root.destroy()
        except Exception as tk_error:
            print(f"Could not show Tkinter error message: {tk_error}")
        sys.exit(1)

    # 2. Create the main UI window instance, passing the history manager.
    app = UserInterface(
        logic_handler=None,
        history_manager=history_manager,  # <<< تعديل: تمرير history_manager
    )

    # 3. Determine and Set Default Save Path
    default_path_to_set: Optional[str] = None
    try:
        downloads_path: Path = Path.home() / "Downloads"
        if downloads_path.is_dir():
            default_path_to_set = str(downloads_path)
        else:
            home_path: Path = Path.home()
            if home_path.is_dir():
                default_path_to_set = str(home_path)
                print(
                    f"Warning: 'Downloads' folder not found. Using home directory '{home_path}' as default."
                )
            else:
                print(
                    "Warning: Could not find 'Downloads' or Home directory. No default save path set."
                )
    except Exception as e:
        print(f"Error determining default save path: {e}")

    if default_path_to_set:
        app.set_default_save_path(default_path_to_set)

    # 4. Create the Logic Handler instance, passing callbacks from the UI instance.
    logic = LogicHandler(
        status_callback=app.update_status,
        progress_callback=app.update_progress,
        finished_callback=app.on_task_finished,
        info_success_callback=app.on_info_success,
        info_error_callback=app.on_info_error,
    )

    # 5. Link the Logic Handler instance back to the UI instance.
    app.logic = logic

    # <<< إضافة: تسجيل دالة لإغلاق قاعدة البيانات عند إغلاق الواجهة >>>
    def on_closing():
        print("Main: Close button pressed. Closing database and destroying window.")
        history_manager.close_db()
        app.destroy()

    app.protocol("WM_DELETE_WINDOW", on_closing)

    # --- Run the Application ---
    print("Starting application main loop...")
    try:
        app.mainloop()
    except Exception as e:
        print(f"FATAL ERROR in main loop: {e}")
        import traceback

        traceback.print_exc()
        # Ensure DB is closed even on unexpected mainloop error
        history_manager.close_db()
    finally:
        # This might not be reached if process terminates abruptly
        print("Application main loop finished.")
        # history_manager.close_db() # Already closed in on_closing or finally block
