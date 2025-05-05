# src/ui_state_manager.py
# -- Mixin class for managing UI states --

import customtkinter as ctk
import os  # Needed for isdir check

# Assumes mixin into a class with necessary attributes/methods


class UIStateManagerMixin:
    """Mixin class containing methods for managing the UI state transitions."""

    def _enable_main_controls(self, enable_playlist_switch=True):
        """Enables the main input controls (URL, options, path)."""
        self.top_frame_widget.enable_fetch()
        self.options_frame_widget.format_combobox.configure(state="normal")
        switch_state = "normal" if enable_playlist_switch else "disabled"
        self.options_frame_widget.playlist_switch.configure(state=switch_state)
        self.path_frame_widget.enable()

    def _enter_idle_state(self):
        """Enters the idle state (ready for a new operation)."""
        print("UI_Interface: Entering idle state.")
        # Enable all controls initially, including playlist switch
        self._enable_main_controls(enable_playlist_switch=True)
        self.bottom_controls_widget.disable_download(button_text="Download")
        self.bottom_controls_widget.hide_cancel_button()
        self.dynamic_area_label.configure(text="")
        self.playlist_selector_widget.grid_remove()
        self.playlist_selector_widget.reset()
        self.fetched_info = None
        # Use update_status for consistency, even for default messages
        self.update_status("Enter URL and click Fetch Info.")
        # Ensure progress bar is visually reset
        self.progress_bar.set(0)
        # Explicitly update visual state of progress bar if needed
        # self.progress_bar.update_idletasks()
        self.current_operation = None
        # Reset playlist switch state and internal tracker
        self.options_frame_widget.set_playlist_mode(True)  # Visually ON
        self._last_toggled_playlist_mode = True  # Tracker matches visual state

    def _enter_fetching_state(self):
        """Enters the state while fetching information."""
        print("UI_Interface: Entering fetching state.")
        self.top_frame_widget.disable_fetch(button_text="Fetching...")
        self.options_frame_widget.disable()
        self.path_frame_widget.disable()
        self.bottom_controls_widget.disable_download()
        self.bottom_controls_widget.show_cancel_button()
        self.update_status("Fetching information...")  # Use update_status
        self.progress_bar.set(0)  # Reset progress for fetch attempt

    def _enter_downloading_state(self):
        """Enters the state during download/processing."""
        print("UI_Interface: Entering downloading state.")
        # Disable all inputs during download
        self.top_frame_widget.disable_fetch()  # Button text doesn't matter here
        self.options_frame_widget.disable()
        self.path_frame_widget.disable()
        # Disable playlist interaction if visible
        self.playlist_selector_widget.disable()

        self.bottom_controls_widget.disable_download(button_text="Downloading...")
        self.bottom_controls_widget.show_cancel_button()
        # Status/progress will be updated by callbacks

    def _display_playlist_view(self):
        """Sets up and displays the playlist selection view."""
        if not self.fetched_info:
            return  # Safety check

        playlist_title = self.fetched_info.get("title", "Untitled Playlist")
        entries = self.fetched_info.get("entries", [])
        total_items = len(entries)
        self.dynamic_area_label.configure(
            text=f"Playlist: {playlist_title} ({total_items} items total)"
        )

        self.playlist_selector_widget.populate_items(entries)
        self.playlist_selector_widget.enable()  # Ensure interaction is enabled
        self.playlist_selector_widget.grid(
            row=4, column=0, padx=20, pady=(5, 10), sticky="nsew"
        )
        print("UI_Interface: Playlist frame gridded and populated.")

    def _enter_info_fetched_state(self):
        """Enters the state after information has been successfully fetched."""
        if not self.fetched_info:
            print("Error: _enter_info_fetched_state called without fetched_info.")
            self._enter_idle_state()
            self.update_status("Error: Failed to process fetched information.")
            return

        is_actually_playlist = isinstance(self.fetched_info.get("entries"), list)
        # Enable main controls; playlist switch state is handled by on_info_success callback now
        self._enable_main_controls(enable_playlist_switch=is_actually_playlist)

        # Use the current state of the switch (set by on_info_success)
        is_playlist_mode_on = self.options_frame_widget.get_playlist_mode()
        should_show_playlist_view = is_playlist_mode_on and is_actually_playlist

        print(
            f"UI_Interface: Entering info fetched state. Actual playlist: {is_actually_playlist}, "
            f"Switch ON: {is_playlist_mode_on}, "
            f"Show Playlist View: {should_show_playlist_view}"
        )

        self.bottom_controls_widget.hide_cancel_button()

        # Enable/disable download button based on path validity
        save_path = self.path_frame_widget.get_path()
        if save_path and os.path.isdir(save_path):
            # Set appropriate download button text based on mode
            btn_text = (
                "Download Selection" if should_show_playlist_view else "Download Video"
            )
            self.bottom_controls_widget.enable_download(button_text=btn_text)
        else:
            self.bottom_controls_widget.disable_download(
                button_text="Select Save Location"
            )

        # Show/hide playlist view or single video title
        if should_show_playlist_view:
            self._display_playlist_view()
        else:
            # Hide playlist view if it was previously visible
            self.playlist_selector_widget.grid_remove()
            # Display single video title
            video_title = self.fetched_info.get("title", "Untitled Video")
            self.dynamic_area_label.configure(text=f"Video: {video_title}")

        # Status message is set by on_info_success
        self.progress_bar.set(0)  # Reset progress bar after fetch
        self.update_idletasks()  # Ensure UI updates visually
