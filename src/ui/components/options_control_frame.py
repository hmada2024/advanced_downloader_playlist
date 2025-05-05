# src/ui/components/options_control_frame.py
# -- ملف لمكون إطار خيارات التحميل العامة --
# Purpose: UI component for the general download options frame (format and playlist switch).

import customtkinter as ctk
from typing import Callable, Any, List

# --- Constants ---
LABEL_FORMAT = "Download Format:"
LABEL_PLAYLIST = "Is Playlist?"
DEFAULT_FORMAT_OPTIONS: List[str] = [
    "Download the best available quality, up to 1440p",
    "Download the best available quality, up to 1080p",
    "Download the best available quality, up to 720p",  # Default selection
    "Download the best available quality, up to 540p",
    "Download the best available quality, up to 480p",
    "Download up to 360p quality",
    "Download up to 240p quality",
    "Download up to 144p quality",
    "Download Audio Only (MP3)",
]
DEFAULT_FORMAT_SELECTION = "Download the best available quality, up to 720p"
PLAYLIST_SWITCH_ON = "on"
PLAYLIST_SWITCH_OFF = "off"


class OptionsControlFrame(ctk.CTkFrame):
    """إطار يحتوي على اختيار الصيغة العامة ومفتاح وضع قائمة التشغيل."""

    """Frame containing the general format selection and the playlist mode switch."""

    def __init__(
        self, master: Any, toggle_playlist_command: Callable[[], None], **kwargs: Any
    ):
        """
        Initializes the OptionsControlFrame.
        Args:
            master (Any): The parent widget.
            toggle_playlist_command (Callable[[], None]): Function called when the playlist switch changes.
            **kwargs: Additional arguments for CTkFrame.
        """
        super().__init__(master, fg_color="transparent", **kwargs)
        self.toggle_playlist_command: Callable[[], None] = toggle_playlist_command

        self.grid_columnconfigure(1, weight=1)  # Format combobox expands
        self.grid_columnconfigure(3, weight=0)  # Playlist switch fixed width

        self.format_label = ctk.CTkLabel(self, text=LABEL_FORMAT)
        self.format_label.grid(row=0, column=0, padx=(0, 5), pady=5, sticky="w")

        self.format_combobox = ctk.CTkComboBox(
            self,
            values=DEFAULT_FORMAT_OPTIONS,
            width=320,
        )
        self.format_combobox.set(DEFAULT_FORMAT_SELECTION)
        self.format_combobox.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.playlist_label = ctk.CTkLabel(self, text=LABEL_PLAYLIST)
        self.playlist_label.grid(row=0, column=2, padx=(20, 5), pady=5, sticky="e")

        self.playlist_switch_var = ctk.StringVar(value=PLAYLIST_SWITCH_ON)
        self.playlist_switch = ctk.CTkSwitch(
            self,
            text="",
            variable=self.playlist_switch_var,
            onvalue=PLAYLIST_SWITCH_ON,
            offvalue=PLAYLIST_SWITCH_OFF,
            command=self.toggle_playlist_command,
        )
        self.playlist_switch.grid(row=0, column=3, padx=5, pady=5, sticky="w")

    def get_format_choice(self) -> str:
        """تُرجع قيمة الصيغة العامة المختارة."""
        return self.format_combobox.get()

    def get_playlist_mode(self) -> bool:
        """تُرجع `True` إذا كان وضع القائمة مفعلًا، وإلا `False`."""
        return self.playlist_switch_var.get() == PLAYLIST_SWITCH_ON

    def set_playlist_mode(self, is_on: bool) -> None:
        """تحدد حالة مفتاح وضع القائمة."""
        value = PLAYLIST_SWITCH_ON if is_on else PLAYLIST_SWITCH_OFF
        self.playlist_switch_var.set(value)

    def enable(self) -> None:
        """تمكين عناصر التحكم (الكومبوبوكس والمفتاح)."""
        self.format_combobox.configure(state="normal")
        # Playlist switch state is managed by UIStateManagerMixin based on context
        # self.playlist_switch.configure(state="normal")

    def disable(self) -> None:
        """تعطيل عناصر التحكم (الكومبوبوكس والمفتاح)."""
        self.format_combobox.configure(state="disabled")
        self.playlist_switch.configure(state="disabled")
