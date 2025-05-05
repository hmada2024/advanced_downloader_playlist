# src/ui_components/playlist_selector.py
# -- ملف لمكون الواجهة الخاص بعرض واختيار عناصر قائمة التشغيل --
# Purpose: UI component for displaying and selecting playlist items.

import customtkinter as ctk


class PlaylistSelector(ctk.CTkScrollableFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, label_text="Playlist Items", **kwargs)
        self.checkboxes_data = []

        self.button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.button_frame.pack(fill="x", pady=5, padx=5)

        self.select_all_button = ctk.CTkButton(
            self.button_frame, text="Select All", command=self.select_all
        )
        self.select_all_button.pack(side="left", padx=(0, 5))
        self.deselect_all_button = ctk.CTkButton(
            self.button_frame, text="Deselect All", command=self.deselect_all
        )
        self.deselect_all_button.pack(side="left", padx=5)

        self.disable()

    def clear_items(self):
        """تدمير مربعات الاختيار القديمة ومسح القائمة الداخلية."""
        for cb, var, index in self.checkboxes_data:
            if cb and isinstance(cb, (ctk.CTkCheckBox, ctk.CTkLabel)):
                try:
                    cb.destroy()
                except Exception as e:
                    print(f"Error destroying playlist item widget: {e}")
        self.checkboxes_data = []
        self.disable()

    def populate_items(self, entries):
        """تملأ الإطار بمربعات الاختيار لعناصر القائمة."""
        self.clear_items()

        if not entries:
            no_items_label = ctk.CTkLabel(self, text="No videos found in playlist.")
            no_items_label.pack(pady=5, padx=5, anchor="w")
            self.checkboxes_data.append((no_items_label, None, -1))
            self.disable()
            return

        self.enable()

        print(f"PlaylistSelector: Populating with {len(entries)} items.")
        for index, entry in enumerate(entries):
            if not entry:
                continue

            video_index = entry.get("playlist_index") or (index + 1)
            title = entry.get("title") or f"Video {video_index} (Untitled)"

            max_len = 70
            display_title = f"{title[:max_len]}..." if len(title) > max_len else title

            var = ctk.StringVar(value="on")  # Select all by default
            cb = ctk.CTkCheckBox(
                self,
                text=f"{video_index}. {display_title}",
                variable=var,
                onvalue="on",
                offvalue="off",
            )
            cb.pack(anchor="w", padx=10, pady=(2, 2), fill="x")
            self.checkboxes_data.append((cb, var, video_index))
        print("PlaylistSelector: Finished packing checkboxes.")

    def select_all(self):
        """تحديد جميع مربعات الاختيار."""
        for cb, var, index in self.checkboxes_data:
            if var and isinstance(var, ctk.StringVar):
                var.set("on")

    def deselect_all(self):
        """إلغاء تحديد جميع مربعات الاختيار."""
        for cb, var, index in self.checkboxes_data:
            if var and isinstance(var, ctk.StringVar):
                var.set("off")

    def get_selected_items_string(self):
        """
        تُرجع سلسلة نصية تحتوي على فهارس العناصر المحددة (مفصولة بفواصل).
        Returns a comma-separated string of selected item indices. Returns None if none selected.
        """
        if selected_indices := [
            index
            for cb, var, index in self.checkboxes_data
            if cb and isinstance(cb, ctk.CTkCheckBox) and var and var.get() == "on"
        ]:
            return ",".join(map(str, sorted(selected_indices)))
        else:
            return None

    def reset(self):
        """إعادة تعيين المكون (مسح العناصر وتعطيل الأزرار)."""
        self.clear_items()

    def enable(self):
        """تمكين أزرار التحكم ومربعات الاختيار."""
        self._set_widgets_state("normal")

    def disable(self):
        """تعطيل أزرار التحكم ومربعات الاختيار."""
        self._set_widgets_state("disabled")

    def _set_widgets_state(self, state):
        """Helper method to set state for controls and checkboxes."""
        self.select_all_button.configure(state=state)
        self.deselect_all_button.configure(state=state)
        for cb, var, index in self.checkboxes_data:
            if cb and isinstance(cb, ctk.CTkCheckBox):
                cb.configure(state=state)
