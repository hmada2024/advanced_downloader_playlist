# src/ui/components/top_input_frame.py
# -- ملف لمكون إطار الإدخال العلوي (الرابط وزر اللصق) --
# Purpose: UI component for the top input frame (URL entry and Paste button).

import customtkinter as ctk
from typing import Callable, Any

# --- Constants ---
LABEL_URL = "Video/Playlist URL:"
PLACEHOLDER_URL = "Enter URL or Paste"
BTN_TXT_PASTE = "Paste"  # <<< تغيير النص


class TopInputFrame(ctk.CTkFrame):
    """إطار يحتوي على حقل إدخال الرابط وزر لصق الرابط."""

    """Frame containing the URL input field and the Paste button."""

    def __init__(
        self, master: Any, paste_command: Callable[[], None], **kwargs: Any
    ):  # <<< تغيير اسم الباراميتر
        """
        Initializes the TopInputFrame.
        Args:
            master (Any): The parent widget.
            paste_command (Callable[[], None]): Function to call when Paste button is clicked. # <<< تحديث الوصف
            **kwargs: Additional arguments for CTkFrame.
        """
        super().__init__(master, fg_color="transparent", **kwargs)
        self.paste_command: Callable[[], None] = paste_command  # <<< تغيير اسم المتغير

        self.grid_columnconfigure(1, weight=1)  # URL entry expands

        self.url_label = ctk.CTkLabel(self, text=LABEL_URL)
        self.url_label.grid(row=0, column=0, padx=(0, 5), pady=5, sticky="w")

        self.url_entry = ctk.CTkEntry(self, placeholder_text=PLACEHOLDER_URL, width=350)
        self.url_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        # <<< إزالة: ربط Enter بزر اللصق ليس منطقيًا >>>
        # self.url_entry.bind("<Return>", lambda event: self.paste_command())

        # <<< تعديل: تغيير الزر إلى زر اللصق >>>
        self.paste_button = ctk.CTkButton(
            self,
            text=BTN_TXT_PASTE,
            width=80,  # <<< تعديل العرض قليلاً
            command=self.paste_command,
        )
        self.paste_button.grid(row=0, column=2, padx=(5, 0), pady=5, sticky="e")

    def get_url(self) -> str:
        """تُرجع النص الموجود في حقل إدخال الرابط."""
        return self.url_entry.get()

    def set_url(self, url_text: str) -> None:
        """تحدد النص في حقل إدخال الرابط."""
        self.url_entry.delete(0, "end")
        self.url_entry.insert(0, url_text)

    def enable_entry(self) -> None:  # <<< تغيير اسم الدالة
        """تمكين حقل الإدخال."""
        self._set_entry_state("normal")  # <<< تبسيط التحكم

    def disable_entry(self) -> None:  # <<< تغيير اسم الدالة
        """تعطيل حقل الإدخال."""
        self._set_entry_state("disabled")  # <<< تبسيط التحكم

    def _set_entry_state(self, entry_state: str) -> None:  # <<< دالة مساعدة معدلة
        """Internal helper to set state for URL entry."""
        try:
            self.url_entry.configure(state=entry_state)
            # زر اللصق يبقى مفعلاً دائماً
            # self.paste_button.configure(state=entry_state) # <<< إزالة التحكم في زر اللصق
        except Exception as e:
            print(f"Error setting entry state: {e}")
