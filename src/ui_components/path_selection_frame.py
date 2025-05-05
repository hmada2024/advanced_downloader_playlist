# src/ui_components/path_selection_frame.py
# -- ملف لمكون إطار اختيار مسار الحفظ --
# Purpose: UI component for the save path selection frame.

import customtkinter as ctk
from typing import Callable, Any  # Added typing

# --- Constants ---
LABEL_PATH = "Save Location:"
PLACEHOLDER_PATH = "Select download folder"
BTN_TXT_BROWSE = "Browse"


class PathSelectionFrame(ctk.CTkFrame):
    """إطار يحتوي على حقل عرض مسار الحفظ وزر التصفح."""

    """Frame containing the save path display field and the Browse button."""

    def __init__(self, master: Any, browse_callback: Callable[[], None], **kwargs: Any):
        """
        Initializes the PathSelectionFrame.
        Args:
            master (Any): The parent widget.
            browse_callback (Callable[[], None]): Function to call when Browse button is clicked.
            **kwargs: Additional arguments for CTkFrame.
        """
        super().__init__(master, fg_color="transparent", **kwargs)
        self.browse_callback: Callable[[], None] = browse_callback

        # --- Grid Layout ---
        self.grid_columnconfigure(1, weight=1)  # Path entry expands

        # --- Widgets ---
        # Path Label
        self.path_label = ctk.CTkLabel(self, text=LABEL_PATH)
        self.path_label.grid(row=0, column=0, padx=(0, 5), pady=5, sticky="w")

        # Path Entry (starts readonly, populated by browse or default path)
        self.path_entry = ctk.CTkEntry(
            self,
            placeholder_text=PLACEHOLDER_PATH,
            state="readonly",  # User selects via Browse, doesn't type here
        )
        self.path_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # Browse Button
        self.browse_button = ctk.CTkButton(
            self,
            text=BTN_TXT_BROWSE,
            width=80,  # Fixed width for Browse button
            command=self.browse_callback,
        )
        self.browse_button.grid(row=0, column=2, padx=(5, 0), pady=5, sticky="e")

    def get_path(self) -> str:
        """تُرجع مسار الحفظ الحالي المعروض في حقل الإدخال."""
        """Returns the current save path displayed in the entry field."""
        return self.path_entry.get()

    def set_path(self, path_text: str) -> None:
        """
        تحدث النص في حقل المسار (تجعله قابلاً للكتابة مؤقتًا).
        Updates the text in the path entry field.
        Temporarily makes it 'normal' to allow insertion, then sets back to 'readonly'.

        Args:
            path_text (str): The new path text to display.
        """
        current_state: str = str(
            self.path_entry.cget("state")
        )  # Get current state as string
        try:
            # Allow setting text even if readonly for initialization/browse
            self.path_entry.configure(state="normal")
            self.path_entry.delete(0, "end")  # Clear existing text
            self.path_entry.insert(0, path_text)  # Insert the new path
            self.path_entry.configure(state="readonly")  # Force back to readonly
        except Exception as e:
            print(f"Error setting path entry text: {e}")
            # Attempt to restore original state on error
            self.path_entry.configure(state=current_state)

    def enable(self) -> None:
        """تمكين زر التصفح."""
        """Enables the Browse button."""
        self.browse_button.configure(state="normal")

    def disable(self) -> None:
        """تعطيل زر التصفح."""
        """Disables the Browse button."""
        self.browse_button.configure(state="disabled")
