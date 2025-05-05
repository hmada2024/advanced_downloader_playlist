# src/ui/callback_handler.py
# -- Mixin class for handling callbacks from the logic layer --

import contextlib
from tkinter import messagebox
from typing import TYPE_CHECKING, Callable, Dict, Any, Optional

# --- Type Hinting for Tkinter/CTk elements (Conditional Import) ---
if TYPE_CHECKING:
    import customtkinter as ctk  # Standard import
    from .interface import UserInterface  # From same directory (ui)

    # Add component hints if needed for accessing specific widget methods directly
    from .components.path_selection_frame import PathSelectionFrame
    from .components.options_control_frame import OptionsControlFrame

# --- Constants for Status Colors ---
COLOR_ERROR = "red"
COLOR_WARNING = "orange"  # Or darkorange
COLOR_CANCEL = "orange"
COLOR_SUCCESS = "green"  # Or #00A000
COLOR_INFO = "blue"  # Or dodgerblue, steelblue
COLOR_DEFAULT = "gray"  # Or system default


class UICallbackHandlerMixin:
    """Mixin class containing methods for handling callbacks from LogicHandler."""

    # --- Type Hinting for attributes assumed to exist in the main class ---
    if TYPE_CHECKING:
        self: "UserInterface"
        status_label: ctk.CTkLabel
        progress_bar: ctk.CTkProgressBar
        # Methods assumed from other mixins/main class
        after: Callable[..., Any]  # Tkinter's after method
        _enter_idle_state: Callable[[], None]
        _enter_info_fetched_state: Callable[[], None]
        # Attributes assumed
        fetched_info: Optional[Dict[str, Any]]
        current_operation: Optional[str]
        # Add component types for clarity
        path_frame_widget: PathSelectionFrame
        options_frame_widget: OptionsControlFrame

    # --- Callback Methods ---

    def update_status(self, message: str) -> None:
        """Updates the status label text and color (thread-safe)."""

        def _update() -> None:
            """Inner function to perform the actual UI update."""
            color: str = COLOR_DEFAULT
            msg_lower: str = message.lower()

            if "error" in msg_lower:
                color = COLOR_ERROR
            elif "warning" in msg_lower:
                color = COLOR_WARNING
            elif "cancel" in msg_lower:
                color = COLOR_CANCEL
            elif any(
                term in msg_lower
                for term in ["complete", "finished", "success", "fetched", "ready"]
            ):
                color = COLOR_SUCCESS
            elif (
                any(
                    term in msg_lower
                    for term in ["downloading", "processing", "fetching", "starting"]
                )
                or "جاري" in message
            ):
                color = COLOR_INFO

            justify_val: str = "left" if "\n" in message else "center"

            try:
                if self.status_label:
                    self.status_label.configure(
                        text=message, text_color=color, justify=justify_val
                    )
            except Exception as e:
                print(f"Error updating status label: {e}")

        self.after(1, _update)

    def update_progress(self, value: float) -> None:
        """Updates the progress bar value (thread-safe). Clamps value between 0.0 and 1.0."""
        clamped_value: float = max(0.0, min(1.0, value))

        def _update() -> None:
            try:
                if self.progress_bar:
                    self.progress_bar.set(clamped_value)
            except Exception as e:
                print(f"Error updating progress bar: {e}")

        self.after(1, _update)  # Use 1ms, lambda removed for clarity

    def on_info_success(self, info_dict: Dict[str, Any]) -> None:
        """Callback executed when info fetch succeeds (thread-safe)."""

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
            is_playlist_mode_on = False  # Default
            with contextlib.suppress(Exception):
                if self.options_frame_widget:
                    is_playlist_mode_on = self.options_frame_widget.get_playlist_mode()
            if is_actually_playlist:
                status_msg = (
                    "Playlist info fetched. Select items and download."
                    if is_playlist_mode_on
                    else "Playlist info fetched. Toggle 'Is Playlist?' switch ON to select items."
                )
            self.update_status(status_msg)

        self.after(0, _update)

    def on_info_error(self, error_message: str) -> None:
        """Callback executed when info fetch fails (thread-safe)."""

        def _update() -> None:
            print(f"UI_Interface: Info error callback received: {error_message}")
            messagebox.showerror(
                "Information Fetch Error",
                f"Could not fetch information:\n{error_message}",
            )
            self._enter_idle_state()

        self.after(0, _update)

    def on_task_finished(self) -> None:
        """Callback executed when any background task finishes (thread-safe)."""

        def _process_finish() -> None:
            final_status_text: str = ""
            final_status_color: str = ""
            try:
                if self.status_label:
                    final_status_text = self.status_label.cget("text")
                    final_status_color = str(self.status_label.cget("text_color"))
            except Exception as e:
                print(f"Error reading final status label state: {e}")

            operation_type: Optional[str] = self.current_operation
            print(
                f"UI_Interface: Task finished notification (Type: '{operation_type}'). Final status: '{final_status_text}' (Color: {final_status_color})"
            )

            was_cancelled: bool = "cancel" in final_status_text.lower()
            was_error: bool = (final_status_color == COLOR_ERROR) or (
                "error" in final_status_text.lower()
            )

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
            elif operation_type == "fetch":
                print(
                    "UI: Info fetch finished successfully (handled by on_info_success)."
                )
            elif operation_type == "download":
                print("UI: Download finished successfully.")
                save_path = ""
                try:
                    if self.path_frame_widget:
                        save_path = self.path_frame_widget.get_path()
                except Exception as e:
                    print(f"Error getting save path for success message: {e}")
                messagebox.showinfo(
                    "Download Complete",
                    f"Download finished successfully!\nFile(s) saved in:\n{save_path or 'Selected folder'}",
                )
                self._enter_idle_state()
            else:
                print(
                    f"UI Warning: Task finished with unknown state/type. Resetting. (Op: {operation_type}, Status: {final_status_text})"
                )
                self._enter_idle_state()

            self.current_operation = None

        self.after(50, _process_finish)
