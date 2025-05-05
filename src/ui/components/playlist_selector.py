# src/ui/components/playlist_selector.py
# -- ملف لمكون الواجهة الخاص بعرض واختيار عناصر قائمة التشغيل --
# Purpose: UI component for displaying and selecting playlist items.

import customtkinter as ctk
from typing import List, Dict, Any, Optional, Tuple, Union

# --- Constants ---
FRAME_LABEL = "Playlist Items"
BTN_SELECT_ALL = "Select All"
BTN_DESELECT_ALL = "Deselect All"
MSG_NO_VIDEOS = "No videos found in playlist."
CHECKBOX_ON = "on"
CHECKBOX_OFF = "off"
TITLE_MAX_LEN = 70  # Max length for displaying video titles

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
        self.checkboxes_data: List[PlaylistItemData] = []

        self.button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.button_frame.pack(fill="x", pady=5, padx=5)

        self.select_all_button = ctk.CTkButton(
            self.button_frame, text=BTN_SELECT_ALL, command=self.select_all
        )
        self.select_all_button.pack(side="left", padx=(0, 5))

        self.deselect_all_button = ctk.CTkButton(
            self.button_frame, text=BTN_DESELECT_ALL, command=self.deselect_all
        )
        self.deselect_all_button.pack(side="left", padx=5)

        self.disable()  # Start disabled

    def clear_items(self) -> None:
        """تدمير مربعات الاختيار القديمة ومسح القائمة الداخلية."""
        for widget, var, index in self.checkboxes_data:
            if widget:
                try:
                    widget.destroy()
                except Exception as e:
                    print(f"Error destroying playlist item widget: {e}")
        self.checkboxes_data = []
        self.disable()

    def populate_items(self, entries: List[Optional[Dict[str, Any]]]) -> None:
        """تملأ الإطار بمربعات الاختيار لعناصر القائمة."""
        self.clear_items()

        if not entries:
            no_items_label = ctk.CTkLabel(self, text=MSG_NO_VIDEOS)
            no_items_label.pack(pady=10, padx=10, anchor="w")
            self.checkboxes_data.append((no_items_label, None, -1))
            self.disable()
            return

        self.enable()  # Enable controls if we have entries

        print(f"PlaylistSelector: Populating with {len(entries)} items.")
        for index, entry in enumerate(entries):
            if not entry or not isinstance(entry, dict):
                print(
                    f"PlaylistSelector: Skipping invalid entry at index {index}: {entry}"
                )
                continue

            video_index: int = entry.get("playlist_index") or (index + 1)
            title: str = entry.get("title") or f"Video {video_index} (Untitled)"
            display_title: str = (
                f"{title[:TITLE_MAX_LEN]}..." if len(title) > TITLE_MAX_LEN else title
            )

            var = ctk.StringVar(value=CHECKBOX_ON)
            cb = ctk.CTkCheckBox(
                self,
                text=f"{video_index}. {display_title}",
                variable=var,
                onvalue=CHECKBOX_ON,
                offvalue=CHECKBOX_OFF,
            )
            cb.pack(anchor="w", padx=10, pady=(2, 2), fill="x")
            self.checkboxes_data.append((cb, var, video_index))

        print("PlaylistSelector: Finished packing checkboxes.")

    def select_all(self) -> None:
        """تحديد جميع مربعات الاختيار."""
        for cb, var, index in self.checkboxes_data:
            if var and isinstance(var, ctk.StringVar):
                var.set(CHECKBOX_ON)

    def deselect_all(self) -> None:
        """إلغاء تحديد جميع مربعات الاختيار."""
        for cb, var, index in self.checkboxes_data:
            if var and isinstance(var, ctk.StringVar):
                var.set(CHECKBOX_OFF)

    def get_selected_items_string(self) -> Optional[str]:
        """تُرجع سلسلة نصية بفهارس العناصر المحددة (مفصولة بفواصل)."""
        selected_indices = [
            index
            for cb, var, index in self.checkboxes_data
            if isinstance(cb, ctk.CTkCheckBox)
            and var
            and var.get() == CHECKBOX_ON
            and index > 0
        ]
        return (
            ",".join(map(str, sorted(selected_indices))) if selected_indices else None
        )

    def reset(self) -> None:
        """إعادة تعيين المكون (مسح العناصر وتعطيل الأزرار)."""
        self.clear_items()

    def enable(self) -> None:
        """تمكين أزرار التحكم ومربعات الاختيار."""
        self._set_widgets_state("normal")

    def disable(self) -> None:
        """تعطيل أزرار التحكم ومربعات الاختيار."""
        self._set_widgets_state("disabled")

    def _set_widgets_state(self, state: str) -> None:
        """Helper method to set state for controls and checkboxes."""
        try:  # Wrap in try-except for safety
            self.select_all_button.configure(state=state)
            self.deselect_all_button.configure(state=state)
            for cb, var, index in self.checkboxes_data:
                if cb and isinstance(cb, ctk.CTkCheckBox):
                    cb.configure(state=state)
        except Exception as e:
            print(f"Error configuring playlist selector state: {e}")
