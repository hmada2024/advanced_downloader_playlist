# src/ui_interface.py
# -- Main application UI window class and coordinator between components --

import customtkinter as ctk

# --- Import Mixin Classes (using new names) ---
from .ui_state_manager import (
    UIStateManagerMixin,
)  # <-- تم التعديل: إزالة الشرطة السفلية
from .ui_callback_handler import (
    UICallbackHandlerMixin,
)  # <-- تم التعديل: إزالة الشرطة السفلية
from .ui_action_handler import (
    UIActionHandlerMixin,
)  # <-- تم التعديل: إزالة الشرطة السفلية

# --- Import UI Components (using new names) ---
from .ui_components.top_input_frame import TopInputFrame  # <-- تم التعديل
from .ui_components.options_control_frame import OptionsControlFrame  # <-- تم التعديل
from .ui_components.path_selection_frame import PathSelectionFrame  # <-- تم التعديل
from .ui_components.bottom_controls_frame import BottomControlsFrame  # <-- تم التعديل
from .ui_components.playlist_selector import PlaylistSelector  # <-- تم التعديل


# The main UI class now inherits from CTk and the three Mixins
class UserInterface(
    ctk.CTk, UIStateManagerMixin, UICallbackHandlerMixin, UIActionHandlerMixin
):
    """
    Main application window.
    Initializes UI components and inherits functionality from Mixin classes for:
    - State management (UIStateManagerMixin)
    - Callback handling (UICallbackHandlerMixin)
    - User action handling (UIActionHandlerMixin)
    """

    def __init__(self, logic_handler):
        """
        Initializes the main window, creates UI components, and sets initial state.
        Args:
            logic_handler: Instance of the LogicHandler (can be None initially).
        """
        super().__init__()

        # --- Instance Attributes ---
        self.logic = logic_handler
        self.fetched_info = None
        self.current_operation = None
        self._last_toggled_playlist_mode = True

        # --- Basic Window Setup ---
        self.title("Advanced Downloader")
        self.geometry("850x750")
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        # --- Main Grid Configuration ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        # --- Create UI Component Instances ---
        self.top_frame_widget = TopInputFrame(self, fetch_command=self.fetch_video_info)
        self.options_frame_widget = OptionsControlFrame(
            self, toggle_playlist_command=self.toggle_playlist_mode
        )
        self.path_frame_widget = PathSelectionFrame(
            self, browse_callback=self.browse_path_logic
        )
        self.playlist_selector_widget = PlaylistSelector(self)
        self.bottom_controls_widget = BottomControlsFrame(
            self,
            download_command=self.start_download_ui,
            cancel_command=self.cancel_operation_ui,
        )
        self.dynamic_area_label = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(weight="bold")
        )
        self.progress_bar = ctk.CTkProgressBar(self)
        self.status_label = ctk.CTkLabel(
            self,
            text="Initializing...",
            text_color="gray",
            font=ctk.CTkFont(size=13),
            justify="left",
            anchor="w",
        )

        # --- Grid the UI Components ---
        self.top_frame_widget.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="ew")
        self.options_frame_widget.grid(row=1, column=0, padx=15, pady=5, sticky="ew")
        self.path_frame_widget.grid(row=2, column=0, padx=15, pady=5, sticky="ew")
        self.dynamic_area_label.grid(row=3, column=0, padx=20, pady=(10, 0), sticky="w")
        # self.playlist_selector_widget is gridded dynamically
        self.bottom_controls_widget.grid(
            row=6, column=0, padx=15, pady=(5, 5), sticky="ew"
        )
        self.progress_bar.grid(row=7, column=0, padx=20, pady=(0, 5), sticky="ew")
        self.status_label.grid(row=8, column=0, padx=25, pady=(0, 10), sticky="ew")

        # --- Enter Initial State ---
        self._enter_idle_state()

    # --- إضافة: دالة لتعيين مسار الحفظ الافتراضي --- Start: Method for default save path ---
    def set_default_save_path(self, path: str):
        """
        Sets the initial text in the save path entry widget.
        Called by main.py after finding the default path.
        """
        if self.path_frame_widget:  # التأكد من وجود الويدجت Ensure widget exists
            try:
                self.path_frame_widget.set_path(path)
                print(f"UI: Default save path set to '{path}'")
                # قد تحتاج إلى إعادة تمكين زر التحميل هنا إذا كان قد تم تعطيله
                # لأنه لم يكن هناك مسار. يتم التعامل مع هذا الآن في _enter_info_fetched_state.
                # May need to re-enable download button here if it was disabled
                # due to no path. This is now handled in _enter_info_fetched_state.
            except Exception as e:
                print(f"UI Error: Could not set default path in widget: {e}")
        else:
            print("UI Error: Path frame widget not available to set default path.")

    # --- إضافة: دالة لتعيين مسار الحفظ الافتراضي --- End: Method for default save path ---
