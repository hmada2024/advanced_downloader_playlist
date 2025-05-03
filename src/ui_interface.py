# src/ui_interface.py
# -- Main application UI window class and coordinator between components --

import customtkinter as ctk

# --- Import Mixin Classes ---
from .ui_state_manager import UIStateManagerMixin
from .ui_callback_handler import UICallbackHandlerMixin
from .ui_action_handler import UIActionHandlerMixin

# --- Import UI Components ---
from .ui_components.top_input_frame import TopInputFrame
from .ui_components.options_control_frame import OptionsControlFrame
from .ui_components.path_selection_frame import PathSelectionFrame
from .ui_components.bottom_controls_frame import BottomControlsFrame
from .ui_components.playlist_selector import PlaylistSelector

# --- استيرادات إضافية ---
import sys
import os
from pathlib import Path
import logging  # <-- إضافة استيراد logging
# -----------------------


class UserInterface(
    ctk.CTk, UIStateManagerMixin, UICallbackHandlerMixin, UIActionHandlerMixin
):
    """Main application window."""

    def __init__(self, logic_handler):
        super().__init__()
        logging.debug("UserInterface: Initializing...")

        self.logic = logic_handler
        self.fetched_info = None
        self.current_operation = None
        self._last_toggled_playlist_mode = True

        # --- Basic Window Setup ---
        self.title("Advanced Downloader")
        self.geometry("850x750")
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        # --- كود تعيين أيقونة النافذة (Title Bar Icon) ---
        try:
            if getattr(sys, "frozen", False):
                base_path = Path(sys._MEIPASS)
            else:
                base_path = Path(__file__).resolve().parent.parent

            icon_path = base_path / "assets" / "logo.ico"

            if icon_path.is_file():
                # تم استخدام print هنا سابقاً، نستخدم logging.info
                logging.info(
                    f"UserInterface: Attempting to set window icon from: {icon_path}"
                )
                self.iconbitmap(str(icon_path))
                logging.info("UserInterface: Window icon set successfully.")
            else:
                # نستخدم logging.warning
                logging.warning(
                    f"UserInterface: Window icon file not found at calculated path: {icon_path}"
                )
                logging.warning(
                    "UserInterface: Ensure 'logo.ico' exists in 'assets' and is included during packaging."
                )

        except Exception as e:
            # نستخدم logging.error
            logging.error(
                f"UserInterface: Failed to set window icon.", exc_info=True
            )  # exc_info=True لتسجيل تتبع الخطأ

        # --- Main Grid Configuration ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        # --- Create UI Component Instances ---
        logging.debug("UserInterface: Creating UI component instances...")
        # (الكود كما هو)
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
        logging.debug("UserInterface: UI component instances created.")

        # --- Grid the UI Components ---
        logging.debug("UserInterface: Gridding UI components...")
        # (الكود كما هو)
        self.top_frame_widget.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="ew")
        self.options_frame_widget.grid(row=1, column=0, padx=15, pady=5, sticky="ew")
        self.path_frame_widget.grid(row=2, column=0, padx=15, pady=5, sticky="ew")
        self.dynamic_area_label.grid(row=3, column=0, padx=20, pady=(10, 0), sticky="w")
        self.bottom_controls_widget.grid(
            row=6, column=0, padx=15, pady=(5, 5), sticky="ew"
        )
        self.progress_bar.grid(row=7, column=0, padx=20, pady=(0, 5), sticky="ew")
        self.status_label.grid(row=8, column=0, padx=25, pady=(0, 10), sticky="ew")
        logging.debug("UserInterface: UI components gridded.")

        # --- Enter Initial State ---
        self._enter_idle_state()  # الدالة نفسها ستقوم بالتسجيل Function will log itself
        logging.debug("UserInterface: Initialization complete.")
