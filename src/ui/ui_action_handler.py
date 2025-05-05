# src/ui_action_handler.py
# -- Mixin class for handling user actions from the UI --

import os # Needed for isdir check
from tkinter import filedialog, messagebox
from typing import TYPE_CHECKING, Optional, Dict, Any, Callable

from src.ui_state_manager import BTN_TXT_DOWNLOAD_SELECTION, BTN_TXT_DOWNLOAD_VIDEO, LABEL_EMPTY # Added typing

# Conditional import for type hinting
if TYPE_CHECKING:
    import customtkinter as ctk
    from .ui.ui_interface import UserInterface
    from .logic_handler import LogicHandler

# --- Constants for Message Box Titles and Messages ---
# Titles
TITLE_INPUT_ERROR = "Input Error"
TITLE_PATH_ERROR = "Path Error"
TITLE_SELECTION_ERROR = "Selection Error"
TITLE_CONFIRM_SINGLE = "Confirm Single Download"
TITLE_LOGIC_ERROR = "Logic Error"
TITLE_ERROR = "Error" # Generic error title

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

# Operation Types
OP_FETCH = "fetch"
OP_DOWNLOAD = "download"


class UIActionHandlerMixin:
    """Mixin class containing methods for handling user actions and initiating logic operations."""

    # Type hints for attributes assumed to exist in the main class
    if TYPE_CHECKING:
        self: 'UserInterface' # Assume UserInterface context
        # Widgets (assuming types defined/imported in UserInterface)
        path_frame_widget: Any # PathSelectionFrame
        top_frame_widget: Any # TopInputFrame
        bottom_controls_widget: Any # BottomControlsFrame
        playlist_selector_widget: Any # PlaylistSelector
        options_frame_widget: Any # OptionsControlFrame
        dynamic_area_label: ctk.CTkLabel
        # Attributes
        fetched_info: Optional[Dict[str, Any]]
        logic: Optional[LogicHandler] # Instance of LogicHandler
        current_operation: Optional[str]
        _last_toggled_playlist_mode: bool
        # Methods from other mixins/main class
        _enter_fetching_state: Callable[[], None]
        _enter_downloading_state: Callable[[], None]
        _enter_info_fetched_state: Callable[[], None]
        _enter_idle_state: Callable[[], None]
        update_status: Callable[[str], None]


    def browse_path_logic(self) -> None:
        """Opens directory dialog, updates path widget, and enables download if appropriate."""
        if directory := filedialog.askdirectory(title="Select Download Folder"):
            # Update the path entry widget with the selected directory
            self.path_frame_widget.set_path(directory)

            # Check if download should be enabled *now*
            # Requires info to be fetched and the path to be a valid directory
            if self.fetched_info and os.path.isdir(directory):
                 # Check if download button was previously disabled (e.g., due to no path)
                is_download_disabled = self.bottom_controls_widget.download_button.cget("state") == "disabled"
                if is_download_disabled:
                    # Determine appropriate button text based on current mode
                    is_playlist_mode = self.options_frame_widget.get_playlist_mode()
                    is_actually_playlist = isinstance(self.fetched_info.get("entries"), list)
                    show_playlist_view = is_playlist_mode and is_actually_playlist
                    btn_text = BTN_TXT_DOWNLOAD_SELECTION if show_playlist_view else BTN_TXT_DOWNLOAD_VIDEO
                    self.bottom_controls_widget.enable_download(button_text=btn_text)
            elif not os.path.isdir(directory):
                 # Show warning if selected path is somehow not a directory
                 # (askdirectory should prevent this, but good to double-check)
                 messagebox.showwarning(
                    TITLE_PATH_ERROR,
                    MSG_PATH_INVALID_DIR.format(path=directory),
                 )


    def fetch_video_info(self) -> None:
        """Initiates the process to fetch info for the entered URL."""
        url: str = self.top_frame_widget.get_url()
        if not url:
            messagebox.showerror(TITLE_INPUT_ERROR, MSG_URL_EMPTY)
            return

        # Reset previous fetch results and UI elements related to fetched info
        self.fetched_info = None
        self.playlist_selector_widget.grid_remove() # Hide playlist view
        self.dynamic_area_label.configure(text=LABEL_EMPTY)
        # Don't clear URL input, user might want to retry the same URL

        # Set state for fetching
        self.current_operation = OP_FETCH
        # Store the current playlist switch state before fetching
        self._last_toggled_playlist_mode = self.options_frame_widget.get_playlist_mode()
        self._enter_fetching_state() # Update UI for fetching

        # Call the logic handler to start the background fetch operation
        if self.logic:
            self.logic.start_info_fetch(url)
        else:
            self._extracted_from_start_download_ui_24()


    def toggle_playlist_mode(self) -> None:
        """Handles the manual toggling of the 'Is Playlist?' switch."""
        print("UI_Interface: Playlist switch toggled manually.")
        # Store the new state of the switch (user's preference)
        self._last_toggled_playlist_mode = self.options_frame_widget.get_playlist_mode()

        # If info is already fetched, re-render the UI based on the new switch state
        if self.fetched_info:
            # This will show/hide the playlist view and update button text accordingly
            self._enter_info_fetched_state()


    def start_download_ui(self) -> None:
        """Initiates the download process based on current selections."""
        # --- Get current state from UI widgets ---
        url: str = self.top_frame_widget.get_url()
        save_path: str = self.path_frame_widget.get_path()
        format_choice: str = self.options_frame_widget.get_format_choice()
        is_playlist_mode_on: bool = self.options_frame_widget.get_playlist_mode()

        # --- Input Validation ---
        if not url:
            messagebox.showerror(TITLE_ERROR, MSG_URL_MISSING)
            return
        if not save_path:
            messagebox.showerror(TITLE_ERROR, MSG_SAVE_PATH_MISSING)
            return
        if not os.path.isdir(save_path): # Check if save path is valid directory
            messagebox.showerror(TITLE_ERROR, MSG_SAVE_PATH_INVALID)
            return
        if not self.fetched_info:
            messagebox.showerror(TITLE_ERROR, MSG_FETCH_INFO_FIRST)
            return

        # --- Determine Download Parameters ---
        playlist_items_string: Optional[str] = None
        selected_items_count: int = 0
        total_playlist_count: int = 0
        # Check if the *fetched data* actually contains a playlist
        is_actually_playlist: bool = isinstance(self.fetched_info.get("entries"), list)

        if is_actually_playlist:
            # Get total count if it's a playlist
            total_playlist_count = len(self.fetched_info.get("entries", []))

        # --- Logic based on playlist mode and actual content ---
        if is_playlist_mode_on and is_actually_playlist:
            # Case 1: Playlist mode ON, content IS a playlist
            playlist_items_string = self.playlist_selector_widget.get_selected_items_string()
            if not playlist_items_string:
                messagebox.showwarning(TITLE_SELECTION_ERROR, MSG_NO_PLAYLIST_ITEMS_SELECTED)
                return
            selected_items_count = len(playlist_items_string.split(","))
            print(
                f"UI: Starting playlist download. Selected: {selected_items_count}, Total: {total_playlist_count}, Items: {playlist_items_string}, Format: {format_choice}"
            )
            is_download_target_playlist = True # Flag for logic handler

        elif not is_playlist_mode_on and self.fetched_info:
            # Case 2: Playlist mode OFF (or content is NOT a playlist)
            if is_actually_playlist:
                 # Content IS playlist, but mode is OFF - Confirm single download
                if not messagebox.askyesno(TITLE_CONFIRM_SINGLE, MSG_CONFIRM_SINGLE_BODY):
                    return # User cancelled
                 # User confirmed, proceed to download first item (handled by yt-dlp without playlist_items)
                print(f"UI: Starting single item download (first from playlist). Format: {format_choice}")
            else:
                 # Content is NOT a playlist, download normally
                 print(f"UI: Starting single video download. Format: {format_choice}")

            selected_items_count = 1 # We are downloading one item
            is_download_target_playlist = False # Tell logic handler it's single item download

        # This case should ideally be prevented by disabling the switch if not a playlist
        # elif not is_actually_playlist and is_playlist_mode_on:
        #     print("UI Warning: Playlist mode ON, but content is not a playlist. Proceeding as single.")
        #     selected_items_count = 1
        #     is_download_target_playlist = False

        else:
            # Fallback for any unexpected state mismatch
            messagebox.showerror(TITLE_LOGIC_ERROR, MSG_MISMATCH_STATE)
            return

        # --- Initiate Download ---
        self.current_operation = OP_DOWNLOAD
        self._enter_downloading_state() # Update UI for downloading

        if self.logic:
            self.logic.start_download(
                url=url,
                save_path=save_path,
                format_choice=format_choice,
                is_playlist=is_download_target_playlist, # Pass the determined flag
                playlist_items=playlist_items_string, # Pass selected items string (None if single)
                selected_items_count=selected_items_count,
                total_playlist_count=total_playlist_count,
            )
        else:
            self._extracted_from_start_download_ui_24()

    # TODO Rename this here and in `fetch_video_info` and `start_download_ui`
    def _extracted_from_start_download_ui_24(self):
        print(MSG_LOGIC_HANDLER_MISSING)
        self.update_status(MSG_LOGIC_HANDLER_MISSING)
        self._enter_idle_state()


    def cancel_operation_ui(self) -> None:
        """Requests cancellation of the active background operation."""
        print("UI_Interface: Cancel button pressed.")
        # Provide immediate feedback even before logic handler confirms
        if self.current_operation:
            self.update_status("Cancellation requested...")

        # Signal the logic handler to cancel the operation
        if self.logic:
            self.logic.cancel_operation()
        else:
            # Should not happen if buttons are managed correctly, but handle defensively
            print("UI_Interface: No logic handler available to cancel.")
            self._enter_idle_state() # Reset UI if logic is missing