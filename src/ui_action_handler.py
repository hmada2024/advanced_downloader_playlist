# src/ui_action_handler.py
# -- Mixin class for handling user actions from the UI --

import customtkinter as ctk
from tkinter import filedialog, messagebox
import os  # Needed for isdir check

# Assumes mixin into a class with necessary attributes/methods from other mixins/UI


class UIActionHandlerMixin:
    """Mixin class containing methods for handling user actions and initiating logic operations."""

    def browse_path_logic(self):
        """Opens directory dialog, updates path widget, and enables download if appropriate."""
        if directory := filedialog.askdirectory(title="Select Download Folder"):
            self.path_frame_widget.set_path(directory)
            # Enable download only if info is already fetched *and* path is now valid
            if (
                self.fetched_info
                and self.bottom_controls_widget.download_button.cget("state")
                == "disabled"
            ):
                # Check if the selected directory is actually valid before enabling
                if os.path.isdir(directory):
                    self.bottom_controls_widget.enable_download(
                        button_text="Download Selection"
                    )
                else:
                    # Should ideally not happen with askdirectory, but good practice
                    messagebox.showwarning(
                        "Path Error",
                        f"Selected path is not a valid directory:\n{directory}",
                    )

    def fetch_video_info(self):
        """Initiates the process to fetch info for the entered URL."""
        url = self.top_frame_widget.get_url()
        if not url:
            messagebox.showerror("Input Error", "Please enter a URL.")
            return

        self.fetched_info = None
        self.playlist_selector_widget.grid_remove()
        self.dynamic_area_label.configure(text="")
        # Don't clear URL, user might want to retry
        # self.top_frame_widget.set_url(url) # Redundant if not clearing

        self.current_operation = "fetch"
        self._last_toggled_playlist_mode = self.options_frame_widget.get_playlist_mode()
        self._enter_fetching_state()

        if self.logic:
            self.logic.start_info_fetch(url)

    def toggle_playlist_mode(self):
        """Handles the manual toggling of the 'Is Playlist?' switch."""
        print("UI_Interface: Playlist switch toggled manually.")
        self._last_toggled_playlist_mode = self.options_frame_widget.get_playlist_mode()
        if self.fetched_info:
            self._enter_info_fetched_state()  # Re-render based on new switch state

    def start_download_ui(self):
        """Initiates the download process based on current selections."""
        url = self.top_frame_widget.get_url()
        save_path = self.path_frame_widget.get_path()
        format_choice = self.options_frame_widget.get_format_choice()
        is_playlist_mode_on = self.options_frame_widget.get_playlist_mode()

        if not url:
            messagebox.showerror("Error", "URL is missing.")
            return
        if not save_path:
            messagebox.showerror("Error", "Save location is missing.")
            return
        if not os.path.isdir(save_path):
            messagebox.showerror("Error", "Save location is not a valid directory.")
            return
        if not self.fetched_info:
            messagebox.showerror("Error", "Fetch info first.")
            return

        playlist_items_string = None
        selected_items_count = 0
        total_playlist_count = 0
        is_actually_playlist = isinstance(self.fetched_info.get("entries"), list)

        if is_actually_playlist:
            total_playlist_count = len(self.fetched_info.get("entries", []))

        if is_playlist_mode_on and is_actually_playlist:
            playlist_items_string = (
                self.playlist_selector_widget.get_selected_items_string()
            )
            if not playlist_items_string:
                messagebox.showwarning(
                    "Selection Error", "No playlist items selected for download."
                )
                return
            selected_items_count = len(playlist_items_string.split(","))
            print(
                f"UI: Starting playlist download. Selected: {selected_items_count}, Total: {total_playlist_count}, Items: {playlist_items_string}, Format: {format_choice}"
            )

        elif not is_playlist_mode_on and self.fetched_info:
            # If it's a real playlist but mode is off, confirm download of first item
            if is_actually_playlist and not messagebox.askyesno(
                "Confirm Single Download",
                "This is a playlist, but playlist mode is off.\nDo you want to download only the first video/item based on the URL?",
            ):
                return
            # If it's not a playlist OR user confirmed first item download
            selected_items_count = 1
            print(
                f"UI: Starting single video/item download. General Format: {format_choice}, Playlist Total (if any): {total_playlist_count}"
            )
        elif not is_actually_playlist and is_playlist_mode_on:
            print(
                "UI Warning: Playlist mode is ON, but fetched info is not a playlist. Proceeding as single video download."
            )
            selected_items_count = 1
        else:
            # Any other unexpected mismatch
            messagebox.showerror(
                "Logic Error",
                "Mismatch between UI state and fetched info during download.",
            )
            return

        self.current_operation = "download"
        self._enter_downloading_state()

        if self.logic:
            self.logic.start_download(
                url=url,
                save_path=save_path,
                format_choice=format_choice,
                is_playlist=(
                    is_playlist_mode_on and is_actually_playlist
                ),  # Only True if both conditions met
                playlist_items=playlist_items_string,
                selected_items_count=selected_items_count,
                total_playlist_count=total_playlist_count,
            )

    def cancel_operation_ui(self):
        """Requests cancellation of the active background operation."""
        print("UI_Interface: Cancel button pressed.")
        if self.current_operation:
            self.update_status("Cancellation requested...")
        if self.logic:
            self.logic.cancel_operation()
        else:
            print("UI_Interface: No logic handler available to cancel.")
            self._enter_idle_state()
