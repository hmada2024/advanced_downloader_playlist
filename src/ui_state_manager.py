# src/ui_state_manager.py
# -- Mixin class for managing UI states --

import os  # Needed for isdir check
from typing import TYPE_CHECKING, Optional, List, Dict, Any, Callable  # Added typing

# Conditional import for type hinting UI elements
if TYPE_CHECKING:
    import customtkinter as ctk
    from .ui_interface import UserInterface
    from .ui_components.top_input_frame import TopInputFrame
    from .ui_components.options_control_frame import OptionsControlFrame
    from .ui_components.path_selection_frame import PathSelectionFrame
    from .ui_components.bottom_controls_frame import BottomControlsFrame
    from .ui_components.playlist_selector import PlaylistSelector

# --- Constants for UI State Management ---
# Button Texts
BTN_TXT_DOWNLOAD = "Download"
BTN_TXT_FETCHING = "Fetching..."
BTN_TXT_DOWNLOADING = "Downloading..."
BTN_TXT_DOWNLOAD_SELECTION = "Download Selection"
BTN_TXT_DOWNLOAD_VIDEO = "Download Video"
BTN_TXT_SELECT_SAVE_LOCATION = "Select Save Location"

# Status Messages
STATUS_IDLE_DEFAULT = "Enter URL and click Fetch Info."
STATUS_ERROR_PROCESSING_FETCHED = "Error: Failed to process fetched information."
STATUS_FETCHING_INFO = "Fetching information..."  # Duplicates constant in info_fetcher, decide where to keep

# Dynamic Area Labels / Titles
LABEL_PLAYLIST_TITLE = "Playlist: {title} ({count} items total)"
LABEL_VIDEO_TITLE = "Video: {title}"
LABEL_EMPTY = ""


class UIStateManagerMixin:
    """Mixin class containing methods for managing the UI state transitions."""

    # Type hints for attributes assumed to exist in the main class
    if TYPE_CHECKING:
        self: "UserInterface"  # Assume UserInterface context
        # Widgets
        top_frame_widget: TopInputFrame
        options_frame_widget: OptionsControlFrame
        path_frame_widget: PathSelectionFrame
        bottom_controls_widget: BottomControlsFrame
        playlist_selector_widget: PlaylistSelector
        dynamic_area_label: ctk.CTkLabel
        progress_bar: ctk.CTkProgressBar
        # Attributes
        fetched_info: Optional[Dict[str, Any]]
        current_operation: Optional[str]
        _last_toggled_playlist_mode: bool
        # Methods assumed from other mixins/main class
        update_status: Callable[[str], None]
        update_idletasks: Callable[[], None]  # Tkinter method

    def _enable_main_controls(self, enable_playlist_switch: bool = True) -> None:
        """Enables the main input controls (URL, options, path)."""
        try:
            self.top_frame_widget.enable_fetch()
            self.options_frame_widget.format_combobox.configure(state="normal")
            # Enable/disable playlist switch based on argument
            switch_state = "normal" if enable_playlist_switch else "disabled"
            self.options_frame_widget.playlist_switch.configure(state=switch_state)
            self.path_frame_widget.enable()  # Enables browse button
        except AttributeError as e:
            print(f"Error enabling main controls (widget might be missing): {e}")
        except Exception as e:
            print(f"Unexpected error enabling main controls: {e}")

    def _enter_idle_state(self) -> None:
        """Enters the idle state (ready for a new operation)."""
        print("UI_Interface: Entering idle state.")
        # Enable all input controls, including the playlist switch by default
        self._enable_main_controls(enable_playlist_switch=True)

        # Configure bottom controls for idle state
        self.bottom_controls_widget.disable_download(button_text=BTN_TXT_DOWNLOAD)
        self.bottom_controls_widget.hide_cancel_button()

        # Reset dynamic areas
        self.dynamic_area_label.configure(text=LABEL_EMPTY)
        self.playlist_selector_widget.grid_remove()  # Hide playlist view
        self.playlist_selector_widget.reset()  # Clear items inside playlist view

        # Reset internal state
        self.fetched_info = None
        self.current_operation = None
        # Reset playlist switch visually and internally
        self.options_frame_widget.set_playlist_mode(True)  # Visually ON
        self._last_toggled_playlist_mode = True  # Tracker matches initial visual state

        # Set initial status message and progress
        self.update_status(STATUS_IDLE_DEFAULT)
        try:
            if self.progress_bar:
                self.progress_bar.set(0.0)  # Reset progress bar to 0
        except Exception as e:
            print(f"Error resetting progress bar: {e}")

    def _enter_fetching_state(self) -> None:
        """Enters the state while fetching information."""
        print("UI_Interface: Entering fetching state.")
        # Disable input controls during fetch
        self.top_frame_widget.disable_fetch(button_text=BTN_TXT_FETCHING)
        self.options_frame_widget.disable()
        self.path_frame_widget.disable()

        # Configure bottom controls for fetching state
        self.bottom_controls_widget.disable_download()  # Keep download disabled
        self.bottom_controls_widget.show_cancel_button()  # Show cancel option

        # Update status and progress
        self.update_status(STATUS_FETCHING_INFO)
        try:
            if self.progress_bar:
                self.progress_bar.set(0.0)  # Reset progress for fetch attempt
        except Exception as e:
            print(f"Error setting progress bar for fetching state: {e}")

    def _enter_downloading_state(self) -> None:
        """Enters the state during download/processing."""
        print("UI_Interface: Entering downloading state.")
        # Disable all interactive input elements during download
        self.top_frame_widget.disable_fetch()  # Disable URL input and fetch button
        self.options_frame_widget.disable()  # Disable format/playlist options
        self.path_frame_widget.disable()  # Disable path browsing
        # Disable playlist interaction if it's visible
        self.playlist_selector_widget.disable()

        # Configure bottom controls for downloading state
        self.bottom_controls_widget.disable_download(button_text=BTN_TXT_DOWNLOADING)
        self.bottom_controls_widget.show_cancel_button()  # Keep cancel visible
        # Status/progress will be updated by callbacks from the downloader thread

    def _display_playlist_view(self) -> None:
        """Sets up and displays the playlist selection view."""
        if not self.fetched_info:
            print("UI State Error: _display_playlist_view called without fetched_info.")
            return  # Safety check

        # Get playlist details from fetched data
        playlist_title: str = self.fetched_info.get("title", "Untitled Playlist")
        entries: List[Dict[str, Any]] = self.fetched_info.get("entries", [])
        total_items: int = len(entries)

        # Update the dynamic label above the playlist view
        self.dynamic_area_label.configure(
            text=LABEL_PLAYLIST_TITLE.format(title=playlist_title, count=total_items)
        )

        # Populate the playlist selector widget with items
        self.playlist_selector_widget.populate_items(entries)
        self.playlist_selector_widget.enable()  # Ensure interaction is enabled

        # Make the playlist selector visible by adding it to the grid
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
            self._enter_idle_state()  # Go back to idle if no info
            self.update_status(STATUS_ERROR_PROCESSING_FETCHED)
            return

        # Determine if the fetched data is actually a playlist
        is_actually_playlist: bool = isinstance(self.fetched_info.get("entries"), list)

        # Enable main controls; disable playlist switch if it's not a playlist
        self._enable_main_controls(enable_playlist_switch=is_actually_playlist)

        # Restore user's last preferred playlist mode *if* it's actually a playlist
        if is_actually_playlist:
            self.options_frame_widget.set_playlist_mode(
                self._last_toggled_playlist_mode
            )
        else:
            self.options_frame_widget.set_playlist_mode(
                False
            )  # Force off if not playlist

        # Use the *current* state of the switch (potentially just updated)
        is_playlist_mode_on: bool = self.options_frame_widget.get_playlist_mode()
        # Determine if the playlist view should be shown
        should_show_playlist_view: bool = is_playlist_mode_on and is_actually_playlist

        print(
            f"UI_Interface: Entering info fetched state. Actual playlist: {is_actually_playlist}, "
            f"Switch ON: {is_playlist_mode_on}, "
            f"Show Playlist View: {should_show_playlist_view}"
        )

        # Configure bottom controls: hide cancel, enable/disable download based on path
        self.bottom_controls_widget.hide_cancel_button()
        save_path: str = self.path_frame_widget.get_path()
        # Enable download only if a valid directory path is selected
        if save_path and os.path.isdir(save_path):
            # Set appropriate download button text based on mode
            btn_text: str = (
                BTN_TXT_DOWNLOAD_SELECTION
                if should_show_playlist_view
                else BTN_TXT_DOWNLOAD_VIDEO
            )
            self.bottom_controls_widget.enable_download(button_text=btn_text)
        else:
            # Disable download and prompt user to select path if path is missing/invalid
            self.bottom_controls_widget.disable_download(
                button_text=BTN_TXT_SELECT_SAVE_LOCATION
            )

        # Show/hide playlist view or display single video title
        if should_show_playlist_view:
            self._display_playlist_view()
        else:
            # Hide playlist view if it was previously visible
            self.playlist_selector_widget.grid_remove()
            # Display single video title in the dynamic area label
            video_title: str = self.fetched_info.get("title", "Untitled Video")
            self.dynamic_area_label.configure(
                text=LABEL_VIDEO_TITLE.format(title=video_title)
            )

        # Reset progress bar after fetch operation completes visually
        try:
            if self.progress_bar:
                self.progress_bar.set(0.0)
        except Exception as e:
            print(f"Error resetting progress bar in info fetched state: {e}")

        # Ensure UI updates visually (sometimes helpful after multiple config changes)
        self.update_idletasks()
