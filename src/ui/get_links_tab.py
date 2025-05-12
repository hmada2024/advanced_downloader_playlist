# src/ui/get_links_tab.py
# -- محتوى تبويب جلب روابط قائمة التشغيل --
# -- Modified to integrate History logging and add Paste button --

import customtkinter as ctk
import threading
import tkinter.filedialog as filedialog
import tkinter.messagebox as messagebox
import tkinter as tk  # <<< إضافة: لاستخدام الحافظة ومعالجة الأخطاء
import os  # <<< إضافة: قد يكون مطلوبًا لـ asksaveasfilename لاحقًا (للحصول على basename)
from typing import List, Optional, Union, Any, TYPE_CHECKING

# --- Imports from project ---
# استخدام مسارات نسبية صحيحة بناءً على الهيكل
# إذا كان get_links_tab.py في src/ui/ و link_fetcher.py في src/logic/
try:
    from ..logic.link_fetcher import LinkFetcher
    from ..logic.utils import find_ffmpeg
except ImportError:
    # محاولة مسار بديل إذا كان التشغيل مختلفًا
    from src.logic.link_fetcher import LinkFetcher
    from src.logic.utils import find_ffmpeg


# Conditional import for type hinting HistoryManager
if TYPE_CHECKING:
    # إذا كان history_manager.py في src/logic/
    try:
        from ..logic.history_manager import HistoryManager
    except ImportError:
        from src.logic.history_manager import HistoryManager

# استيراد الثوابت المشتركة من مكون آخر
# إذا كان options_control_frame.py في src/ui/components/
try:
    from .components.options_control_frame import (
        DEFAULT_FORMAT_OPTIONS,
        DEFAULT_FORMAT_SELECTION,
    )
except ImportError:
    # محاولة مسار بديل إذا كان التشغيل مختلفًا
    try:
        from src.ui.components.options_control_frame import (
            DEFAULT_FORMAT_OPTIONS,
            DEFAULT_FORMAT_SELECTION,
        )
    except ImportError:
        print(
            "Warning: Could not import format constants from options_control_frame. Using fallback."
        )
        DEFAULT_FORMAT_OPTIONS = ["best", "worst"]
        DEFAULT_FORMAT_SELECTION = "best"


class GetLinksTab(ctk.CTkFrame):
    """
    يمثل محتوى الواجهة الرسومية والمنطق الخاص بتبويب جلب روابط قائمة التشغيل.
    Logs successful operations to history and includes a Paste button.
    """

    def __init__(
        self,
        master: Any,
        history_manager: Optional["HistoryManager"] = None,
        # ui_interface_ref: Optional["UserInterface"] = None, # <-- لا حاجة لهذا المرجع حاليًا
        **kwargs: Any,
    ):
        """
        تهيئة إطار تبويب جلب الروابط.
        Args:
            master (Any): الويدجت الأب.
            history_manager (Optional[HistoryManager]): Instance for logging history.
            **kwargs: وسائط إضافية لـ CTkFrame.
        """
        super().__init__(master, fg_color="transparent", **kwargs)
        print("GetLinksTab: Initializing...")

        # --- الحالة الداخلية ---
        self.history_manager: Optional["HistoryManager"] = history_manager
        # self.ui_interface = ui_interface_ref # <-- لا حاجة لتخزينه حاليًا
        self.cancel_event = threading.Event()
        self.current_thread: Optional[threading.Thread] = None
        self.fetched_links: List[str] = []
        self.ffmpeg_path: Optional[str] = find_ffmpeg()

        # --- تكوين تخطيط الشبكة ---
        # Column 0: Labels
        # Column 1: Entry (expands)
        # Column 2: Paste Button (fixed)
        self.grid_columnconfigure(1, weight=1)  # <<< تعديل: جعل العمود 1 يتمدد
        self.grid_columnconfigure(2, weight=0)  # <<< إضافة: جعل العمود 2 ثابت العرض
        self.grid_rowconfigure(3, weight=1)  # Textbox row expands vertically

        # --- عناصر واجهة المستخدم ---

        # 1. URL Input and Paste Button
        self.url_label = ctk.CTkLabel(self, text="Playlist URL:")
        self.url_label.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="w")

        self.url_entry = ctk.CTkEntry(
            self,
            placeholder_text="Enter YouTube Playlist URL or Paste",  # تعديل النص التلقائي
        )
        # <<< تعديل: وضع حقل الإدخال في العمود 1 فقط >>>
        self.url_entry.grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        self.url_entry.bind("<Return>", lambda event: self._on_get_links_click())

        # <<< إضافة: زر اللصق الجديد >>>
        self.paste_button = ctk.CTkButton(
            self,
            text="Paste",
            width=80,
            command=self._paste_from_clipboard,  # ربط الزر بالدالة الجديدة
        )
        self.paste_button.grid(
            row=0, column=2, padx=(0, 10), pady=10, sticky="w"
        )  # وضعه في العمود 2

        # 2. Format Selection
        self.format_label = ctk.CTkLabel(self, text="Select Quality:")
        self.format_label.grid(row=1, column=0, padx=(10, 5), pady=5, sticky="w")
        self.format_combobox = ctk.CTkComboBox(
            self, values=DEFAULT_FORMAT_OPTIONS, width=350
        )
        self.format_combobox.set(DEFAULT_FORMAT_SELECTION)
        # <<< تعديل: جعل الكومبوبوكس يمتد عبر الأعمدة 1 و 2 >>>
        self.format_combobox.grid(
            row=1, column=1, columnspan=2, padx=5, pady=5, sticky="ew"
        )

        # 3. Control Buttons (Fetch/Cancel)
        self.control_button_frame = ctk.CTkFrame(self, fg_color="transparent")
        # <<< تعديل: جعل إطار الأزرار يمتد عبر الأعمدة 0, 1, 2 >>>
        self.control_button_frame.grid(
            row=2, column=0, columnspan=3, pady=(5, 10), sticky="ew"
        )
        self.control_button_frame.grid_columnconfigure(
            0, weight=1
        )  # زر Get Links يتمدد
        # self.control_button_frame.grid_columnconfigure(1, weight=0) # زر Cancel ثابت (يتم إضافته ديناميكيًا)

        self.get_links_button = ctk.CTkButton(
            self.control_button_frame,
            text="Get Links",
            command=self._on_get_links_click,
        )
        self.get_links_button.grid(row=0, column=0, padx=(10, 5), sticky="ew")

        self.cancel_button = ctk.CTkButton(
            self.control_button_frame,
            text="Cancel",
            command=self._on_cancel_click,
            state="disabled",
            fg_color="red",
            hover_color="darkred",
        )
        # Cancel button gridded dynamically in _enter_fetching_state

        # 4. Links Textbox
        self.links_textbox = ctk.CTkTextbox(
            self, wrap="none", state="disabled", height=200
        )
        # <<< تعديل: جعل مربع النص يمتد عبر الأعمدة 0, 1, 2 >>>
        self.links_textbox.grid(
            row=3, column=0, columnspan=3, padx=10, pady=5, sticky="nsew"
        )

        # 5. Result Buttons (Copy/Save)
        self.result_button_frame = ctk.CTkFrame(self, fg_color="transparent")
        # <<< تعديل: جعل إطار أزرار النتائج يمتد عبر الأعمدة 0, 1, 2 >>>
        self.result_button_frame.grid(
            row=4, column=0, columnspan=3, pady=5, sticky="ew"
        )
        self.result_button_frame.grid_columnconfigure(0, weight=1)  # زر النسخ يتمدد
        self.result_button_frame.grid_columnconfigure(1, weight=1)  # زر الحفظ يتمدد

        self.copy_button = ctk.CTkButton(
            self.result_button_frame,
            text="Copy Links to Clipboard",
            command=self._on_copy_click,
            state="disabled",
        )
        self.copy_button.grid(row=0, column=0, padx=(10, 5), sticky="ew")

        self.save_button = ctk.CTkButton(
            self.result_button_frame,
            text="Save Links to File...",
            command=self._on_save_click,
            state="disabled",
        )
        self.save_button.grid(row=0, column=1, padx=(5, 10), sticky="ew")

        # 6. Status Label
        self.status_label = ctk.CTkLabel(
            self, text="Enter playlist URL and select quality.", text_color="gray"
        )
        # <<< تعديل: جعل ليبل الحالة يمتد عبر الأعمدة 0, 1, 2 >>>
        self.status_label.grid(
            row=5, column=0, columnspan=3, padx=10, pady=(10, 10), sticky="ew"
        )

        print("GetLinksTab: Initialization complete.")

    # --- <<< إضافة: دالة معالجة زر اللصق >>> ---
    def _paste_from_clipboard(self) -> None:
        """يجلب النص من الحافظة ويلصقه في حقل إدخال الرابط."""
        try:
            if clipboard_content := self.clipboard_get():
                self.url_entry.delete(0, "end")  # مسح الحقل الحالي
                self.url_entry.insert(0, clipboard_content)  # لصق المحتوى الجديد
                self._update_status(
                    "URL pasted from clipboard.", info=True
                )  # تحديث الحالة
            else:
                # الحافظة فارغة ولكن العملية نجحت
                self._update_status("Clipboard is empty.", warning=True)
        except tk.TclError:
            # خطأ شائع إذا كانت الحافظة فارغة أو تحتوي على تنسيق غير نصي
            messagebox.showwarning(
                "Paste Error",
                "Could not paste from clipboard. Clipboard might be empty or contain non-text data.",
            )
            self._update_status(
                "Paste failed (clipboard empty or non-text?).", warning=True
            )
        except Exception as e:
            # معالجة أي أخطاء أخرى غير متوقعة
            messagebox.showerror(
                "Paste Error", f"An unexpected error occurred during paste:\n{e}"
            )
            self._update_status(f"Paste Error: {e}", error=True)

    # --- <<< نهاية الإضافة >>> ---

    # --- معالجات الأحداث ---
    # ( _on_get_links_click, _on_copy_click, _on_save_click, _on_cancel_click - الكود الأصلي يبقى كما هو)
    def _on_get_links_click(self) -> None:
        """يتم استدعاؤها عند الضغط على زر 'Get Links'."""
        print("GetLinksTab: Get Links button clicked.")
        playlist_url: str = self.url_entry.get().strip()
        format_choice: str = self.format_combobox.get()

        if not playlist_url:
            messagebox.showerror("Input Error", "Please enter a playlist URL.")
            return

        if self.current_thread and self.current_thread.is_alive():
            messagebox.showwarning(
                "Busy", "Already fetching links. Please wait or cancel."
            )
            return

        self._enter_fetching_state()
        self.fetched_links = []
        self.links_textbox.configure(state="normal")
        self.links_textbox.delete("1.0", "end")
        self.links_textbox.configure(state="disabled")
        self.cancel_event.clear()

        link_fetcher_instance = LinkFetcher(
            playlist_url=playlist_url,
            format_choice=format_choice,
            ffmpeg_path=self.ffmpeg_path,
            cancel_event=self.cancel_event,
            success_callback=self._on_links_success,
            error_callback=self._on_links_error,
            status_callback=self._update_status,
            finished_callback=self._on_fetch_finished,
        )
        self.current_thread = threading.Thread(
            target=link_fetcher_instance.run, daemon=True
        )
        self.current_thread.start()

    def _on_copy_click(self) -> None:
        """نسخ محتوى مربع النص إلى الحافظة."""
        print("GetLinksTab: Copy button clicked.")
        try:
            if links_text := self.links_textbox.get("1.0", "end-1c"):
                self.clipboard_clear()
                self.clipboard_append(links_text)
                self._update_status(
                    "Links copied to clipboard!", success=True
                )  # علامة نجاح
                # إعادة الحالة إلى "Ready" بعد فترة قصيرة إذا لم تكن هناك عملية جارية
                self.after(
                    3000,
                    lambda: (
                        self._update_status("Ready.")
                        if not (self.current_thread and self.current_thread.is_alive())
                        else None
                    ),
                )
            else:
                self._update_status("Nothing to copy.", warning=True)  # علامة تحذير
        except Exception as e:
            print(f"Error copying to clipboard: {e}")
            messagebox.showerror("Copy Error", f"Could not copy links: {e}")
            self._update_status(f"Copy Error: {e}", error=True)  # علامة خطأ

    def _on_save_click(self) -> None:
        """فتح مربع حوار لحفظ الروابط في ملف نصي."""
        print("GetLinksTab: Save button clicked.")
        if not self.fetched_links:
            self._update_status("No links to save.", warning=True)  # علامة تحذير
            return
        try:
            if file_path := filedialog.asksaveasfilename(
                title="Save Playlist Links",
                defaultextension=".txt",
                filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
                initialfile="playlist_links.txt",  # اسم ملف افتراضي مقترح
            ):
                links_text = "\n".join(self.fetched_links)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(links_text)
                # عرض اسم الملف فقط وليس المسار الكامل في الحالة
                saved_filename = os.path.basename(file_path)
                self._update_status(
                    f"Links saved to: {saved_filename}", success=True
                )  # علامة نجاح
                # إعادة الحالة إلى "Ready" بعد فترة أطول قليلاً
                self.after(
                    5000,
                    lambda: (
                        None
                        if self.current_thread and self.current_thread.is_alive()
                        else self._update_status("Ready.")
                    ),
                )
            # else: # المستخدم ألغى مربع الحوار
            #    self._update_status("Save cancelled.") # اختياري: إعلام بالإلغاء
        except Exception as e:
            print(f"Error saving links to file: {e}")
            messagebox.showerror("Save Error", f"Could not save links: {e}")
            self._update_status(f"Save Error: {e}", error=True)  # علامة خطأ

    def _on_cancel_click(self) -> None:
        """طلب إلغاء عملية الجلب الجارية."""
        print("GetLinksTab: Cancel button clicked.")
        if self.current_thread and self.current_thread.is_alive():
            self._update_status(
                "Cancellation requested...", warning=True
            )  # علامة تحذير/إلغاء
            self.cancel_event.set()
            # تعطيل زر الإلغاء فورًا لتقديم تغذية راجعة مرئية
            self.cancel_button.configure(state="disabled")
        else:
            self._update_status("Nothing to cancel.", info=True)  # علامة معلومة

    # --- دوال الكولباك ---

    def _on_links_success(self, links: List[str]) -> None:
        """تُنفذ عند نجاح جلب الروابط. تسجل في السجل."""
        logged = False
        if self.history_manager:
            try:
                current_url = self.url_entry.get()  # Get URL from entry field
                # Try to create a meaningful title
                title = f"Playlist Links ({len(links)} items) [{self.format_combobox.get()}]"  # إضافة الصيغة للعنوان
                if current_url:  # Only log if URL is present
                    logged = self.history_manager.add_entry(
                        url=current_url, title=title, operation_type="Get Links"
                    )
                    if logged:
                        print(
                            "GetLinksTab: Successfully logged 'Get Links' operation to history."
                        )
                    else:
                        print(
                            "GetLinksTab Warning: Failed to log 'Get Links' operation to history."
                        )
                else:
                    print(
                        "GetLinksTab Warning: URL field was empty, skipping history log."
                    )
            except Exception as log_err:
                print(f"GetLinksTab Error: Failed during history logging: {log_err}")

        # استخدام after لتحديث الواجهة من الخيط الرئيسي
        def update_ui():
            # --- باقي الكود الأصلي للدالة ---
            print(f"GetLinksTab: Received {len(links)} links successfully.")
            self.fetched_links = links
            links_text = "\n".join(links)

            self.links_textbox.configure(state="normal")
            self.links_textbox.delete("1.0", "end")
            self.links_textbox.insert("1.0", links_text)
            self.links_textbox.configure(state="disabled")

            # تمكين أزرار النتائج
            self.copy_button.configure(state="normal")
            self.save_button.configure(state="normal")
            self._update_status(
                f"Successfully fetched {len(links)} links.", success=True
            )  # علامة نجاح

        self.after(0, update_ui)

    def _on_links_error(self, error_msg: str) -> None:
        """تُنفذ عند فشل جلب الروابط."""

        def update_ui():
            print(f"GetLinksTab: Link fetch error: {error_msg}")
            self._update_status(f"Error: {error_msg}", error=True)  # Pass error flag
            # يمكنك إظهار messagebox هنا أيضًا إذا أردت
            # messagebox.showerror("Fetch Error", f"Could not fetch links:\n{error_msg}")

        self.after(0, update_ui)

    def _update_status(
        self,
        message: str,
        error: bool = False,
        success: bool = False,
        info: bool = False,
        warning: bool = False,
    ) -> None:
        """تحديث ليبل الحالة الخاص بهذا التبويب مع ألوان دلالية."""

        def update_ui():
            color = "gray"  # اللون الافتراضي
            if error:
                color = "red"
            elif success:
                color = "green"
            elif warning:  # يشمل الإلغاء أيضًا
                color = "orange"
            elif info:  # يشمل العمليات الجارية
                color = "blue"
            # تحديد المحاذاة بناءً على وجود أسطر جديدة
            justify_val = "left" if "\n" in message else "center"
            try:
                self.status_label.configure(
                    text=message, text_color=color, justify=justify_val
                )
            except Exception as e:
                print(f"GetLinksTab Error: Failed to update status label: {e}")

        # استخدام after لضمان التحديث من الخيط الرئيسي
        self.after(0, update_ui)

    def _on_fetch_finished(self) -> None:
        """تُنفذ عند انتهاء عملية الجلب (نجاح أو فشل أو إلغاء)."""

        def update_ui():
            print("GetLinksTab: Fetch operation finished.")
            self._enter_idle_state()  # إعادة الواجهة إلى الحالة الخاملة
            # لا تقم بتغيير الحالة هنا إلا إذا كانت "Ready"
            # لأنها قد تكون رسالة خطأ أو نجاح نهائية
            current_status_color = str(self.status_label.cget("text_color"))
            if current_status_color not in ["red", "green", "orange"]:
                self._update_status("Ready.")

        self.after(100, update_ui)  # تأخير بسيط للسماح بمعالجة الكولباكات الأخرى

    # --- إدارة حالة الواجهة ---

    def _set_controls_state(self, state: str) -> None:
        """تمكين/تعطيل عناصر التحكم الرئيسية (الإدخال، اللصق، الاختيار، الجلب)."""
        try:
            self.url_entry.configure(state=state)
            self.paste_button.configure(state=state)  # <<< إضافة: التحكم بزر اللصق >>>
            self.format_combobox.configure(state=state)
            self.get_links_button.configure(state=state)
        except Exception as e:
            print(f"GetLinksTab Error: Could not set controls state: {e}")

    def _enter_fetching_state(self) -> None:
        """تغيير حالة الواجهة إلى وضع الجلب."""
        print("GetLinksTab: Entering fetching state.")
        self._set_controls_state("disabled")  # تعطيل عناصر الإدخال
        # تعطيل أزرار النتائج
        self.copy_button.configure(state="disabled")
        self.save_button.configure(state="disabled")

        # إظهار وتمكين زر الإلغاء
        self.cancel_button.grid(
            row=0, column=1, padx=(5, 10), sticky="e"
        )  # وضعه بجوار زر الجلب
        self.control_button_frame.grid_columnconfigure(
            1, weight=0
        )  # التأكد من أن عمود الإلغاء لا يتمدد
        self.cancel_button.configure(state="normal")

        self._update_status("Fetching links...", info=True)  # Use info flag

    def _enter_idle_state(self) -> None:
        """إعادة الواجهة إلى الحالة الخاملة بعد انتهاء العملية."""
        print("GetLinksTab: Entering idle state.")
        self.current_thread = None  # مسح مرجع الخيط
        self._set_controls_state("normal")  # تمكين عناصر الإدخال مجددًا

        # تحديد حالة أزرار النتائج بناءً على وجود روابط
        result_buttons_state = "normal" if self.fetched_links else "disabled"
        self.copy_button.configure(state=result_buttons_state)
        self.save_button.configure(state=result_buttons_state)

        # إخفاء وتعطيل زر الإلغاء
        self.cancel_button.grid_remove()
        self.cancel_button.configure(state="disabled")

        # لا تقم بتغيير الحالة تلقائيًا هنا، دع _on_fetch_finished تقرر
        # current_status_text = self.status_label.cget("text")
        # current_status_color = str(self.status_label.cget("text_color"))
        # # Only reset status if it wasn't a final success/error/cancel message
        # if current_status_color not in ["red", "green", "orange"]:
        #     self._update_status("Ready.")
