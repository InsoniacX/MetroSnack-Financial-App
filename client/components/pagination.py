from math import ceil

import flet as ft


DEFAULT_PAGE_SIZE = 10


class ClientPagination:
    """Pagination ringan untuk data yang sudah dimuat di sisi client."""

    def __init__(self, on_page_change, page_size=DEFAULT_PAGE_SIZE):
        if page_size <= 0:
            raise ValueError("page_size harus lebih besar dari nol")

        self.page_size = page_size
        self.current_page = 1
        self.total_items = 0
        self.total_pages = 1
        self._on_page_change = on_page_change

        self.range_text = ft.Text(size=12, color=ft.Colors.GREY_600)
        self.page_text = ft.Text(
            "Halaman 1 dari 1",
            size=12,
            weight=ft.FontWeight.W_500,
        )
        self.previous_button = ft.IconButton(
            ft.Icons.CHEVRON_LEFT,
            tooltip="Halaman sebelumnya",
            on_click=self._previous,
        )
        self.next_button = ft.IconButton(
            ft.Icons.CHEVRON_RIGHT,
            tooltip="Halaman berikutnya",
            on_click=self._next,
        )

        self.control = ft.Container(
            content=ft.Row(
                [
                    self.range_text,
                    ft.Row(
                        [
                            self.previous_button,
                            self.page_text,
                            self.next_button,
                        ],
                        spacing=4,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                wrap=True,
                spacing=8,
                run_spacing=4,
            ),
            padding=ft.Padding.only(top=4),
            visible=False,
        )

        self._sync_controls()

    def reset(self):
        self.current_page = 1

    def paginate(self, items):
        """Kembalikan potongan halaman dan sinkronkan kontrol navigasi."""
        self.total_items = len(items)
        self.total_pages = max(
            1,
            ceil(self.total_items / self.page_size),
        )
        self.current_page = min(
            max(1, self.current_page),
            self.total_pages,
        )

        start_index = (self.current_page - 1) * self.page_size
        end_index = min(
            start_index + self.page_size,
            self.total_items,
        )

        self._sync_controls(start_index, end_index)
        return items[start_index:end_index]

    def _sync_controls(self, start_index=0, end_index=0):
        if self.total_items:
            self.range_text.value = (
                f"{start_index + 1}-{end_index} "
                f"dari {self.total_items} data"
            )
        else:
            self.range_text.value = "0 data"

        self.page_text.value = (
            f"Halaman {self.current_page} dari {self.total_pages}"
        )
        self.previous_button.disabled = self.current_page <= 1
        self.next_button.disabled = self.current_page >= self.total_pages
        self.control.visible = self.total_items > self.page_size

    def _previous(self, e=None):
        del e
        if self.current_page <= 1:
            return

        self.current_page -= 1
        self._on_page_change()

    def _next(self, e=None):
        del e
        if self.current_page >= self.total_pages:
            return

        self.current_page += 1
        self._on_page_change()
