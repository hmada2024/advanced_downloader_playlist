# src/ui_components/top_input_frame.py
# -- ملف لمكون إطار الإدخال العلوي (الرابط وزر الجلب) --
# Purpose: UI component for the top input frame (URL entry and Fetch button).

import customtkinter as ctk
from typing import Callable, Any  # Added typing

# --- Constants ---
LABEL_URL = "Video/Playlist URL:"
PLACEHOLDER_URL = "Enter URL and click Fetch Info"
BTN_TXT_FETCH = "Fetch Info"
BTN_TXT_FETCHING = "Fetching..."


class TopInputFrame(ctk.CTkFrame):
    """إطار يحتوي على حقل إدخال الرابط وزر جلب المعلومات."""

    """Frame containing the URL input field and the Fetch Info button."""

    def __init__(self, master: Any, fetch_command: Callable[[], None], **kwargs: Any):
        """
        Initializes the TopInputFrame.
        Args:
            master (Any): The parent widget.
            fetch_command (Callable[[], None]): Function to call when Fetch button is clicked.
            **kwargs: Additional arguments for CTkFrame.
        """
        super().__init__(master, fg_color="transparent", **kwargs)
        self.fetch_command: Callable[[], None] = fetch_command

        # --- Grid Layout ---
        self.grid_columnconfigure(1, weight=1)  # URL entry expands

        # --- Widgets ---
        # URL Label
        self.url_label = ctk.CTkLabel(self, text=LABEL_URL)
        self.url_label.grid(row=0, column=0, padx=(0, 5), pady=5, sticky="w")

        # URL Entry
        self.url_entry = ctk.CTkEntry(
            self, placeholder_text=PLACEHOLDER_URL, width=350  # Adjust width as needed
        )
        self.url_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        # Bind Enter key press in URL entry to the fetch command
        self.url_entry.bind("<Return>", lambda event: self.fetch_command())

        # Fetch Button
        self.fetch_button = ctk.CTkButton(
            self,
            text=BTN_TXT_FETCH,
            width=100,  # Fixed width for Fetch button
            command=self.fetch_command,
        )
        self.fetch_button.grid(row=0, column=2, padx=(5, 0), pady=5, sticky="e")

    def get_url(self) -> str:
        """تُرجع النص الموجود في حقل إدخال الرابط."""
        """Returns the text currently in the URL entry field."""
        return self.url_entry.get()

    def set_url(self, url_text: str) -> None:
        """تحدد النص في حقل إدخال الرابط."""
        """Sets the text in the URL entry field."""
        self.url_entry.delete(0, "end")  # Clear existing text
        self.url_entry.insert(0, url_text)  # Insert new text

    def enable_fetch(self) -> None:
        """تمكين حقل الإدخال وزر الجلب."""
        """Enables the URL entry and Fetch button."""
        self._set_fetch_state("normal", BTN_TXT_FETCH)

    def disable_fetch(self, button_text: str = BTN_TXT_FETCHING) -> None:
        """تعطيل حقل الإدخال وزر الجلب وتغيير نص الزر."""
        """Disables the URL entry and Fetch button, setting the button text."""
        self._set_fetch_state("disabled", button_text)

    def _set_fetch_state(self, entry_state: str, button_text: str) -> None:
        """Helper method to set state for URL entry and fetch button."""
        """Internal helper to set the state ('normal' or 'disabled') and text for fetch controls."""
        try:
            self.url_entry.configure(state=entry_state)
            # Button state typically matches entry state when disabling/enabling fetch
            self.fetch_button.configure(state=entry_state, text=button_text)
        except Exception as e:
            print(f"Error setting fetch state: {e}")
