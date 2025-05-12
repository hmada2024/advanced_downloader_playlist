# src/ui/callback_handler.py
# -- Mixin class for handling callbacks from the logic layer --
# -- Modified to route callbacks to QueueTab or main status based on task_id --

import contextlib
from tkinter import messagebox
from typing import TYPE_CHECKING, Callable, Dict, Any, Optional

# --- Type Hinting ---
if TYPE_CHECKING:
    import customtkinter as ctk
    from .interface import UserInterface
    from .queue_tab import QueueTab  # Import QueueTab for type hinting

    # Add component hints if needed
    from .components.path_selection_frame import PathSelectionFrame
    from .components.options_control_frame import OptionsControlFrame

# --- Constants for Status Colors (Unchanged) ---
COLOR_ERROR = "red"
COLOR_WARNING = "orange"
COLOR_CANCEL = "orange"
COLOR_SUCCESS = "green"
COLOR_INFO = "blue"
COLOR_DEFAULT = "gray"

# Import queue statuses if needed for logic, though LogicHandler should handle status mapping
# from .queue_tab import STATUS_COMPLETED, STATUS_ERROR, STATUS_CANCELLED, ...


class UICallbackHandlerMixin:
    """
    Mixin class containing methods for handling callbacks from LogicHandler.
    Routes callbacks to the appropriate UI element (QueueTab or main status bar)
    based on whether a task_id is provided.
    """

    # --- Type Hinting for attributes/methods in UserInterface ---
    if TYPE_CHECKING:
        self: "UserInterface"
        # Main status/progress
        status_label: ctk.CTkLabel
        progress_bar: ctk.CTkProgressBar
        # Reference to the queue tab
        queue_tab: Optional[QueueTab]
        # Methods from other mixins/main class
        after: Callable[..., Any]
        _enter_idle_state: Callable[[], None]
        _enter_info_fetched_state: Callable[[], None]
        # Attributes assumed
        fetched_info: Optional[Dict[str, Any]]
        current_operation: Optional[str]  # Tracks 'fetch' mainly now
        # Component types
        path_frame_widget: PathSelectionFrame
        options_frame_widget: OptionsControlFrame

    # --- Callback Methods ---

    def update_status(
        self, message: str, task_id: Optional[str] = None, details: str = ""
    ) -> None:
        """
        Updates status. Routes to QueueTab if task_id is provided, otherwise updates main status label.
        Args:
            message (str): The primary status message (e.g., STATUS_DOWNLOADING, "Fetching...", "Ready.").
            task_id (Optional[str]): The ID of the download task, if applicable.
            details (str): Additional details (e.g., percentage, filename, error message).
        """
        if task_id and self.queue_tab:
            # Route to QueueTab's status update method
            # Run in main thread using after
            def _update_queue():
                self.queue_tab.update_task_status(task_id, message, details)  # type: ignore

            self.after(0, _update_queue)
        else:
            # Update main status label (e.g., for Fetch Info, general messages)
            def _update_main():
                color: str = COLOR_DEFAULT
                msg_lower: str = message.lower()
                full_message = f"{message}{f' ({details})' if details else ''}"

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
                # Add more specific checks if needed

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
        """
        Updates progress. Routes to QueueTab if task_id is provided, otherwise updates main progress bar.
        Args:
            value (float): Progress value (0.0 to 1.0).
            task_id (Optional[str]): The ID of the download task, if applicable.
        """
        clamped_value: float = max(0.0, min(1.0, value))

        if task_id and self.queue_tab:
            # Route to QueueTab's progress update method
            def _update_queue():
                self.queue_tab.update_task_progress(task_id, clamped_value)  # type: ignore

            self.after(0, _update_queue)
        else:
            # Update main progress bar (e.g., for Fetch Info)
            def _update_main():
                try:
                    if self.progress_bar:
                        self.progress_bar.set(clamped_value)
                except Exception as e:
                    print(f"Error updating main progress bar: {e}")

            self.after(1, _update_main)

    def on_info_success(self, info_dict: Dict[str, Any]) -> None:
        """Callback executed when info fetch succeeds (thread-safe). Logs to history."""
        # --- History Logging ---
        logged = False
        if self.history_manager and self._current_fetch_url:
            try:
                title = info_dict.get("title", "Untitled")
                logged = self.history_manager.add_entry(
                    url=self._current_fetch_url,
                    title=title,
                    operation_type="Fetch Info",
                )
                print(
                    f"History logging for Fetch Info {'succeeded' if logged else 'failed'}."
                )
            except Exception as log_err:
                print(f"Error during history logging for Fetch Info: {log_err}")
            finally:
                self._current_fetch_url = None  # Clear URL after attempting log

        # --- UI Update (in main thread) ---
        def _update() -> None:
            self.fetched_info = info_dict
            if not info_dict:
                # Call on_info_error directly, as it handles UI state reset
                self.on_info_error("Received empty or invalid info from fetcher.")
                return

            # --- Logic to configure UI based on fetched info (playlist vs single) ---
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

            # --- Enter the appropriate UI state (displays info, enables add button) ---
            self._enter_info_fetched_state()  # This now also handles thumbnail display

            # --- Update main status bar ---
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
            self.update_status(status_msg)  # Update main status bar

        self.after(0, _update)

    def on_info_error(self, error_message: str) -> None:
        """Callback executed when info fetch fails (thread-safe)."""

        def _update() -> None:
            print(f"UI_Interface: Info error callback received: {error_message}")
            messagebox.showerror(
                "Information Fetch Error",
                f"Could not fetch information:\n{error_message}",
            )
            # Reset the main "Add Download" tab to idle state
            self._enter_idle_state()
            # Update main status bar with error
            self.update_status(f"Fetch Error: {error_message}")

        self.after(0, _update)

    def on_task_finished(self, task_id: Optional[str] = None) -> None:
        """
        Callback executed when any background task finishes.
        If task_id is None, it's likely the Fetch Info task.
        If task_id is provided, it's a download task managed by the queue worker.
        """

        def _process_finish() -> None:
            if task_id:
                # This is a download task completion signal from LogicHandler's worker
                # The final status should already be set in the QueueTab via status callbacks
                print(
                    f"UI_Interface: Download task {task_id} finished processing (worker loop notified)."
                )
                # Optional: Remove the task from QueueTab UI after a delay?
                # Or add a "Clear Finished" button in QueueTab.
                # For now, just leave it in its final state (Completed/Error/Cancelled).

                # Check if the completed task requires history logging
                if self.history_manager and self.logic:
                    with self.logic.queue_lock:  # Access task info safely
                        task_info = self.logic.tasks_info.get(task_id)
                    if task_info:
                        final_status = task_info.get("status")
                        # Log only successful downloads
                        if (
                            final_status == "Completed"
                        ):  # Use the constant STATUS_COMPLETED
                            try:
                                logged = self.history_manager.add_entry(
                                    url=task_info["url"],
                                    title=task_info.get("title", "Untitled Download"),
                                    operation_type="Download",
                                )
                                print(
                                    f"History logging for completed task {task_id} {'succeeded' if logged else 'failed'}."
                                )
                            except Exception as log_err:
                                print(
                                    f"Error during history logging for task {task_id}: {log_err}"
                                )

            else:
                # This is the finish signal for Fetch Info task
                print("UI_Interface: Fetch Info task finished.")
                self.current_operation = None  # Clear fetch operation flag

                # Check the final status on the main status bar
                final_status_text = ""
                final_status_color = ""
                try:
                    if self.status_label:
                        final_status_text = self.status_label.cget("text")
                        final_status_color = str(self.status_label.cget("text_color"))
                except Exception as e:
                    print(f"Error reading final status label state for fetch: {e}")

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
                    self._enter_idle_state()  # Reset Home tab
                    self.update_status("Fetch cancelled.")
                elif was_error:
                    print("UI: Fetch Info failed with error.")
                    # Error message and state reset handled by on_info_error
                else:
                    # Fetch finished successfully, state handled by on_info_success
                    print(
                        "UI: Fetch Info finished successfully (handled by on_info_success)."
                    )

        # Use a small delay to ensure other callbacks might have finished updating state
        self.after(50, _process_finish)
