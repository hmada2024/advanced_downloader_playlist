# src/ui/interface.py
# -- Main application UI window class and coordinator between components --
# -- Modified for Queue Tab, removed GetLinks, adjusted callbacks, status bar size/font --

import contextlib
from tkinter import messagebox
import customtkinter as ctk
from typing import Optional, Dict, Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from ..logic.logic_handler import LogicHandler
    from ..logic.history_manager import HistoryManager
    from .queue_tab import QueueTab

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
    COLOR_DEFAULT,  # Import COLOR_DEFAULT
)
from .action_handler import (
    UIActionHandlerMixin,
    TITLE_INPUT_ERROR,
    MSG_URL_EMPTY,
    OP_FETCH,
    MSG_LOGIC_HANDLER_MISSING,
)

# --- Component Imports ---
from .components.top_input_frame import TopInputFrame
from .components.options_control_frame import OptionsControlFrame
from .components.path_selection_frame import PathSelectionFrame
from .components.bottom_controls_frame import BottomControlsFrame
from .components.playlist_selector import PlaylistSelector

# --- Tab Imports ---
from .history_tab import HistoryTab
from .queue_tab import QueueTab

# Import utility for placeholder image
from src.logic.utils import get_placeholder_ctk_image

APP_TITLE = "Advanced Spider Fetch"
INITIAL_GEOMETRY = "900x800"  # Increased height slightly for status bar
DEFAULT_STATUS = "Initializing..."
# Constants for Tabs (English)
TAB_HOME = "Add Download"
TAB_QUEUE = "Download Queue"
TAB_HISTORY = "History"


# --- Main UI Class ---
class UserInterface(
    ctk.CTk, UIStateManagerMixin, UICallbackHandlerMixin, UIActionHandlerMixin
):
    def __init__(
        self,
        logic_handler: Optional["LogicHandler"] = None,
        history_manager: Optional["HistoryManager"] = None,
    ) -> None:
        super().__init__()

        self.logic: Optional["LogicHandler"] = logic_handler
        self.history_manager: Optional["HistoryManager"] = history_manager
        self.fetched_info: Optional[Dict[str, Any]] = None
        self.current_operation: Optional[str] = None  # Tracks 'fetch' primarily
        self._last_toggled_playlist_mode: bool = True
        self._current_fetch_url: Optional[str] = None
        self.queue_tab: Optional[QueueTab] = None

        self.title(APP_TITLE)
        self.geometry(INITIAL_GEOMETRY)
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)  # Tab view row
        self.grid_rowconfigure(1, weight=0)  # Progress bar row
        self.grid_rowconfigure(2, weight=0)  # Status label row (will have more padding)

        # --- Tab View Setup ---
        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.tab_view.configure(command=self._on_tab_change)

        self.tab_view.add(TAB_HOME)
        self.tab_view.add(TAB_QUEUE)
        self.tab_view.add(TAB_HISTORY)
        self.tab_view.set(TAB_HOME)

        self.home_tab_frame = self.tab_view.tab(TAB_HOME)
        self.queue_tab_frame = self.tab_view.tab(TAB_QUEUE)
        self.history_tab_frame = self.tab_view.tab(TAB_HISTORY)

        # --- Initialize Tabs ---
        self._setup_home_tab()
        # Queue tab setup deferred until logic handler is set
        self._setup_history_tab()

        # --- Bottom Status/Progress Bar ---
        # Increased font size and padding
        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.set(0)
        self.status_label = ctk.CTkLabel(
            self,
            text=DEFAULT_STATUS,
            text_color=COLOR_DEFAULT,  # Use constant
            font=ctk.CTkFont(size=19),  # <<< Increased font size
            justify="left",
            anchor="w",
        )
        self.progress_bar.grid(row=1, column=0, padx=20, pady=(0, 5), sticky="ew")
        # <<< Increased bottom padding for status label >>>
        self.status_label.grid(row=2, column=0, padx=25, pady=(5, 20), sticky="ew")

        self._enter_idle_state()

    def _setup_home_tab(self) -> None:
        """Sets up the widgets for the main 'Add Download' tab."""
        # (Grid/Widget setup remains the same as previous version)
        self.home_tab_frame.grid_columnconfigure(0, weight=1)
        self.home_tab_frame.grid_rowconfigure(4, weight=1)  # Dynamic area row

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
        self.dynamic_area_label = ctk.CTkLabel(
            self.home_tab_frame,
            text="",
            font=ctk.CTkFont(weight="bold"),
            wraplength=750,
        )
        self.single_video_thumbnail_label = ctk.CTkLabel(
            self.home_tab_frame,
            text="",
            image=get_placeholder_ctk_image(SINGLE_VIDEO_THUMBNAIL_SIZE),
            width=SINGLE_VIDEO_THUMBNAIL_SIZE[0],
            height=SINGLE_VIDEO_THUMBNAIL_SIZE[1],
        )
        self.playlist_selector_widget = PlaylistSelector(self.home_tab_frame)
        self.bottom_controls_widget = BottomControlsFrame(
            self.home_tab_frame,
            fetch_command=self.fetch_video_info,
            download_command=self.start_download_ui,
            cancel_command=self.cancel_operation_ui,
        )

        self.top_frame_widget.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="ew")
        self.options_frame_widget.grid(row=1, column=0, padx=15, pady=5, sticky="ew")
        self.path_frame_widget.grid(row=2, column=0, padx=15, pady=5, sticky="ew")
        self.bottom_controls_widget.grid(
            row=5, column=0, padx=15, pady=(10, 15), sticky="ew"
        )

    def _setup_queue_tab(self) -> None:
        """Sets up the Download Queue tab."""
        if not self.logic:
            print("UI Error: Logic Handler not available for Queue Tab setup.")
            error_label = ctk.CTkLabel(
                self.queue_tab_frame, text="Error: Queue unavailable.", text_color="red"
            )
            error_label.pack(pady=20)
            return

        self.queue_tab_frame.grid_rowconfigure(0, weight=1)  # Scrollable frame row
        self.queue_tab_frame.grid_rowconfigure(
            1, weight=0
        )  # Button row (for Clear Finished)
        self.queue_tab_frame.grid_columnconfigure(0, weight=1)

        self.queue_tab = QueueTab(
            master=self.queue_tab_frame,
            logic_handler=self.logic,
            history_manager=self.history_manager,
        )
        # QueueTab now internally creates the scroll frame and button, just grid QueueTab itself
        self.queue_tab.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        print("UI: Queue tab setup complete.")

    def _setup_history_tab(self) -> None:
        """Sets up the History tab."""
        # (No changes needed here from previous version)
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
        self.history_content = HistoryTab(
            master=self.history_tab_frame,
            history_manager=self.history_manager,
            ui_interface_ref=self,
        )
        self.history_content.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

    def _on_tab_change(self) -> None:
        """Handles actions when the selected tab changes."""
        # (No changes needed here from previous version)
        selected_tab = self.tab_view.get()
        print(f"UI: Tab changed to: {selected_tab}")
        if selected_tab == TAB_HISTORY and hasattr(self, "history_content"):
            self.history_content.refresh_history()

    # --- Methods for Tab Switching (from History) ---
    def switch_to_downloader_tab(self, url: str) -> None:
        """Switches to the main download tab and populates the URL."""
        # (No changes needed here from previous version)
        print(f"UI: Switching to Downloader tab with URL: {url}")
        self.tab_view.set(TAB_HOME)
        if hasattr(self, "top_frame_widget"):
            self.top_frame_widget.set_url(url)
            self.update_status("URL loaded from history. Click 'Fetch Info'.")
        else:
            print("UI Error: Downloader tab widgets not ready for URL population.")

    def set_default_save_path(self, path: str) -> None:
        """Sets the default save path in the PathSelectionFrame."""
        # (No changes needed here from previous version)
        if hasattr(self, "path_frame_widget") and self.path_frame_widget:
            try:
                self.path_frame_widget.set_path(path)
                print(f"UI: Default save path set to '{path}' for Downloader tab.")
            except Exception as e:
                print(f"UI Error: Could not set default path: {e}")
        else:
            print("UI Error: Path frame widget not available to set default path.")

    def set_logic_handler(self, logic_handler: "LogicHandler"):
        """Sets the logic handler and finalizes dependent UI setup."""
        # (No changes needed here from previous version)
        print("UI: Setting Logic Handler.")
        self.logic = logic_handler
        self._setup_queue_tab()  # Setup queue tab now that logic handler is available
