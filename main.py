# -- ملف نقطة الدخول الرئيسي لتشغيل التطبيق --
# Purpose: Main entry point script to run the application.

import customtkinter as ctk
import sys
import os
from pathlib import Path  # <-- إضافة: لاستخدام Path.home()

# استيراد الكلاسات الرئيسية من حزمة src بالأسماء الجديدة
# Import the main classes from the src package with new names
from src.ui_interface import UserInterface  # <-- تم التعديل: إزالة الشرطة السفلية
from src.logic_handler import LogicHandler  # <-- تم التعديل: إزالة الشرطة السفلية

# Optional High DPI handling (Uncomment if needed)
# try:
#     from ctypes import windll, byref, sizeof, c_int
# except ImportError:
#     pass # Ignore if not on Windows or ctypes not available

# def set_high_dpi_awareness():
#     """Attempts to set high DPI awareness for the application."""
#     try:
#         # PROCESS_SYSTEM_DPI_AWARE = 1, PROCESS_PER_MONITOR_DPI_AWARE = 2
#         PROCESS_PER_MONITOR_DPI_AWARE_V2 = 2
#         windll.shcore.SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE_V2)
#         print("High DPI awareness set (Per-Monitor v2).")
#         return True
#     except AttributeError:
#         print("Could not set Per-Monitor v2 DPI awareness (likely older Windows or not Windows).")
#         try:
#             windll.user32.SetProcessDPIAware()
#             print("High DPI awareness set (System Aware).")
#             return True
#         except AttributeError:
#             print("Could not set System DPI awareness.")
#             return False
#     except Exception as e:
#         print(f"An error occurred while setting DPI awareness: {e}")
#         return False

# نقطة البداية عند تشغيل السكربت مباشرة
# Entry point when script is run directly
if __name__ == "__main__":
    # # --- Uncomment the line below to enable High DPI ---
    # set_high_dpi_awareness()

    # التعامل مع مسار التطبيق عند التجميع بـ PyInstaller
    # Handle application path when bundled with PyInstaller
    if getattr(sys, "frozen", False):
        application_path = os.path.dirname(sys.executable)
    else:
        try:
            application_path = os.path.dirname(os.path.abspath(__file__))
        except NameError:
            application_path = os.getcwd()

    # --- إنشاء مكونات التطبيق --- Instantiate application components ---
    # إنشاء نسخة الواجهة أولاً Create UI instance first
    app = UserInterface(logic_handler=None)

    # --- إضافة: تحديد مسار الحفظ الافتراضي --- Start: Determine Default Save Path ---
    default_path_to_set = None
    try:
        downloads_path = Path.home() / "Downloads"
        if downloads_path.is_dir():  # التحقق من وجود المجلد Check if directory exists
            default_path_to_set = str(downloads_path)
        else:
            # إذا لم يوجد مجلد Downloads، حاول استخدام مجلد المنزل
            # If Downloads folder doesn't exist, try using the home directory
            home_path = Path.home()
            if home_path.is_dir():
                default_path_to_set = str(home_path)
                print(
                    f"Warning: 'Downloads' folder not found. Using home directory '{home_path}' as default save path."
                )
            else:
                print(
                    "Warning: Could not find 'Downloads' or Home directory. No default save path set."
                )
    except Exception as e:
        print(f"Error determining default save path: {e}")

    # قم بتعيين المسار الافتراضي في الواجهة إذا تم العثور عليه
    # Set the default path in the UI if found
    if default_path_to_set:
        # التأكد من أن الواجهة جاهزة قبل استدعاء الدالة (يتم استدعاؤه بعد التهيئة وقبل mainloop)
        # Ensure UI is ready before calling the method (called after init, before mainloop)
        app.set_default_save_path(default_path_to_set)
    # --- إضافة: تحديد مسار الحفظ الافتراضي --- End: Determine Default Save Path ---

    # إنشاء نسخة المنطق وتمرير دوال الكول باك من الواجهة إليه Create logic instance and pass UI callbacks
    logic = LogicHandler(
        status_callback=app.update_status,
        progress_callback=app.update_progress,
        finished_callback=app.on_task_finished,
        info_success_callback=app.on_info_success,
        info_error_callback=app.on_info_error,
    )

    # ربط نسخة المنطق بنسخة الواجهة Link logic instance to UI instance
    app.logic = logic

    # --- تشغيل حلقة الأحداث الرئيسية للواجهة --- Run the main UI event loop ---
    app.mainloop()
