# main.py (في المجلد الجذر للمشروع)
# -- ملف نقطة الدخول الرئيسي لتشغيل التطبيق --
# -- Corrected LogicHandler instantiation --

import sys
import os
from pathlib import Path
from tkinter import Tk
import tkinter.messagebox
from typing import Optional, Dict, Callable, Any  # Added Dict, Callable, Any

# --- Import Core Application Classes ---
try:
    from src.ui.interface import UserInterface
    from src.logic.logic_handler import LogicHandler
    from src.logic.history_manager import HistoryManager
except ImportError as e:
    print(f"Import Error: {e}")
    print(
        "Please ensure you are running from the project root and 'src' is importable."
    )
    sys.exit(1)


# --- Optional High DPI Awareness (Windows) ---
def set_high_dpi_awareness():
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

    # 2. Create the main UI window instance
    app = UserInterface(logic_handler=None, history_manager=history_manager)

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
                    f"Warning: 'Downloads' folder not found. Using home directory '{home_path}'."
                )
            else:
                print("Warning: Could not find default save path.")
    except Exception as e:
        print(f"Error determining default save path: {e}")
    if default_path_to_set:
        app.set_default_save_path(default_path_to_set)

    # 4. Prepare Queue Callbacks Dictionary <<< NEW STEP >>>
    queue_callbacks_dict: Dict[str, Callable] = {}

    # Define dummy callbacks first as a fallback
    def dummy_queue_add(tid: str, title: str, status: str):
        print(f"DUMMY_WARN: QueueTab add not ready: {tid}")

    def dummy_queue_update_display(tid: str, msg: str):
        print(f"DUMMY_WARN: QueueTab update_display not ready: {tid} -> {msg}")

    def dummy_queue_update_progress(tid: str, val: float):
        print(f"DUMMY_WARN: QueueTab update_progress not ready: {tid} -> {val}")

    def dummy_queue_remove(tid: str):
        print(f"DUMMY_WARN: QueueTab remove not ready: {tid}")

    queue_callbacks_dict["add"] = dummy_queue_add
    queue_callbacks_dict["update_display"] = dummy_queue_update_display
    queue_callbacks_dict["update_progress"] = dummy_queue_update_progress
    queue_callbacks_dict["remove"] = dummy_queue_remove

    # We'll assign the real callbacks after UI and Logic are linked

    # 5. Create the Logic Handler instance <<< MODIFIED CALL >>>
    logic = LogicHandler(
        status_callback_main=app.update_status,
        progress_callback_main=app.update_progress,
        finished_callback_main=lambda: app.on_task_finished(
            task_id=None
        ),  # Signal Fetch completion
        info_success_callback=app.on_info_success,
        info_error_callback=app.on_info_error,
        queue_callbacks=queue_callbacks_dict,  # <<< Pass the dictionary
    )

    # 6. Link the Logic Handler back to the UI instance and finalize UI setup
    app.set_logic_handler(logic)  # This should create/link app.queue_tab

    # 7. Assign REAL Queue Callbacks now that app.queue_tab exists <<< NEW STEP >>>
    if hasattr(app, "queue_tab") and app.queue_tab:
        print("Main: Assigning real QueueTab callbacks to LogicHandler.")
        logic.queue_add_task_callback = app.queue_tab.add_task
        logic.queue_update_task_display_callback = app.queue_tab.update_task_display
        logic.queue_update_progress_callback = app.queue_tab.update_task_progress
        logic.queue_remove_task_callback = app.queue_tab.remove_task
    else:
        print(
            "FATAL ERROR: QueueTab was not initialized correctly after setting Logic Handler."
        )
        # Maybe show error messagebox?
        sys.exit(1)

    # --- Application Closing Handler ---
    def on_closing():
        print(
            "Main: Close button pressed. Shutting down logic handler, closing DB, destroying window."
        )
        if logic:
            logic.shutdown()
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
    finally:
        print("Application main loop finished. Running final cleanup.")
        # Ensure cleanup happens even on unexpected exit, might be redundant if on_closing is called
        if "logic" in locals() and logic:
            logic.shutdown()
        if "history_manager" in locals() and history_manager and history_manager.conn:
            history_manager.close_db()
