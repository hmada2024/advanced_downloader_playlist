# src/ui_action_handler.py
# -- Mixin class for handling user actions from the UI --

import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import logging  # <-- إضافة استيراد logging


class UIActionHandlerMixin:
    """Mixin class containing methods for handling user actions."""

    def browse_path_logic(self):
        """Opens directory dialog, updates path widget, and enables download if appropriate."""
        logging.debug("UIActionHandler: browse_path_logic triggered.")
        if directory := filedialog.askdirectory(title="Select Download Folder"):
            logging.info(f"UIActionHandler: Directory selected: {directory}")
            self.path_frame_widget.set_path(directory)
            if (
                self.fetched_info
                and self.bottom_controls_widget.download_button.cget("state")
                == "disabled"
            ):
                logging.debug(
                    "UIActionHandler: Info already fetched, enabling download button after path selection."
                )
                self.bottom_controls_widget.enable_download(
                    button_text="Download Selection"
                )

    def fetch_video_info(self):
        """Initiates the process to fetch info for the entered URL."""
        logging.debug("UIActionHandler: fetch_video_info triggered.")
        url = self.top_frame_widget.get_url()
        if not url:
            logging.warning("UIActionHandler: Fetch button clicked with empty URL.")
            messagebox.showerror("Input Error", "Please enter a URL.")
            return

        logging.info(f"UIActionHandler: Requesting info fetch for URL: {url[:50]}...")
        self.fetched_info = None
        self.playlist_selector_widget.grid_remove()
        self.dynamic_area_label.configure(text="")
        self.top_frame_widget.set_url(url)

        self.current_operation = "fetch"
        self._last_toggled_playlist_mode = self.options_frame_widget.get_playlist_mode()
        logging.debug(
            f"UIActionHandler: Stored playlist mode before fetch: {self._last_toggled_playlist_mode}"
        )
        self._enter_fetching_state()  # الدالة تسجل بنفسها Function logs itself

        if self.logic:
            self.logic.start_info_fetch(url)
        else:
            logging.error(
                "UIActionHandler: Logic handler not available to start fetch!"
            )
            self._enter_idle_state()  # العودة لحالة آمنة Go back to safe state

    def toggle_playlist_mode(self):
        """Handles the manual toggling of the 'Is Playlist?' switch."""
        new_state = self.options_frame_widget.get_playlist_mode()
        logging.info(
            f"UIActionHandler: Playlist switch toggled manually to: {'ON' if new_state else 'OFF'}"
        )
        self._last_toggled_playlist_mode = new_state
        if self.fetched_info:
            logging.debug(
                "UIActionHandler: Info already fetched, re-rendering UI for playlist mode toggle."
            )
            self._enter_info_fetched_state()  # إعادة رسم الواجهة Re-render UI

    def start_download_ui(self):
        """Initiates the download process based on current selections."""
        logging.debug("UIActionHandler: start_download_ui triggered.")
        url = self.top_frame_widget.get_url()
        save_path = self.path_frame_widget.get_path()
        format_choice = self.options_frame_widget.get_format_choice()
        is_playlist_mode_on = self.options_frame_widget.get_playlist_mode()

        # Validation
        if not url:
            messagebox.showerror("Error", "URL is missing.")
            logging.error("UIActionHandler: Download start failed - URL missing.")
            return
        if not save_path:
            messagebox.showerror("Error", "Save location is missing.")
            logging.error("UIActionHandler: Download start failed - Save path missing.")
            return
        if not os.path.isdir(save_path):
            messagebox.showerror("Error", "Save location is not a valid directory.")
            logging.error(
                f"UIActionHandler: Download start failed - Invalid save path: {save_path}"
            )
            return
        if not self.fetched_info:
            messagebox.showerror("Error", "Fetch info first.")
            logging.error("UIActionHandler: Download start failed - Info not fetched.")
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
                logging.warning(
                    "UIActionHandler: Download start aborted - No playlist items selected."
                )
                return
            selected_items_count = len(playlist_items_string.split(","))
            logging.info(
                f"UIActionHandler: Starting playlist download. Selected: {selected_items_count}, Total: {total_playlist_count}, Items: {playlist_items_string}, Format: {format_choice}"
            )

        elif not is_playlist_mode_on and self.fetched_info:
            if is_actually_playlist:
                if messagebox.askyesno(
                    "Confirm Single Download",
                    "This is a playlist, but playlist mode is off.\nDo you want to download only the first video/item based on the URL?",
                ):
                    logging.info(
                        "UIActionHandler: Confirmed single download from playlist (mode OFF)."
                    )

                else:
                    logging.info(
                        "UIActionHandler: Single download from playlist cancelled by user."
                    )
                    return
            selected_items_count = 1
            logging.info(
                f"UIActionHandler: Starting single video/item download. General Format: {format_choice}, Playlist Total (if any): {total_playlist_count}"
            )
        else:
            # حالة غير متوقعة Unexpected state
            messagebox.showerror(
                "Logic Error",
                "Mismatch between UI state and fetched info during download start.",
            )
            logging.error(
                "UIActionHandler: Download start failed - Mismatch between UI state and fetched info."
            )
            return

        self.current_operation = "download"
        self._enter_downloading_state()  # الدالة تسجل Function logs

        if self.logic:
            self.logic.start_download(
                url=url,
                save_path=save_path,
                format_choice=format_choice,
                is_playlist=is_playlist_mode_on and is_actually_playlist,
                playlist_items=playlist_items_string,
                selected_items_count=selected_items_count,
                total_playlist_count=total_playlist_count,
            )
        else:
            logging.error(
                "UIActionHandler: Logic handler not available to start download!"
            )
            self._enter_idle_state()

    def cancel_operation_ui(self):
        """Requests cancellation of the active background operation."""
        logging.info("UIActionHandler: Cancel button pressed.")
        if self.current_operation:
            self.update_status(
                "Cancellation requested..."
            )  # تحديث مرئي للمستخدم Visual update
        if self.logic:
            self.logic.cancel_operation()  # الدالة تسجل Function logs
        else:
            logging.error("UIActionHandler: No logic handler available to cancel.")
            self._enter_idle_state()  # الدالة تسجل Function logs
