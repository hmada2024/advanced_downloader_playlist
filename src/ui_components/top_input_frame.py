# src/ui_components/top_input_frame.py
# -- ملف لمكون إطار الإدخال العلوي (الرابط وزر الجلب) --
# Purpose: UI component for the top input frame (URL entry and Fetch button).

import customtkinter as ctk


class TopInputFrame(ctk.CTkFrame):
    """إطار يحتوي على حقل إدخال الرابط وزر جلب المعلومات."""

    """Frame containing the URL input field and the Fetch Info button."""

    def __init__(self, master, fetch_command, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.fetch_command = fetch_command

        self.grid_columnconfigure(1, weight=1)

        self.url_label = ctk.CTkLabel(self, text="Video/Playlist URL:")
        self.url_label.grid(row=0, column=0, padx=(0, 5), pady=5, sticky="w")

        self.url_entry = ctk.CTkEntry(
            self, placeholder_text="Enter URL and click Fetch Info", width=350
        )
        self.url_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.fetch_button = ctk.CTkButton(
            self, text="Fetch Info", width=100, command=self.fetch_command
        )
        self.fetch_button.grid(row=0, column=2, padx=(5, 0), pady=5, sticky="e")

    def get_url(self):
        """تُرجع النص الموجود في حقل إدخال الرابط."""
        return self.url_entry.get()

    def set_url(self, url_text):
        """تحدد النص في حقل إدخال الرابط."""
        self.url_entry.delete(0, "end")
        self.url_entry.insert(0, url_text)

    def enable_fetch(self):
        """تمكين حقل الإدخال وزر الجلب."""
        self._set_fetch_state("normal", "Fetch Info")

    def disable_fetch(self, button_text="Fetching..."):
        """تعطيل حقل الإدخال وزر الجلب وتغيير نص الزر."""
        self._set_fetch_state("disabled", button_text)

    def _set_fetch_state(self, entry_state, button_text):
        """Helper method to set state for URL entry and fetch button."""
        self.url_entry.configure(state=entry_state)
        self.fetch_button.configure(
            state=entry_state, text=button_text
        )  # Button state matches entry state
