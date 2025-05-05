# src/ui_callback_handler.py
# -- Mixin class for handling callbacks from the logic layer --

from tkinter import messagebox
from typing import TYPE_CHECKING, Callable, Dict, Any, Optional  # Added typing imports

# --- Type Hinting for Tkinter/CTk elements (Conditional Import) ---
# This avoids runtime errors if the mixin is imported without the main UI class.
if TYPE_CHECKING:
    import customtkinter as ctk
    from .ui.ui_interface import UserInterface  # Assuming UserInterface is the main class

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
    # These hints help type checkers understand the context of 'self'.
    # We declare them here but they are actually initialized in the main UI class.
    if TYPE_CHECKING:
        # Assume UserInterface type for self within this mixin context
        # This allows accessing methods/attributes defined in other mixins or the main UI class
        # Requires the main class (UserInterface) to be defined or forward-referenced
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
        path_frame_widget: Any  # Type hint for PathSelectionFrame if defined
        options_frame_widget: Any  # Type hint for OptionsControlFrame if defined

    # --- Callback Methods ---

    def update_status(self, message: str) -> None:
        """Updates the status label text and color (thread-safe)."""

        def _update() -> None:
            """Inner function to perform the actual UI update."""
            # Determine text color based on message content
            color: str = COLOR_DEFAULT
            msg_lower: str = message.lower()

            # Check keywords to determine color
            if "error" in msg_lower:
                color = COLOR_ERROR
            elif "warning" in msg_lower:
                color = COLOR_WARNING
            elif "cancel" in msg_lower:
                color = COLOR_CANCEL
            elif (
                "complete" in msg_lower
                or "finished" in msg_lower
                or "success" in msg_lower
                or "fetched" in msg_lower  # Consider fetched as success/neutral
                or "ready" in msg_lower
            ):
                color = COLOR_SUCCESS  # Use success color for positive outcomes
            elif (
                "downloading" in msg_lower
                or "processing" in msg_lower
                or "fetching" in msg_lower
                or "starting" in msg_lower
                or "جاري" in message  # Check for Arabic "processing" word
            ):
                color = COLOR_INFO  # Use info color for ongoing processes

            # Determine text justification (left for multi-line, center for single)
            justify_val: str = "left" if "\n" in message else "center"

            # Configure the status label widget
            # Use try-except in case the widget gets destroyed unexpectedly
            try:
                if self.status_label:  # Check if widget exists
                    self.status_label.configure(
                        text=message, text_color=color, justify=justify_val
                    )
            except Exception as e:
                print(f"Error updating status label: {e}")

        # Schedule the UI update using `after` to run in the main thread
        # Use 1ms delay, generally safe and responsive. 0ms can sometimes cause issues.
        self.after(1, _update)

    def update_progress(self, value: float) -> None:
        """Updates the progress bar value (thread-safe). Clamps value between 0.0 and 1.0."""
        # Ensure the value is within the valid range for the progress bar
        clamped_value: float = max(0.0, min(1.0, value))

        def _update() -> None:
            """Inner function for the actual UI update."""
            try:
                if self.progress_bar:  # Check if widget exists
                    self.progress_bar.set(clamped_value)
            except Exception as e:
                print(f"Error updating progress bar: {e}")

        self.after(1, lambda: _update())  # Use lambda for simple updates

    def on_info_success(self, info_dict: Dict[str, Any]) -> None:
        """Callback executed when info fetch succeeds (thread-safe)."""

        def _update() -> None:
            """Inner function to update UI after successful info fetch."""
            self.fetched_info = info_dict  # Store the fetched data
            if not info_dict:
                # Handle case where logic layer might return empty dict on success (should ideally be error)
                self.on_info_error("Received empty or invalid info from fetcher.")
                return

            # Determine if the fetched data represents a playlist
            # Check if 'entries' key exists and is a list
            is_actually_playlist: bool = isinstance(info_dict.get("entries"), list)

            # Set playlist switch state based on fetched data
            # Note: Logic to restore user's last preference is now in UIStateManagerMixin._enter_info_fetched_state
            # Here, we just ensure the switch is enabled/disabled appropriately.
            try:
                if self.options_frame_widget:
                    switch_state = "normal" if is_actually_playlist else "disabled"
                    self.options_frame_widget.playlist_switch.configure(
                        state=switch_state
                    )
                    # Also ensure the mode reflects reality if it's NOT a playlist
                    if not is_actually_playlist:
                        self.options_frame_widget.set_playlist_mode(False)
            except Exception as e:
                print(f"Error configuring playlist switch: {e}")

            # Transition the UI to the 'info fetched' state
            self._enter_info_fetched_state()  # This method now handles UI setup based on fetched info and switch state

            # --- Refined status message after info fetch ---
            status_msg: str = (
                "Info fetched. Ready to download."  # Default for single video
            )
            # Read the *current* state of the switch *after* potential changes
            is_playlist_mode_on = self.options_frame_widget.get_playlist_mode()

            if is_actually_playlist:
                if is_playlist_mode_on:
                    status_msg = "Playlist info fetched. Select items and download."
                else:
                    # Playlist detected, but switch is off (user might want first item only)
                    status_msg = "Playlist info fetched. Toggle 'Is Playlist?' switch ON to select items."
            # else: The default message "Info fetched. Ready to download." is appropriate

            self.update_status(status_msg)  # Update status label with the final message

        self.after(
            0, _update
        )  # Use 0ms for immediate scheduling in the next UI loop cycle

    def on_info_error(self, error_message: str) -> None:
        """Callback executed when info fetch fails (thread-safe)."""

        def _update() -> None:
            """Inner function to show error message and reset UI."""
            print(f"UI_Interface: Info error callback received: {error_message}")
            # Display the error in a popup message box
            messagebox.showerror(
                "Information Fetch Error",  # Title of the message box
                f"Could not fetch information:\n{error_message}",  # Body text
            )
            # Return the UI to the idle state after an info fetch error
            self._enter_idle_state()

        self.after(0, _update)

    def on_task_finished(self) -> None:
        """Callback executed when any background task finishes (thread-safe)."""

        def _process_finish() -> None:
            """Inner function to determine next UI state based on task outcome."""
            # Read the *final* status message and color directly from the widget
            # This reflects the very last update sent by the background task (or cancellation)
            final_status_text: str = ""
            final_status_color: str = ""
            try:
                if self.status_label:
                    final_status_text = self.status_label.cget("text")
                    # Getting text_color might be specific to CTk implementation detail, be cautious
                    # It might be safer to rely on keywords in the text.
                    final_status_color = str(
                        self.status_label.cget("text_color")
                    )  # Convert to string
            except Exception as e:
                print(f"Error reading final status label state: {e}")

            operation_type: Optional[str] = (
                self.current_operation
            )  # Get the type of operation that just finished

            print(
                f"UI_Interface: Task finished notification (Type: '{operation_type}'). Final status: '{final_status_text}' (Color: {final_status_color})"
            )

            # Determine outcome based on final status text/color
            # Check for cancellation keywords first
            was_cancelled: bool = "cancel" in final_status_text.lower()
            # Check for error color OR error keywords
            was_error: bool = (final_status_color == COLOR_ERROR) or (
                "error" in final_status_text.lower()
            )

            if was_cancelled:
                print("UI: Operation was cancelled.")
                # If cancelled, return to previous state (idle or info_fetched)
                if self.fetched_info and operation_type == "download":
                    # If download was cancelled, return to info fetched state
                    self._enter_info_fetched_state()
                    self.update_status("Download Cancelled.")
                else:
                    # If info fetch was cancelled or state is unclear, return to idle
                    self._enter_idle_state()
                    self.update_status(
                        "Operation Cancelled."
                    )  # Generic cancellation message

            elif was_error:
                print("UI: Operation failed with error.")
                # Error status message should already be displayed by update_status
                # Return to appropriate state based on what failed
                if self.fetched_info and operation_type == "download":
                    # Download failed, return to info fetched state so user can retry/change options
                    self._enter_info_fetched_state()
                else:
                    # Info fetch failed, or state unclear, return to idle
                    # Error messagebox was likely shown by on_info_error already
                    self._enter_idle_state()

            elif operation_type == "fetch":  # Successful fetch
                # State transition already handled by on_info_success
                print(
                    "UI: Info fetch finished successfully (handled by on_info_success)."
                )
                # No state change needed here, just logging. Status message set by on_info_success.

            elif operation_type == "download":  # Successful download
                print("UI: Download finished successfully.")
                # Show success message box
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
                # Reset to idle state after successful download
                self._enter_idle_state()

            else:  # Unknown state or operation type after finish
                print(
                    f"UI Warning: Task finished with unknown state or type. Resetting to idle. (Op: {operation_type}, Status: {final_status_text})"
                )
                self._enter_idle_state()  # Reset to idle as a safe fallback

            # Reset the current operation tracker
            self.current_operation = None

        # Delay slightly (e.g., 50ms) before processing finish.
        # This helps ensure the *very last* status update from the background thread
        # has had a chance to render in the UI before we read it.
        self.after(50, _process_finish)
