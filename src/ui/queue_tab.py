# src/ui/queue_tab.py
# -- الواجهة الرسومية والمنطق لتبويب قائمة انتظار التحميل --
# Purpose: UI and logic for the Download Queue tab.

import customtkinter as ctk
import tkinter.messagebox as messagebox
from typing import TYPE_CHECKING, Dict, Any, Optional, Tuple, Union
import uuid  # لتوليد معرفات فريدة للمهام

# Conditional import for type hinting
if TYPE_CHECKING:
    from ..logic.logic_handler import LogicHandler  # Import modified LogicHandler
    from ..logic.history_manager import HistoryManager  # Keep HistoryManager import

# --- Constants ---
TAB_TITLE = "Download Queue"
FRAME_LABEL = "Current & Pending Downloads"
BTN_CANCEL_TASK = "Cancel"
NO_TASKS_MSG = "No downloads in queue."
MAX_TITLE_DISPLAY_LEN_QUEUE = 50  # طول أقصر لعرض العنوان في القائمة

# Define possible task statuses (يمكن تحسينها باستخدام Enum لاحقًا)
STATUS_PENDING = "Pending"
STATUS_RUNNING = "Running"
STATUS_DOWNLOADING = "Downloading"  # سيتم إضافة النسبة المئوية
STATUS_PROCESSING = "Processing"  # للدمج وغيره
STATUS_COMPLETED = "Completed"
STATUS_ERROR = "Error"
STATUS_CANCELLING = "Cancelling..."
STATUS_CANCELLED = "Cancelled"

# ألوان الحالة
STATUS_COLORS = {
    STATUS_PENDING: "gray",
    STATUS_RUNNING: "blue",
    STATUS_DOWNLOADING: "blue",
    STATUS_PROCESSING: "dodgerblue",
    STATUS_COMPLETED: "green",
    STATUS_ERROR: "red",
    STATUS_CANCELLING: "orange",
    STATUS_CANCELLED: "orange",
}

# تخزين عناصر واجهة المستخدم لكل مهمة
TaskWidgets = Dict[
    str, Union[ctk.CTkFrame, ctk.CTkLabel, ctk.CTkProgressBar, ctk.CTkButton]
]


class QueueTab(ctk.CTkFrame):
    """
    يمثل واجهة المستخدم والمنطق الخاص بتبويب عرض قائمة انتظار التحميل.
    Represents the UI and logic for the Download Queue display tab.
    """

    def __init__(
        self,
        master: Any,
        logic_handler: "LogicHandler",
        history_manager: Optional[
            "HistoryManager"
        ],  # Keep HistoryManager if needed elsewhere, but not used directly here
        **kwargs: Any,
    ):
        """
        Initializes the QueueTab frame.
        Args:
            master (Any): The parent widget (the CTkTabview tab frame).
            logic_handler (LogicHandler): Instance to interact with the queue logic.
            history_manager (Optional[HistoryManager]): History manager instance.
            **kwargs: Additional arguments for CTkFrame.
        """
        super().__init__(master, fg_color="transparent", **kwargs)
        print("QueueTab: Initializing...")

        self.logic_handler: "LogicHandler" = logic_handler
        # self.history_manager = history_manager # Not directly used in this tab for now

        # لتخزين عناصر الواجهة لكل مهمة، المفتاح هو task_id
        self.task_widgets: Dict[str, TaskWidgets] = {}

        # --- Configure Grid Layout ---
        self.grid_rowconfigure(0, weight=1)  # Scrollable frame takes vertical space
        self.grid_columnconfigure(0, weight=1)  # Everything spans the single column

        # --- UI Elements ---

        # 1. Scrollable Frame for Queue Entries
        self.scrollable_frame = ctk.CTkScrollableFrame(self, label_text=FRAME_LABEL)
        self.scrollable_frame.grid(
            row=0, column=0, padx=10, pady=(10, 5), sticky="nsew"
        )
        self.scrollable_frame.grid_columnconfigure(
            0, weight=1
        )  # Allow entry frames to expand horizontally

        # 2. Placeholder Label (shown when queue is empty)
        self.no_tasks_label = ctk.CTkLabel(
            self.scrollable_frame, text=NO_TASKS_MSG, text_color="gray"
        )
        # Initially packed, will be removed when first task is added

        # --- Initial Load / State ---
        self._update_placeholder_visibility()
        print("QueueTab: Initialization complete.")

    def _update_placeholder_visibility(self) -> None:
        """Shows or hides the 'No tasks' label based on whether tasks exist."""
        if not self.task_widgets:
            self.no_tasks_label.pack(pady=20, padx=10, anchor="center", fill="x")
        elif self.no_tasks_label.winfo_ismapped():
            self.no_tasks_label.pack_forget()

    # --- Public Methods for UI Updates (called by LogicHandler/UserInterface) ---

    def add_task(self, task_id: str, title: str, status: str = STATUS_PENDING) -> None:
        """Adds a new task entry to the queue UI."""
        if task_id in self.task_widgets:
            print(
                f"QueueTab Warning: Task {task_id} already exists in UI. Ignoring add."
            )
            return

        print(f"QueueTab: Adding task {task_id} - Title: {title}")
        self._update_placeholder_visibility()  # Hide placeholder if it was visible

        task_frame = ctk.CTkFrame(
            self.scrollable_frame, fg_color="gray15"
        )  # Slightly different background
        task_frame.pack(fill="x", padx=5, pady=(5, 5))
        task_frame.grid_columnconfigure(0, weight=1)  # Info column expands
        task_frame.grid_columnconfigure(
            1, weight=0
        )  # Progress bar fixed (relative) width
        task_frame.grid_columnconfigure(2, weight=0)  # Cancel button fixed width

        # --- Column 0: Title and Status ---
        info_frame = ctk.CTkFrame(task_frame, fg_color="transparent")
        info_frame.grid(row=0, column=0, padx=(10, 5), pady=5, sticky="nsew")

        display_title = title
        if len(title) > MAX_TITLE_DISPLAY_LEN_QUEUE:
            display_title = f"{title[:MAX_TITLE_DISPLAY_LEN_QUEUE - 3]}..."

        title_label = ctk.CTkLabel(
            info_frame,
            text=display_title,
            anchor="w",
            font=ctk.CTkFont(weight="bold"),
        )
        title_label.pack(fill="x", pady=(0, 2))

        status_label = ctk.CTkLabel(
            info_frame,
            text=status,
            anchor="w",
            text_color=STATUS_COLORS.get(status, "gray"),
            font=ctk.CTkFont(size=11),
        )
        status_label.pack(fill="x")

        # --- Column 1: Progress Bar ---
        progress_bar = ctk.CTkProgressBar(
            task_frame, width=150
        )  # Fixed width looks better here
        progress_bar.set(0.0)
        # Progress bar initially hidden, shown when status is Running/Downloading/Processing
        progress_bar.grid(row=0, column=1, padx=5, pady=(8, 8), sticky="e")
        progress_bar.grid_remove()  # Start hidden

        # --- Column 2: Cancel Button ---
        cancel_button = ctk.CTkButton(
            task_frame,
            text=BTN_CANCEL_TASK,
            width=60,
            fg_color="red",
            hover_color="darkred",
            command=lambda tid=task_id: self._handle_cancel_click(tid),
        )
        cancel_button.grid(row=0, column=2, padx=(5, 10), pady=5, sticky="e")

        # Store widgets for later access
        self.task_widgets[task_id] = {
            "frame": task_frame,
            "title_label": title_label,
            "status_label": status_label,
            "progress_bar": progress_bar,
            "cancel_button": cancel_button,
        }

        self._update_placeholder_visibility()  # Ensure placeholder is hidden now

    def update_task_status(self, task_id: str, status: str, details: str = "") -> None:
        """Updates the status label and visibility of progress bar for a specific task."""
        if task_id not in self.task_widgets:
            print(f"QueueTab Error: Cannot update status for unknown task {task_id}")
            return

        widgets = self.task_widgets[task_id]
        status_label: Optional[ctk.CTkLabel] = widgets.get("status_label")  # type: ignore
        progress_bar: Optional[ctk.CTkProgressBar] = widgets.get("progress_bar")  # type: ignore
        cancel_button: Optional[ctk.CTkButton] = widgets.get("cancel_button")  # type: ignore

        if status_label:
            status_text = f"{status} ({details})" if details else status
            status_label.configure(
                text=status_text, text_color=STATUS_COLORS.get(status, "gray")
            )

        if progress_bar:
            if status in [STATUS_RUNNING, STATUS_DOWNLOADING, STATUS_PROCESSING]:
                if not progress_bar.winfo_ismapped():
                    progress_bar.grid()
            elif progress_bar.winfo_ismapped():
                progress_bar.grid_remove()

        # Disable cancel button for final states
        if cancel_button:
            if status in [STATUS_COMPLETED, STATUS_ERROR, STATUS_CANCELLED]:
                cancel_button.configure(
                    state="disabled", fg_color="gray50"
                )  # Visually disable
            elif status == STATUS_CANCELLING:
                cancel_button.configure(
                    state="disabled"
                )  # Temporarily disable during cancelling

    def update_task_progress(self, task_id: str, value: float) -> None:
        """Updates the progress bar value for a specific task."""
        if task_id not in self.task_widgets:
            # print(f"QueueTab Error: Cannot update progress for unknown task {task_id}") # Can be noisy
            return

        widgets = self.task_widgets[task_id]
        progress_bar: Optional[ctk.CTkProgressBar] = widgets.get("progress_bar")  # type: ignore

        if progress_bar and progress_bar.winfo_ismapped():
            # Clamp value between 0.0 and 1.0
            clamped_value = max(0.0, min(1.0, value))
            progress_bar.set(clamped_value)

    def remove_task(self, task_id: str) -> None:
        """Removes a task's UI elements from the queue display."""
        if task_id not in self.task_widgets:
            print(f"QueueTab Warning: Cannot remove non-existent task {task_id}")
            return

        print(f"QueueTab: Removing task {task_id} from UI.")
        widgets = self.task_widgets[task_id]
        if task_frame := widgets.get("frame"):
            task_frame.destroy()

        del self.task_widgets[task_id]
        self._update_placeholder_visibility()  # Show placeholder if queue becomes empty

    # --- Internal Event Handlers ---

    def _handle_cancel_click(self, task_id: str) -> None:
        """Handles the click on a task's cancel button."""
        print(f"QueueTab: Cancel button clicked for task {task_id}")
        # Provide immediate visual feedback
        if task_id in self.task_widgets:
            if cancel_button := self.task_widgets[task_id].get("cancel_button"):
                cancel_button.configure(state="disabled")  # Disable button immediately
            self.update_task_status(task_id, STATUS_CANCELLING)

        # Delegate cancellation logic to LogicHandler
        self.logic_handler.cancel_task(task_id)

    def clear_completed_tasks(self):
        """(Optional) Removes tasks marked as Completed, Error, or Cancelled."""
        # This could be triggered by a button or automatically
        tasks_to_remove = [
            tid
            for tid, info in self.logic_handler.tasks_info.items()  # Assuming LogicHandler exposes this
            if info["status"] in [STATUS_COMPLETED, STATUS_ERROR, STATUS_CANCELLED]
        ]
        print(f"QueueTab: Clearing {len(tasks_to_remove)} finished tasks from UI.")
        for task_id in tasks_to_remove:
            self.remove_task(task_id)
            # Optionally, tell LogicHandler to prune its internal info too if not needed anymore

    # --- Helper Methods ---
    # (Add any helper methods if needed)

    def __del__(self):
        print("QueueTab: Destroying...")
