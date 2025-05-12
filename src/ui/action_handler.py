# src/ui/action_handler.py
# -- Mixin class for handling user actions from the UI --
# -- Modified start_download_ui to add to queue, cancel only Fetch Info --

import os
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import TYPE_CHECKING, Optional, Dict, Any, Callable

# --- Imports from current package/subpackages ---
if TYPE_CHECKING:
    import customtkinter as ctk
    from .interface import UserInterface
    from ..logic.logic_handler import LogicHandler  # Needs updated LogicHandler
    from .queue_tab import (
        QueueTab,
    )  # Import QueueTab if needed for direct interaction (unlikely)

    # Import component types
    from .components.path_selection_frame import PathSelectionFrame
    from .components.top_input_frame import TopInputFrame
    from .components.bottom_controls_frame import BottomControlsFrame
    from .components.playlist_selector import PlaylistSelector
    from .components.options_control_frame import OptionsControlFrame

# --- Constants ---
BTN_TXT_DOWNLOAD = "Add to Queue"  # Changed button text meaning
BTN_TXT_FETCHING = "Fetching..."
BTN_TXT_DOWNLOADING = "Adding..."  # Text while adding to queue (very brief)
BTN_TXT_DOWNLOAD_SELECTION = "Add Selection to Queue"
BTN_TXT_DOWNLOAD_VIDEO = "Add Video to Queue"
BTN_TXT_SELECT_SAVE_LOCATION = "Select Save Location"
LABEL_EMPTY = ""

# Message Box Titles and Messages (Mostly unchanged, some updated)
TITLE_INPUT_ERROR = "Input Error"
TITLE_PATH_ERROR = "Path Error"
TITLE_SELECTION_ERROR = "Selection Error"
TITLE_CONFIRM_SINGLE = "Confirm Single Download"
TITLE_LOGIC_ERROR = "Logic Error"
TITLE_ERROR = "Error"
TITLE_QUEUE_ERROR = "Queue Error"  # New Title

MSG_URL_EMPTY = "Please enter a URL."
MSG_PATH_INVALID_DIR = "Selected path is not a valid directory:\n{path}"
MSG_NO_PLAYLIST_ITEMS_SELECTED = "No playlist items selected to add to queue."
MSG_CONFIRM_SINGLE_BODY = "This is a playlist, but playlist mode is off.\nDo you want to add only the first video/item (based on URL) to the queue?"
MSG_URL_MISSING = "URL is missing."
MSG_SAVE_PATH_MISSING = "Save location is missing."
MSG_SAVE_PATH_INVALID = "Save location is not a valid directory."
MSG_FETCH_INFO_FIRST = "Fetch info first before adding to queue."
MSG_MISMATCH_STATE = "Mismatch between UI state and fetched info when adding to queue."
MSG_LOGIC_HANDLER_MISSING = "UI_Interface Error: Logic handler not available."
TITLE_PASTE_ERROR = "Paste Error"
MSG_PASTE_FAILED = (
    "Could not paste from clipboard. Clipboard might be empty or contain non-text data."
)
MSG_QUEUE_ADD_FAILED = (
    "Failed to add task to download queue. Check console/logs."  # New Message
)

# Operation Types
OP_FETCH = "fetch"
# OP_DOWNLOAD removed as it's now managed by the queue


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
        logic: Optional[
            LogicHandler
        ]  # Updated type hint might be needed if class changes significantly
        current_operation: Optional[str]  # Tracks 'fetch' primarily
        _last_toggled_playlist_mode: bool
        # Methods from other Mixins/Base Class
        _enter_fetching_state: Callable[[], None]
        # _enter_downloading_state: Callable[[], None] # <<< REMOVED: No longer enters downloading state here
        _enter_info_fetched_state: Callable[[], None]
        _enter_idle_state: Callable[
            [], None
        ]  # Used to reset the Home tab after adding to queue
        update_status: Callable[..., None]  # Accepts task_id optionally now
        clipboard_get: Callable[[], str]

    # --- Paste URL Action ---
    def paste_url_action(self) -> None:
        """Gets content from clipboard and pastes it into the URL entry field."""
        # --- Logic remains the same ---
        try:
            if clipboard_content := self.clipboard_get():
                self.top_frame_widget.set_url(clipboard_content)
                self.update_status("URL pasted from clipboard.")
            else:
                self.update_status("Clipboard is empty.")
        except tk.TclError:
            messagebox.showwarning(TITLE_PASTE_ERROR, MSG_PASTE_FAILED)
            self.update_status("Paste failed. Clipboard might be empty or non-text.")
        except Exception as e:
            messagebox.showerror(
                TITLE_PASTE_ERROR, f"An unexpected error occurred during paste:\n{e}"
            )
            self.update_status(f"Paste Error: {e}")

    # --- Browse Path Action ---
    def browse_path_logic(self) -> None:
        """Opens directory dialog, updates path widget, and enables download button if appropriate."""
        # --- Logic remains the same, but button text constants change ---
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
        # --- Logic remains largely the same ---
        url: str = self.top_frame_widget.get_url()
        if not url:
            messagebox.showerror(TITLE_INPUT_ERROR, MSG_URL_EMPTY)
            return

        # Prevent starting fetch if another fetch is running
        if self.current_operation == OP_FETCH:
            messagebox.showwarning(
                "Busy", "Already fetching information. Please wait or cancel."
            )
            return

        self.fetched_info = None
        self.playlist_selector_widget.grid_remove()  # Hide playlist view
        if hasattr(self, "single_video_thumbnail_label"):  # Hide thumbnail
            self.single_video_thumbnail_label.grid_remove()
        self.dynamic_area_label.configure(text=LABEL_EMPTY)  # Clear title label

        self.current_operation = OP_FETCH  # Mark that fetching is active
        self._last_toggled_playlist_mode = self.options_frame_widget.get_playlist_mode()
        self._enter_fetching_state()  # Update UI for fetching state

        if self.logic:
            self._current_fetch_url = url  # Store for history logging on success
            self.logic.start_info_fetch(url)  # Call logic handler to start fetch
        else:
            self._handle_missing_logic_handler()  # Handle case where logic handler isn't set

    # --- Toggle Playlist Mode ---
    def toggle_playlist_mode(self) -> None:
        """Handles the manual toggling of the 'Is Playlist?' switch."""
        # --- Logic remains the same ---
        print("UI_Interface: Playlist switch toggled manually.")
        self._last_toggled_playlist_mode = self.options_frame_widget.get_playlist_mode()
        # If info was already fetched, re-evaluate the display based on the new switch state
        if self.fetched_info:
            self._enter_info_fetched_state()

    # --- Add Download to Queue Action ---
    def start_download_ui(self) -> None:
        """
        Validates inputs, gathers task details, and adds the download task to the LogicHandler's queue.
        Resets the Home tab UI immediately after adding.
        """
        # 1. Get necessary info from UI
        url: str = self.top_frame_widget.get_url()
        save_path: str = self.path_frame_widget.get_path()
        format_choice: str = self.options_frame_widget.get_format_choice()
        is_playlist_mode_on: bool = self.options_frame_widget.get_playlist_mode()

        # 2. Basic Validations
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

        # 3. Determine Playlist Settings and Title
        playlist_items_string: Optional[str] = None
        selected_items_count: int = 0
        total_playlist_count: int = 0
        is_actually_playlist: bool = isinstance(self.fetched_info.get("entries"), list)
        task_title: str = self.fetched_info.get(
            "title", "Untitled"
        )  # Get title for the queue

        if is_actually_playlist:
            total_playlist_count = len(self.fetched_info.get("entries", []))

        # Determine if we are adding the whole playlist, selected items, or a single video
        add_as_playlist: bool = False
        if is_playlist_mode_on and is_actually_playlist:
            # Playlist mode ON, get selected items
            playlist_items_string = (
                self.playlist_selector_widget.get_selected_items_string()
            )
            if not playlist_items_string:
                messagebox.showwarning(
                    TITLE_SELECTION_ERROR, MSG_NO_PLAYLIST_ITEMS_SELECTED
                )
                return
            selected_items_count = len(playlist_items_string.split(","))
            task_title += f" (Selection: {selected_items_count}/{total_playlist_count})"
            add_as_playlist = True
            print(
                f"UI: Adding playlist selection to queue. Items: {playlist_items_string}"
            )

        elif not is_playlist_mode_on and self.fetched_info:
            # Playlist mode OFF
            if is_actually_playlist:
                # It's a playlist URL, but mode is off - ask user
                if not messagebox.askyesno(
                    TITLE_CONFIRM_SINGLE, MSG_CONFIRM_SINGLE_BODY
                ):
                    return  # User chose not to add the single item
                task_title += " (First Item)"
                print("UI: Adding first item of playlist to queue.")
            else:
                print("UI: Adding single video to queue.")
            add_as_playlist = False  # Add based on URL, let yt-dlp pick first
            # User confirmed, treat as single download (LogicHandler/Downloader handle this)
            selected_items_count = 1
        else:
            # Should not happen if validations passed
            messagebox.showerror(TITLE_LOGIC_ERROR, MSG_MISMATCH_STATE)
            return

        # 4. Add Task to Logic Handler Queue
        if self.logic:
            print(f"UI: Calling logic.add_download_task for '{task_title}'")
            if task_id := self.logic.add_download_task(
                url=url,
                save_path=save_path,
                format_choice=format_choice,
                is_playlist=add_as_playlist,  # Whether to pass --yes-playlist implicitly
                playlist_items=playlist_items_string,  # Pass selected items if applicable
                selected_items_count=selected_items_count,
                total_playlist_count=total_playlist_count,
                title=task_title,  # Pass the determined title
            ):
                # --- SUCCESS ---
                # Immediately reset the Home tab UI to allow adding another task
                print(f"UI: Task {task_id} added successfully. Resetting Home tab.")
                self._enter_idle_state()
                self.update_status(
                    f"Task '{task_title[:30]}...' added. View in Queue tab."
                )  # Update main status bar
            else:
                # Failed to add task (LogicHandler might have logged details)
                messagebox.showerror(TITLE_QUEUE_ERROR, MSG_QUEUE_ADD_FAILED)
        else:
            self._handle_missing_logic_handler()  # Logic handler not available

    # --- Handle Missing Logic Handler ---
    def _handle_missing_logic_handler(self):
        """Handles the case where the logic handler is missing."""
        print(MSG_LOGIC_HANDLER_MISSING)
        self.update_status(MSG_LOGIC_HANDLER_MISSING)
        self._enter_idle_state()  # Go idle if logic is missing

    # --- Cancel Operation ---
    def cancel_operation_ui(self) -> None:
        """
        Requests cancellation of the *active Fetch Info* operation.
        Download cancellation is handled within the Queue tab.
        """
        print("UI_Interface: Bottom Cancel button pressed.")
        if self.current_operation == OP_FETCH:
            if self.logic:
                # Call the specific cancel method for fetch info
                self.logic.cancel_fetch_info()
            else:
                print("UI_Interface: No logic handler available to cancel fetch.")
                self._enter_idle_state()  # Reset if logic is missing
        else:
            print(
                "UI_Interface: No active Fetch Info operation to cancel with this button."
            )
            # Optionally provide feedback: self.update_status("Nothing to cancel here.")
