# src/ui/components/playlist_selector.py
# -- ملف لمكون الواجهة الخاص بعرض واختيار عناصر قائمة التشغيل --
# -- Modified to display thumbnails and fix wraplength issue --

import customtkinter as ctk
from typing import List, Dict, Any, Optional, Tuple, Union

# Import image loading utility
# <<<< تأكد من صحة هذا المسار بناءً على مكان utils.py بالنسبة لـ playlist_selector.py >>>>
# إذا كان utils.py في src/logic/utils.py و playlist_selector.py في src/ui/components/playlist_selector.py
# فإن المسار الصحيح هو:
from src.logic.utils import ( # استخدم مسارًا مطلقًا من الحزمة الجذرية 'src'
    load_image_from_url_async,
    get_placeholder_ctk_image,
    DEFAULT_THUMBNAIL_SIZE,
)


# --- Constants ---
FRAME_LABEL = "Playlist Items"
BTN_SELECT_ALL = "Select All"
BTN_DESELECT_ALL = "Deselect All"
MSG_NO_VIDEOS = "No videos found in playlist."
CHECKBOX_ON = "on"
CHECKBOX_OFF = "off"
# يمكنك تجربة قيم مختلفة لـ TITLE_MAX_LEN لتناسب الواجهة بشكل أفضل
TITLE_MAX_LEN = 50  # Adjusted for thumbnail space and to avoid needing wraplength
THUMBNAIL_SIZE = DEFAULT_THUMBNAIL_SIZE

PlaylistItemWidgets = Tuple[
    ctk.CTkLabel,
    ctk.CTkCheckBox,
    Optional[ctk.StringVar],
    int,
]


class PlaylistSelector(ctk.CTkScrollableFrame):
    """Scrollable frame for displaying and selecting playlist items with thumbnails."""

    def __init__(self, master: Any, **kwargs: Any):
        super().__init__(master, label_text=FRAME_LABEL, **kwargs)

        self.item_widgets_data: List[
            Union[PlaylistItemWidgets, Tuple[ctk.CTkLabel, None, None, int]]
        ] = []

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

        self.placeholder_ctk_image = get_placeholder_ctk_image(THUMBNAIL_SIZE)

        self.disable()

    def clear_items(self) -> None:
        for item_data_tuple in self.item_widgets_data:
            if (
                isinstance(item_data_tuple[0], ctk.CTkLabel)
                and item_data_tuple[1] is None
            ):
                try:
                    item_data_tuple[0].destroy()
                except Exception as e:
                    print(f"Error destroying no_items_label: {e}")
            elif len(item_data_tuple) == 4:
                thumb_label, checkbox, _, _ = item_data_tuple
                if thumb_label:
                    try:
                        thumb_label.destroy()
                    except Exception as e:
                        print(f"Error destroying playlist item thumbnail: {e}")
                if checkbox:
                    try:
                        checkbox.destroy()
                    except Exception as e:
                        print(f"Error destroying playlist item checkbox: {e}")

        self.item_widgets_data = []
        self.disable()

    def populate_items(self, entries: List[Optional[Dict[str, Any]]]) -> None:
        self.clear_items()

        if not entries:
            no_items_label = ctk.CTkLabel(self, text=MSG_NO_VIDEOS, text_color="gray")
            no_items_label.pack(pady=10, padx=10, anchor="w")
            self.item_widgets_data.append((no_items_label, None, None, -1))
            self.disable()
            return

        self.enable()
        # print(f"PlaylistSelector: Populating with {len(entries)} items.") # يمكن إلغاء هذا للتقليل من المخرجات

        for index, entry in enumerate(entries):
            if not entry or not isinstance(entry, dict):
                # print(f"PlaylistSelector: Skipping invalid entry at index {index}: {entry}")
                continue

            video_index: int = entry.get("playlist_index") or (index + 1)
            title: str = entry.get("title") or f"Video {video_index} (Untitled)"
            display_title: str = (
                f"{title[:TITLE_MAX_LEN]}..." if len(title) > TITLE_MAX_LEN else title
            )
            thumbnail_url: Optional[str] = entry.get("thumbnail_url")

            item_frame = ctk.CTkFrame(self, fg_color="transparent")
            item_frame.pack(anchor="w", padx=5, pady=(3, 3), fill="x") # جعل الإطار يملأ العرض

            thumbnail_label = ctk.CTkLabel(
                item_frame,
                text="",
                image=self.placeholder_ctk_image,
                width=THUMBNAIL_SIZE[0],
                height=THUMBNAIL_SIZE[1],
            )
            thumbnail_label.pack(side="left", padx=(0, 10))

            var = ctk.StringVar(value=CHECKBOX_ON)
            # --- !!! إزالة wraplength من CTkCheckBox !!! ---
            cb = ctk.CTkCheckBox(
                item_frame,
                text=f"{video_index}. {display_title}",
                variable=var,
                onvalue=CHECKBOX_ON,
                offvalue=CHECKBOX_OFF,
                # anchor="w" # CTkCheckbox يتم محاذاته لليسار افتراضيًا داخل pack
            )
            # اجعل مربع الاختيار يتمدد ليملأ المساحة المتبقية
            cb.pack(side="left", anchor="w", expand=True, fill="x", padx=(0,5))


            self.item_widgets_data.append((thumbnail_label, cb, var, video_index))

            if thumbnail_url:
                def _update_thumbnail_callback(
                    loaded_image: Optional[Any], label_to_update=thumbnail_label
                ):
                    if label_to_update.winfo_exists() and loaded_image:
                        label_to_update.configure(image=loaded_image)

                # استخدم self (الـ PlaylistSelector) كـ target_widget
                # لأنه موجود دائمًا عندما تكون هذه الدالة تُستدعى
                load_image_from_url_async(
                    thumbnail_url,
                    _update_thumbnail_callback,
                    target_widget=self, # استخدام self هنا ( PlaylistSelector )
                    target_size=THUMBNAIL_SIZE,
                )
        
        # self.update_idletasks() # قد لا يكون ضروريًا هنا دائمًا، ولكن لا يضر
        # print("PlaylistSelector: Finished packing items with thumbnails.") # يمكن إلغاؤه

    def select_all(self) -> None:
        for _thumb, _cb, var, _index in self.item_widgets_data:
            if var and isinstance(var, ctk.StringVar):
                var.set(CHECKBOX_ON)

    def deselect_all(self) -> None:
        for _thumb, _cb, var, _index in self.item_widgets_data:
            if var and isinstance(var, ctk.StringVar):
                var.set(CHECKBOX_OFF)

    def get_selected_items_string(self) -> Optional[str]:
        selected_indices = []
        selected_indices.extend(
            index_val
            for _thumb, cb, var, index_val in self.item_widgets_data
            if (
                isinstance(cb, ctk.CTkCheckBox)
                and var
                and var.get() == CHECKBOX_ON
                and index_val > 0
            )
        )
        return (
            ",".join(map(str, sorted(selected_indices))) if selected_indices else None
        )

    def reset(self) -> None:
        self.clear_items()

    def enable(self) -> None:
        self._set_widgets_state("normal")

    def disable(self) -> None:
        self._set_widgets_state("disabled")

    def _set_widgets_state(self, state: str) -> None:
        try:
            self.select_all_button.configure(state=state)
            self.deselect_all_button.configure(state=state)
            for _thumb, cb, _var, _index in self.item_widgets_data:
                if cb and isinstance(cb, ctk.CTkCheckBox) and cb.winfo_exists():
                    cb.configure(state=state)
        except Exception as e:
            print(f"Error configuring playlist selector state: {e}")