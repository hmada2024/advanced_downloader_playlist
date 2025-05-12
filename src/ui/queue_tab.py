# src/ui/queue_tab.py
# -- الواجهة الرسومية والمنطق لتبويب قائمة انتظار التحميل --
# -- Fixed initialization order for clear_finished_button --

import customtkinter as ctk
import tkinter.messagebox as messagebox
from typing import TYPE_CHECKING, Dict, Any, Optional, Union
import uuid

from src.logic.downloader_constants import STATUS_DOWNLOAD_CANCELLED

# Conditional import for type hinting
if TYPE_CHECKING:
    from ..logic.logic_handler import LogicHandler
    from ..logic.history_manager import HistoryManager

# --- Constants ---
TAB_TITLE = "Download Queue"
FRAME_LABEL = "Current & Pending Downloads"
BTN_CANCEL_TASK = "Cancel"
BTN_CLEAR_FINISHED = "Clear Finished Tasks"
NO_TASKS_MSG = "No downloads in queue."
MAX_TITLE_DISPLAY_LEN_QUEUE = 50
MAX_ERROR_DISPLAY_LEN = 60

# Define possible task statuses
STATUS_PENDING = "Pending"
STATUS_RUNNING = "Running"
STATUS_DOWNLOADING = "Downloading"
STATUS_PROCESSING = "Processing"
STATUS_COMPLETED = "Completed"
STATUS_ERROR = "Error"
STATUS_CANCELLING = "Cancelling..."
STATUS_CANCELLED = "Cancelled"

# --- Define Colors ---
COLOR_TEXT_NORMAL = ("gray10", "gray90")
COLOR_TEXT_STATUS_PENDING = ("gray50", "gray50")
COLOR_TEXT_STATUS_RUNNING = ("#1F618D", "#AED6F1")
COLOR_TEXT_STATUS_COMPLETED = ("#1E8449", "#ABEBC6")
COLOR_TEXT_STATUS_ERROR = ("#CB4335", "#F5B7B1")
COLOR_TEXT_STATUS_CANCELLED = ("#D68910", "#FAD7A0")

COLOR_BG_DEFAULT = ("gray92", "gray17")
COLOR_BG_COMPLETED = ("#D5F5E3", "#1E462E")
COLOR_BG_ERROR = ("#FADBD8", "#5E312C")
COLOR_BG_CANCELLED = ("#FEF9E7", "#615C45")

STATUS_TEXT_COLORS = {
    STATUS_PENDING: COLOR_TEXT_STATUS_PENDING,
    STATUS_RUNNING: COLOR_TEXT_STATUS_RUNNING,
    STATUS_DOWNLOADING: COLOR_TEXT_STATUS_RUNNING,
    STATUS_PROCESSING: COLOR_TEXT_STATUS_RUNNING,
    STATUS_COMPLETED: COLOR_TEXT_STATUS_COMPLETED,
    STATUS_ERROR: COLOR_TEXT_STATUS_ERROR,
    STATUS_CANCELLING: COLOR_TEXT_STATUS_CANCELLED,
    STATUS_CANCELLED: COLOR_TEXT_STATUS_CANCELLED,
}

# تخزين عناصر واجهة المستخدم لكل مهمة
TaskWidgets = Dict[
    str, Union[ctk.CTkFrame, ctk.CTkLabel, ctk.CTkProgressBar, ctk.CTkButton]
]


class QueueTab(ctk.CTkFrame):
    """Represents the UI and logic for the Download Queue display tab."""

    def __init__(
        self,
        master: Any,
        logic_handler: "LogicHandler",
        history_manager: Optional["HistoryManager"],
        **kwargs: Any,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        print("QueueTab: Initializing...")

        self.logic_handler: "LogicHandler" = logic_handler
        self.task_widgets: Dict[str, TaskWidgets] = {}

        # --- Configure Grid Layout ---
        self.grid_rowconfigure(0, weight=1)  # Scrollable frame row
        self.grid_rowconfigure(1, weight=0)  # Button row
        self.grid_columnconfigure(0, weight=1)

        # --- UI Elements ---
        # 1. Scrollable Frame
        self.scrollable_frame = ctk.CTkScrollableFrame(self, label_text=FRAME_LABEL)
        self.scrollable_frame.grid(
            row=0, column=0, padx=10, pady=(10, 5), sticky="nsew"
        )
        self.scrollable_frame.grid_columnconfigure(0, weight=1)

        # 2. Placeholder Label
        self.no_tasks_label = ctk.CTkLabel(
            self.scrollable_frame, text=NO_TASKS_MSG, text_color=("gray60", "gray40")
        )

        # 3. Clear Finished Button <<< DEFINITION MOVED HERE >>>
        self.clear_finished_button = ctk.CTkButton(
            self, text=BTN_CLEAR_FINISHED, command=self._handle_clear_finished
        )
        self.clear_finished_button.grid(
            row=1, column=0, padx=10, pady=(5, 10), sticky="ew"
        )
        # Initial state will be set by _update_placeholder_visibility

        # --- Initial Load / State <<< CALL MOVED HERE >>>
        self._update_placeholder_visibility()  # Call AFTER button is defined

        print("QueueTab: Initialization complete.")

    def _update_placeholder_visibility(self) -> None:
        """Shows or hides the 'No tasks' label and sets button state."""
        # <<< الآن self.clear_finished_button معرف هنا >>>
        if not self.task_widgets:
            self.no_tasks_label.pack(pady=20, padx=10, anchor="center", fill="x")
            if hasattr(self, "clear_finished_button"):  # Add safety check just in case
                self.clear_finished_button.configure(state="disabled")
        else:
            if self.no_tasks_label.winfo_ismapped():
                self.no_tasks_label.pack_forget()
            if hasattr(self, "clear_finished_button"):
                # Enable button if there are tasks (actual check if any are finished happens on click)
                self.clear_finished_button.configure(state="normal")

    # --- (باقي دوال الكلاس تبقى كما هي من الإصدار السابق) ---
    # add_task, update_task_display, update_task_progress, remove_task,
    # _handle_cancel_click, _handle_clear_finished, __del__
    def add_task(self, task_id: str, title: str, status: str = STATUS_PENDING) -> None:
        """Adds a new task entry to the queue UI."""
        if task_id in self.task_widgets:
            return
        print(f"QueueTab: Adding task {task_id} - Title: {title}")

        task_frame = ctk.CTkFrame(self.scrollable_frame, fg_color=COLOR_BG_DEFAULT)
        task_frame.pack(fill="x", padx=5, pady=(5, 5))
        task_frame.grid_columnconfigure(0, weight=1)
        task_frame.grid_columnconfigure(1, weight=0)
        task_frame.grid_columnconfigure(2, weight=0)
        task_frame.grid_rowconfigure(1, weight=0)

        info_frame = ctk.CTkFrame(task_frame, fg_color="transparent")
        info_frame.grid(
            row=0, column=0, columnspan=2, padx=(10, 5), pady=(5, 0), sticky="nsew"
        )
        display_title = (
            f"{title[:MAX_TITLE_DISPLAY_LEN_QUEUE - 3]}..."
            if len(title) > MAX_TITLE_DISPLAY_LEN_QUEUE
            else title
        )
        title_label = ctk.CTkLabel(
            info_frame,
            text=display_title,
            anchor="w",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLOR_TEXT_NORMAL,
        )
        title_label.pack(fill="x", pady=(0, 2))
        status_label = ctk.CTkLabel(
            info_frame,
            text=status,
            anchor="nw",
            font=ctk.CTkFont(size=12),
            text_color=STATUS_TEXT_COLORS.get(status, COLOR_TEXT_STATUS_PENDING),
            justify="left",
        )
        status_label.pack(fill="x", pady=(0, 5))

        progress_bar = ctk.CTkProgressBar(task_frame)
        progress_bar.set(0.0)
        progress_bar.grid(
            row=1, column=0, columnspan=2, padx=(10, 5), pady=(0, 8), sticky="ew"
        )
        progress_bar.grid_remove()

        cancel_button = ctk.CTkButton(
            task_frame,
            text=BTN_CANCEL_TASK,
            width=60,
            fg_color="red",
            hover_color="darkred",
            command=lambda tid=task_id: self._handle_cancel_click(tid),
        )
        cancel_button.grid(row=0, column=2, padx=(5, 10), pady=5, sticky="ne")

        self.task_widgets[task_id] = {
            "frame": task_frame,
            "title_label": title_label,
            "status_label": status_label,
            "progress_bar": progress_bar,
            "cancel_button": cancel_button,
        }
        self._update_placeholder_visibility()

    def update_task_display(self, task_id: str, raw_message: str) -> None:
        """Updates the display (status, color, progress visibility) based on the raw message."""
        if task_id not in self.task_widgets:
            return
        widgets = self.task_widgets[task_id]
        status_label: Optional[ctk.CTkLabel] = widgets.get("status_label")  # type: ignore
        progress_bar: Optional[ctk.CTkProgressBar] = widgets.get("progress_bar")  # type: ignore
        cancel_button: Optional[ctk.CTkButton] = widgets.get("cancel_button")  # type: ignore
        task_frame: Optional[ctk.CTkFrame] = widgets.get("frame")  # type: ignore

        base_status = raw_message.split("\n")[0]
        details = ""
        display_text = raw_message
        if base_status.startswith(STATUS_DOWNLOADING):
            base_status = STATUS_DOWNLOADING
        elif base_status.startswith(STATUS_PROCESSING):
            base_status = STATUS_PROCESSING
        elif base_status.startswith("Error:"):
            base_status = STATUS_ERROR
            details = base_status[6:].strip()
        elif base_status.startswith(f"{STATUS_COMPLETED}:"):
            base_status = STATUS_COMPLETED
            details = base_status.split(":", 1)[-1].strip()
        elif base_status == STATUS_DOWNLOAD_CANCELLED:
            base_status = STATUS_CANCELLED

        if base_status == STATUS_ERROR:
            details = (
                f"{details[:MAX_ERROR_DISPLAY_LEN - 3]}..."
                if len(details) > MAX_ERROR_DISPLAY_LEN
                else details
            )
            display_text = f"Error: {details}"

        if status_label:
            status_label.configure(
                text=display_text,
                text_color=STATUS_TEXT_COLORS.get(
                    base_status, COLOR_TEXT_STATUS_PENDING
                ),
                anchor="nw",
                justify="left",
            )
        if progress_bar:
            if base_status in [STATUS_RUNNING, STATUS_DOWNLOADING, STATUS_PROCESSING]:
                if not progress_bar.winfo_ismapped():
                    progress_bar.grid()
            elif progress_bar.winfo_ismapped():
                progress_bar.grid_remove()
        is_final_state = base_status in [
            STATUS_COMPLETED,
            STATUS_ERROR,
            STATUS_CANCELLED,
        ]
        if task_frame:
            bg_color = COLOR_BG_DEFAULT
            if base_status == STATUS_COMPLETED:
                bg_color = COLOR_BG_COMPLETED
            elif base_status == STATUS_ERROR:
                bg_color = COLOR_BG_ERROR
            elif base_status == STATUS_CANCELLED:
                bg_color = COLOR_BG_CANCELLED
            task_frame.configure(fg_color=bg_color)
        if cancel_button:
            if is_final_state:
                cancel_button.configure(state="disabled", fg_color=("gray70", "gray30"))
            elif base_status == STATUS_CANCELLING:
                cancel_button.configure(state="disabled")
            else:
                cancel_button.configure(state="normal", fg_color="red")

    def update_task_progress(self, task_id: str, value: float) -> None:
        """Updates the progress bar value."""
        if task_id not in self.task_widgets:
            return
        widgets = self.task_widgets[task_id]
        progress_bar: Optional[ctk.CTkProgressBar] = widgets.get("progress_bar")  # type: ignore
        if progress_bar and progress_bar.winfo_ismapped():
            progress_bar.set(max(0.0, min(1.0, value)))

    def remove_task(self, task_id: str) -> None:
        """Removes a task's UI elements."""
        if task_id not in self.task_widgets:
            return
        print(f"QueueTab: Removing task {task_id} from UI.")
        widgets = self.task_widgets[task_id]
        if task_frame := widgets.get("frame"):
            task_frame.destroy()
        del self.task_widgets[task_id]
        self._update_placeholder_visibility()

    def _handle_cancel_click(self, task_id: str) -> None:
        """Handles click on a task's cancel button."""
        print(f"QueueTab: Cancel button clicked for task {task_id}")
        if task_id in self.task_widgets:
            if cancel_button := self.task_widgets[task_id].get("cancel_button"):
                cancel_button.configure(state="disabled")
            self.update_task_display(task_id, STATUS_CANCELLING)
        if self.logic_handler:
            self.logic_handler.cancel_task(task_id)

    def _handle_clear_finished(self) -> None:
        """Removes completed, errored, and cancelled tasks from the UI and optionally LogicHandler."""
        print("QueueTab: Clear Finished button clicked.")
        if not self.logic_handler:
            return
        try:
            finished_task_ids = self.logic_handler.get_finished_task_ids()
            if not finished_task_ids:
                print("QueueTab: No finished tasks to clear.")
                if hasattr(self.master.master, "update_status"):
                    self.master.master.update_status("No finished tasks to clear.")
                return
            if messagebox.askyesno(
                "Confirm Clear",
                f"Remove {len(finished_task_ids)} finished task(s) from the list?",
            ):
                self._extracted_from__handle_clear_finished_17(finished_task_ids)
        except Exception as e:
            print(f"QueueTab Error during Clear Finished: {e}")
            messagebox.showerror(
                "Error", f"An error occurred while clearing tasks: {e}"
            )

    # TODO Rename this here and in `_handle_clear_finished`
    def _extracted_from__handle_clear_finished_17(self, finished_task_ids):
        print(f"QueueTab: Clearing {len(finished_task_ids)} tasks from UI.")
        ui_cleared_count = 0
        for task_id in finished_task_ids:
            if task_id in self.task_widgets:
                self.remove_task(task_id)
                ui_cleared_count += 1
        if hasattr(self.logic_handler, "prune_finished_tasks"):
            self.logic_handler.prune_finished_tasks(finished_task_ids)
        print(f"QueueTab: Finished clearing {ui_cleared_count} tasks from UI.")
        if hasattr(self.master.master, "update_status"):
            self.master.master.update_status(
                f"Cleared {ui_cleared_count} finished tasks from queue list."
            )

    def __del__(self):
        print("QueueTab: Destroying...")
