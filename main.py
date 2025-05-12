# main.py (في المجلد الجذر للمشروع)
# -- ملف نقطة الدخول الرئيسي لتشغيل التطبيق --
# -- Modified to initialize QueueTab and pass correct callbacks to LogicHandler --

import sys
import os
from pathlib import Path
from tkinter import Tk  # For potential error message box
import tkinter.messagebox  # For error message box
from typing import Optional

# --- Import Core Application Classes ---
try:
    from src.ui.interface import UserInterface
    from src.logic.logic_handler import LogicHandler
    from src.logic.history_manager import HistoryManager

    # QueueTab is initialized within UserInterface now
except ImportError as e:
    print(f"Import Error: {e}")
    print(
        "Please ensure you are running from the project root and 'src' is importable."
    )
    sys.exit(1)


# --- Optional High DPI Awareness (Windows) ---
def set_high_dpi_awareness():
    """Attempts to enable high DPI awareness on Windows."""
    if sys.platform != "win32":
        return
    try:
        from ctypes import windll

        windll.shcore.SetProcessDpiAwareness(1)
        print("High DPI awareness set (System Aware).")
    except Exception as e:
        print(f"Could not set DPI awareness: {e}")


# --- Main Execution Block ---
if __name__ == "__main__":
    set_high_dpi_awareness()

    # --- Instantiate Application Components ---

    # 1. Initialize History Manager
    history_manager = HistoryManager()
    if not history_manager.conn:
        print("FATAL ERROR: Could not initialize History Database. Exiting.")
        try:
            root = Tk()
            root.withdraw()
            tkinter.messagebox.showerror(
                "Initialization Error", "Failed to initialize the history database."
            )
            root.destroy()
        except Exception:
            pass
        sys.exit(1)

    # 2. Create the main UI window instance (passing history manager)
    # Logic Handler is linked *after* UI initialization now
    app = UserInterface(
        logic_handler=None,
        history_manager=history_manager,
    )

    # 3. Determine and Set Default Save Path (Logic Unchanged)
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
                    f"Warning: 'Downloads' folder not found. Using home directory '{home_path}'."
                )
            else:
                print("Warning: Could not find default save path.")
    except Exception as e:
        print(f"Error determining default save path: {e}")

    if default_path_to_set:
        app.set_default_save_path(default_path_to_set)

    # 4. Create the Logic Handler instance, passing the NEW set of callbacks from the UI
    #    Ensure the UI instance (app) and its queue_tab are ready first.
    if not hasattr(app, "queue_tab") or app.queue_tab is None:
        # This check is crucial if _setup_queue_tab relies on logic handler being set *first*
        # Let's adjust UI to initialize queue_tab frame structure always,
        # and pass methods even if logic handler isn't fully linked yet.
        # The methods in QueueTab should handle logic_handler being None initially if needed.
        # Or, we ensure UI.set_logic_handler is called right after creating LogicHandler.

        # Safer approach: Pass methods directly if available
        queue_add_cb = (
            getattr(app.queue_tab, "add_task", None) if app.queue_tab else None
        )
        queue_status_cb = (
            getattr(app.queue_tab, "update_task_status", None)
            if app.queue_tab
            else None
        )
        queue_progress_cb = (
            getattr(app.queue_tab, "update_task_progress", None)
            if app.queue_tab
            else None
        )
        queue_remove_cb = (
            getattr(app.queue_tab, "remove_task", None) if app.queue_tab else None
        )

        # Define dummy callbacks if queue tab isn't ready (should not happen with current UI setup)
        def dummy_queue_add(tid, title, status):
            print(f"WARN: QueueTab not ready for add: {tid}")

        def dummy_queue_status(tid, status, details):
            print(f"WARN: QueueTab not ready for status: {tid} -> {status}")

        def dummy_queue_progress(tid, value):
            print(f"WARN: QueueTab not ready for progress: {tid} -> {value}")

        def dummy_queue_remove(tid):
            print(f"WARN: QueueTab not ready for remove: {tid}")

        logic = LogicHandler(
            status_callback_main=app.update_status,  # Main status bar
            progress_callback_main=app.update_progress,  # Main progress bar
            finished_callback_main=lambda: app.on_task_finished(
                task_id=None
            ),  # Explicitly signal fetch finish
            info_success_callback=app.on_info_success,
            info_error_callback=app.on_info_error,
            # --- Pass Queue Tab Callbacks ---
            queue_add_task_callback=queue_add_cb or dummy_queue_add,
            queue_update_status_callback=queue_status_cb or dummy_queue_status,
            queue_update_progress_callback=queue_progress_cb or dummy_queue_progress,
            queue_remove_task_callback=queue_remove_cb or dummy_queue_remove,
        )

    else:
        # If UI.set_logic_handler approach is used, create logic handler first
        logic = LogicHandler(
            status_callback_main=app.update_status,
            progress_callback_main=app.update_progress,
            finished_callback_main=lambda: app.on_task_finished(task_id=None),
            info_success_callback=app.on_info_success,
            info_error_callback=app.on_info_error,
            # These will be assigned when set_logic_handler calls _setup_queue_tab
            queue_add_task_callback=lambda tid, title, status: None,  # Placeholder initially
            queue_update_status_callback=lambda tid, status, details: None,  # Placeholder
            queue_update_progress_callback=lambda tid, value: None,  # Placeholder
            queue_remove_task_callback=lambda tid: None,  # Placeholder
        )

    # 5. Link the Logic Handler back to the UI instance and finalize UI setup.
    #    This allows QueueTab setup to access the logic handler instance.
    app.set_logic_handler(
        logic
    )  # This call should now also trigger _setup_queue_tab in the UI

    # Re-assign callbacks in LogicHandler now that QueueTab is guaranteed to exist
    # This avoids the dummy callback complexity above if set_logic_handler works as intended.
    if hasattr(app, "queue_tab") and app.queue_tab:
        logic.queue_add_task_callback = app.queue_tab.add_task
        logic.queue_update_status_callback = app.queue_tab.update_task_status
        logic.queue_update_progress_callback = app.queue_tab.update_task_progress
        logic.queue_remove_task_callback = app.queue_tab.remove_task
    else:
        print(
            "FATAL ERROR: QueueTab was not initialized correctly after setting Logic Handler."
        )
        sys.exit(1)

    # --- Application Closing Handler ---
    def on_closing():
        print(
            "Main: Close button pressed. Shutting down logic handler, closing DB, destroying window."
        )
        if logic:
            logic.shutdown()  # Gracefully stop the worker thread
        if history_manager:
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
        # --- يمكنك ترك الكود هنا للتعامل مع الأخطاء الفادحة أثناء التشغيل ---
        # --- لكن تأكد من عدم استدعاء on_closing هنا إذا كان يسبب مشاكل ---
        # --- ربما تكتفي بإيقاف الـ LogicHandler وقاعدة البيانات ---
        try:
            if logic:
                logic.shutdown()
            if history_manager:
                history_manager.close_db()
        except Exception as cleanup_err:
            print(f"Error during emergency cleanup: {cleanup_err}")

    finally:
        # --- يتم تنفيذ هذا دائمًا بعد انتهاء mainloop ---
        # --- لا تستدعِ on_closing() هنا لأنها ستكون قد استُدعيت بالفعل ---
        print("Application main loop finished.")
