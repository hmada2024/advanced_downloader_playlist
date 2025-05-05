# src/ui/state_manager.py
# -- Mixin class for managing UI states --
# -- Updated to control Fetch button in BottomControlsFrame --

import os
from typing import TYPE_CHECKING, Optional, List, Dict, Any, Callable

if TYPE_CHECKING:
    import customtkinter as ctk
    from .interface import UserInterface

    # Import component types
    from .components.top_input_frame import TopInputFrame
    from .components.options_control_frame import OptionsControlFrame
    from .components.path_selection_frame import PathSelectionFrame
    from .components.bottom_controls_frame import (
        BottomControlsFrame,
    )  # <<< تأكد من الاسم الصحيح
    from .components.playlist_selector import PlaylistSelector

# --- Constants ---
BTN_TXT_FETCH = "Fetch Info"  # <<< إضافة
BTN_TXT_FETCHING = "Fetching..."  # <<< إضافة (للاستخدام في زر الجلب السفلي)
BTN_TXT_DOWNLOAD = "Download"
BTN_TXT_DOWNLOADING = "Downloading..."
BTN_TXT_DOWNLOAD_SELECTION = "Download Selection"
BTN_TXT_DOWNLOAD_VIDEO = "Download Video"
BTN_TXT_SELECT_SAVE_LOCATION = "Select Save Location"
STATUS_IDLE_DEFAULT = "Enter URL or Paste, then click Fetch Info."  # <<< تحديث الرسالة
STATUS_ERROR_PROCESSING_FETCHED = "Error: Failed to process fetched information."
STATUS_FETCHING_INFO = "Fetching information..."
LABEL_PLAYLIST_TITLE = "Playlist: {title} ({count} items total)"
LABEL_VIDEO_TITLE = "Video: {title}"
LABEL_EMPTY = ""


class UIStateManagerMixin:
    """Mixin class containing methods for managing the UI state transitions."""

    if TYPE_CHECKING:
        self: "UserInterface"
        # Widgets
        top_frame_widget: TopInputFrame
        options_frame_widget: OptionsControlFrame
        path_frame_widget: PathSelectionFrame
        bottom_controls_widget: BottomControlsFrame  # <<< تأكد من الاسم الصحيح
        playlist_selector_widget: PlaylistSelector
        dynamic_area_label: ctk.CTkLabel
        progress_bar: ctk.CTkProgressBar
        # Attributes
        fetched_info: Optional[Dict[str, Any]]
        current_operation: Optional[str]
        _last_toggled_playlist_mode: bool
        # Methods
        update_status: Callable[[str], None]
        update_idletasks: Callable[[], None]

    def _enable_main_controls(self, enable_playlist_switch: bool = True) -> None:
        """Enables the main input controls (URL entry, options, path, Fetch button)."""
        try:
            # <<< تعديل: تمكين حقل الإدخال فقط في الإطار العلوي >>>
            self.top_frame_widget.enable_entry()
            # <<< --- >>>
            self.options_frame_widget.format_combobox.configure(state="normal")
            switch_state = "normal" if enable_playlist_switch else "disabled"
            self.options_frame_widget.playlist_switch.configure(state=switch_state)
            self.path_frame_widget.enable()
            # <<< إضافة: تمكين زر الجلب السفلي >>>
            self.bottom_controls_widget.enable_fetch()
            # <<< --- >>>
        except AttributeError as e:
            print(f"Error enabling main controls (widget might be missing): {e}")
        except Exception as e:
            print(f"Unexpected error enabling main controls: {e}")

    def _enter_idle_state(self) -> None:
        """Enters the idle state (ready for a new operation)."""
        print("UI_Interface: Entering idle state.")
        self._enable_main_controls(
            enable_playlist_switch=True
        )  # تمكين كل شيء بما في ذلك زر الجلب

        # <<< تعديل: تعطيل زر التحميل فقط >>>
        self.bottom_controls_widget.disable_download(button_text=BTN_TXT_DOWNLOAD)
        self.bottom_controls_widget.hide_cancel_button()

        self.dynamic_area_label.configure(text=LABEL_EMPTY)
        self.playlist_selector_widget.grid_remove()
        self.playlist_selector_widget.reset()

        self.fetched_info = None
        self.current_operation = None
        try:
            self.options_frame_widget.set_playlist_mode(True)
            self._last_toggled_playlist_mode = True
        except Exception as e:
            print(f"Error resetting playlist mode in idle state: {e}")

        self.update_status(STATUS_IDLE_DEFAULT)  # <<< تحديث الرسالة
        try:
            if self.progress_bar:
                self.progress_bar.set(0.0)
        except Exception as e:
            print(f"Error resetting progress bar: {e}")

    def _enter_fetching_state(self) -> None:
        """Enters the state while fetching information."""
        self._extracted_from__enter_downloading_state_3(
            "UI_Interface: Entering fetching state."
        )
        # <<< تعديل: تعطيل زر الجلب وزر التحميل السفليين >>>
        self.bottom_controls_widget.disable_fetch(
            button_text=BTN_TXT_FETCHING
        )  # تغيير نص زر الجلب
        self.bottom_controls_widget.disable_download()
        self.bottom_controls_widget.show_cancel_button()

        self.update_status(STATUS_FETCHING_INFO)
        try:
            if self.progress_bar:
                self.progress_bar.set(0.0)
        except Exception as e:
            print(f"Error setting progress bar for fetching state: {e}")

    def _enter_downloading_state(self) -> None:
        """Enters the state during download/processing."""
        self._extracted_from__enter_downloading_state_3(
            "UI_Interface: Entering downloading state."
        )
        self.playlist_selector_widget.disable()

        # <<< تعديل: تعطيل زر الجلب وزر التحميل السفليين >>>
        self.bottom_controls_widget.disable_fetch()  # تعطيل زر الجلب
        self.bottom_controls_widget.disable_download(button_text=BTN_TXT_DOWNLOADING)
        self.bottom_controls_widget.show_cancel_button()

    # TODO Rename this here and in `_enter_fetching_state` and `_enter_downloading_state`
    def _extracted_from__enter_downloading_state_3(self, arg0):
        print(arg0)
        self.top_frame_widget.disable_entry()
        self.options_frame_widget.disable()
        self.path_frame_widget.disable()

    def _display_playlist_view(self) -> None:
        """Sets up and displays the playlist selection view."""
        # --- يبقى الكود كما هو ---
        if not self.fetched_info:
            print("UI State Error: _display_playlist_view called without fetched_info.")
            return
        playlist_title: str = self.fetched_info.get("title", "Untitled Playlist")
        entries: List[Dict[str, Any]] = self.fetched_info.get("entries", [])
        total_items: int = len(entries)
        self.dynamic_area_label.configure(
            text=LABEL_PLAYLIST_TITLE.format(title=playlist_title, count=total_items)
        )
        self.playlist_selector_widget.populate_items(entries)
        self.playlist_selector_widget.enable()
        self.playlist_selector_widget.grid(
            row=4, column=0, padx=20, pady=(5, 10), sticky="nsew"
        )
        print("UI_Interface: Playlist frame gridded and populated.")

    def _enter_info_fetched_state(self) -> None:
        """Enters the state after information has been successfully fetched."""
        if not self.fetched_info:
            print(
                "UI State Error: _enter_info_fetched_state called without fetched_info."
            )
            self._enter_idle_state()
            self.update_status(STATUS_ERROR_PROCESSING_FETCHED)
            return

        is_actually_playlist: bool = isinstance(self.fetched_info.get("entries"), list)
        self._enable_main_controls(
            enable_playlist_switch=is_actually_playlist
        )  # تمكين زر الجلب هنا أيضًا

        if is_actually_playlist:
            self.options_frame_widget.set_playlist_mode(
                self._last_toggled_playlist_mode
            )
        else:
            self.options_frame_widget.set_playlist_mode(False)

        is_playlist_mode_on: bool = self.options_frame_widget.get_playlist_mode()
        should_show_playlist_view: bool = is_playlist_mode_on and is_actually_playlist

        print(
            f"UI_Interface: Entering info fetched state. Actual playlist: {is_actually_playlist}, "
            f"Switch ON: {is_playlist_mode_on}, Show Playlist View: {should_show_playlist_view}"
        )

        self.bottom_controls_widget.hide_cancel_button()
        save_path: str = self.path_frame_widget.get_path()
        # <<< تعديل: التحكم بزر التحميل السفلي >>>
        if save_path and os.path.isdir(save_path):
            btn_text: str = (
                BTN_TXT_DOWNLOAD_SELECTION
                if should_show_playlist_view
                else BTN_TXT_DOWNLOAD_VIDEO
            )
            self.bottom_controls_widget.enable_download(
                button_text=btn_text
            )  # تمكين زر التحميل
        else:
            self.bottom_controls_widget.disable_download(
                button_text=BTN_TXT_SELECT_SAVE_LOCATION
            )  # تعطيل زر التحميل

        # --- بقية الكود لتحديث عرض القائمة أو الفيديو يبقى كما هو ---
        if should_show_playlist_view:
            self._display_playlist_view()
        else:
            self.playlist_selector_widget.grid_remove()
            video_title: str = self.fetched_info.get("title", "Untitled Video")
            if hasattr(self, "dynamic_area_label"):
                self.dynamic_area_label.configure(
                    text=LABEL_VIDEO_TITLE.format(title=video_title)
                )
            else:
                print(
                    "Warning: dynamic_area_label not found in _enter_info_fetched_state"
                )

        try:
            if self.progress_bar:
                self.progress_bar.set(0.0)
        except Exception as e:
            print(f"Error resetting progress bar in info fetched state: {e}")

        self.update_idletasks()
