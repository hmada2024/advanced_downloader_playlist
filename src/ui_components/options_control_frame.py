# src/ui_components/options_control_frame.py
# -- ملف لمكون إطار خيارات التحميل العامة --
# Purpose: UI component for the general download options frame (format and playlist switch).

import customtkinter as ctk


class OptionsControlFrame(ctk.CTkFrame):
    """إطار يحتوي على اختيار الصيغة العامة ومفتاح وضع قائمة التشغيل."""

    """Frame containing the general format selection and the playlist mode switch."""

    def __init__(self, master, toggle_playlist_command, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.toggle_playlist_command = toggle_playlist_command

        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(3, weight=0)

        self.format_label = ctk.CTkLabel(self, text="Download Format:")
        self.format_label.grid(row=0, column=0, padx=(0, 5), pady=5, sticky="w")

        new_format_options = [
            "Download the best available quality, up to 1440p",
            "Download the best available quality, up to 1080p",
            "Download the best available quality, up to 720p",
            "Download the best available quality, up to 540p",
            "Download the best available quality, up to 480p",
            "Download up to 360p quality",
            "Download up to 240p quality",
            "Download up to 144p quality",
            "Download Audio Only (MP3)",
        ]

        self.format_combobox = ctk.CTkComboBox(
            self,
            values=new_format_options,
            width=320,
        )
        self.format_combobox.set("Download the best available quality, up to 720p")
        self.format_combobox.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.playlist_label = ctk.CTkLabel(self, text="Is Playlist?")
        self.playlist_label.grid(row=0, column=2, padx=(20, 5), pady=5, sticky="e")

        self.playlist_switch_var = ctk.StringVar(value="on")  # Default is ON
        self.playlist_switch = ctk.CTkSwitch(
            self,
            text="",
            variable=self.playlist_switch_var,
            onvalue="on",
            offvalue="off",
            command=self.toggle_playlist_command,
        )
        self.playlist_switch.grid(row=0, column=3, padx=5, pady=5, sticky="w")

    def get_format_choice(self):
        """تُرجع قيمة الصيغة العامة المختارة."""
        return self.format_combobox.get()

    def get_playlist_mode(self):
        """تُرجع `True` إذا كان وضع القائمة مفعلًا، وإلا `False`."""
        return self.playlist_switch_var.get() == "on"

    def set_playlist_mode(self, is_on):
        """تحدد حالة مفتاح وضع القائمة."""
        self.playlist_switch_var.set("on" if is_on else "off")

    def enable(self):
        """تمكين عناصر التحكم."""
        self.format_combobox.configure(state="normal")
        self.playlist_switch.configure(state="normal")

    def disable(self):
        """تعطيل عناصر التحكم."""
        self.format_combobox.configure(state="disabled")
        self.playlist_switch.configure(state="disabled")
