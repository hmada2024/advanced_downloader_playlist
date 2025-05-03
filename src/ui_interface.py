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

# --- *** استيرادات إضافية لتعيين الأيقونة وتحديد المسار *** ---
import sys
import os
from pathlib import Path
# -----------------------------------------------------------


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
        super().__init__()  # Call CTk __init__

        # --- Instance Attributes ---
        self.logic = logic_handler  # Logic Handler instance (set later by main.py)
        self.fetched_info = None  # Stores fetched video/playlist metadata
        self.current_operation = (
            None  # Tracks the active operation ('fetch' or 'download')
        )
        # Stores the user's last explicit choice for the playlist switch
        self._last_toggled_playlist_mode = (
            True  # Start with playlist mode ON by default visually
        )

        # --- Basic Window Setup ---
        self.title("Advanced Downloader")
        self.geometry("850x750")  # Adjusted geometry
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        # --- *** كود تعيين أيقونة النافذة (Title Bar Icon) *** ---
        try:
            # تحديد المسار الأساسي سواء كان التطبيق مجمداً أم لا
            if getattr(sys, "frozen", False):
                # المسار عند تشغيل الملف التنفيذي المجمَّد
                base_path = Path(sys._MEIPASS)
            else:
                # المسار عند تشغيل السكربت مباشرة (ui_interface.py داخل src)
                # نصعد مستويين للوصول لمجلد المشروع الرئيسي
                base_path = Path(__file__).resolve().parent.parent

            # بناء المسار الكامل لملف الأيقونة
            icon_path = base_path / "assets" / "logo.ico"

            # التحقق من وجود الملف قبل محاولة تعيينه
            if icon_path.is_file():
                print(f"INFO: Attempting to set window icon from: {icon_path}")
                self.iconbitmap(str(icon_path))  # تعيين الأيقونة للنافذة
                print("INFO: Window icon set successfully.")
            else:
                # طباعة تحذير إذا لم يتم العثور على الملف
                # هذا يساعد في التشخيص إذا لم تظهر الأيقونة
                print(
                    f"WARNING: Window icon file not found at calculated path: {icon_path}"
                )
                print(
                    "WARNING: Ensure 'logo.ico' exists in the 'assets' folder and is included during packaging (e.g., using PyInstaller's --add-data)."
                )

        except Exception as e:
            # طباعة أي خطأ قد يحدث أثناء محاولة تعيين الأيقونة
            print("ERROR: Failed to set window icon.")
            print(f"ERROR Details: {e}")
            # قد يكون السبب ملف .ico غير صالح، أو خطأ في المسار، أو مشكلة في Tkinter/Tcl
            # مثال لخطأ محتمل: except tk.TclError as tcl_err: print(f"ERROR: TclError setting icon (invalid .ico?): {tcl_err}")

        # --- *** نهاية كود تعيين أيقونة النافذة *** ---

        # --- Main Grid Configuration ---
        self.grid_columnconfigure(0, weight=1)  # Single column expands
        self.grid_rowconfigure(
            4, weight=1
        )  # Dynamic row (for playlist selector) expands

        # --- Create UI Component Instances ---
        # Pass methods from the Mixins as commands where needed
        self.top_frame_widget = TopInputFrame(self, fetch_command=self.fetch_video_info)
        self.options_frame_widget = OptionsControlFrame(
            self, toggle_playlist_command=self.toggle_playlist_mode
        )
        self.path_frame_widget = PathSelectionFrame(
            self, browse_callback=self.browse_path_logic
        )
        self.playlist_selector_widget = PlaylistSelector(
            self
        )  # Frame for playlist items
        self.bottom_controls_widget = BottomControlsFrame(
            self,
            download_command=self.start_download_ui,
            cancel_command=self.cancel_operation_ui,
        )
        self.dynamic_area_label = ctk.CTkLabel(  # Label above the dynamic area
            self, text="", font=ctk.CTkFont(weight="bold")
        )
        self.progress_bar = ctk.CTkProgressBar(self)
        self.status_label = ctk.CTkLabel(  # Status message display
            self,
            text="Initializing...",  # Initial text before idle state
            text_color="gray",
            font=ctk.CTkFont(size=13),
            justify="left",
            anchor="w",
        )

        # --- Grid the UI Components ---
        # Order matters for visual layout and row numbers
        self.top_frame_widget.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="ew")
        self.options_frame_widget.grid(row=1, column=0, padx=15, pady=5, sticky="ew")
        self.path_frame_widget.grid(row=2, column=0, padx=15, pady=5, sticky="ew")
        self.dynamic_area_label.grid(row=3, column=0, padx=20, pady=(10, 0), sticky="w")
        # Note: self.playlist_selector_widget is gridded dynamically inside _display_playlist_view
        self.bottom_controls_widget.grid(
            row=6, column=0, padx=15, pady=(5, 5), sticky="ew"
        )  # After potential playlist frame
        self.progress_bar.grid(row=7, column=0, padx=20, pady=(0, 5), sticky="ew")
        self.status_label.grid(row=8, column=0, padx=25, pady=(0, 10), sticky="ew")

        # --- Enter Initial State ---
        # _enter_idle_state is inherited from UIStateManagerMixin
        self._enter_idle_state()

    # --- No other methods are defined here ---
    # All other methods (_enter_*, on_*, update_*, fetch_*, start_*, etc.)
    # are inherited from the Mixin classes.
