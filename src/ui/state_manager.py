# src/ui/state_manager.py
# -- Mixin class for managing UI states --
# -- Updated to control Fetch button and display single video thumbnail --

import os
from typing import TYPE_CHECKING, Optional, List, Dict, Any, Callable
import customtkinter as ctk  # For CTkLabel and CTkImage

# Import image loading utility
from src.logic.utils import (
    load_image_from_url_async,
    get_placeholder_ctk_image,
    DEFAULT_THUMBNAIL_SIZE,
)


if TYPE_CHECKING:
    # import customtkinter as ctk # Already imported above
    from .interface import UserInterface

    from .components.top_input_frame import TopInputFrame
    from .components.options_control_frame import OptionsControlFrame
    from .components.path_selection_frame import PathSelectionFrame
    from .components.bottom_controls_frame import BottomControlsFrame
    from .components.playlist_selector import PlaylistSelector

BTN_TXT_FETCH = "Fetch Info"
BTN_TXT_FETCHING = "Fetching..."
BTN_TXT_DOWNLOAD = "Download"
BTN_TXT_DOWNLOADING = "Downloading..."
BTN_TXT_DOWNLOAD_SELECTION = "Download Selection"
BTN_TXT_DOWNLOAD_VIDEO = "Download Video"
BTN_TXT_SELECT_SAVE_LOCATION = "Select Save Location"
STATUS_IDLE_DEFAULT = "Enter URL or Paste, then click Fetch Info."
STATUS_ERROR_PROCESSING_FETCHED = "Error: Failed to process fetched information."
STATUS_FETCHING_INFO = "Fetching information..."
LABEL_PLAYLIST_TITLE = "Playlist: {title} ({count} items total)"
LABEL_VIDEO_TITLE = "Video: {title}"
LABEL_EMPTY = ""
SINGLE_VIDEO_THUMBNAIL_SIZE = (240, 135)  # Larger thumbnail for single video display


class UIStateManagerMixin:
    if TYPE_CHECKING:
        self: "UserInterface"
        top_frame_widget: TopInputFrame
        options_frame_widget: OptionsControlFrame
        path_frame_widget: PathSelectionFrame
        bottom_controls_widget: BottomControlsFrame
        playlist_selector_widget: PlaylistSelector
        dynamic_area_label: ctk.CTkLabel
        # --- Add new widget for single video thumbnail ---
        single_video_thumbnail_label: ctk.CTkLabel
        # --- ---
        progress_bar: ctk.CTkProgressBar
        fetched_info: Optional[Dict[str, Any]]
        current_operation: Optional[str]
        _last_toggled_playlist_mode: bool
        update_status: Callable[[str], None]
        update_idletasks: Callable[[], None]
        # Method from UserInterface to get the root window for .after()
        winfo_toplevel: Callable[[], Any]

    def _enable_main_controls(self, enable_playlist_switch: bool = True) -> None:
        try:
            self.top_frame_widget.enable_entry()
            self.options_frame_widget.format_combobox.configure(state="normal")
            switch_state = "normal" if enable_playlist_switch else "disabled"
            self.options_frame_widget.playlist_switch.configure(state=switch_state)
            self.path_frame_widget.enable()
            self.bottom_controls_widget.enable_fetch()
        except AttributeError as e:
            print(f"Error enabling main controls (widget might be missing): {e}")
        except Exception as e:
            print(f"Unexpected error enabling main controls: {e}")

    def _enter_idle_state(self) -> None:
        print("UI_Interface: Entering idle state.")
        self._enable_main_controls(enable_playlist_switch=True)
        self.bottom_controls_widget.disable_download(button_text=BTN_TXT_DOWNLOAD)
        self.bottom_controls_widget.hide_cancel_button()

        self.dynamic_area_label.configure(text=LABEL_EMPTY)
        if hasattr(self, "single_video_thumbnail_label"):  # Hide thumbnail label
            self.single_video_thumbnail_label.grid_remove()
            self.single_video_thumbnail_label.configure(
                image=None
            )  # Clear previous image

        self.playlist_selector_widget.grid_remove()
        self.playlist_selector_widget.reset()

        self.fetched_info = None
        self.current_operation = None
        try:
            self.options_frame_widget.set_playlist_mode(True)
            self._last_toggled_playlist_mode = True
        except Exception as e:
            print(f"Error resetting playlist mode in idle state: {e}")

        self.update_status(STATUS_IDLE_DEFAULT)
        try:
            if self.progress_bar:
                self.progress_bar.set(0.0)
        except Exception as e:
            print(f"Error resetting progress bar: {e}")

    def _enter_fetching_state(self) -> None:
        self._extracted_from__enter_downloading_state_3(
            "UI_Interface: Entering fetching state."
        )
        self.bottom_controls_widget.disable_fetch(button_text=BTN_TXT_FETCHING)
        self.bottom_controls_widget.disable_download()
        self.bottom_controls_widget.show_cancel_button()
        self.update_status(STATUS_FETCHING_INFO)
        try:
            if self.progress_bar:
                self.progress_bar.set(0.0)
        except Exception as e:
            print(f"Error setting progress bar for fetching state: {e}")

    def _enter_downloading_state(self) -> None:
        self._extracted_from__enter_downloading_state_3(
            "UI_Interface: Entering downloading state."
        )
        self.playlist_selector_widget.disable()
        self.bottom_controls_widget.disable_fetch()
        self.bottom_controls_widget.disable_download(button_text=BTN_TXT_DOWNLOADING)
        self.bottom_controls_widget.show_cancel_button()

    def _extracted_from__enter_downloading_state_3(self, arg0):
        print(arg0)
        self.top_frame_widget.disable_entry()
        self.options_frame_widget.disable()
        self.path_frame_widget.disable()

    def _display_playlist_view(self) -> None:
        if not self.fetched_info:
            print("UI State Error: _display_playlist_view called without fetched_info.")
            return

        # Hide single video thumbnail if it was visible
        if hasattr(self, "single_video_thumbnail_label"):
            self.single_video_thumbnail_label.grid_remove()
            self.single_video_thumbnail_label.configure(image=None)

        playlist_title: str = self.fetched_info.get("title", "Untitled Playlist")
        entries: List[Dict[str, Any]] = self.fetched_info.get("entries", [])
        total_items: int = len(entries)
        self.dynamic_area_label.configure(
            text=LABEL_PLAYLIST_TITLE.format(title=playlist_title, count=total_items)
        )
        self.playlist_selector_widget.populate_items(entries)
        self.playlist_selector_widget.enable()
        # Ensure dynamic_area_label is above playlist_selector
        self.dynamic_area_label.grid(
            row=3, column=0, padx=20, pady=(10, 0), sticky="w"
        )  # Ensure it's gridded
        self.playlist_selector_widget.grid(
            row=4, column=0, padx=20, pady=(5, 10), sticky="nsew"
        )
        print("UI_Interface: Playlist frame gridded and populated.")

    def _enter_info_fetched_state(self) -> None:
        if not self.fetched_info:
            print(
                "UI State Error: _enter_info_fetched_state called without fetched_info."
            )
            self._enter_idle_state()
            self.update_status(STATUS_ERROR_PROCESSING_FETCHED)
            return

        is_actually_playlist: bool = isinstance(self.fetched_info.get("entries"), list)
        self._enable_main_controls(enable_playlist_switch=is_actually_playlist)

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
        if save_path and os.path.isdir(save_path):
            btn_text: str = (
                BTN_TXT_DOWNLOAD_SELECTION
                if should_show_playlist_view
                else BTN_TXT_DOWNLOAD_VIDEO
            )
            self.bottom_controls_widget.enable_download(button_text=btn_text)
        else:
            self.bottom_controls_widget.disable_download(
                button_text=BTN_TXT_SELECT_SAVE_LOCATION
            )

        if should_show_playlist_view:
            self._display_playlist_view()
        else:  # Single video
            self.playlist_selector_widget.grid_remove()
            video_title: str = self.fetched_info.get("title", "Untitled Video")
            thumbnail_url: Optional[str] = self.fetched_info.get("thumbnail_url")

            # Configure and grid the title label
            if hasattr(self, "dynamic_area_label"):
                self.dynamic_area_label.configure(
                    text=LABEL_VIDEO_TITLE.format(title=video_title)
                )
                self.dynamic_area_label.grid(
                    row=3, column=0, padx=20, pady=(10, 0), sticky="w"
                )  # Ensure it's visible
            else:
                print(
                    "Warning: dynamic_area_label not found in _enter_info_fetched_state"
                )

            # Configure and grid the thumbnail label
            if hasattr(self, "single_video_thumbnail_label"):
                # Set placeholder first
                placeholder_img = get_placeholder_ctk_image(SINGLE_VIDEO_THUMBNAIL_SIZE)
                self.single_video_thumbnail_label.configure(image=placeholder_img)
                self.single_video_thumbnail_label.grid(
                    row=4, column=0, padx=20, pady=5, sticky="w"
                )  # Below title

                if thumbnail_url:

                    def _update_single_thumb_callback(loaded_image: Optional[Any]):
                        if loaded_image:
                            self.single_video_thumbnail_label.configure(
                                image=loaded_image
                            )
                        # If None, placeholder remains

                    # Use self.winfo_toplevel() to get the root window for .after() context
                    root_window = (
                        self.winfo_toplevel()
                        if hasattr(self, "winfo_toplevel")
                        else self
                    )
                    load_image_from_url_async(
                        thumbnail_url,
                        _update_single_thumb_callback,
                        target_widget=root_window,  # Pass the root window
                        target_size=SINGLE_VIDEO_THUMBNAIL_SIZE,
                    )
            else:
                print(
                    "Warning: single_video_thumbnail_label not found in _enter_info_fetched_state"
                )

        try:
            if self.progress_bar:
                self.progress_bar.set(0.0)
        except Exception as e:
            print(f"Error resetting progress bar in info fetched state: {e}")

        self.update_idletasks()
