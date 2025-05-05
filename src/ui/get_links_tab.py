# src/ui/get_links_tab.py
# -- محتوى تبويب جلب روابط قائمة التشغيل --
# -- Modified to integrate History logging --

import customtkinter as ctk
import threading
import tkinter.filedialog as filedialog
import tkinter.messagebox as messagebox
from typing import List, Optional, Union, Any, TYPE_CHECKING

# --- Imports from project ---
from ..logic.link_fetcher import LinkFetcher
from ..logic.utils import find_ffmpeg

# Conditional import for type hinting HistoryManager
if TYPE_CHECKING:
    from ..logic.history_manager import HistoryManager

try:
    from .components.options_control_frame import (
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
    Logs successful operations to history.
    """

    def __init__(
        self,
        master: Any,
        history_manager: Optional["HistoryManager"] = None,
        **kwargs: Any,
    ):  # <<< تعديل: استقبال history_manager
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
        self.history_manager: Optional["HistoryManager"] = (
            history_manager  # <<< إضافة: تخزين history_manager
        )
        self.cancel_event = threading.Event()
        self.current_thread: Optional[threading.Thread] = None
        self.fetched_links: List[str] = []
        self.ffmpeg_path: Optional[str] = find_ffmpeg()

        # --- تكوين تخطيط الشبكة ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # --- عناصر واجهة المستخدم ---
        # (الكود الأصلي لإنشاء الويدجتس يبقى كما هو)
        # 1. URL Input
        self.url_label = ctk.CTkLabel(self, text="Playlist URL:")
        self.url_label.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="w")
        self.url_entry = ctk.CTkEntry(
            self, placeholder_text="Enter YouTube Playlist URL"
        )
        self.url_entry.grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        self.url_entry.bind("<Return>", lambda event: self._on_get_links_click())

        # 2. Format Selection
        self.format_label = ctk.CTkLabel(self, text="Select Quality:")
        self.format_label.grid(row=1, column=0, padx=(10, 5), pady=5, sticky="w")
        self.format_combobox = ctk.CTkComboBox(
            self, values=DEFAULT_FORMAT_OPTIONS, width=350
        )
        self.format_combobox.set(DEFAULT_FORMAT_SELECTION)
        self.format_combobox.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # 3. Control Buttons (Fetch/Cancel)
        self.control_button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.control_button_frame.grid(
            row=2, column=0, columnspan=2, pady=(5, 10), sticky="ew"
        )
        self.control_button_frame.grid_columnconfigure(0, weight=1)
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
        # Cancel button gridded dynamically

        # 4. Links Textbox
        self.links_textbox = ctk.CTkTextbox(
            self, wrap="none", state="disabled", height=200
        )
        self.links_textbox.grid(
            row=3, column=0, columnspan=2, padx=10, pady=5, sticky="nsew"
        )

        # 5. Result Buttons (Copy/Save)
        self.result_button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.result_button_frame.grid(
            row=4, column=0, columnspan=2, pady=5, sticky="ew"
        )
        self.result_button_frame.grid_columnconfigure(0, weight=1)
        self.result_button_frame.grid_columnconfigure(1, weight=1)
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
        self.status_label.grid(
            row=5, column=0, columnspan=2, padx=10, pady=(10, 10), sticky="ew"
        )

        print("GetLinksTab: Initialization complete.")

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
                self._update_status("Links copied to clipboard!")
                self.after(
                    3000,
                    lambda: (
                        self._update_status("Ready.")
                        if not (self.current_thread and self.current_thread.is_alive())
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
                initialfile="playlist_links.txt",
            ):
                links_text = "\n".join(self.fetched_links)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(links_text)
                self._update_status(f"Links saved to: {os.path.basename(file_path)}")
                self.after(
                    5000,
                    lambda: (
                        self._update_status("Ready.")
                        if not (self.current_thread and self.current_thread.is_alive())
                        else None
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
            self.cancel_button.configure(state="disabled")
        else:
            self._update_status("Nothing to cancel.")

    # --- دوال الكولباك ---

    def _on_links_success(self, links: List[str]) -> None:
        """تُنفذ عند نجاح جلب الروابط. تسجل في السجل."""

        # <<< إضافة: تسجيل السجل عند النجاح >>>
        if self.history_manager:
            current_url = self.url_entry.get()  # Get URL from entry field
            # Try to create a meaningful title
            title = f"Playlist Links ({len(links)} items)"
            if current_url:  # Only log if URL is present
                self.history_manager.add_entry(
                    url=current_url, title=title, operation_type="Get Links"
                )
            else:
                print("GetLinksTab Warning: URL field was empty, skipping history log.")

        def update_ui():
            # --- باقي الكود الأصلي للدالة ---
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

        self.after(0, update_ui)

    # ( _on_links_error, _update_status, _on_fetch_finished - الكود الأصلي يبقى كما هو)
    def _on_links_error(self, error_msg: str) -> None:
        """تُنفذ عند فشل جلب الروابط."""

        def update_ui():
            print(f"GetLinksTab: Link fetch error: {error_msg}")
            self._update_status(f"Error: {error_msg}", error=True)  # Pass error flag
            # Optionally show a messagebox
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
        """تحديث ليبل الحالة الخاص بهذا التبويب."""

        def update_ui():
            color = "gray"
            if error:
                color = "red"
            elif success or "saved" in message.lower() or "copied" in message.lower():
                color = "green"
            elif warning or "cancel" in message.lower():
                color = "orange"
            elif (
                info or "fetching" in message.lower() or "preparing" in message.lower()
            ):
                color = "blue"
            self.status_label.configure(text=message, text_color=color)

        self.after(0, update_ui)

    def _on_fetch_finished(self) -> None:
        """تُنفذ عند انتهاء عملية الجلب."""

        def update_ui():
            print("GetLinksTab: Fetch operation finished.")
            self._enter_idle_state()

        self.after(100, update_ui)

    # --- إدارة حالة الواجهة ---
    # ( _set_controls_state, _enter_fetching_state, _enter_idle_state - الكود الأصلي يبقى كما هو)
    def _set_controls_state(self, state: str) -> None:
        """تمكين/تعطيل عناصر التحكم الرئيسية."""
        self.url_entry.configure(state=state)
        self.format_combobox.configure(state=state)
        self.get_links_button.configure(state=state)

    def _enter_fetching_state(self) -> None:
        """تغيير حالة الواجهة إلى وضع الجلب."""
        print("GetLinksTab: Entering fetching state.")
        self._set_controls_state("disabled")
        self.copy_button.configure(state="disabled")
        self.save_button.configure(state="disabled")
        self.cancel_button.grid(row=0, column=1, padx=(5, 10), sticky="e")
        self.control_button_frame.grid_columnconfigure(
            1, weight=0
        )  # Reset weight if needed
        self.cancel_button.configure(state="normal")
        self._update_status("Fetching links...", info=True)  # Use info flag

    def _enter_idle_state(self) -> None:
        """إعادة الواجهة إلى الحالة الخاملة."""
        print("GetLinksTab: Entering idle state.")
        self.current_thread = None
        self._set_controls_state("normal")
        result_buttons_state = "normal" if self.fetched_links else "disabled"
        self.copy_button.configure(state=result_buttons_state)
        self.save_button.configure(state=result_buttons_state)
        self.cancel_button.grid_remove()
        self.cancel_button.configure(state="disabled")
        current_status_text = self.status_label.cget("text")
        current_status_color = str(self.status_label.cget("text_color"))
        # Only reset status if it wasn't a final success/error/cancel message
        if current_status_color not in ["red", "green", "orange"]:
            self._update_status("Ready.")
