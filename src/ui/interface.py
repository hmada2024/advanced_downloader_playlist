# src/ui/interface.py
# -- Main application UI window class and coordinator between components --
# -- Modified for Queue Tab, removed GetLinks, adjusted callbacks --

import contextlib
from tkinter import messagebox
import customtkinter as ctk
from typing import Optional, Dict, Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from ..logic.logic_handler import LogicHandler
    from ..logic.history_manager import HistoryManager
    from .queue_tab import QueueTab  # Import new QueueTab

from .state_manager import (
    UIStateManagerMixin,
    LABEL_EMPTY,
    BTN_TXT_DOWNLOAD_VIDEO,
    BTN_TXT_DOWNLOAD_SELECTION,
    SINGLE_VIDEO_THUMBNAIL_SIZE,
)
from .callback_handler import (
    UICallbackHandlerMixin,
    COLOR_CANCEL,
    COLOR_ERROR,
    COLOR_SUCCESS,
    COLOR_INFO,
)
from .action_handler import (
    UIActionHandlerMixin,
    TITLE_INPUT_ERROR,
    MSG_URL_EMPTY,
    OP_FETCH,  # Still used for fetch info
    # OP_DOWNLOAD removed as individual downloads aren't tracked this way anymore
    MSG_LOGIC_HANDLER_MISSING,
)

# --- Component Imports ---
from .components.top_input_frame import TopInputFrame
from .components.options_control_frame import OptionsControlFrame
from .components.path_selection_frame import PathSelectionFrame
from .components.bottom_controls_frame import BottomControlsFrame
from .components.playlist_selector import PlaylistSelector

# --- Tab Imports ---
# from .get_links_tab import GetLinksTab # <<< REMOVED
from .history_tab import HistoryTab
from .queue_tab import QueueTab  # <<< ADDED

# Import utility for placeholder image
from src.logic.utils import get_placeholder_ctk_image

APP_TITLE = "Advanced Spider Fetch"
INITIAL_GEOMETRY = "900x750"
DEFAULT_STATUS = "Initializing..."
DEFAULT_STATUS_COLOR = "gray"
TAB_HOME = "Add Download"  # Renamed for clarity
# TAB_GET_LINKS = "Get Temporary Playlist Links For Downloading" # <<< REMOVED
TAB_QUEUE = "Download Queue"  # <<< ADDED
TAB_HISTORY = "History"


class UserInterface(
    ctk.CTk, UIStateManagerMixin, UICallbackHandlerMixin, UIActionHandlerMixin
):
    def __init__(
        self,
        logic_handler: Optional[
            "LogicHandler"
        ] = None,  # LogicHandler will be set later
        history_manager: Optional["HistoryManager"] = None,
    ) -> None:
        super().__init__()

        self.logic: Optional["LogicHandler"] = logic_handler
        self.history_manager: Optional["HistoryManager"] = history_manager
        self.fetched_info: Optional[Dict[str, Any]] = None
        self.current_operation: Optional[str] = None  # Now primarily tracks 'fetch'
        self._last_toggled_playlist_mode: bool = True
        self._current_fetch_url: Optional[str] = None

        # --- Queue Tab Reference ---
        self.queue_tab: Optional[QueueTab] = None  # Will be initialized

        self.title(APP_TITLE)
        self.geometry(INITIAL_GEOMETRY)
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)  # Tab view row
        self.grid_rowconfigure(1, weight=0)  # Progress bar row
        self.grid_rowconfigure(2, weight=0)  # Status label row

        # --- Tab View Setup ---
        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.tab_view.configure(command=self._on_tab_change)  # Keep tab change logic

        self.tab_view.add(TAB_HOME)
        self.tab_view.add(TAB_QUEUE)  # <<< ADDED
        # self.tab_view.add(TAB_GET_LINKS) # <<< REMOVED
        self.tab_view.add(TAB_HISTORY)
        self.tab_view.set(TAB_HOME)  # Start on the main download tab

        self.home_tab_frame = self.tab_view.tab(TAB_HOME)
        self.queue_tab_frame = self.tab_view.tab(TAB_QUEUE)  # <<< ADDED
        # self.get_links_tab_frame = self.tab_view.tab(TAB_GET_LINKS) # <<< REMOVED
        self.history_tab_frame = self.tab_view.tab(TAB_HISTORY)

        # --- Initialize Tabs ---
        self._setup_home_tab()
        # Queue tab setup needs logic handler, defer slightly or handle missing logic later
        # self._setup_queue_tab() # Call will happen after logic handler is assigned
        self._setup_history_tab()

        # --- Bottom Status/Progress Bar ---
        # Still useful for Fetch Info and general messages
        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.set(0)
        self.status_label = ctk.CTkLabel(
            self,
            text=DEFAULT_STATUS,
            text_color=DEFAULT_STATUS_COLOR,
            font=ctk.CTkFont(size=13),
            justify="left",
            anchor="w",
        )
        self.progress_bar.grid(row=1, column=0, padx=20, pady=(0, 5), sticky="ew")
        self.status_label.grid(row=2, column=0, padx=25, pady=(0, 10), sticky="ew")

        # Initialize state (Home tab starts idle)
        self._enter_idle_state()

    def _setup_home_tab(self) -> None:
        """Sets up the widgets for the main 'Add Download' tab."""
        # --- Grid and Widget setup remains largely the same ---
        self.home_tab_frame.grid_columnconfigure(0, weight=1)
        self.home_tab_frame.grid_rowconfigure(4, weight=1)  # Dynamic area row

        # Create components
        self.top_frame_widget = TopInputFrame(
            self.home_tab_frame,
            paste_command=self.paste_url_action,
        )
        self.options_frame_widget = OptionsControlFrame(
            self.home_tab_frame, toggle_playlist_command=self.toggle_playlist_mode
        )
        self.path_frame_widget = PathSelectionFrame(
            self.home_tab_frame, browse_callback=self.browse_path_logic
        )
        # Label for playlist/video title
        self.dynamic_area_label = ctk.CTkLabel(
            self.home_tab_frame,
            text="",
            font=ctk.CTkFont(weight="bold"),
            wraplength=750,
        )
        # Label for single video thumbnail
        self.single_video_thumbnail_label = ctk.CTkLabel(
            self.home_tab_frame,
            text="",
            image=get_placeholder_ctk_image(SINGLE_VIDEO_THUMBNAIL_SIZE),
            width=SINGLE_VIDEO_THUMBNAIL_SIZE[0],
            height=SINGLE_VIDEO_THUMBNAIL_SIZE[1],
        )
        # Playlist item selector
        self.playlist_selector_widget = PlaylistSelector(self.home_tab_frame)
        # Bottom controls (Fetch, Download->Add To Queue, Cancel Fetch)
        self.bottom_controls_widget = BottomControlsFrame(
            self.home_tab_frame,
            fetch_command=self.fetch_video_info,  # Starts info fetch
            download_command=self.start_download_ui,  # Now adds to queue
            cancel_command=self.cancel_operation_ui,  # Now cancels fetch info
        )

        # Grid components
        self.top_frame_widget.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="ew")
        self.options_frame_widget.grid(row=1, column=0, padx=15, pady=5, sticky="ew")
        self.path_frame_widget.grid(row=2, column=0, padx=15, pady=5, sticky="ew")
        # row 3: dynamic_area_label (gridded by state manager)
        # row 4: single_video_thumbnail_label OR playlist_selector_widget (gridded by state manager)
        self.bottom_controls_widget.grid(
            row=5, column=0, padx=15, pady=(10, 15), sticky="ew"
        )

    # <<< REMOVED: _setup_get_links_tab method >>>

    def _setup_queue_tab(self) -> None:
        """Sets up the Download Queue tab."""
        if not self.logic:
            print("UI Error: Logic Handler not available for Queue Tab setup.")
            # Display error message in the tab
            error_label = ctk.CTkLabel(
                self.queue_tab_frame,
                text="Error: Queue unavailable (Logic Handler missing).",
                text_color="red",
            )
            error_label.pack(pady=20)
            return

        self.queue_tab_frame.grid_rowconfigure(0, weight=1)
        self.queue_tab_frame.grid_columnconfigure(0, weight=1)

        # --- Create the QueueTab instance ---
        self.queue_tab = QueueTab(
            master=self.queue_tab_frame,
            logic_handler=self.logic,
            history_manager=self.history_manager,  # Pass history manager if needed
        )
        self.queue_tab.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        print("UI: Queue tab setup complete.")

    def _setup_history_tab(self) -> None:
        """Sets up the History tab."""
        if not self.history_manager:
            print("UI Error: History Manager not available for History Tab setup.")
            error_label = ctk.CTkLabel(
                self.history_tab_frame,
                text="Error: History unavailable.",
                text_color="red",
            )
            error_label.pack(pady=20)
            return

        self.history_tab_frame.grid_rowconfigure(0, weight=1)
        self.history_tab_frame.grid_columnconfigure(0, weight=1)
        # --- HistoryTab initialization remains the same ---
        self.history_content = HistoryTab(
            master=self.history_tab_frame,
            history_manager=self.history_manager,
            ui_interface_ref=self,  # Pass self for callbacks like switching tabs
        )
        self.history_content.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

    def _on_tab_change(self) -> None:
        """Handles actions when the selected tab changes."""
        selected_tab = self.tab_view.get()
        print(f"UI: Tab changed to: {selected_tab}")
        # Refresh history tab when viewed
        if selected_tab == TAB_HISTORY and hasattr(self, "history_content"):
            self.history_content.refresh_history()
        # Add any actions needed when switching to/from Queue tab if necessary

    # --- Callback Methods (Routing to QueueTab or Main Status) ---
    # These methods are now part of UICallbackHandlerMixin,
    # the signatures and routing logic will be updated there.

    # --- Methods for Tab Switching (from History) ---
    def switch_to_downloader_tab(self, url: str) -> None:
        """Switches to the main download tab and populates the URL."""
        print(f"UI: Switching to Downloader tab with URL: {url}")
        self.tab_view.set(TAB_HOME)  # Use the constant for the home tab
        if hasattr(self, "top_frame_widget"):
            self.top_frame_widget.set_url(url)
            # Update main status bar, as this is a general action
            self.update_status("URL loaded from history. Click 'Fetch Info'.")
        else:
            print("UI Error: Downloader tab widgets not ready for URL population.")

    # <<< REMOVED: switch_to_getlinks_tab method >>>

    def set_default_save_path(self, path: str) -> None:
        """Sets the default save path in the PathSelectionFrame."""
        if hasattr(self, "path_frame_widget") and self.path_frame_widget:
            try:
                self.path_frame_widget.set_path(path)
                print(f"UI: Default save path set to '{path}' for Downloader tab.")
            except Exception as e:
                print(f"UI Error: Could not set default path: {e}")
        else:
            print("UI Error: Path frame widget not available to set default path.")

    # --- Link Logic Handler ---
    def set_logic_handler(self, logic_handler: "LogicHandler"):
        """Sets the logic handler after initialization and sets up dependent tabs."""
        print("UI: Setting Logic Handler.")
        self.logic = logic_handler
        # Now that logic handler is available, setup the queue tab
        self._setup_queue_tab()
