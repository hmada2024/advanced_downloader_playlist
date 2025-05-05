# src/ui_interface.py
# -- Main application UI window class and coordinator between components --
# -- Modified to include TabView for Home and History --

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
TAB_HOME = "Home"
TAB_HISTORY = "History"


# The main UI class now inherits from CTk window and the functional Mixins
class UserInterface(
    ctk.CTk, UIStateManagerMixin, UICallbackHandlerMixin, UIActionHandlerMixin
):
    """
    Main application window with TabView interface.
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

        # --- Main Window Grid Configuration ---
        # Configure grid for TabView (row 0) and status/progress (rows 1, 2)
        self.grid_columnconfigure(0, weight=1)  # Main column expands
        self.grid_rowconfigure(0, weight=1)  # TabView row expands
        self.grid_rowconfigure(1, weight=0)  # Progress bar row fixed height
        self.grid_rowconfigure(2, weight=0)  # Status label row fixed height

        # --- Create Tab View ---
        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # --- Add Tabs ---
        self.tab_view.add(TAB_HOME)
        self.tab_view.add(TAB_HISTORY)
        self.tab_view.set(TAB_HOME)  # Set "Home" as the initially visible tab

        # --- Get Tab Frames ---
        self.home_tab_frame = self.tab_view.tab(TAB_HOME)
        self.history_tab_frame = self.tab_view.tab(TAB_HISTORY)

        # --- Configure Grid Layout inside Home Tab ---
        self.home_tab_frame.grid_columnconfigure(
            0, weight=1
        )  # Column 0 expands horizontally
        # Assuming PlaylistSelector is in row 4 and should expand vertically
        self.home_tab_frame.grid_rowconfigure(4, weight=1)

        # --- Create UI Component Instances for Home Tab ---
        # IMPORTANT: Change 'master' to 'self.home_tab_frame' for components inside the Home tab
        self.top_frame_widget = TopInputFrame(
            self.home_tab_frame,  # Master is now Home tab
            fetch_command=self.fetch_video_info,
        )
        self.options_frame_widget = OptionsControlFrame(
            self.home_tab_frame,  # Master is now Home tab
            toggle_playlist_command=self.toggle_playlist_mode,
        )
        self.path_frame_widget = PathSelectionFrame(
            self.home_tab_frame,  # Master is now Home tab
            browse_callback=self.browse_path_logic,
        )
        # Label for dynamic content (Video title or Playlist title) inside Home tab
        self.dynamic_area_label = ctk.CTkLabel(
            self.home_tab_frame,  # Master is now Home tab
            text="",
            font=ctk.CTkFont(weight="bold"),
        )
        # Playlist selector (Scrollable frame for playlist items) inside Home tab
        self.playlist_selector_widget = PlaylistSelector(
            self.home_tab_frame  # Master is now Home tab
        )
        # Bottom controls (Download/Cancel buttons) inside Home tab
        self.bottom_controls_widget = BottomControlsFrame(
            self.home_tab_frame,  # Master is now Home tab
            download_command=self.start_download_ui,
            cancel_command=self.cancel_operation_ui,
        )

        # --- Grid the UI Components into the Home Tab Frame ---
        # Grid positions are relative to home_tab_frame
        self.top_frame_widget.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="ew")
        self.options_frame_widget.grid(row=1, column=0, padx=15, pady=5, sticky="ew")
        self.path_frame_widget.grid(row=2, column=0, padx=15, pady=5, sticky="ew")
        self.dynamic_area_label.grid(row=3, column=0, padx=20, pady=(10, 0), sticky="w")
        # Playlist selector (row 4) is gridded dynamically by _display_playlist_view (inside home_tab_frame)
        # self.playlist_selector_widget.grid(...) # Done in state manager
        self.bottom_controls_widget.grid(
            row=6,
            column=0,
            padx=15,
            pady=(5, 5),
            sticky="ew",  # Below potential playlist
        )

        # --- Create Widgets Below the TabView (in the main window) ---
        # Progress Bar (master is self - the main window)
        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.set(0)  # Initialize progress to 0

        # Status Label at the bottom (master is self - the main window)
        self.status_label = ctk.CTkLabel(
            self,
            text=DEFAULT_STATUS,
            text_color=DEFAULT_STATUS_COLOR,
            font=ctk.CTkFont(size=13),
            justify="left",  # Justify left for multi-line status
            anchor="w",  # Anchor text to the west (left)
        )

        # --- Grid Widgets Below TabView ---
        # Use row 1 and 2 of the main window's grid
        self.progress_bar.grid(row=1, column=0, padx=20, pady=(0, 5), sticky="ew")
        self.status_label.grid(row=2, column=0, padx=25, pady=(0, 10), sticky="ew")

        # --- History Tab Content (Placeholder) ---
        # Leave the history_tab_frame empty for now
        # You could add a simple label as a placeholder if you like:
        # history_placeholder = ctk.CTkLabel(self.history_tab_frame, text="History will be shown here.")
        # history_placeholder.pack(padx=20, pady=20)

        # --- Enter Initial UI State ---
        # Call the state management method to set up the initial idle appearance
        # This should still work as it references the widgets stored in 'self'
        self._enter_idle_state()

    def set_default_save_path(self, path: str) -> None:
        """
        Sets the initial text in the save path entry widget.
        Called by main.py after finding the default path.

        Args:
            path (str): The default save path string.
        """
        # This method should still work correctly as self.path_frame_widget exists
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


# --- Mixin Methods ---
# The methods inherited from UIStateManagerMixin, UICallbackHandlerMixin,
# and UIActionHandlerMixin should generally continue to work because they
# access the widgets through `self.widget_name` (e.g., self.top_frame_widget,
# self.bottom_controls_widget), and we still store these references in `self`
# even though the widgets' master has changed to `self.home_tab_frame`.
# Make sure any grid operations inside the mixins correctly handle the context
# (e.g., `self.playlist_selector_widget.grid(...)` will grid inside its master,
# which is now `home_tab_frame`).
