# src/main.py
# -- ملف نقطة الدخول الرئيسي لتشغيل التطبيق --

import customtkinter as ctk
import sys
import os
import logging  # <-- استيراد مكتبة التسجيل
from pathlib import Path

# استيراد الكلاسات الرئيسية من حزمة src الجديدة
from src.ui_interface import UserInterface
from src.logic_handler import LogicHandler

# --- *** تهيئة نظام التسجيل *** ---
log_file_path = "advanced_downloader.log"
logging.basicConfig(
    level=logging.DEBUG,  # سجل كل شيء (DEBUG, INFO, WARNING, ERROR, CRITICAL) - غيره إلى INFO عند التوزيع
    format="%(asctime)s - %(levelname)-8s - %(name)-25s - %(message)s",  # تنسيق الرسائل
    handlers=[
        logging.FileHandler(log_file_path, encoding="utf-8"),  # الكتابة إلى ملف
        logging.StreamHandler(),  # عرض السجلات في الطرفية (للتطوير)
    ],
)
logger = logging.getLogger(__name__)  # الحصول على المسجل الخاص بهذا الملف
logger.info("Application starting...")
logger.info(f"Log file path: {Path(log_file_path).resolve()}")
# ---------------------------------

# Optional High DPI handling
# ... (الكود الخاص بـ set_high_dpi_awareness إذا كنت تستخدمه) ...
# if __name__ == "__main__":
#    if set_high_dpi_awareness():
#        logger.info("High DPI awareness set.")
#    else:
#        logger.warning("Could not set High DPI awareness.")


# نقطة البداية عند تشغيل السكربت مباشرة
if __name__ == "__main__":
    # التعامل مع مسار التطبيق عند التجميع بـ PyInstaller
    try:
        if getattr(sys, "frozen", False):
            application_path = os.path.dirname(sys.executable)
            logger.info(
                f"Application running as frozen executable. Path: {application_path}"
            )
        else:
            application_path = os.path.dirname(os.path.abspath(__file__))
            logger.info(f"Application running as script. Path: {application_path}")
    except Exception as e:
        application_path = os.getcwd()
        logger.exception(
            f"Error determining application path, using CWD: {application_path}",
            exc_info=e,
        )

    # --- إنشاء مكونات التطبيق ---
    logger.debug("Creating UserInterface instance.")
    app = UserInterface(logic_handler=None)

    logger.debug("Creating LogicHandler instance.")
    logic = LogicHandler(
        status_callback=app.update_status,
        progress_callback=app.update_progress,
        finished_callback=app.on_task_finished,
        info_success_callback=app.on_info_success,
        info_error_callback=app.on_info_error,
    )

    # ربط نسخة المنطق بنسخة الواجهة
    logger.debug("Linking LogicHandler to UserInterface.")
    app.logic = logic

    # --- تشغيل حلقة الأحداث الرئيسية للواجهة ---
    logger.info("Starting main UI loop.")
    try:
        app.mainloop()
    except Exception as e:
        logger.critical("An unhandled exception occurred in the main loop!", exc_info=e)
    finally:
        logger.info("Application finished.")
