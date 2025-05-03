# src/main.py
# -- ملف نقطة الدخول الرئيسي لتشغيل التطبيق --
# Purpose: Main entry point script to run the application.

import customtkinter as ctk
import sys
import os
import logging  # <-- إضافة استيراد logging

# استيراد الكلاسات الرئيسية من حزمة src الجديدة
from src.ui_interface import UserInterface
from src.logic_handler import LogicHandler

# --- *** تهيئة نظام التسجيل (Logging) *** ---
log_file_path = "advanced_downloader.log"
# تحديد مستوى التسجيل: INFO يظهر المعلومات العامة، التحذيرات، والأخطاء.
# DEBUG يظهر كل شيء (مفيد للتطوير).
# WARNING يظهر التحذيرات والأخطاء فقط.
log_level = logging.INFO  # أو logging.DEBUG للتصحيح المفصل

log_format = "%(asctime)s - %(levelname)s - [%(module)s:%(lineno)d] - %(message)s"
date_format = "%Y-%m-%d %H:%M:%S"

logging.basicConfig(
    level=log_level,
    format=log_format,
    datefmt=date_format,
    handlers=[
        logging.FileHandler(log_file_path, encoding="utf-8"),  # الكتابة إلى ملف
        logging.StreamHandler(sys.stdout),  # اختياري: العرض في الكونسول أيضاً
    ],
)
logging.info("-----------------------------------")
logging.info("Application starting...")
logging.info(f"Log level set to: {logging.getLevelName(log_level)}")
# --- *** نهاية تهيئة Logging *** ---


# Optional High DPI handling (Uncomment if needed)
# ... (كود set_high_dpi_awareness إذا كنت تستخدمه) ...

# نقطة البداية عند تشغيل السكربت مباشرة
if __name__ == "__main__":
    # --- Uncomment the line below to enable High DPI ---
    # set_high_dpi_awareness()

    logging.info("Application __main__ block entered.")

    # التعامل مع مسار التطبيق عند التجميع بـ PyInstaller
    if getattr(sys, "frozen", False):
        application_path = os.path.dirname(sys.executable)
        logging.info(
            f"Application running as frozen executable. Path: {application_path}"
        )
    else:
        try:
            application_path = os.path.dirname(os.path.abspath(__file__))
            logging.info(f"Application running as script. Path: {application_path}")
        except NameError:
            application_path = os.getcwd()
            logging.warning(
                f"Could not determine script path, using current working directory: {application_path}"
            )

    # --- إنشاء مكونات التطبيق ---
    logging.info("Initializing UI...")
    app = UserInterface(logic_handler=None)  # تمرير None مؤقتاً
    logging.info("UI Initialized.")

    logging.info("Initializing Logic Handler...")
    logic = LogicHandler(
        status_callback=app.update_status,
        progress_callback=app.update_progress,
        finished_callback=app.on_task_finished,
        info_success_callback=app.on_info_success,
        info_error_callback=app.on_info_error,
    )
    logging.info("Logic Handler Initialized.")

    # ربط نسخة المنطق بنسخة الواجهة
    app.logic = logic
    logging.info("Logic Handler linked to UI.")

    # --- تشغيل حلقة الأحداث الرئيسية للواجهة ---
    logging.info("Starting main UI event loop (app.mainloop()).")
    app.mainloop()
    logging.info("Application finished.")
    logging.info("-----------------------------------")
