# src/ui_components/bottom_controls_frame.py
# -- ملف لمكون إطار أزرار التحكم السفلية (تحميل وإلغاء) --
# Purpose: UI component for the bottom control buttons frame (Download and Cancel).

import customtkinter as ctk


class BottomControlsFrame(ctk.CTkFrame):
    """إطار يحتوي على أزرار التحميل والإلغاء."""

    """Frame containing the Download and Cancel buttons."""

    def __init__(self, master, download_command, cancel_command, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.download_command = download_command
        self.cancel_command = cancel_command

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)

        self.download_button = ctk.CTkButton(
            self, text="Download", command=self.download_command, state="disabled"
        )
        self.download_button.grid(
            row=0, column=0, columnspan=2, padx=(0, 5), pady=5, sticky="ew"
        )

        self.cancel_button = ctk.CTkButton(
            self,
            text="Cancel",
            command=self.cancel_command,
            state="disabled",
            fg_color="red",
            hover_color="darkred",
        )

    def show_cancel_button(self):
        """إظهار زر الإلغاء وتعديل عرض زر التحميل."""
        self.download_button.grid_configure(columnspan=1)
        self.cancel_button.grid(row=0, column=1, padx=(5, 0), pady=5, sticky="e")
        self.cancel_button.configure(state="normal")

    def hide_cancel_button(self):
        """إخفاء زر الإلغاء وإعادة عرض زر التحميل ليأخذ كامل العرض."""
        self.cancel_button.grid_remove()
        self.cancel_button.configure(state="disabled")
        self.download_button.grid_configure(columnspan=2)

    def enable_download(self, button_text="Download Selection"):
        """تمكين زر التحميل وتحديد نصه."""
        self.download_button.configure(state="normal", text=button_text)

    def disable_download(self, button_text="Download"):
        """تعطيل زر التحميل وتحديد نصه."""
        self.download_button.configure(state="disabled", text=button_text)

    def set_download_button_text(self, text):
        """تحديد نص زر التحميل."""
        self.download_button.configure(text=text)
