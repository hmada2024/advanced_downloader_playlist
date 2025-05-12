# src/ui/callback_handler.py
# -- Mixin class for handling callbacks from the logic layer --
# -- Routes callbacks, passes raw message to queue tab --

import contextlib
from tkinter import messagebox
from typing import TYPE_CHECKING, Callable, Dict, Any, Optional

# --- Type Hinting ---
if TYPE_CHECKING:
    import customtkinter as ctk
    from .interface import UserInterface
    from .queue_tab import QueueTab
    from .components.path_selection_frame import PathSelectionFrame
    from .components.options_control_frame import OptionsControlFrame

# --- Constants ---
COLOR_ERROR = "red"
COLOR_WARNING = "orange"
COLOR_CANCEL = "orange"
COLOR_SUCCESS = "green"
COLOR_INFO = "blue"
COLOR_DEFAULT = "gray"

# Import queue statuses for logic within this handler if needed (e.g. on_task_finished)
from .queue_tab import STATUS_COMPLETED, STATUS_ERROR, STATUS_CANCELLED


class UICallbackHandlerMixin:
    """
    Handles callbacks from LogicHandler, routing them appropriately.
    Passes raw status messages to the QueueTab for detailed display.
    """

    if TYPE_CHECKING:
        self: "UserInterface"
        status_label: ctk.CTkLabel
        progress_bar: ctk.CTkProgressBar
        queue_tab: Optional[QueueTab]
        after: Callable[..., Any]
        _enter_idle_state: Callable[[], None]
        _enter_info_fetched_state: Callable[[], None]
        fetched_info: Optional[Dict[str, Any]]
        current_operation: Optional[str]
        path_frame_widget: PathSelectionFrame
        options_frame_widget: OptionsControlFrame
        history_manager: Optional[Any]  # HistoryManager type
        logic: Optional[Any]  # LogicHandler type
        _current_fetch_url: Optional[str]

    # --- Callback Methods ---

    def update_status(
        self, message: str, task_id: Optional[str] = None, details: str = ""
    ) -> None:
        """
        Updates status. Routes RAW message to QueueTab if task_id is present.
        Updates main status bar otherwise, using English for static text.
        """
        if task_id and self.queue_tab:
            # Pass the RAW message directly to the queue tab's update method
            # The QueueTab is now responsible for parsing/displaying multi-line info
            def _update_queue():
                self.queue_tab.update_task_display(task_id, message)  # type: ignore Use the raw message

            self.after(0, _update_queue)
        else:
            # Update main status label (English for static parts)
            def _update_main():
                color: str = COLOR_DEFAULT
                # Combine message and details for main status bar display
                full_message = message
                # Use English for known static messages
                if message == "URL pasted from clipboard.":
                    full_message = "URL pasted from clipboard."
                elif message == "Clipboard is empty.":
                    full_message = "Clipboard is empty."
                elif message == "Paste failed (clipboard empty or non-text?).":
                    full_message = "Paste failed (clipboard empty or non-text?)."
                elif message.startswith("Paste Error:"):
                    full_message = message  # Keep error details
                elif message == "Fetch cancelled.":
                    full_message = "Fetch cancelled."
                elif message.startswith("Fetch Error:"):
                    full_message = message  # Keep error details
                elif message == MSG_LOGIC_HANDLER_MISSING:
                    full_message = "Error: Logic handler missing."
                elif message.startswith("Added"):
                    full_message = message  # Keep the formatted "Added..." message
                # Add more translations for other static messages if needed
                elif not message:
                    full_message = "Ready."  # Default empty to Ready

                # Determine color based on keywords in the potentially translated message
                msg_lower = message.lower()  # Use original message for keyword check
                if "error" in msg_lower:
                    color = COLOR_ERROR
                elif "warning" in msg_lower:
                    color = COLOR_WARNING
                elif "cancel" in msg_lower:
                    color = COLOR_CANCEL
                elif any(
                    term in msg_lower
                    for term in [
                        "complete",
                        "finished",
                        "success",
                        "fetched",
                        "ready",
                        "added",
                        "pasted",
                    ]
                ):
                    color = COLOR_SUCCESS
                elif any(
                    term in msg_lower
                    for term in [
                        "downloading",
                        "processing",
                        "fetching",
                        "starting",
                        "running",
                    ]
                ):
                    color = COLOR_INFO

                justify_val: str = "left" if "\n" in full_message else "center"
                try:
                    if self.status_label:
                        self.status_label.configure(
                            text=full_message, text_color=color, justify=justify_val
                        )
                except Exception as e:
                    print(f"Error updating main status label: {e}")

            self.after(1, _update_main)

    def update_progress(self, value: float, task_id: Optional[str] = None) -> None:
        """Updates progress bar for QueueTab task or main bar."""
        # (No changes needed here from previous version)
        clamped_value: float = max(0.0, min(1.0, value))
        if task_id and self.queue_tab:

            def _update_queue():
                self.queue_tab.update_task_progress(task_id, clamped_value)  # type: ignore

            self.after(0, _update_queue)
        else:

            def _update_main():
                try:
                    if self.progress_bar:
                        self.progress_bar.set(clamped_value)
                except Exception as e:
                    print(f"Error updating main progress bar: {e}")

            self.after(1, _update_main)

    def on_info_success(self, info_dict: Dict[str, Any]) -> None:
        """Callback for successful info fetch. Logs to history."""
        # (No changes needed here from previous version)
        logged = False
        if self.history_manager and self._current_fetch_url:
            try:
                title = info_dict.get("title", "Untitled Fetch")
                logged = self.history_manager.add_entry(
                    url=self._current_fetch_url,
                    title=title,
                    operation_type="Fetch Info",
                )
                print(
                    f"History logging for Fetch Info {'succeeded' if logged else 'failed'}."
                )
            except Exception as log_err:
                print(f"Error logging Fetch Info: {log_err}")
            finally:
                self._current_fetch_url = None

        def _update() -> None:
            self.fetched_info = info_dict
            if not info_dict:
                self.on_info_error("Received empty or invalid info from fetcher.")
                return

            is_actually_playlist: bool = isinstance(info_dict.get("entries"), list)
            try:  # Configure playlist switch
                if self.options_frame_widget:
                    sw_state = "normal" if is_actually_playlist else "disabled"
                    self.options_frame_widget.playlist_switch.configure(state=sw_state)
                    if not is_actually_playlist:
                        self.options_frame_widget.set_playlist_mode(False)
            except Exception as e:
                print(f"Error configuring playlist switch: {e}")

            self._enter_info_fetched_state()  # Update UI display

            # Update main status bar (English)
            status_msg: str = "Info fetched. Ready to add to queue."
            is_playlist_mode_on = False
            with contextlib.suppress(Exception):
                if self.options_frame_widget:
                    is_playlist_mode_on = self.options_frame_widget.get_playlist_mode()

            if is_actually_playlist:
                item_count = len(info_dict.get("entries", []))
                status_msg = (
                    f"Playlist info fetched ({item_count} items). Select items and add to queue."
                    if is_playlist_mode_on
                    else f"Playlist info fetched ({item_count} items). Toggle switch ON to select items."
                )
            self.update_status(status_msg)

        self.after(0, _update)

    def on_info_error(self, error_message: str) -> None:
        """Callback for failed info fetch."""

        # (No changes needed here from previous version)
        def _update() -> None:
            print(f"UI: Info error callback: {error_message}")
            messagebox.showerror(
                "Fetch Error", f"Could not fetch information:\n{error_message}"
            )
            self._enter_idle_state()
            self.update_status(f"Fetch Error: {error_message}")

        self.after(0, _update)

    def on_task_finished(self, task_id: Optional[str] = None) -> None:
        """Callback when any background task finishes processing."""

        # (Logic remains similar, handles history logging for completed downloads)
        def _process_finish() -> None:
            if task_id:
                # Download task finished
                print(f"UI: Download task {task_id} finished processing.")
                # Log successful downloads to history
                if self.history_manager and self.logic:
                    task_info = None
                    with self.logic.queue_lock:  # Access safely
                        task_info = self.logic.tasks_info.get(task_id)
                    if task_info and task_info.get("status") == STATUS_COMPLETED:
                        try:
                            logged = self.history_manager.add_entry(
                                url=task_info["url"],
                                title=task_info.get("title", "Untitled Download"),
                                operation_type="Download",
                            )
                            print(
                                f"History logging for task {task_id} {'succeeded' if logged else 'failed'}."
                            )
                        except Exception as log_err:
                            print(f"Error logging task {task_id}: {log_err}")
            else:
                # Fetch Info task finished
                print("UI: Fetch Info task finished.")
                self.current_operation = None  # Clear fetch flag

                # Check final status on main status bar
                final_status_text = ""
                final_status_color = ""
                try:
                    if self.status_label:
                        final_status_text = self.status_label.cget("text")
                        final_status_color = str(self.status_label.cget("text_color"))
                except Exception as e:
                    print(f"Error reading fetch status: {e}")

                was_cancelled = (
                    COLOR_CANCEL in final_status_color
                    or "cancel" in final_status_text.lower()
                )
                was_error = (
                    COLOR_ERROR in final_status_color
                    or "error" in final_status_text.lower()
                )

                if was_cancelled:
                    print("UI: Fetch Info was cancelled.")
                    self._enter_idle_state()
                    self.update_status("Fetch cancelled.")
                elif was_error:
                    print("UI: Fetch Info failed (handled by on_info_error).")
                else:
                    print("UI: Fetch Info success (handled by on_info_success).")

        self.after(50, _process_finish)
