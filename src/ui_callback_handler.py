# src/ui_callback_handler.py
# -- Mixin class for handling callbacks from the logic layer --

import customtkinter as ctk
from tkinter import messagebox

# Assumes mixin into a class with necessary attributes/methods


class UICallbackHandlerMixin:
    """Mixin class containing methods for handling callbacks from LogicHandler."""

    def update_status(self, message):
        """Updates the status label text and color (thread-safe)."""

        def _update():
            color = "gray"
            msg_lower = message.lower()
            justify_val = "left" if "\n" in message else "center"

            if "error" in msg_lower:
                color = "red"
            elif "warning" in msg_lower:
                color = "orange"
            elif "cancel" in msg_lower:
                color = "orange"
            elif (
                "complete" in msg_lower
                or "finished" in msg_lower
                or "success" in msg_lower
            ):
                color = "green"
            elif (
                "downloading" in msg_lower
                or "processing" in msg_lower
                or "fetching" in msg_lower
                or "starting" in msg_lower
            ):
                color = "blue"

            self.status_label.configure(
                text=message, text_color=color, justify=justify_val
            )

        self.after(1, _update)  # Use 1ms delay, less likely to race condition than 0

    def update_progress(self, value):
        """Updates the progress bar value (thread-safe)."""
        value = max(0.0, min(1.0, value))
        self.after(1, lambda: self.progress_bar.set(value))

    def on_info_success(self, info_dict):
        """Callback executed when info fetch succeeds (thread-safe)."""

        def _update():
            self.fetched_info = info_dict
            if not info_dict:
                self.on_info_error("Received empty or invalid info from fetcher.")
                return

            is_actually_playlist = isinstance(info_dict.get("entries"), list)

            # Set switch state based on whether it's *actually* a playlist
            # AND restore user's last preference if it was a playlist
            if is_actually_playlist:
                print(
                    f"Info success: It's a playlist. Restoring switch state to: {self._last_toggled_playlist_mode}"
                )
                self.options_frame_widget.set_playlist_mode(
                    self._last_toggled_playlist_mode
                )
                # Ensure switch is enabled if it's a playlist
                self.options_frame_widget.playlist_switch.configure(state="normal")
            else:
                print(
                    "Info success: It's not a playlist. Ensuring switch is OFF and disabled."
                )
                self.options_frame_widget.set_playlist_mode(False)
                self.options_frame_widget.playlist_switch.configure(state="disabled")

            self._enter_info_fetched_state()  # Display info based on current state

            # Refined status message
            status_msg = "Info fetched. Ready to download."
            if self.options_frame_widget.get_playlist_mode() and is_actually_playlist:
                status_msg = "Playlist info fetched. Select items and download."
            elif is_actually_playlist:  # It's a playlist, but mode is off
                status_msg = "Playlist info fetched (showing first item). Toggle 'Is Playlist?' switch to select items."
            self.update_status(status_msg)

        self.after(0, _update)  # Use 0 for immediate scheduling

    def on_info_error(self, error_message):
        """Callback executed when info fetch fails (thread-safe)."""

        def _update():
            print(f"UI_Interface: Info error callback received: {error_message}")
            # Show error even if it's empty/invalid info
            messagebox.showerror(
                "Information Fetch Error",
                f"Could not fetch information:\n{error_message}",
            )
            self._enter_idle_state()  # Return to idle on any info error

        self.after(0, _update)

    def on_task_finished(self):
        """Callback executed when any background task finishes (thread-safe)."""

        def _process_finish():
            operation_type = self.current_operation
            # Read final status directly from widget *now*
            final_status_text = self.status_label.cget("text")
            final_status_color = self.status_label.cget("text_color")

            print(
                f"UI_Interface: Task finished notification (Type: '{operation_type}'). Final status: '{final_status_text}' (Color: {final_status_color})"
            )

            was_cancelled = "cancel" in final_status_text.lower()
            was_error = (final_status_color == "red") or (
                "error" in final_status_text.lower()
            )

            if was_cancelled:
                print("UI: Operation was cancelled.")
                if self.fetched_info:
                    self._enter_info_fetched_state()  # Restore info view
                    self.update_status("Operation Cancelled.")
                else:
                    self._enter_idle_state()  # Back to idle if fetch was cancelled
                    self.update_status("Info Fetch Cancelled.")
            elif was_error:
                print("UI: Operation failed with error.")
                if self.fetched_info:
                    # Restore info view, error status already displayed by update_status
                    self._enter_info_fetched_state()
                else:
                    # Back to idle if fetch failed, error already shown
                    self._enter_idle_state()
            elif operation_type == "fetch":  # Successful fetch
                # Already handled by on_info_success, state is already _info_fetched_state
                print(
                    "UI: Info fetch finished successfully (handled by on_info_success)."
                )
            elif operation_type == "download":  # Successful download
                print("UI: Download finished successfully.")
                save_path = self.path_frame_widget.get_path()
                messagebox.showinfo(
                    "Download Complete",
                    f"Download finished successfully!\nFile(s) saved in:\n{save_path}",
                )
                self._enter_idle_state()  # Reset to idle after successful download
            else:  # Unknown state
                print(
                    f"UI: Task finished with unknown state or type. Resetting to idle. (Op: {operation_type}, Status: {final_status_text})"
                )
                self._enter_idle_state()

            self.current_operation = None  # Reset tracker

        # Delay slightly to ensure status label update has rendered
        self.after(50, _process_finish)
