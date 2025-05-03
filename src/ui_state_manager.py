# src/ui_state_manager.py
# -- Mixin class for managing UI states --

import customtkinter as ctk
import os
import logging  # <-- إضافة استيراد logging


class UIStateManagerMixin:
    """Mixin class containing methods for managing the UI state transitions."""

    def _enable_main_controls(self, enable_playlist_switch=True):
        """Enables the main input controls."""
        logging.debug(
            f"UIStateManager: Enabling main controls (Playlist Switch Enabled: {enable_playlist_switch})."
        )
        self.top_frame_widget.enable_fetch()
        self.options_frame_widget.format_combobox.configure(state="normal")
        switch_state = "normal" if enable_playlist_switch else "disabled"
        self.options_frame_widget.playlist_switch.configure(state=switch_state)
        self.path_frame_widget.enable()

    def _enter_idle_state(self):
        """Enters the idle state (ready for a new operation)."""
        # تم استخدام print هنا سابقاً، نستخدم logging.info
        logging.info("UIStateManager: Entering idle state.")
        self._enable_main_controls(enable_playlist_switch=True)
        self.bottom_controls_widget.disable_download(button_text="Download")
        self.bottom_controls_widget.hide_cancel_button()
        self.dynamic_area_label.configure(text="")

        self.playlist_selector_widget.grid_remove()
        self.playlist_selector_widget.reset()

        self.fetched_info = None
        self.status_label.configure(
            text="Enter URL and click Fetch Info.", text_color="gray", justify="center"
        )  # العودة للوسط Reset justify
        self.progress_bar.set(0)
        self.current_operation = None
        self.options_frame_widget.set_playlist_mode(True)
        self._last_toggled_playlist_mode = True

    def _enter_fetching_state(self):
        """Enters the state while fetching information."""
        logging.info("UIStateManager: Entering fetching state.")
        self.top_frame_widget.disable_fetch(button_text="Fetching...")
        self.options_frame_widget.disable()
        self.path_frame_widget.disable()
        self.bottom_controls_widget.disable_download()
        self.bottom_controls_widget.show_cancel_button()
        self.status_label.configure(
            text="Fetching information...", text_color="orange", justify="center"
        )
        self.progress_bar.set(0)
        # يمكن إضافة وضع indeterminate هنا إذا أردت
        # self.progress_bar.configure(mode="indeterminate"); self.progress_bar.start()

    def _enter_downloading_state(self):
        """Enters the state during download/processing."""
        logging.info("UIStateManager: Entering downloading state.")
        # إيقاف شريط التقدم غير المحدد إذا كان يعمل Stop indeterminate progress bar if running
        # self.progress_bar.stop(); self.progress_bar.configure(mode="determinate")
        self.top_frame_widget.disable_fetch()
        self.options_frame_widget.disable()
        self.path_frame_widget.disable()
        self.playlist_selector_widget.disable()

        self.bottom_controls_widget.disable_download(button_text="Downloading...")
        self.bottom_controls_widget.show_cancel_button()

    def _display_playlist_view(self):
        """Sets up and displays the playlist selection view."""
        logging.debug("UIStateManager: Displaying playlist view.")
        playlist_title = self.fetched_info.get("title", "Untitled Playlist")
        total_items = len(self.fetched_info.get("entries", []))
        self.dynamic_area_label.configure(
            text=f"Playlist: {playlist_title} ({total_items} items total)"
        )

        self.playlist_selector_widget.populate_items(self.fetched_info.get("entries"))
        self.playlist_selector_widget.enable()
        self.playlist_selector_widget.grid(
            row=4, column=0, padx=20, pady=(5, 10), sticky="nsew"
        )
        logging.debug("UIStateManager: Playlist frame gridded.")

    def _enter_info_fetched_state(self):
        """Enters the state after information has been successfully fetched."""
        # إيقاف شريط التقدم غير المحدد إذا كان يعمل Stop indeterminate progress bar if running
        # self.progress_bar.stop(); self.progress_bar.configure(mode="determinate")

        if not self.fetched_info:
            logging.error(
                "UIStateManager: _enter_info_fetched_state called without fetched_info."
            )
            self._enter_idle_state()
            self.update_status("Error: Failed to process fetched information.")
            return

        is_actually_playlist = isinstance(self.fetched_info.get("entries"), list)
        should_show_playlist_view = (
            self.options_frame_widget.get_playlist_mode() and is_actually_playlist
        )

        log_msg = (
            f"UIStateManager: Entering info fetched state.\n"
            f"  Actual Playlist: {is_actually_playlist}\n"
            f"  Switch ON: {self.options_frame_widget.get_playlist_mode()}\n"
            f"  Show Playlist View: {should_show_playlist_view}"
        )
        logging.info(log_msg)

        self._enable_main_controls(enable_playlist_switch=is_actually_playlist)
        self.bottom_controls_widget.hide_cancel_button()

        save_path = self.path_frame_widget.get_path()
        if save_path and os.path.isdir(save_path):
            logging.debug("UIStateManager: Valid save path found, enabling download.")
            self.bottom_controls_widget.enable_download(
                button_text="Download Selection"
            )
        else:
            logging.debug("UIStateManager: No valid save path, disabling download.")
            self.bottom_controls_widget.disable_download(
                button_text="Select Save Location"
            )

        if should_show_playlist_view:
            self._display_playlist_view()
        else:
            logging.debug(
                "UIStateManager: Hiding playlist view, showing single video title."
            )
            video_title = self.fetched_info.get("title", "Untitled Video")
            self.dynamic_area_label.configure(text=f"Video: {video_title}")
            self.playlist_selector_widget.grid_remove()
            if (
                is_actually_playlist
            ):  # إذا كانت قائمة ولكن الوضع مطفأ، تأكد من تمكين المفتاح
                self.options_frame_widget.playlist_switch.configure(state="normal")

        self.update_idletasks()  # لا يزال مفيداً Sometimes useful
