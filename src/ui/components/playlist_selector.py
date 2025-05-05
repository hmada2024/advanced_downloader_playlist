# src/ui_components/playlist_selector.py
# -- ملف لمكون الواجهة الخاص بعرض واختيار عناصر قائمة التشغيل --
# Purpose: UI component for displaying and selecting playlist items.

import customtkinter as ctk
from typing import List, Dict, Any, Optional, Tuple, Union  # Added typing

# --- Constants ---
FRAME_LABEL = "Playlist Items"
BTN_SELECT_ALL = "Select All"
BTN_DESELECT_ALL = "Deselect All"
MSG_NO_VIDEOS = "No videos found in playlist."
CHECKBOX_ON = "on"
CHECKBOX_OFF = "off"
TITLE_MAX_LEN = 70  # Max length for displaying video titles


# Type alias for the data stored for each checkbox item
# (Widget, StringVar or None, Video Index)
PlaylistItemData = Tuple[
    Union[ctk.CTkCheckBox, ctk.CTkLabel], Optional[ctk.StringVar], int
]


class PlaylistSelector(ctk.CTkScrollableFrame):
    """Scrollable frame for displaying and selecting playlist items."""

    def __init__(self, master: Any, **kwargs: Any):
        """
        Initializes the PlaylistSelector.
        Args:
            master (Any): The parent widget.
            **kwargs: Additional arguments for CTkScrollableFrame.
        """
        super().__init__(master, label_text=FRAME_LABEL, **kwargs)
        # List to store tuples of (checkbox_widget, string_var, video_index)
        self.checkboxes_data: List[PlaylistItemData] = []

        # --- Frame for Select/Deselect Buttons ---
        self.button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.button_frame.pack(fill="x", pady=5, padx=5)  # Pack at the top

        # Select All Button
        self.select_all_button = ctk.CTkButton(
            self.button_frame, text=BTN_SELECT_ALL, command=self.select_all
        )
        self.select_all_button.pack(side="left", padx=(0, 5))

        # Deselect All Button
        self.deselect_all_button = ctk.CTkButton(
            self.button_frame, text=BTN_DESELECT_ALL, command=self.deselect_all
        )
        self.deselect_all_button.pack(side="left", padx=5)

        # Start in a disabled state until populated
        self.disable()

    def clear_items(self) -> None:
        """تدمير مربعات الاختيار القديمة ومسح القائمة الداخلية."""
        """Destroys old checkbox/label widgets and clears the internal data list."""
        # Iterate through the stored widget data
        for widget, var, index in self.checkboxes_data:
            if widget:  # Check if widget exists
                try:
                    widget.destroy()  # Destroy the widget
                except Exception as e:
                    # Log error if destroying fails (widget might already be gone)
                    print(f"Error destroying playlist item widget: {e}")
        # Clear the internal list holding references
        self.checkboxes_data = []
        # Ensure controls are disabled after clearing
        self.disable()

    def populate_items(self, entries: List[Optional[Dict[str, Any]]]) -> None:
        """تملأ الإطار بمربعات الاختيار لعناصر القائمة."""
        """Populates the frame with checkboxes for the given playlist entries.

        Args:
            entries (List[Optional[Dict[str, Any]]]): A list of dictionaries,
                where each dictionary represents a video entry from yt-dlp.
                Can contain None entries if yt-dlp failed to fetch some items.
        """
        self.clear_items()  # Clear previous items first

        # Handle empty or invalid entries list
        if not entries:
            # Display a message indicating no videos were found
            no_items_label = ctk.CTkLabel(self, text=MSG_NO_VIDEOS)
            no_items_label.pack(pady=10, padx=10, anchor="w")
            # Store the label info (though no selection possible)
            self.checkboxes_data.append((no_items_label, None, -1))
            self.disable()  # Keep controls disabled
            return

        # If we have entries, enable the controls
        self.enable()

        print(f"PlaylistSelector: Populating with {len(entries)} items.")
        # Iterate through the provided entries
        for index, entry in enumerate(entries):
            # Skip if an entry is None (e.g., yt-dlp ignored an error)
            if not entry or not isinstance(entry, dict):
                print(
                    f"PlaylistSelector: Skipping invalid entry at index {index}: {entry}"
                )
                continue

            # Extract video index and title (provide defaults)
            # yt-dlp playlist_index is 1-based
            video_index: int = entry.get("playlist_index") or (index + 1)
            title: str = entry.get("title") or f"Video {video_index} (Untitled)"

            # Truncate long titles for display
            display_title: str = (
                f"{title[:TITLE_MAX_LEN]}..." if len(title) > TITLE_MAX_LEN else title
            )

            # Create a StringVar for the checkbox state (selected by default)
            var = ctk.StringVar(value=CHECKBOX_ON)
            # Create the checkbox widget
            cb = ctk.CTkCheckBox(
                self,  # Parent is the scrollable frame itself
                text=f"{video_index}. {display_title}",  # Display index and title
                variable=var,
                onvalue=CHECKBOX_ON,
                offvalue=CHECKBOX_OFF,
                # Add other styling as needed (e.g., font)
            )
            # Pack the checkbox into the frame
            cb.pack(anchor="w", padx=10, pady=(2, 2), fill="x")
            # Store the checkbox, its variable, and the original video index
            self.checkboxes_data.append((cb, var, video_index))

        print("PlaylistSelector: Finished packing checkboxes.")

    def select_all(self) -> None:
        """تحديد جميع مربعات الاختيار."""
        """Selects all valid checkboxes."""
        for cb, var, index in self.checkboxes_data:
            # Check if it's a valid checkbox variable
            if var and isinstance(var, ctk.StringVar):
                var.set(CHECKBOX_ON)  # Set variable to 'on' state

    def deselect_all(self) -> None:
        """إلغاء تحديد جميع مربعات الاختيار."""
        """Deselects all valid checkboxes."""
        for cb, var, index in self.checkboxes_data:
            # Check if it's a valid checkbox variable
            if var and isinstance(var, ctk.StringVar):
                var.set(CHECKBOX_OFF)  # Set variable to 'off' state

    def get_selected_items_string(self) -> Optional[str]:
        """
        تُرجع سلسلة نصية تحتوي على فهارس العناصر المحددة (مفصولة بفواصل).
        Returns a comma-separated string of selected item indices (1-based).
        Returns None if no items are selected or the list is empty/invalid.
        """
        selected_indices: List[int] = []
        selected_indices.extend(
            index
            for cb, var, index in self.checkboxes_data
            if (
                isinstance(cb, ctk.CTkCheckBox)
                and var
                and isinstance(var, ctk.StringVar)
                and var.get() == CHECKBOX_ON
            )
            and index > 0
        )
        if selected_indices:
            # Sort indices numerically and join into a comma-separated string
            return ",".join(map(str, sorted(selected_indices)))
        else:
            # Return None if nothing was selected
            return None

    def reset(self) -> None:
        """إعادة تعيين المكون (مسح العناصر وتعطيل الأزرار)."""
        """Resets the component by clearing items and disabling controls."""
        self.clear_items()
        # self.disable() is called within clear_items

    def enable(self) -> None:
        """تمكين أزرار التحكم ومربعات الاختيار."""
        """Enables the control buttons and all checkboxes."""
        self._set_widgets_state("normal")

    def disable(self) -> None:
        """تعطيل أزرار التحكم ومربعات الاختيار."""
        """Disables the control buttons and all checkboxes."""
        self._set_widgets_state("disabled")

    def _set_widgets_state(self, state: str) -> None:
        """Helper method to set the state ('normal' or 'disabled') for controls and checkboxes."""
        # Configure button states
        self.select_all_button.configure(state=state)
        self.deselect_all_button.configure(state=state)
        # Configure state for all checkbox widgets
        for cb, var, index in self.checkboxes_data:
            if cb and isinstance(
                cb, ctk.CTkCheckBox
            ):  # Only configure actual checkboxes
                try:
                    cb.configure(state=state)
                except Exception as e:
                    print(f"Error configuring checkbox state: {e}")
