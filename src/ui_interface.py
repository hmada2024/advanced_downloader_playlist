# src/ui_interface.py
# -- Main application UI window class and coordinator between components --

import customtkinter as ctk
from typing import Optional, Dict, Any, Callable  # Added typing

# --- Import Logic and Handler Classes ---
# Use Optional since logic_handler might be injected after __init__
from .logic_handler import LogicHandler, Optional

# Import Mixin Classes (which provide functionality to UserInterface)
from .ui_state_manager import UIStateManagerMixin
from .ui_callback_handler import UICallbackHandlerMixin
from .ui_action_handler import UIActionHandlerMixin

# --- Import UI Component Classes ---
from .ui_components.top_input_frame import TopInputFrame
from .ui_components.options_control_frame import OptionsControlFrame
from .ui_components.path_selection_frame import PathSelectionFrame
from .ui_components.bottom_controls_frame import BottomControlsFrame
from .ui_components.playlist_selector import PlaylistSelector

# --- Constants ---
APP_TITLE = "Advanced Downloader"
INITIAL_GEOMETRY = "850x750"  # Initial window size
DEFAULT_STATUS = "Initializing..."
DEFAULT_STATUS_COLOR = "gray"


# The main UI class now inherits from CTk window and the functional Mixins
class UserInterface(
    ctk.CTk, UIStateManagerMixin, UICallbackHandlerMixin, UIActionHandlerMixin
):
    """
    Main application window.
    Initializes UI components and inherits functionality from Mixin classes for:
    - State management (UIStateManagerMixin)
    - Callback handling from logic layer (UICallbackHandlerMixin)
    - Handling user actions like button clicks (UIActionHandlerMixin)
    """

    def __init__(self, logic_handler: Optional[LogicHandler] = None) -> None:
        """
        Initializes the main window, creates UI components, links logic, and sets initial state.
        Args:
            logic_handler (Optional[LogicHandler]): Instance of the LogicHandler.
                                                     Can be None initially and set later.
        """
        super().__init__()  # Initialize the CTk window

        # --- Instance Attributes ---
        # Logic Handler (can be set after initialization)
        self.logic: Optional[LogicHandler] = logic_handler
        # Data fetched from URL
        self.fetched_info: Optional[Dict[str, Any]] = None
        # Tracks the current background operation ('fetch' or 'download')
        self.current_operation: Optional[str] = None
        # Stores user's last explicit playlist switch preference
        self._last_toggled_playlist_mode: bool = (
            True  # Default to playlist mode ON preference
        )

        # --- Basic Window Setup ---
        self.title(APP_TITLE)
        self.geometry(INITIAL_GEOMETRY)
        # Appearance settings (consider making these configurable)
        ctk.set_appearance_mode("System")  # Follow system theme (Light/Dark)
        ctk.set_default_color_theme("blue")  # Set theme color

        # --- Main Grid Configuration ---
        # Make the main column expandable
        self.grid_columnconfigure(0, weight=1)
        # Make the row containing the playlist selector expandable (row 4)
        self.grid_rowconfigure(4, weight=1)
        # Add weights to other rows if needed for specific resize behavior

        # --- Create UI Component Instances ---
        # Pass 'self' as master and necessary callbacks from ActionHandlerMixin
        self.top_frame_widget = TopInputFrame(self, fetch_command=self.fetch_video_info)
        self.options_frame_widget = OptionsControlFrame(
            self, toggle_playlist_command=self.toggle_playlist_mode
        )
        self.path_frame_widget = PathSelectionFrame(
            self, browse_callback=self.browse_path_logic
        )
        self.playlist_selector_widget = PlaylistSelector(
            self
        )  # Scrollable frame for playlist items
        self.bottom_controls_widget = BottomControlsFrame(
            self,
            download_command=self.start_download_ui,
            cancel_command=self.cancel_operation_ui,
        )
        # Label for dynamic content (Video title or Playlist title)
        self.dynamic_area_label = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(weight="bold")  # Start empty
        )
        # Progress Bar
        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.set(0)  # Initialize progress to 0

        # Status Label at the bottom
        self.status_label = ctk.CTkLabel(
            self,
            text=DEFAULT_STATUS,
            text_color=DEFAULT_STATUS_COLOR,
            font=ctk.CTkFont(size=13),
            justify="left",  # Justify left for multi-line status
            anchor="w",  # Anchor text to the west (left)
        )

        # --- Grid the UI Components into the Main Window ---
        # Order matters for layout and row numbers
        self.top_frame_widget.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="ew")
        self.options_frame_widget.grid(row=1, column=0, padx=15, pady=5, sticky="ew")
        self.path_frame_widget.grid(row=2, column=0, padx=15, pady=5, sticky="ew")
        self.dynamic_area_label.grid(row=3, column=0, padx=20, pady=(10, 0), sticky="w")
        # Playlist selector (row 4) is gridded dynamically by _display_playlist_view
        # self.playlist_selector_widget.grid(...) # Done in state manager
        self.bottom_controls_widget.grid(
            row=6, column=0, padx=15, pady=(5, 5), sticky="ew"
        )  # Below potential playlist
        self.progress_bar.grid(row=7, column=0, padx=20, pady=(0, 5), sticky="ew")
        self.status_label.grid(row=8, column=0, padx=25, pady=(0, 10), sticky="ew")

        # --- Enter Initial UI State ---
        # Call the state management method to set up the initial idle appearance
        self._enter_idle_state()

    def set_default_save_path(self, path: str) -> None:
        """
        Sets the initial text in the save path entry widget.
        Called by main.py after finding the default path.

        Args:
            path (str): The default save path string.
        """
        if self.path_frame_widget:  # Ensure widget exists
            try:
                self.path_frame_widget.set_path(path)
                print(f"UI: Default save path set to '{path}'")
                # If info was fetched *before* default path was set,
                # we might need to re-evaluate the download button state.
                # This is now handled within _enter_info_fetched_state.
            except Exception as e:
                print(f"UI Error: Could not set default path in widget: {e}")
        else:
            # This shouldn't happen if called after __init__
            print("UI Error: Path frame widget not available to set default path.")
