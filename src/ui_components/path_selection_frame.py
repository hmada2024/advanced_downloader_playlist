# src/ui_components/path_selection_frame.py
# -- ملف لمكون إطار اختيار مسار الحفظ --
# Purpose: UI component for the save path selection frame.

import customtkinter as ctk

# tkinter is only used by the action handler now
# from tkinter import filedialog


class PathSelectionFrame(ctk.CTkFrame):
    """إطار يحتوي على حقل عرض مسار الحفظ وزر التصفح."""

    """Frame containing the save path display field and the Browse button."""

    def __init__(self, master, browse_callback, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.browse_callback = browse_callback

        self.grid_columnconfigure(1, weight=1)

        self.path_label = ctk.CTkLabel(self, text="Save Location:")
        self.path_label.grid(row=0, column=0, padx=(0, 5), pady=5, sticky="w")

        # Start with an empty placeholder, default path set by main.py later
        self.path_entry = ctk.CTkEntry(
            self, placeholder_text="Select download folder", state="readonly"
        )
        self.path_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.browse_button = ctk.CTkButton(
            self, text="Browse", width=80, command=self.browse_callback
        )
        self.browse_button.grid(row=0, column=2, padx=(5, 0), pady=5, sticky="e")

    def get_path(self):
        """تُرجع مسار الحفظ الحالي."""
        return self.path_entry.get()

    def set_path(self, path_text):
        """
        تحدث النص في حقل المسار (تجعله قابلاً للكتابة مؤقتًا).
        Updates the text in the path field (makes it writable temporarily).
        """
        current_state = self.path_entry.cget("state")
        # Allow setting text even if readonly for initialization/browse
        self.path_entry.configure(state="normal")
        self.path_entry.delete(0, "end")
        self.path_entry.insert(0, path_text)
        self.path_entry.configure(state="readonly")  # Force back to readonly

    def enable(self):
        """تمكين زر التصفح."""
        self.browse_button.configure(state="normal")

    def disable(self):
        """تعطيل زر التصفح."""
        self.browse_button.configure(state="disabled")
