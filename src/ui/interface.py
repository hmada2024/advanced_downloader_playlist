# src/ui/ui_interface.py
# -- Main application UI window class and coordinator between components --
# -- Modified to include TabView for Home and History --

import customtkinter as ctk
from typing import Optional, Dict, Any, Callable

# --- استيراد كلاسات المنطق والـ Handler ---
# استخدام Optional لأن logic_handler قد يتم حقنه بعد الإنشاء
# استخدم '..' للخروج من مجلد 'ui' والوصول إلى 'logic'
from ..logic.logic_handler import LogicHandler, Optional

# --- استيراد كلاسات Mixin (التي توفر وظائف لـ UserInterface) ---
# استخدم '.' للاستيراد من نفس المجلد 'ui'
from .state_manager import UIStateManagerMixin
from .callback_handler import UICallbackHandlerMixin
from .action_handler import UIActionHandlerMixin

# --- استيراد كلاسات مكونات الواجهة ---
# استخدم '.' للاستيراد من نفس المجلد 'ui'، ثم ادخل 'components'
from .components.top_input_frame import TopInputFrame
from .components.options_control_frame import OptionsControlFrame
from .components.path_selection_frame import PathSelectionFrame
from .components.bottom_controls_frame import BottomControlsFrame
from .components.playlist_selector import PlaylistSelector

# --- الثوابت ---
APP_TITLE = "Advanced Downloader"  # عنوان التطبيق
INITIAL_GEOMETRY = "850x750"  # حجم النافذة الأولي
DEFAULT_STATUS = "Initializing..."  # تم تغيير رسالة الحالة الافتراضية
DEFAULT_STATUS_COLOR = "gray"  # لون الحالة الافتراضي
TAB_HOME = "Home"  # اسم تبويب الصفحة الرئيسية
TAB_HISTORY = "History"  # اسم تبويب السجل


# الكلاس الرئيسي للواجهة يرث الآن من CTk ومن Mixins الوظيفية
class UserInterface(
    ctk.CTk, UIStateManagerMixin, UICallbackHandlerMixin, UIActionHandlerMixin
):
    """
    Main application window with TabView interface.
    Initializes UI components and inherits functionality from Mixin classes for:
    - State management (UIStateManagerMixin)
    - Callback handling from logic layer (UICallbackHandlerMixin)
    - Handling user actions like button clicks (UIActionHandlerMixin)
    """

    def __init__(self, logic_handler: Optional[LogicHandler] = None) -> None:
        """
        Initializes the main window, creates UI components, links logic, and sets initial state.
        Args:
            logic_handler (Optional[LogicHandler]): Instance of the LogicHandler.
                                                     Can be None initially and set later.
        """
        super().__init__()  # تهيئة نافذة CTk

        # --- متغيرات النسخة (Instance Attributes) ---
        # معالج المنطق (يمكن تعيينه بعد التهيئة)
        self.logic: Optional[LogicHandler] = logic_handler
        # البيانات التي تم جلبها من الرابط
        self.fetched_info: Optional[Dict[str, Any]] = None
        # يتتبع العملية الحالية في الخلفية ('fetch' أو 'download')
        self.current_operation: Optional[str] = None
        # يخزن آخر تفضيل صريح للمستخدم لمفتاح وضع قائمة التشغيل
        self._last_toggled_playlist_mode: bool = (
            True  # الافتراضي هو تفعيل وضع قائمة التشغيل
        )

        # --- إعداد النافذة الأساسي ---
        self.title(APP_TITLE)  # تعيين عنوان النافذة
        self.geometry(INITIAL_GEOMETRY)  # تعيين أبعاد النافذة الأولية
        # إعدادات المظهر (يمكن جعلها قابلة للتكوين لاحقًا)
        ctk.set_appearance_mode("System")  # اتباع نسق النظام (فاتح/داكن)
        ctk.set_default_color_theme("blue")  # تعيين لون النسق

        # --- تكوين الشبكة الرئيسية للنافذة ---
        # تكوين الشبكة لعرض التبويبات (صف 0) والحالة/التقدم (صف 1، 2)
        self.grid_columnconfigure(0, weight=1)  # السماح للعمود الرئيسي بالتمدد أفقيًا
        self.grid_rowconfigure(0, weight=1)  # السماح لصف عرض التبويبات بالتمدد رأسيًا
        self.grid_rowconfigure(1, weight=0)  # صف شريط التقدم بارتفاع ثابت
        self.grid_rowconfigure(2, weight=0)  # صف رسالة الحالة بارتفاع ثابت

        # --- إنشاء عرض التبويبات ---
        self.tab_view = ctk.CTkTabview(self)  # الـ master هو النافذة الرئيسية (self)
        # وضع عرض التبويبات في الشبكة ليملأ المنطقة الرئيسية، مع ترك مساحة للتقدم/الحالة أدناه
        self.tab_view.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # --- إضافة التبويبات ---
        self.tab_view.add(TAB_HOME)  # إضافة التبويب الأول
        self.tab_view.add(TAB_HISTORY)  # إضافة التبويب الثاني
        self.tab_view.set(TAB_HOME)  # تعيين "Home" كالتبويب المرئي في البداية

        # --- الحصول على إطارات التبويبات ---
        self.home_tab_frame = self.tab_view.tab(TAB_HOME)  # إطار تبويب Home
        self.history_tab_frame = self.tab_view.tab(TAB_HISTORY)  # إطار تبويب History

        # --- تكوين تخطيط الشبكة داخل تبويب Home ---
        self.home_tab_frame.grid_columnconfigure(0, weight=1)  # العمود 0 يتمدد أفقيًا
        # افتراض أن PlaylistSelector في الصف 4 ويجب أن يتمدد رأسيًا
        self.home_tab_frame.grid_rowconfigure(4, weight=1)

        # --- إنشاء نسخ مكونات الواجهة لتبويب Home ---
        # هام: تغيير 'master' إلى 'self.home_tab_frame' للمكونات داخل تبويب Home
        self.top_frame_widget = TopInputFrame(
            self.home_tab_frame,  # الـ master الآن هو تبويب Home
            fetch_command=self.fetch_video_info,
        )
        self.options_frame_widget = OptionsControlFrame(
            self.home_tab_frame,  # الـ master الآن هو تبويب Home
            toggle_playlist_command=self.toggle_playlist_mode,
        )
        self.path_frame_widget = PathSelectionFrame(
            self.home_tab_frame,  # الـ master الآن هو تبويب Home
            browse_callback=self.browse_path_logic,
        )
        # ليبل للمحتوى الديناميكي (عنوان الفيديو أو قائمة التشغيل) داخل تبويب Home
        self.dynamic_area_label = ctk.CTkLabel(
            self.home_tab_frame,  # الـ master الآن هو تبويب Home
            text="",
            font=ctk.CTkFont(weight="bold"),
            wraplength=650,  # Added wraplength to prevent very long titles from expanding window
        )
        # محدد قائمة التشغيل (إطار قابل للتمرير لعناصر قائمة التشغيل) داخل تبويب Home
        self.playlist_selector_widget = PlaylistSelector(
            self.home_tab_frame  # الـ master الآن هو تبويب Home
        )
        # عناصر التحكم السفلية (أزرار التحميل/الإلغاء) داخل تبويب Home
        self.bottom_controls_widget = BottomControlsFrame(
            self.home_tab_frame,  # الـ master الآن هو تبويب Home
            download_command=self.start_download_ui,
            cancel_command=self.cancel_operation_ui,
        )

        # --- وضع مكونات الواجهة في شبكة إطار تبويب Home ---
        # مواقع الشبكة نسبة إلى home_tab_frame
        self.top_frame_widget.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="ew")
        self.options_frame_widget.grid(row=1, column=0, padx=15, pady=5, sticky="ew")
        self.path_frame_widget.grid(row=2, column=0, padx=15, pady=5, sticky="ew")
        self.dynamic_area_label.grid(row=3, column=0, padx=20, pady=(10, 0), sticky="w")
        # محدد قائمة التشغيل (row 4) يتم وضعه في الشبكة ديناميكيًا بواسطة _display_playlist_view (داخل home_tab_frame)
        # self.playlist_selector_widget.grid(...) # يتم بواسطة مدير الحالة
        self.bottom_controls_widget.grid(
            row=6,  # Adjusted row to leave space for playlist
            column=0,
            padx=15,
            pady=(5, 5),
            sticky="ew",
        )

        # --- إنشاء الويدجتس أسفل عرض التبويبات (في النافذة الرئيسية) ---
        # شريط التقدم (الـ master هو self - النافذة الرئيسية)
        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.set(0)  # تهيئة التقدم إلى 0

        # ليبل الحالة في الأسفل (الـ master هو self - النافذة الرئيسية)
        self.status_label = ctk.CTkLabel(
            self,
            text=DEFAULT_STATUS,  # النص الافتراضي
            text_color=DEFAULT_STATUS_COLOR,  # اللون الافتراضي
            font=ctk.CTkFont(size=13),  # حجم الخط
            justify="left",  # محاذاة لليسار للحالة متعددة الأسطر
            anchor="w",  # تثبيت النص إلى الغرب (يسار)
        )

        # --- وضع الويدجتس أسفل عرض التبويبات في الشبكة ---
        # استخدام الصف 1 و 2 من شبكة النافذة الرئيسية
        self.progress_bar.grid(row=1, column=0, padx=20, pady=(0, 5), sticky="ew")
        self.status_label.grid(row=2, column=0, padx=25, pady=(0, 10), sticky="ew")

        # --- محتوى تبويب السجل (History) (عنصر نائب) ---
        # ترك إطار history_tab_frame فارغًا الآن
        history_placeholder = ctk.CTkLabel(
            self.history_tab_frame, text="History will be shown here."
        )
        history_placeholder.pack(padx=20, pady=20)

        # --- الدخول في حالة الواجهة الأولية ---
        self._enter_idle_state()

    def set_default_save_path(self, path: str) -> None:
        """
        Sets the initial text in the save path entry widget.
        Called by main.py after finding the default path.

        Args:
            path (str): The default save path string.
        """
        if self.path_frame_widget:
            try:
                self.path_frame_widget.set_path(path)
                print(f"UI: Default save path set to '{path}'")
            except Exception as e:
                print(f"UI Error: Could not set default path in widget: {e}")
        else:
            print("UI Error: Path frame widget not available to set default path.")


# --- دوال Mixin ---
# The inherited methods from mixins should generally continue to work
# as they access widgets via `self.widget_name`. The placement of widgets
# (gridding) is handled either here in __init__ or in the state manager mixin.
