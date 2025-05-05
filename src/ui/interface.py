# src/ui/interface.py
# -- Main application UI window class and coordinator between components --
# -- Modified to integrate HistoryTab and fix NameError --

import contextlib
from tkinter import messagebox
import customtkinter as ctk
from typing import Optional, Dict, Any, Callable, TYPE_CHECKING

# --- استيراد كلاسات المنطق والـ Handler ---
if TYPE_CHECKING:
    from ..logic.logic_handler import LogicHandler
    from ..logic.history_manager import HistoryManager

# --- استيراد كلاسات Mixin ---
from .state_manager import (
    UIStateManagerMixin,
)  # Imports constants like BTN_TXT_DOWNLOAD etc.
from .callback_handler import (
    COLOR_CANCEL,
    COLOR_ERROR,
    UICallbackHandlerMixin,
)  # Imports constants like COLOR_ERROR etc.
from .action_handler import (
    MSG_URL_EMPTY,
    OP_FETCH,
    TITLE_INPUT_ERROR,
    UIActionHandlerMixin,
)  # Imports constants like TITLE_INPUT_ERROR etc.

# --- استيراد كلاسات مكونات الواجهة ---
from .components.top_input_frame import TopInputFrame
from .components.options_control_frame import OptionsControlFrame
from .components.path_selection_frame import PathSelectionFrame
from .components.bottom_controls_frame import BottomControlsFrame
from .components.playlist_selector import PlaylistSelector

# --- استيراد كلاسات التبويبات ---
from .get_links_tab import GetLinksTab
from .history_tab import HistoryTab

# --- الثوابت ---
APP_TITLE = "Advanced Spider Fetch"
INITIAL_GEOMETRY = "900x750"
DEFAULT_STATUS = "Initializing..."
DEFAULT_STATUS_COLOR = "gray"
TAB_HOME = "Download a Playlist or Video yourself"
TAB_GET_LINKS = "Get Temporary Playlist Links For Downloading"
TAB_HISTORY = "History"
LABEL_EMPTY = ""


# الكلاس الرئيسي للواجهة يرث الآن من CTk ومن Mixins الوظيفية
class UserInterface(
    ctk.CTk, UIStateManagerMixin, UICallbackHandlerMixin, UIActionHandlerMixin
):
    """
    Main application window with TabView interface.
    Initializes UI components and inherits functionality from Mixin classes for:
    - State management (UIStateManagerMixin)
    - Callback handling from logic layer (UICallbackHandlerMixin)
    - Handling user actions like button clicks (UIActionHandlerMixin)
    Integrates Download, Get Links, and History tabs.
    """

    def __init__(
        self,
        logic_handler: Optional["LogicHandler"] = None,
        history_manager: Optional["HistoryManager"] = None,
    ) -> None:
        """
        Initializes the main window, creates UI components, links logic, sets up history, and sets initial state.
        Args:
            logic_handler (Optional[LogicHandler]): Instance of the LogicHandler.
            history_manager (Optional[HistoryManager]): Instance of the HistoryManager.
        """
        super().__init__()

        # --- متغيرات النسخة ---
        self.logic: Optional["LogicHandler"] = logic_handler
        self.history_manager: Optional["HistoryManager"] = history_manager
        self.fetched_info: Optional[Dict[str, Any]] = None
        self.current_operation: Optional[str] = None
        self._last_toggled_playlist_mode: bool = True
        self._current_fetch_url: Optional[str] = None

        # --- إعداد النافذة الأساسي ---
        self.title(APP_TITLE)
        self.geometry(INITIAL_GEOMETRY)
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        # --- تكوين الشبكة الرئيسية ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=0)

        # --- إنشاء عرض التبويبات ---
        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.tab_view.configure(command=self._on_tab_change)

        # --- إضافة التبويبات ---
        self.tab_view.add(TAB_HOME)
        self.tab_view.add(TAB_GET_LINKS)
        self.tab_view.add(TAB_HISTORY)
        self.tab_view.set(TAB_HOME)

        # --- الحصول على إطارات التبويبات ---
        self.home_tab_frame = self.tab_view.tab(TAB_HOME)
        self.get_links_tab_frame = self.tab_view.tab(TAB_GET_LINKS)
        self.history_tab_frame = self.tab_view.tab(TAB_HISTORY)

        # --- تهيئة تبويب Home (Downloader) ---
        self._setup_home_tab()

        # --- تهيئة تبويب Get Links ---
        self._setup_get_links_tab()

        # --- تهيئة تبويب History ---
        self._setup_history_tab()

        # --- إنشاء ووضع الويدجتس السفلية (التقدم والحالة) ---
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

        # --- الدخول في حالة الواجهة الأولية (لتبويب Home) ---
        self._enter_idle_state()

    def _setup_home_tab(self) -> None:
        """Creates and grids widgets for the Home (Downloader) tab."""
        self.home_tab_frame.grid_columnconfigure(0, weight=1)
        self.home_tab_frame.grid_rowconfigure(
            4, weight=1
        )  # Playlist selector row expands

        self.top_frame_widget = TopInputFrame(
            self.home_tab_frame, fetch_command=self.fetch_video_info
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
        self.playlist_selector_widget = PlaylistSelector(self.home_tab_frame)
        self.bottom_controls_widget = BottomControlsFrame(
            self.home_tab_frame,
            download_command=self.start_download_ui,
            cancel_command=self.cancel_operation_ui,
        )

        self.top_frame_widget.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="ew")
        self.options_frame_widget.grid(row=1, column=0, padx=15, pady=5, sticky="ew")
        self.path_frame_widget.grid(row=2, column=0, padx=15, pady=5, sticky="ew")
        self.dynamic_area_label.grid(row=3, column=0, padx=20, pady=(10, 0), sticky="w")
        # Playlist selector is gridded dynamically
        self.bottom_controls_widget.grid(
            row=6, column=0, padx=15, pady=(5, 5), sticky="ew"
        )

    def _setup_get_links_tab(self) -> None:
        """Creates and grids widgets for the Get Links tab."""
        self.get_links_tab_frame.grid_rowconfigure(0, weight=1)
        self.get_links_tab_frame.grid_columnconfigure(0, weight=1)
        self.get_links_content = GetLinksTab(
            master=self.get_links_tab_frame, history_manager=self.history_manager
        )
        self.get_links_content.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

    def _setup_history_tab(self) -> None:
        """Creates and grids widgets for the History tab."""
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
        """Called when the selected tab changes."""
        selected_tab = self.tab_view.get()
        print(f"UI: Tab changed to: {selected_tab}")
        if selected_tab == TAB_HISTORY and hasattr(self, "history_content"):
            self.history_content.refresh_history()

    # --- Callback Methods (Including History Logging) ---

    def on_info_success(self, info_dict: Dict[str, Any]) -> None:
        """Callback executed when info fetch succeeds (thread-safe). Also logs history."""
        logged = False
        if self.history_manager and self._current_fetch_url:
            title = info_dict.get("title", "Untitled")
            logged = self.history_manager.add_entry(
                url=self._current_fetch_url, title=title, operation_type="Fetch Info"
            )
            # Optionally clear URL only if successfully logged to avoid double logging on retry
            # if logged:
            #     self._current_fetch_url = None

        def _update() -> None:
            self.fetched_info = info_dict
            if not info_dict:
                self.on_info_error("Received empty or invalid info from fetcher.")
                return

            is_actually_playlist: bool = isinstance(info_dict.get("entries"), list)

            try:
                if self.options_frame_widget:
                    switch_state = "normal" if is_actually_playlist else "disabled"
                    self.options_frame_widget.playlist_switch.configure(
                        state=switch_state
                    )
                    if not is_actually_playlist:
                        self.options_frame_widget.set_playlist_mode(False)
            except Exception as e:
                print(f"Error configuring playlist switch: {e}")

            self._enter_info_fetched_state()

            status_msg: str = "Info fetched. Ready to download."
            is_playlist_mode_on = False
            with contextlib.suppress(Exception):
                if self.options_frame_widget:
                    is_playlist_mode_on = self.options_frame_widget.get_playlist_mode()
            if is_actually_playlist:
                item_count = len(info_dict.get("entries", []))
                status_msg = (
                    f"Playlist info fetched ({item_count} items). Select items and download."
                    if is_playlist_mode_on
                    else f"Playlist info fetched ({item_count} items). Toggle switch ON to select items."
                )
            self.update_status(status_msg)
            # Clear the fetch URL here after successful UI update to prevent double logging
            self._current_fetch_url = None

        self.after(0, _update)

    def on_task_finished(self) -> None:
        """Callback executed when any background task finishes (thread-safe). Handles history logging on download success."""

        def _process_finish() -> None:
            final_status_text: str = ""
            final_status_color: str = ""
            operation_type: Optional[str] = self.current_operation
            was_success = False
            download_url_for_log = None
            download_title_for_log = None

            try:
                if self.status_label:
                    final_status_text = self.status_label.cget("text")
                    final_status_color = str(self.status_label.cget("text_color"))
            except Exception as e:
                print(f"Error reading final status label state: {e}")

            print(
                f"UI_Interface: Task finished (Type: '{operation_type}'). Final status: '{final_status_text}' (Color: {final_status_color})"
            )

            # Determine state based on status label text/color
            # Use constants imported from callback_handler
            was_cancelled: bool = (
                COLOR_CANCEL in final_status_color
                or "cancel" in final_status_text.lower()
            )
            was_error: bool = (
                COLOR_ERROR in final_status_color
                or "error" in final_status_text.lower()
            )

            # Check for success (specifically for download logging)
            if operation_type == "download" and not was_cancelled and not was_error:
                # More reliable: Check if status message indicates completion/success
                if any(
                    term in final_status_text.lower()
                    for term in ["finished", "complete", "download successful"]
                ):
                    was_success = True
                    try:
                        download_url_for_log = self.top_frame_widget.get_url()
                        if self.fetched_info:
                            download_title_for_log = self.fetched_info.get(
                                "title", "Untitled Download"
                            )
                            # Refine title for playlists
                            if isinstance(self.fetched_info.get("entries"), list):
                                # Maybe get selected items count from LogicHandler if passed back?
                                # For now, just indicate it was a playlist
                                download_title_for_log += " (Playlist)"
                    except Exception as e:
                        print(
                            f"UI Warning: Could not retrieve URL/Title for history logging after download: {e}"
                        )
                else:
                    # If download finished but status doesn't clearly indicate success, don't log yet.
                    print(
                        f"UI Info: Download task finished but final status '{final_status_text}' doesn't confirm success. Skipping history log."
                    )

            # UI State transitions based on outcome
            if was_cancelled:
                print("UI: Operation was cancelled.")
                if self.fetched_info and operation_type == "download":
                    self._enter_info_fetched_state()
                    self.update_status("Download Cancelled.")
                else:
                    self._enter_idle_state()
                    self.update_status("Operation Cancelled.")
            elif was_error:
                print("UI: Operation failed with error.")
                if self.fetched_info and operation_type == "download":
                    self._enter_info_fetched_state()
                else:
                    self._enter_idle_state()
                # Keep the error message set by on_info_error or status_callback
            elif operation_type == "fetch":
                print(
                    "UI: Info fetch finished (handled by on_info_success/on_info_error)."
                )
                # State transition handled in those callbacks
            elif operation_type == "download":
                if was_success:
                    print("UI: Download finished successfully.")
                    save_path = ""
                    try:
                        if self.path_frame_widget:
                            save_path = self.path_frame_widget.get_path()
                    except Exception as e:
                        print(f"Error getting save path: {e}")

                    messagebox.showinfo(
                        "Download Complete",
                        f"Download finished successfully!\nFile(s) saved in:\n{save_path or 'Selected folder'}",
                    )

                    # Log history AFTER showing success message and before resetting state
                    if self.history_manager and download_url_for_log:
                        self.history_manager.add_entry(
                            url=download_url_for_log,
                            title=download_title_for_log,
                            operation_type="Download",
                        )
                    self._enter_idle_state()
                else:
                    # Handle case where download finishes but status wasn't clearly success
                    print(
                        "UI Warning: Download finished but not marked as success. Resetting."
                    )
                    self._enter_idle_state()
                    # Keep whatever status message was last shown (might indicate partial success/failure)

            else:
                print(
                    f"UI Warning: Task finished with unknown state/type. Resetting. (Op: {operation_type}, Status: {final_status_text})"
                )
                self._enter_idle_state()

            self.current_operation = None

        self.after(50, _process_finish)

    # --- Action Methods (Including modifications for History) ---

    def fetch_video_info(self) -> None:
        """Initiates the process to fetch info for the entered URL. Stores URL for history."""
        url: str = self.top_frame_widget.get_url()
        if not url:
            # Use constants imported from action_handler
            messagebox.showerror(TITLE_INPUT_ERROR, MSG_URL_EMPTY)
            return

        # Store URL for logging in on_info_success
        self._current_fetch_url = url

        # Reset previous fetch results
        self.fetched_info = None
        if hasattr(self, "playlist_selector_widget"):  # Check if widget exists
            self.playlist_selector_widget.grid_remove()
        # Use the defined LABEL_EMPTY constant
        if hasattr(self, "dynamic_area_label"):  # Check if widget exists
            self.dynamic_area_label.configure(text=LABEL_EMPTY)

        # Set state for fetching
        self.current_operation = OP_FETCH  # Use constant from action_handler
        if hasattr(self, "options_frame_widget"):
            self._last_toggled_playlist_mode = (
                self.options_frame_widget.get_playlist_mode()
            )
        self._enter_fetching_state()  # Method from state_manager

        if self.logic:
            self.logic.start_info_fetch(url)
        else:
            self._handle_missing_logic_handler()  # Method from action_handler

    # --- Helper methods for tab switching (used by HistoryTab) ---

    def switch_to_downloader_tab(self, url: str) -> None:
        """Switches to the Downloader tab and populates the URL."""
        print(f"UI: Switching to Downloader tab with URL: {url}")
        self.tab_view.set(TAB_HOME)
        if hasattr(self, "top_frame_widget"):
            self.top_frame_widget.set_url(url)
            self.update_status("URL loaded from history. Click 'Fetch Info'.")
        else:
            print("UI Error: Downloader tab widgets not ready for URL population.")

    def switch_to_getlinks_tab(self, url: str) -> None:
        """Switches to the Get Links tab and populates the URL."""
        print(f"UI: Switching to Get Links tab with URL: {url}")
        self.tab_view.set(TAB_GET_LINKS)
        if hasattr(self, "get_links_content") and hasattr(
            self.get_links_content, "url_entry"
        ):
            self.get_links_content.url_entry.delete(0, "end")
            self.get_links_content.url_entry.insert(0, url)
            # Access the internal status update method of GetLinksTab
            self.get_links_content._update_status(
                "URL loaded from history. Click 'Get Links'."
            )
        else:
            print("UI Error: Get Links tab widgets not ready for URL population.")

    def set_default_save_path(self, path: str) -> None:
        """Sets the initial text in the save path entry widget."""
        if hasattr(self, "path_frame_widget") and self.path_frame_widget:
            try:
                self.path_frame_widget.set_path(path)
                print(f"UI: Default save path set to '{path}' for Downloader tab.")
            except Exception as e:
                print(f"UI Error: Could not set default path in widget: {e}")
        else:
            print("UI Error: Path frame widget not available to set default path.")

    # --- Other Inherited Mixin Methods ---
    # These methods (like start_download_ui, browse_path_logic, _enter_idle_state, update_status etc.)
    # are inherited from the Mixin classes and should work as intended, using constants defined
    # within those Mixin files or now globally in this file.
