# src/ui/components/bottom_controls_frame.py
# -- ملف لمكون إطار أزرار التحكم السفلية (جلب، تحميل، إلغاء) --
# Purpose: UI component for the bottom control buttons frame (Fetch, Download, Cancel).

import customtkinter as ctk
from typing import Callable, Any

# --- Constants ---
BTN_TXT_FETCH = "Fetch Info"  # <<< إضافة
BTN_TXT_DOWNLOAD = "Download"
BTN_TXT_CANCEL = "Cancel"
BTN_TXT_DOWNLOAD_SELECTION = "Download Selection"
COLOR_CANCEL_FG = "red"
COLOR_CANCEL_HOVER = "darkred"


class BottomControlsFrame(ctk.CTkFrame):
    """إطار يحتوي على أزرار جلب المعلومات والتحميل والإلغاء."""

    """Frame containing the Fetch Info, Download and Cancel buttons."""

    def __init__(
        self,
        master: Any,
        fetch_command: Callable[[], None],  # <<< إضافة
        download_command: Callable[[], None],
        cancel_command: Callable[[], None],
        **kwargs: Any
    ):
        """
        Initializes the BottomControlsFrame.
        Args:
            master (Any): The parent widget.
            fetch_command (Callable[[], None]): Function to call when Fetch Info is clicked. # <<< إضافة
            download_command (Callable[[], None]): Function to call when Download is clicked.
            cancel_command (Callable[[], None]): Function to call when Cancel is clicked.
            **kwargs: Additional arguments for CTkFrame.
        """
        super().__init__(master, fg_color="transparent", **kwargs)
        self.fetch_command: Callable[[], None] = fetch_command  # <<< إضافة
        self.download_command: Callable[[], None] = download_command
        self.cancel_command: Callable[[], None] = cancel_command

        # --- Grid Layout ---
        self.grid_columnconfigure(0, weight=1)  # Fetch button expands
        self.grid_columnconfigure(1, weight=1)  # Download button expands
        self.grid_columnconfigure(2, weight=0)  # Cancel button fixed width

        # --- Widget Creation ---
        # <<< إضافة: زر جلب المعلومات >>>
        self.fetch_button = ctk.CTkButton(
            self,
            text=BTN_TXT_FETCH,
            command=self.fetch_command,
            state="normal",  # يبدأ مفعلاً
        )
        self.fetch_button.grid(row=0, column=0, padx=(0, 5), pady=5, sticky="ew")

        self.download_button = ctk.CTkButton(
            self,
            text=BTN_TXT_DOWNLOAD,
            command=self.download_command,
            state="disabled",  # يبدأ معطلاً
        )
        self.download_button.grid(row=0, column=1, padx=(5, 0), pady=5, sticky="ew")

        self.cancel_button = ctk.CTkButton(
            self,
            text=BTN_TXT_CANCEL,
            command=self.cancel_command,
            state="disabled",
            fg_color=COLOR_CANCEL_FG,
            hover_color=COLOR_CANCEL_HOVER,
        )
        # Cancel button is added/removed from grid dynamically

    def show_cancel_button(self) -> None:
        """إظهار زر الإلغاء وتعديل أماكن الأزرار الأخرى."""
        # إعادة تعيين الأوزان لضمان توزيع المساحة بشكل صحيح
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0)  # Cancel button fixed width

        # لا حاجة لتغيير مكان زر الجلب والتحميل
        self.cancel_button.grid(
            row=0, column=2, padx=(10, 0), pady=5, sticky="e"
        )  # إضافة زر الإلغاء في العمود الثالث
        self.cancel_button.configure(state="normal")

    def hide_cancel_button(self) -> None:
        """إخفاء زر الإلغاء وإعادة الأزرار الأخرى لوضعها الطبيعي."""
        self.cancel_button.grid_remove()
        self.cancel_button.configure(state="disabled")
        # لا حاجة لتغيير مكان زر الجلب والتحميل أو الـ columnspan

    # <<< إضافة: دوال التحكم بزر الجلب >>>
    def enable_fetch(self, button_text: str = BTN_TXT_FETCH) -> None:
        """تمكين زر الجلب وتحديد نصه."""
        self.fetch_button.configure(state="normal", text=button_text)

    def disable_fetch(self, button_text: str = BTN_TXT_FETCH) -> None:
        """تعطيل زر الجلب وتحديد نصه."""
        self.fetch_button.configure(state="disabled", text=button_text)

    # <<< --- >>>

    def enable_download(self, button_text: str = BTN_TXT_DOWNLOAD_SELECTION) -> None:
        """تمكين زر التحميل وتحديد نصه."""
        self.download_button.configure(state="normal", text=button_text)

    def disable_download(self, button_text: str = BTN_TXT_DOWNLOAD) -> None:
        """تعطيل زر التحميل وتحديد نصه."""
        self.download_button.configure(state="disabled", text=button_text)

    def set_download_button_text(self, text: str) -> None:
        """تحديد نص زر التحميل."""
        self.download_button.configure(text=text)
