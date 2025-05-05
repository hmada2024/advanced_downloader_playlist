# src/ui_components/bottom_controls_frame.py
# -- ملف لمكون إطار أزرار التحكم السفلية (تحميل وإلغاء) --
# Purpose: UI component for the bottom control buttons frame (Download and Cancel).

import customtkinter as ctk
from typing import Callable, Any  # Added typing

# --- Constants ---
BTN_TXT_DOWNLOAD = "Download"
BTN_TXT_CANCEL = "Cancel"
BTN_TXT_DOWNLOAD_SELECTION = "Download Selection"  # Example specific text
COLOR_CANCEL_FG = "red"
COLOR_CANCEL_HOVER = "darkred"


class BottomControlsFrame(ctk.CTkFrame):
    """إطار يحتوي على أزرار التحميل والإلغاء."""

    """Frame containing the Download and Cancel buttons."""

    def __init__(
        self,
        master: Any,  # Typically the parent CTk window or frame
        download_command: Callable[[], None],
        cancel_command: Callable[[], None],
        **kwargs: Any
    ):
        """
        Initializes the BottomControlsFrame.
        Args:
            master (Any): The parent widget.
            download_command (Callable[[], None]): Function to call when Download is clicked.
            cancel_command (Callable[[], None]): Function to call when Cancel is clicked.
            **kwargs: Additional arguments for CTkFrame.
        """
        super().__init__(master, fg_color="transparent", **kwargs)
        self.download_command: Callable[[], None] = download_command
        self.cancel_command: Callable[[], None] = cancel_command

        # --- Grid Layout ---
        # Configure column weights for resizing behavior
        self.grid_columnconfigure(0, weight=1)  # Download button takes available space
        self.grid_columnconfigure(1, weight=0)  # Cancel button has fixed width

        # --- Widget Creation ---
        # Download Button (initially disabled)
        self.download_button = ctk.CTkButton(
            self,
            text=BTN_TXT_DOWNLOAD,
            command=self.download_command,
            state="disabled",  # Start disabled
        )
        # Place download button spanning both columns initially
        self.download_button.grid(
            row=0, column=0, columnspan=2, padx=(0, 5), pady=5, sticky="ew"
        )

        # Cancel Button (created but not initially shown)
        self.cancel_button = ctk.CTkButton(
            self,
            text=BTN_TXT_CANCEL,
            command=self.cancel_command,
            state="disabled",  # Start disabled
            fg_color=COLOR_CANCEL_FG,
            hover_color=COLOR_CANCEL_HOVER,
        )
        # Cancel button is added/removed from grid dynamically

    def show_cancel_button(self) -> None:
        """إظهار زر الإلغاء وتعديل عرض زر التحميل."""
        """Shows the Cancel button and adjusts the Download button's grid span."""
        # Make download button take only the first column
        self.download_button.grid_configure(columnspan=1)
        # Place cancel button in the second column
        self.cancel_button.grid(row=0, column=1, padx=(5, 0), pady=5, sticky="e")
        # Enable the cancel button when shown
        self.cancel_button.configure(state="normal")

    def hide_cancel_button(self) -> None:
        """إخفاء زر الإلغاء وإعادة عرض زر التحميل ليأخذ كامل العرض."""
        """Hides the Cancel button and makes the Download button span both columns again."""
        self.cancel_button.grid_remove()  # Remove from layout
        self.cancel_button.configure(state="disabled")  # Disable when hidden
        # Make download button span both columns again
        self.download_button.grid_configure(columnspan=2)

    def enable_download(self, button_text: str = BTN_TXT_DOWNLOAD_SELECTION) -> None:
        """تمكين زر التحميل وتحديد نصه."""
        """Enables the Download button and sets its text."""
        self.download_button.configure(state="normal", text=button_text)

    def disable_download(self, button_text: str = BTN_TXT_DOWNLOAD) -> None:
        """تعطيل زر التحميل وتحديد نصه."""
        """Disables the Download button and sets its text."""
        self.download_button.configure(state="disabled", text=button_text)

    def set_download_button_text(self, text: str) -> None:
        """تحديد نص زر التحميل."""
        """Sets the text of the Download button."""
        self.download_button.configure(text=text)
