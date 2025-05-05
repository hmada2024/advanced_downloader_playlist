# src/ui/action_handler.py
# -- Mixin class for handling user actions from the UI --

import os
import tkinter as tk  # <<< إضافة: لاستخدام الحافظة
from tkinter import filedialog, messagebox
from typing import TYPE_CHECKING, Optional, Dict, Any, Callable

# --- Imports from current package/subpackages ---
if TYPE_CHECKING:
    import customtkinter as ctk
    from .interface import UserInterface
    from ..logic.logic_handler import LogicHandler

    # Import component types
    from .components.path_selection_frame import PathSelectionFrame
    from .components.top_input_frame import TopInputFrame
    from .components.bottom_controls_frame import BottomControlsFrame
    from .components.playlist_selector import PlaylistSelector
    from .components.options_control_frame import OptionsControlFrame

# --- Constants ---
# Import constants from state_manager (assuming they are defined there or kept here)
# For simplicity, redefine them here if they are UI specific button texts/labels
# If they were in state_manager, use: from .state_manager import BTN_TXT_DOWNLOAD_SELECTION, ...
BTN_TXT_DOWNLOAD = "Download"
BTN_TXT_FETCHING = "Fetching..."
BTN_TXT_DOWNLOADING = "Downloading..."
BTN_TXT_DOWNLOAD_SELECTION = "Download Selection"
BTN_TXT_DOWNLOAD_VIDEO = "Download Video"
BTN_TXT_SELECT_SAVE_LOCATION = "Select Save Location"
LABEL_EMPTY = ""  # Assuming empty label text is needed

# --- Constants for Message Box Titles and Messages ---
# Titles
TITLE_INPUT_ERROR = "Input Error"
TITLE_PATH_ERROR = "Path Error"
TITLE_SELECTION_ERROR = "Selection Error"
TITLE_CONFIRM_SINGLE = "Confirm Single Download"
TITLE_LOGIC_ERROR = "Logic Error"
TITLE_ERROR = "Error"  # Generic error title

# Messages
MSG_URL_EMPTY = "Please enter a URL."
MSG_PATH_INVALID_DIR = "Selected path is not a valid directory:\n{path}"
MSG_NO_PLAYLIST_ITEMS_SELECTED = "No playlist items selected for download."
MSG_CONFIRM_SINGLE_BODY = "This is a playlist, but playlist mode is off.\nDo you want to download only the first video/item based on the URL?"
MSG_URL_MISSING = "URL is missing."
MSG_SAVE_PATH_MISSING = "Save location is missing."
MSG_SAVE_PATH_INVALID = "Save location is not a valid directory."
MSG_FETCH_INFO_FIRST = "Fetch info first before downloading."
MSG_MISMATCH_STATE = "Mismatch between UI state and fetched info during download."
MSG_LOGIC_HANDLER_MISSING = "UI_Interface Error: Logic handler not available."
TITLE_PASTE_ERROR = "Paste Error"  # <<< إضافة
MSG_PASTE_FAILED = "Could not paste from clipboard. Clipboard might be empty or contain non-text data."  # <<< إضافة

# Operation Types
OP_FETCH = "fetch"
OP_DOWNLOAD = "download"


class UIActionHandlerMixin:
    """Mixin class containing methods for handling user actions and initiating logic operations."""

    if TYPE_CHECKING:
        self: "UserInterface"
        # Widgets
        path_frame_widget: PathSelectionFrame
        top_frame_widget: TopInputFrame
        bottom_controls_widget: BottomControlsFrame  # <<< Note: widget name might need update if changed in interface.py
        playlist_selector_widget: PlaylistSelector
        options_frame_widget: OptionsControlFrame
        dynamic_area_label: ctk.CTkLabel
        # Attributes
        fetched_info: Optional[Dict[str, Any]]
        logic: Optional[LogicHandler]
        current_operation: Optional[str]
        _last_toggled_playlist_mode: bool
        # Methods
        _enter_fetching_state: Callable[[], None]
        _enter_downloading_state: Callable[[], None]
        _enter_info_fetched_state: Callable[[], None]
        _enter_idle_state: Callable[[], None]
        update_status: Callable[[str], None]
        # Tkinter/CTk methods needed
        clipboard_get: Callable[[], str]

    # <<< إضافة: دالة لمعالجة زر اللصق >>>
    def paste_url_action(self) -> None:
        """Gets content from clipboard and pastes it into the URL entry field."""
        try:
            if clipboard_content := self.clipboard_get():
                self.top_frame_widget.set_url(
                    clipboard_content
                )  # Set URL in the widget
                self.update_status("URL pasted from clipboard.")
            else:
                self.update_status("Clipboard is empty.")
        except tk.TclError:
            # This error often occurs if clipboard is empty or has non-text data
            messagebox.showwarning(TITLE_PASTE_ERROR, MSG_PASTE_FAILED)
            self.update_status("Paste failed. Clipboard might be empty or non-text.")
        except Exception as e:
            messagebox.showerror(
                TITLE_PASTE_ERROR, f"An unexpected error occurred during paste:\n{e}"
            )
            self.update_status(f"Paste Error: {e}")

    # <<< --- >>>

    def browse_path_logic(self) -> None:
        """Opens directory dialog, updates path widget, and enables download if appropriate."""
        if directory := filedialog.askdirectory(title="Select Download Folder"):
            self.path_frame_widget.set_path(directory)

            if self.fetched_info and os.path.isdir(directory):
                # <<< تعديل: استخدم bottom_controls_widget للتحكم بزر التحميل >>>
                is_download_disabled = (
                    self.bottom_controls_widget.download_button.cget("state")
                    == "disabled"
                )
                if is_download_disabled:
                    is_playlist_mode = self.options_frame_widget.get_playlist_mode()
                    is_actually_playlist = isinstance(
                        self.fetched_info.get("entries"), list
                    )
                    show_playlist_view = is_playlist_mode and is_actually_playlist
                    btn_text = (
                        BTN_TXT_DOWNLOAD_SELECTION
                        if show_playlist_view
                        else BTN_TXT_DOWNLOAD_VIDEO
                    )
                    # <<< تعديل: استدعاء الدالة من bottom_controls_widget >>>
                    self.bottom_controls_widget.enable_download(button_text=btn_text)
            elif not os.path.isdir(directory):
                messagebox.showwarning(
                    TITLE_PATH_ERROR,
                    MSG_PATH_INVALID_DIR.format(path=directory),
                )

    def fetch_video_info(self) -> None:
        """Initiates the process to fetch info for the entered URL."""
        # <<< ملاحظة: هذه الدالة الآن تُستدعى بواسطة الزر السفلي 'Fetch Info' >>>
        url: str = self.top_frame_widget.get_url()
        if not url:
            messagebox.showerror(TITLE_INPUT_ERROR, MSG_URL_EMPTY)
            return

        # --- بقية منطق الدالة يبقى كما هو ---
        self.fetched_info = None
        self.playlist_selector_widget.grid_remove()
        self.dynamic_area_label.configure(text=LABEL_EMPTY)

        self.current_operation = OP_FETCH
        self._last_toggled_playlist_mode = self.options_frame_widget.get_playlist_mode()
        self._enter_fetching_state()

        if self.logic:
            # Store URL for history logging (as done previously in interface.py)
            self._current_fetch_url = url
            self.logic.start_info_fetch(url)
        else:
            self._handle_missing_logic_handler()

    # --- بقية دوال Mixin (toggle_playlist_mode, start_download_ui, _handle_missing_logic_handler) تبقى كما هي ---
    # ...

    def toggle_playlist_mode(self) -> None:
        """Handles the manual toggling of the 'Is Playlist?' switch."""
        print("UI_Interface: Playlist switch toggled manually.")
        self._last_toggled_playlist_mode = self.options_frame_widget.get_playlist_mode()
        if self.fetched_info:
            self._enter_info_fetched_state()

    def start_download_ui(self) -> None:
        """Initiates the download process based on current selections."""
        url: str = self.top_frame_widget.get_url()
        save_path: str = self.path_frame_widget.get_path()
        format_choice: str = self.options_frame_widget.get_format_choice()
        is_playlist_mode_on: bool = self.options_frame_widget.get_playlist_mode()

        if not url:
            messagebox.showerror(TITLE_ERROR, MSG_URL_MISSING)
            return
        if not save_path:
            messagebox.showerror(TITLE_ERROR, MSG_SAVE_PATH_MISSING)
            return
        if not os.path.isdir(save_path):
            messagebox.showerror(TITLE_ERROR, MSG_SAVE_PATH_INVALID)
            return
        if not self.fetched_info:
            messagebox.showerror(TITLE_ERROR, MSG_FETCH_INFO_FIRST)
            return

        playlist_items_string: Optional[str] = None
        selected_items_count: int = 0
        total_playlist_count: int = 0
        is_actually_playlist: bool = isinstance(self.fetched_info.get("entries"), list)

        if is_actually_playlist:
            total_playlist_count = len(self.fetched_info.get("entries", []))

        if is_playlist_mode_on and is_actually_playlist:
            playlist_items_string = (
                self.playlist_selector_widget.get_selected_items_string()
            )
            if not playlist_items_string:
                messagebox.showwarning(
                    TITLE_SELECTION_ERROR, MSG_NO_PLAYLIST_ITEMS_SELECTED
                )
                return
            selected_items_count = len(playlist_items_string.split(","))
            print(
                f"UI: Starting playlist download. Selected: {selected_items_count}, Total: {total_playlist_count}, Items: {playlist_items_string}, Format: {format_choice}"
            )
            is_download_target_playlist = True

        elif not is_playlist_mode_on and self.fetched_info:
            if is_actually_playlist:
                if not messagebox.askyesno(
                    TITLE_CONFIRM_SINGLE, MSG_CONFIRM_SINGLE_BODY
                ):
                    return
                print(
                    f"UI: Starting single item download (first from playlist). Format: {format_choice}"
                )
            else:
                print(f"UI: Starting single video download. Format: {format_choice}")
            selected_items_count = 1
            is_download_target_playlist = False

        else:
            messagebox.showerror(TITLE_LOGIC_ERROR, MSG_MISMATCH_STATE)
            return

        self.current_operation = OP_DOWNLOAD
        self._enter_downloading_state()

        if self.logic:
            self.logic.start_download(
                url=url,
                save_path=save_path,
                format_choice=format_choice,
                is_playlist=is_download_target_playlist,
                playlist_items=playlist_items_string,
                selected_items_count=selected_items_count,
                total_playlist_count=total_playlist_count,
            )
        else:
            self._handle_missing_logic_handler()

    def _handle_missing_logic_handler(self):
        """Handles the case where the logic handler is missing."""
        print(MSG_LOGIC_HANDLER_MISSING)
        self.update_status(MSG_LOGIC_HANDLER_MISSING)
        self._enter_idle_state()

    def cancel_operation_ui(self) -> None:
        """Requests cancellation of the active background operation."""
        print("UI_Interface: Cancel button pressed.")
        if self.current_operation:
            self.update_status("Cancellation requested...")
        if self.logic:
            self.logic.cancel_operation()
        else:
            print("UI_Interface: No logic handler available to cancel.")
            self._enter_idle_state()
