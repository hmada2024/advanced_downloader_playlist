# src/ui/get_links_tab.py
# -- محتوى تبويب جلب روابط قائمة التشغيل --
# Purpose: Contains the UI content and logic for the "Get Playlist Links" tab.

import customtkinter as ctk
import threading
import tkinter.filedialog as filedialog
import tkinter.messagebox as messagebox

# --- <<< تصحيح: إضافة Any إلى الاستيراد >>> ---
from typing import List, Optional, Union, Any

# --- Imports from project ---
# Assuming this file is in src/ui/, we need to go up one level ('..') then into 'logic'
from ..logic.link_fetcher import LinkFetcher
from ..logic.utils import find_ffmpeg

# Import format choices - assuming options_control_frame defines them
# If not, define them here or import from downloader_constants
try:
    from .components.options_control_frame import (
        DEFAULT_FORMAT_OPTIONS,
        DEFAULT_FORMAT_SELECTION,
    )
except ImportError:
    # Fallback if constants are moved or structure changes
    print(
        "Warning: Could not import format constants from options_control_frame. Using fallback."
    )
    DEFAULT_FORMAT_OPTIONS = ["best", "worst"]  # Basic fallback
    DEFAULT_FORMAT_SELECTION = "best"


class GetLinksTab(ctk.CTkFrame):
    """
    يمثل محتوى الواجهة الرسومية والمنطق الخاص بتبويب جلب روابط قائمة التشغيل.
    Represents the GUI content and logic for the 'Get Playlist Links' tab.
    """

    # --- <<< تصحيح: استخدام Any المستوردة هنا >>> ---
    def __init__(self, master: Any, **kwargs: Any):
        """
        تهيئة إطار تبويب جلب الروابط.
        Args:
            master (Any): الويدجت الأب (إطار التبويب من CTkTabView).
            **kwargs: وسائط إضافية لـ CTkFrame.
        """
        super().__init__(master, fg_color="transparent", **kwargs)
        print("GetLinksTab: Initializing...")

        # --- الحالة الداخلية ---
        self.cancel_event = threading.Event()
        self.current_thread: Optional[threading.Thread] = None
        self.fetched_links: List[str] = []
        self.ffmpeg_path: Optional[str] = find_ffmpeg()  # البحث عن ffmpeg عند التهيئة

        # --- تكوين تخطيط الشبكة ---
        self.grid_columnconfigure(1, weight=1)  # عمود حقل الإدخال ومربع النص يتمدد
        # الصفوف: 0: URL, 1: Format, 2: Fetch/Cancel Buttons, 3: Result Textbox, 4: Copy/Save Buttons, 5: Status
        self.grid_rowconfigure(3, weight=1)  # صف مربع النص يتمدد رأسيًا

        # --- عناصر واجهة المستخدم ---

        # 1. إدخال رابط قائمة التشغيل
        self.url_label = ctk.CTkLabel(self, text="Playlist URL:")
        self.url_label.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="w")
        self.url_entry = ctk.CTkEntry(
            self, placeholder_text="Enter YouTube Playlist URL"
        )
        self.url_entry.grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        self.url_entry.bind(
            "<Return>", lambda event: self._on_get_links_click()
        )  # ربط Enter

        # 2. اختيار الصيغة/الجودة
        self.format_label = ctk.CTkLabel(self, text="Select Quality:")
        self.format_label.grid(row=1, column=0, padx=(10, 5), pady=5, sticky="w")
        self.format_combobox = ctk.CTkComboBox(
            self, values=DEFAULT_FORMAT_OPTIONS, width=350  # عرض أكبر قليلاً
        )
        self.format_combobox.set(DEFAULT_FORMAT_SELECTION)
        self.format_combobox.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # 3. أزرار التحكم الرئيسية (جلب/إلغاء)
        self.control_button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.control_button_frame.grid(
            row=2, column=0, columnspan=2, pady=(5, 10), sticky="ew"
        )
        self.control_button_frame.grid_columnconfigure(0, weight=1)  # زر الجلب يتمدد

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
            state="disabled",  # يبدأ معطلاً
            fg_color="red",
            hover_color="darkred",
        )
        # زر الإلغاء يتم وضعه/إزالته ديناميكيًا

        # 4. مربع النص لعرض الروابط
        self.links_textbox = ctk.CTkTextbox(
            self,
            wrap="none",  # منع التفاف النص لرؤية الروابط كاملة
            state="disabled",  # يبدأ معطلاً للقراءة فقط
            height=200,  # ارتفاع افتراضي
        )
        self.links_textbox.grid(
            row=3, column=0, columnspan=2, padx=10, pady=5, sticky="nsew"
        )

        # 5. أزرار التحكم بالنتائج (نسخ/حفظ)
        self.result_button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.result_button_frame.grid(
            row=4, column=0, columnspan=2, pady=5, sticky="ew"
        )
        self.result_button_frame.grid_columnconfigure(0, weight=1)  # زر النسخ
        self.result_button_frame.grid_columnconfigure(1, weight=1)  # زر الحفظ

        self.copy_button = ctk.CTkButton(
            self.result_button_frame,
            text="Copy Links to Clipboard",
            command=self._on_copy_click,
            state="disabled",  # يبدأ معطلاً
        )
        self.copy_button.grid(row=0, column=0, padx=(10, 5), sticky="ew")

        self.save_button = ctk.CTkButton(
            self.result_button_frame,
            text="Save Links to File...",
            command=self._on_save_click,
            state="disabled",  # يبدأ معطلاً
        )
        self.save_button.grid(row=0, column=1, padx=(5, 10), sticky="ew")

        # 6. ليبل الحالة
        self.status_label = ctk.CTkLabel(
            self, text="Enter playlist URL and select quality.", text_color="gray"
        )
        self.status_label.grid(
            row=5, column=0, columnspan=2, padx=10, pady=(10, 10), sticky="ew"
        )

        print("GetLinksTab: Initialization complete.")

    # --- معالجات الأحداث (تُستدعى بواسطة أفعال المستخدم) ---

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

        # الدخول في حالة الجلب
        self._enter_fetching_state()

        # مسح النتائج السابقة
        self.fetched_links = []
        self.links_textbox.configure(state="normal")
        self.links_textbox.delete("1.0", "end")
        self.links_textbox.configure(state="disabled")

        # إعادة تعيين حدث الإلغاء
        self.cancel_event.clear()

        # إنشاء وتشغيل خيط جلب الروابط
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
                self._update_status("Links copied to clipboard!")
                # جعل رسالة النسخ مؤقتة (اختياري)
                self.after(
                    3000,
                    lambda: (
                        self._update_status("Ready.")
                        if not self.current_thread
                        else None
                    ),
                )
            else:
                self._update_status("Nothing to copy.")
        except Exception as e:
            print(f"Error copying to clipboard: {e}")
            messagebox.showerror("Copy Error", f"Could not copy links: {e}")

    def _on_save_click(self) -> None:
        """فتح مربع حوار لحفظ الروابط في ملف نصي."""
        print("GetLinksTab: Save button clicked.")
        if not self.fetched_links:
            self._update_status("No links to save.")
            return

        try:
            if file_path := filedialog.asksaveasfilename(
                title="Save Playlist Links",
                defaultextension=".txt",
                filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
                initialfile="playlist_links.txt",  # اسم افتراضي مقترح
            ):
                links_text = "\n".join(self.fetched_links)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(links_text)
                self._update_status(f"Links saved to: {file_path}")
                # جعل الرسالة مؤقتة (اختياري)
                self.after(
                    5000,
                    lambda: (
                        None if self.current_thread else self._update_status("Ready.")
                    ),
                )

        except Exception as e:
            print(f"Error saving links to file: {e}")
            messagebox.showerror("Save Error", f"Could not save links: {e}")

    def _on_cancel_click(self) -> None:
        """طلب إلغاء عملية الجلب الجارية."""
        print("GetLinksTab: Cancel button clicked.")
        if self.current_thread and self.current_thread.is_alive():
            self._update_status("Cancellation requested...")
            self.cancel_event.set()
            self.cancel_button.configure(state="disabled")  # تعطيل زر الإلغاء فورًا
        else:
            self._update_status("Nothing to cancel.")

    # --- دوال الكولباك (تُستدعى بواسطة LinkFetcher من خيط آخر) ---

    def _on_links_success(self, links: List[str]) -> None:
        """تُنفذ عند نجاح جلب الروابط (تستدعى من الخيط الرئيسي باستخدام after)."""

        def update_ui():
            print(f"GetLinksTab: Received {len(links)} links successfully.")
            self.fetched_links = links
            links_text = "\n".join(links)

            self.links_textbox.configure(state="normal")
            self.links_textbox.delete("1.0", "end")
            self.links_textbox.insert("1.0", links_text)
            self.links_textbox.configure(state="disabled")

            self.copy_button.configure(state="normal")
            self.save_button.configure(state="normal")
            self._update_status(f"Successfully fetched {len(links)} links.")

        self.after(0, update_ui)  # التنفيذ في الخيط الرئيسي فورًا

    def _on_links_error(self, error_msg: str) -> None:
        """تُنفذ عند فشل جلب الروابط (تستدعى من الخيط الرئيسي باستخدام after)."""

        def update_ui():
            print(f"GetLinksTab: Link fetch error: {error_msg}")
            self._update_status(f"Error: {error_msg}")  # تحديث ليبل الحالة بالخطأ
            # يمكن إضافة messagebox هنا إذا أردت مربع حوار منفصل
            # messagebox.showerror("Fetch Error", f"Could not fetch links:\n{error_msg}")

        self.after(0, update_ui)

    def _update_status(self, message: str) -> None:
        """تحديث ليبل الحالة الخاص بهذا التبويب (تستدعى من الخيط الرئيسي باستخدام after)."""

        def update_ui():
            # تحديد لون النص بناءً على الرسالة (اختياري)
            color = "gray"
            msg_lower = message.lower()
            if "error" in msg_lower:
                color = "red"
            elif "cancel" in msg_lower:
                color = "orange"
            elif (
                "success" in msg_lower or "saved" in msg_lower or "copied" in msg_lower
            ):
                color = "green"
            elif "fetching" in msg_lower or "preparing" in msg_lower:
                color = "blue"

            self.status_label.configure(text=message, text_color=color)

        self.after(0, update_ui)

    def _on_fetch_finished(self) -> None:
        """تُنفذ عند انتهاء عملية الجلب (نجاح، فشل، إلغاء) (تستدعى من الخيط الرئيسي باستخدام after)."""

        def update_ui():
            print("GetLinksTab: Fetch operation finished.")
            self._enter_idle_state()  # إعادة الواجهة للحالة الخاملة

        # تأخير بسيط لضمان معالجة آخر رسالة حالة قبل إعادة التمكين
        self.after(100, update_ui)

    # --- إدارة حالة الواجهة ---

    def _set_controls_state(self, state: str) -> None:
        """تمكين/تعطيل عناصر التحكم الرئيسية (الإدخال، الكومبوبوكس، زر الجلب)."""
        self.url_entry.configure(state=state)
        self.format_combobox.configure(state=state)
        self.get_links_button.configure(state=state)

    def _enter_fetching_state(self) -> None:
        """تغيير حالة الواجهة إلى وضع الجلب."""
        print("GetLinksTab: Entering fetching state.")
        self._set_controls_state("disabled")
        self.copy_button.configure(state="disabled")
        self.save_button.configure(state="disabled")
        # إظهار زر الإلغاء وتمكينه
        self.cancel_button.grid(
            row=0, column=1, padx=(5, 10), sticky="e"
        )  # وضعه بجانب زر الجلب
        self.get_links_button.grid_configure(sticky="ew")  # التأكد من تمدد زر الجلب
        self.control_button_frame.grid_columnconfigure(
            1, weight=0
        )  # Cancel button fixed width
        self.cancel_button.configure(state="normal")
        self._update_status("Fetching links...")  # تحديث الحالة فورًا

    def _enter_idle_state(self) -> None:
        """إعادة الواجهة إلى الحالة الخاملة."""
        print("GetLinksTab: Entering idle state.")
        self.current_thread = None
        self._set_controls_state("normal")
        # تمكين أزرار النسخ/الحفظ فقط إذا كان هناك روابط
        result_buttons_state = "normal" if self.fetched_links else "disabled"
        self.copy_button.configure(state=result_buttons_state)
        self.save_button.configure(state=result_buttons_state)
        # إخفاء وتعطيل زر الإلغاء
        self.cancel_button.grid_remove()
        self.cancel_button.configure(state="disabled")
        # Remove column configuration for cancel button when hidden
        self.control_button_frame.grid_columnconfigure(
            1, weight=0
        )  # Explicitly set back to 0 weight or configure as needed

        # تحديث الحالة إذا لم تكن رسالة نجاح/خطأ
        current_status = self.status_label.cget("text").lower()
        if not (
            "success" in current_status
            or "error" in current_status
            or "saved" in current_status
            or "copied" in current_status
            or "cancel" in current_status
        ):
            self._update_status("Ready.")
