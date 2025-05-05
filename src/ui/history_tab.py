# src/ui/history_tab.py
# -- محتوى تبويب السجل --
# Purpose: Contains the UI content and logic for the History tab.
# -- Updated for improved visual appearance --

import customtkinter as ctk
import tkinter.messagebox as messagebox
from typing import TYPE_CHECKING, List, Dict, Any, Optional

# Conditional import for type hinting
if TYPE_CHECKING:
    from ..logic.history_manager import HistoryManager
    from .interface import UserInterface

# --- Constants ---
TAB_TITLE = "History"
FRAME_LABEL = "Recent Activity"
BTN_CLEAR_ALL = "Clear History"
BTN_USE_AGAIN = "Use Again"
BTN_COPY_URL = "Copy URL"
BTN_DELETE_ENTRY = "Delete"
CONFIRM_CLEAR_TITLE = "Confirm Clear History"
CONFIRM_CLEAR_MSG = "Are you sure you want to delete all history entries?\nThis action cannot be undone."
CONFIRM_DELETE_TITLE = "Confirm Delete Entry"
CONFIRM_DELETE_MSG = "Are you sure you want to delete this history entry?"
NO_HISTORY_MSG = "No history entries found."
MAX_TITLE_DISPLAY_LEN = 60


class HistoryTab(ctk.CTkFrame):
    """
    يمثل واجهة المستخدم والمنطق الخاص بتبويب عرض السجل.
    Represents the UI and logic for the History display tab.
    """

    def __init__(
        self,
        master: Any,
        history_manager: "HistoryManager",
        ui_interface_ref: "UserInterface",
        **kwargs: Any,
    ):
        """
        Initializes the HistoryTab frame.
        Args:
            master (Any): The parent widget (the CTkTabview tab frame).
            history_manager (HistoryManager): Instance to interact with the history database.
            ui_interface_ref (UserInterface): Reference to the main UI window for actions like switching tabs.
            **kwargs: Additional arguments for CTkFrame.
        """
        super().__init__(master, fg_color="transparent", **kwargs)
        print("HistoryTab: Initializing...")

        self.history_manager: "HistoryManager" = history_manager
        self.ui_interface: "UserInterface" = ui_interface_ref

        # --- Configure Grid Layout ---
        self.grid_rowconfigure(0, weight=1)  # Scrollable frame takes vertical space
        self.grid_rowconfigure(1, weight=0)  # Button row has fixed height
        self.grid_columnconfigure(0, weight=1)  # Everything spans the single column

        # --- UI Elements ---

        # 1. Scrollable Frame for History Entries
        self.scrollable_frame = ctk.CTkScrollableFrame(self, label_text=FRAME_LABEL)
        self.scrollable_frame.grid(
            row=0, column=0, padx=10, pady=(10, 5), sticky="nsew"
        )
        self.scrollable_frame.grid_columnconfigure(
            0, weight=1
        )  # Allow entry frames to expand horizontally

        # 2. Clear History Button
        self.clear_button = ctk.CTkButton(
            self, text=BTN_CLEAR_ALL, command=self._handle_clear_history
        )
        self.clear_button.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="ew")

        # --- Initial Load ---
        self.load_history()
        print("HistoryTab: Initialization complete.")

    def load_history(self) -> None:
        """Loads history entries from the manager and displays them with improved style."""
        print("HistoryTab: Loading history...")
        # 1. Clear existing widgets
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        # 2. Get entries
        entries: List[Dict[str, Any]] = self.history_manager.get_all_entries()

        # 3. Check if empty
        if not entries:
            no_history_label = ctk.CTkLabel(
                self.scrollable_frame, text=NO_HISTORY_MSG, text_color="gray"
            )
            no_history_label.pack(pady=20)
            self.clear_button.configure(state="disabled")
            print("HistoryTab: No history entries found.")
            return
        else:
            self.clear_button.configure(state="normal")

        # 4. Create and display widgets for each entry
        for entry_data in entries:
            # <<< تغيير: جعل خلفية الإطار شفافة وإضافة مسافة بين الإطارات >>>
            entry_frame = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent")
            entry_frame.pack(
                fill="x", padx=5, pady=(0, 8)
            )  # Use pack within scrollable frame, add vertical padding
            entry_frame.grid_columnconfigure(0, weight=1)  # Text column expands
            entry_frame.grid_columnconfigure(1, weight=0)  # Buttons column fixed

            # --- Left side: Information Labels ---
            # <<< تعديل: زيادة المسافة الأفقية قليلاً >>>
            info_frame = ctk.CTkFrame(entry_frame, fg_color="transparent")
            info_frame.grid(
                row=0, column=0, padx=(10, 5), pady=5, sticky="nsew"
            )  # Increased left padx

            # Title or URL (truncated)
            display_text = entry_data.get("title") or entry_data["url"]
            if len(display_text) > MAX_TITLE_DISPLAY_LEN:
                display_text = f"{display_text[:MAX_TITLE_DISPLAY_LEN - 3]}..."

            # <<< ملاحظة: لون النص الافتراضي يجب أن يعمل جيدًا الآن >>>
            title_label = ctk.CTkLabel(
                info_frame,
                text=display_text,
                anchor="w",
                font=ctk.CTkFont(weight="bold"),
            )
            title_label.pack(fill="x", pady=(0, 2))

            # Timestamp and Operation Type
            details_text = (
                f"{entry_data['timestamp']}  |  Use The Link in : {entry_data['operation_type']}"
            )
            # <<< ملاحظة: لون النص الرمادي سيعمل جيدًا للتمييز >>>
            details_label = ctk.CTkLabel(
                info_frame,
                text=details_text,
                anchor="w",
                text_color="gray",
                font=ctk.CTkFont(size=11),
            )
            details_label.pack(fill="x")

            # --- Right side: Action Buttons ---
            # <<< تعديل: زيادة المسافة الأفقية قليلاً >>>
            button_frame = ctk.CTkFrame(entry_frame, fg_color="transparent")
            button_frame.grid(
                row=0, column=1, padx=(5, 10), pady=5, sticky="e"
            )  # Increased right padx

            use_button = ctk.CTkButton(
                button_frame,
                text=BTN_USE_AGAIN,
                width=80,
                command=lambda data=entry_data: self._handle_use_again(data),
            )
            use_button.pack(side="left", padx=(0, 5))

            copy_button = ctk.CTkButton(
                button_frame,
                text=BTN_COPY_URL,
                width=80,
                command=lambda url=entry_data["url"]: self._handle_copy(url),
            )
            copy_button.pack(side="left", padx=5)

            delete_button = ctk.CTkButton(
                button_frame,
                text=BTN_DELETE_ENTRY,
                width=60,
                fg_color="red",
                hover_color="darkred",
                command=lambda entry_id=entry_data["id"]: self._handle_delete(entry_id),
            )
            delete_button.pack(side="left", padx=(5, 0))

        print(f"HistoryTab: Displayed {len(entries)} history entries.")

    # --- بقية دوال الكلاس (_handle_use_again, _handle_copy, _handle_delete, _handle_clear_history, refresh_history) تبقى كما هي ---
    def _handle_use_again(self, entry_data: Dict[str, Any]) -> None:
        """Handles the 'Use Again' button click."""
        url: str = entry_data["url"]
        op_type: str = entry_data["operation_type"]
        print(f"HistoryTab: Use Again clicked - URL: {url}, Type: {op_type}")
        if op_type in {"Download", "Fetch Info"}:
            self.ui_interface.switch_to_downloader_tab(url)
        elif op_type == "Get Links":
            self.ui_interface.switch_to_getlinks_tab(url)
        else:
            print(
                f"HistoryTab Warning: Unknown operation type '{op_type}' for Use Again."
            )
            messagebox.showwarning(
                "Action Error", f"Cannot automatically reuse entry with type: {op_type}"
            )

    def _handle_copy(self, url: str) -> None:
        """Handles the 'Copy URL' button click."""
        print(f"HistoryTab: Copy URL clicked - URL: {url}")
        try:
            self.clipboard_clear()
            self.clipboard_append(url)
            self.ui_interface.update_status("URL copied to clipboard!")
            self.after(3000, lambda: self.ui_interface.update_status("Ready."))
        except Exception as e:
            print(f"HistoryTab Error copying URL: {e}")
            messagebox.showerror("Copy Error", f"Could not copy URL to clipboard: {e}")

    def _handle_delete(self, entry_id: int) -> None:
        """Handles the 'Delete' button click for a specific entry."""
        print(f"HistoryTab: Delete clicked for entry ID: {entry_id}")
        if messagebox.askyesno(CONFIRM_DELETE_TITLE, CONFIRM_DELETE_MSG):
            if self.history_manager.delete_entry(entry_id):
                print(f"HistoryTab: Entry {entry_id} deleted successfully.")
                self.load_history()  # Refresh the display
                self.ui_interface.update_status("History entry deleted.")
            else:
                print(
                    f"HistoryTab Error: Failed to delete entry {entry_id} from database."
                )
                messagebox.showerror(
                    "Database Error", "Could not delete the history entry."
                )
        else:
            print("HistoryTab: Delete cancelled by user.")

    def _handle_clear_history(self) -> None:
        """Handles the 'Clear History' button click."""
        print("HistoryTab: Clear History clicked.")
        if messagebox.askyesno(CONFIRM_CLEAR_TITLE, CONFIRM_CLEAR_MSG):
            if self.history_manager.clear_all_entries():
                print("HistoryTab: History cleared successfully.")
                self.load_history()  # Refresh the display
                self.ui_interface.update_status("History cleared.")
            else:
                print("HistoryTab Error: Failed to clear history from database.")
                messagebox.showerror("Database Error", "Could not clear the history.")
        else:
            print("HistoryTab: Clear history cancelled by user.")

    def refresh_history(self):
        """Public method to allow external refresh if needed."""
        self.load_history()
