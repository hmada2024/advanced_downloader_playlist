# src/ui_interface.py
# -- Main application UI window class and coordinator between components --
# -- Modified to include TabView for Home and History --

import customtkinter as ctk
from typing import Optional, Dict, Any, Callable  # استيراد أنواع البيانات للتلميحات

# --- استيراد كلاسات المنطق والـ Handler ---
# استخدام Optional لأن logic_handler قد يتم حقنه بعد الإنشاء
from .logic_handler import LogicHandler, Optional

# استيراد كلاسات Mixin (التي توفر وظائف لـ UserInterface)
from .ui_state_manager import UIStateManagerMixin
from .ui_callback_handler import UICallbackHandlerMixin
from .ui_action_handler import UIActionHandlerMixin

# --- استيراد كلاسات مكونات الواجهة ---
from .ui_components.top_input_frame import TopInputFrame
from .ui_components.options_control_frame import OptionsControlFrame
from .ui_components.path_selection_frame import PathSelectionFrame
from .ui_components.bottom_controls_frame import BottomControlsFrame
from .ui_components.playlist_selector import PlaylistSelector

# --- الثوابت ---
APP_TITLE = "Advanced Downloader"  # عنوان التطبيق
INITIAL_GEOMETRY = "850x750"  # حجم النافذة الأولي
DEFAULT_STATUS = "جارٍ التهيئة..."  # رسالة الحالة الافتراضية
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
            row=6,
            column=0,
            padx=15,
            pady=(5, 5),
            sticky="ew",  # أسفل قائمة التشغيل المحتملة
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
        # يمكنك إضافة ليبل بسيط كعنصر نائب إذا أردت:
        # history_placeholder = ctk.CTkLabel(self.history_tab_frame, text="سيتم عرض السجل هنا.")
        # history_placeholder.pack(padx=20, pady=20)

        # --- الدخول في حالة الواجهة الأولية ---
        # استدعاء دالة إدارة الحالة لإعداد المظهر الخامل الأولي
        # يجب أن تعمل هذه الدالة كما هي لأنها تشير إلى الويدجتس المخزنة في 'self'
        self._enter_idle_state()

    def set_default_save_path(self, path: str) -> None:
        """
        Sets the initial text in the save path entry widget.
        Called by main.py after finding the default path.

        Args:
            path (str): The default save path string.
        """
        # يجب أن تعمل هذه الدالة بشكل صحيح لأن self.path_frame_widget موجود
        if self.path_frame_widget:  # التأكد من وجود الويدجت
            try:
                self.path_frame_widget.set_path(path)  # تعيين المسار
                print(f"UI: تم تعيين مسار الحفظ الافتراضي إلى '{path}'")
                # إذا تم جلب المعلومات *قبل* تعيين المسار الافتراضي،
                # قد نحتاج إلى إعادة تقييم حالة زر التحميل.
                # يتم التعامل مع هذا الآن داخل _enter_info_fetched_state.
            except Exception as e:
                print(
                    f"خطأ في واجهة المستخدم: تعذر تعيين المسار الافتراضي في الويدجت: {e}"
                )
        else:
            # لا يجب أن يحدث هذا إذا تم استدعاؤه بعد __init__
            print(
                "خطأ في واجهة المستخدم: ويدجت إطار المسار غير متاح لتعيين المسار الافتراضي."
            )


# --- دوال Mixin ---
# الدوال الموروثة من UIStateManagerMixin, UICallbackHandlerMixin,
# و UIActionHandlerMixin يجب أن تستمر في العمل بشكل عام لأنها
# تصل إلى الويدجتس عبر `self.widget_name` (مثل self.top_frame_widget,
# self.bottom_controls_widget)، وما زلنا نخزن هذه المراجع في `self`
# حتى لو تغير الـ master الخاص بالويدجتس إلى `self.home_tab_frame`.
# تأكد من أن أي عمليات grid داخل mixins تتعامل بشكل صحيح مع السياق
# (على سبيل المثال، `self.playlist_selector_widget.grid(...)` ستضع في شبكة الـ master الخاص بها،
# والذي هو الآن `home_tab_frame`).
