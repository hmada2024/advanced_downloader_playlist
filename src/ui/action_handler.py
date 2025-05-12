# src/ui/action_handler.py
# -- Mixin class for handling user actions from the UI --
# -- Updated status message on adding task --

import os
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import TYPE_CHECKING, Optional, Dict, Any, Callable

# --- Imports ---
if TYPE_CHECKING:
    import customtkinter as ctk
    from .interface import UserInterface
    from ..logic.logic_handler import LogicHandler

    # Component types
    from .components.path_selection_frame import PathSelectionFrame
    from .components.top_input_frame import TopInputFrame
    from .components.bottom_controls_frame import BottomControlsFrame
    from .components.playlist_selector import PlaylistSelector
    from .components.options_control_frame import OptionsControlFrame

# --- Constants ---
# Button text reflects adding to queue
BTN_TXT_DOWNLOAD = "Add to Queue"
BTN_TXT_FETCHING = "Fetching..."
# BTN_TXT_DOWNLOADING = "Adding..." # No longer needed as UI resets instantly
BTN_TXT_DOWNLOAD_SELECTION = "Add Selection to Queue"
BTN_TXT_DOWNLOAD_VIDEO = "Add Video to Queue"
BTN_TXT_SELECT_SAVE_LOCATION = "Select Save Location"
LABEL_EMPTY = ""

# Message Box Titles and Messages (English where static)
TITLE_INPUT_ERROR = "Input Error"
TITLE_PATH_ERROR = "Path Error"
TITLE_SELECTION_ERROR = "Selection Error"
TITLE_CONFIRM_SINGLE = "Confirm Single Item"
TITLE_LOGIC_ERROR = "Logic Error"
TITLE_ERROR = "Error"
TITLE_QUEUE_ERROR = "Queue Error"

MSG_URL_EMPTY = "Please enter a URL."
MSG_PATH_INVALID_DIR = "Selected path is not a valid directory:\n{path}"
MSG_NO_PLAYLIST_ITEMS_SELECTED = "No playlist items selected to add to queue."
MSG_CONFIRM_SINGLE_BODY = "This is a playlist, but playlist mode is off.\nDo you want to add only the first video/item (based on URL) to the queue?"
MSG_URL_MISSING = "URL is missing."
MSG_SAVE_PATH_MISSING = "Save location is missing."
MSG_SAVE_PATH_INVALID = "Save location is not a valid directory."
MSG_FETCH_INFO_FIRST = "Fetch info first before adding to queue."
MSG_MISMATCH_STATE = "Mismatch between UI state and fetched info when adding to queue."
MSG_LOGIC_HANDLER_MISSING = "UI Error: Logic handler not available."
TITLE_PASTE_ERROR = "Paste Error"
MSG_PASTE_FAILED = "Could not paste from clipboard."
MSG_QUEUE_ADD_FAILED = "Failed to add task to download queue. Check logs."

# Operation Types
OP_FETCH = "fetch"


class UIActionHandlerMixin:
    """Mixin class containing methods for handling user actions and initiating logic operations."""

    if TYPE_CHECKING:
        self: "UserInterface"
        # Widgets
        path_frame_widget: PathSelectionFrame
        top_frame_widget: TopInputFrame
        bottom_controls_widget: BottomControlsFrame
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
        _enter_info_fetched_state: Callable[[], None]
        _enter_idle_state: Callable[[], None]
        update_status: Callable[
            ..., None
        ]  # Signature potentially changed in base class
        clipboard_get: Callable[[], str]

    # --- Paste URL Action ---
    def paste_url_action(self) -> None:
        """Gets content from clipboard and pastes it into the URL entry field."""
        # (No changes needed here)
        try:
            if clipboard_content := self.clipboard_get():
                self.top_frame_widget.set_url(clipboard_content)
                self.update_status("URL pasted from clipboard.")
            else:
                self.update_status("Clipboard is empty.")
        except tk.TclError:
            messagebox.showwarning(TITLE_PASTE_ERROR, MSG_PASTE_FAILED)
            self.update_status("Paste failed (clipboard empty or non-text?).")
        except Exception as e:
            messagebox.showerror(TITLE_PASTE_ERROR, f"Paste Error:\n{e}")
            self.update_status(f"Paste Error: {e}")

    # --- Browse Path Action ---
    def browse_path_logic(self) -> None:
        """Opens directory dialog, updates path widget, and enables Add button if appropriate."""
        # (No changes needed here, uses updated button text constants)
        if directory := filedialog.askdirectory(title="Select Download Folder"):
            self.path_frame_widget.set_path(directory)
            if self.fetched_info and os.path.isdir(directory):
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
                        BTN_TXT_DOWNLOAD_SELECTION  # "Add Selection to Queue"
                        if show_playlist_view
                        else BTN_TXT_DOWNLOAD_VIDEO  # "Add Video to Queue"
                    )
                    self.bottom_controls_widget.enable_download(button_text=btn_text)
            elif not os.path.isdir(directory):
                messagebox.showwarning(
                    TITLE_PATH_ERROR, MSG_PATH_INVALID_DIR.format(path=directory)
                )

    # --- Fetch Info Action ---
    def fetch_video_info(self) -> None:
        """Initiates the process to fetch info for the entered URL."""
        # (No changes needed here)
        url: str = self.top_frame_widget.get_url()
        if not url:
            messagebox.showerror(TITLE_INPUT_ERROR, MSG_URL_EMPTY)
            return
        if self.current_operation == OP_FETCH:
            messagebox.showwarning("Busy", "Already fetching information.")
            return

        self.fetched_info = None
        self.playlist_selector_widget.grid_remove()
        if hasattr(self, "single_video_thumbnail_label"):
            self.single_video_thumbnail_label.grid_remove()
        self.dynamic_area_label.configure(text=LABEL_EMPTY)

        self.current_operation = OP_FETCH
        self._last_toggled_playlist_mode = self.options_frame_widget.get_playlist_mode()
        self._enter_fetching_state()

        if self.logic:
            self._current_fetch_url = url
            self.logic.start_info_fetch(url)
        else:
            self._handle_missing_logic_handler()

    # --- Toggle Playlist Mode ---
    def toggle_playlist_mode(self) -> None:
        """Handles the manual toggling of the 'Is Playlist?' switch."""
        # (No changes needed here)
        print("UI_Interface: Playlist switch toggled manually.")
        self._last_toggled_playlist_mode = self.options_frame_widget.get_playlist_mode()
        if self.fetched_info:
            self._enter_info_fetched_state()

    # --- Add Download to Queue Action ---
    def start_download_ui(self) -> None:
        """Validates inputs, adds the download task to the queue, and resets the Home tab UI."""
        # (Validation logic remains similar)
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
        task_title: str = self.fetched_info.get("title", "Untitled")

        if is_actually_playlist:
            total_playlist_count = len(self.fetched_info.get("entries", []))

        add_as_playlist: bool = False
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
            # task_title += f" (Selection: {selected_items_count}/{total_playlist_count})" # Keep title shorter for status
            add_as_playlist = True
            print(
                f"UI: Adding playlist selection to queue. Items: {playlist_items_string}"
            )
        elif not is_playlist_mode_on and self.fetched_info:
            if is_actually_playlist:
                if not messagebox.askyesno(
                    TITLE_CONFIRM_SINGLE, MSG_CONFIRM_SINGLE_BODY
                ):
                    return
                selected_items_count = 1
                # task_title += " (First Item)" # Keep title shorter
                add_as_playlist = False
                print("UI: Adding first item of playlist to queue.")
            else:
                selected_items_count = 1
                add_as_playlist = False
                print("UI: Adding single video to queue.")
        else:
            messagebox.showerror(TITLE_LOGIC_ERROR, MSG_MISMATCH_STATE)
            return

        # --- Add Task to Logic Handler Queue ---
        if self.logic:
            print(f"UI: Calling logic.add_download_task for '{task_title}'")
            task_id = self.logic.add_download_task(
                url=url,
                save_path=save_path,
                format_choice=format_choice,
                is_playlist=add_as_playlist,
                playlist_items=playlist_items_string,
                selected_items_count=selected_items_count,
                total_playlist_count=total_playlist_count,
                title=task_title,
            )

            if task_id:
                # --- SUCCESS ---
                # <<< Updated Status Message Logic >>>
                queue_size = self.logic.get_queue_size()
                max_title_len = 40  # Max length for status bar display
                truncated_title = task_title
                if len(task_title) > max_title_len:
                    truncated_title = task_title[: max_title_len - 3] + "..."
                plural_s = "s" if queue_size != 1 else ""
                # Construct message in English
                status_message = f"Added '{truncated_title}'. Queue size: {queue_size} task({plural_s}). View in Queue tab."

                self._enter_idle_state()  # Reset Home tab UI immediately
                self.update_status(status_message)  # Update main status bar
            else:
                messagebox.showerror(TITLE_QUEUE_ERROR, MSG_QUEUE_ADD_FAILED)
        else:
            self._handle_missing_logic_handler()

    # --- Handle Missing Logic Handler ---
    def _handle_missing_logic_handler(self):
        # (No changes needed here)
        print(MSG_LOGIC_HANDLER_MISSING)
        self.update_status(MSG_LOGIC_HANDLER_MISSING)
        self._enter_idle_state()

    # --- Cancel Operation ---
    def cancel_operation_ui(self) -> None:
        """Requests cancellation of the active Fetch Info operation."""
        # (No changes needed here, only cancels Fetch)
        print("UI_Interface: Bottom Cancel button pressed.")
        if self.current_operation == OP_FETCH:
            if self.logic:
                self.logic.cancel_fetch_info()
            else:
                print("UI: No logic handler available to cancel fetch.")
                self._enter_idle_state()
        else:
            print("UI: No active Fetch Info operation to cancel.")
