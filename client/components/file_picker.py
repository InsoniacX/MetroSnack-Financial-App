import flet as ft


def get_file_picker(page, key):
    """Kembalikan FilePicker bernama yang sudah terdaftar pada halaman."""
    picker_key = f"metrosnack:{key}"

    for service in page.services:
        if (
            isinstance(service, ft.FilePicker)
            and service.data == picker_key
        ):
            return service

    picker = ft.FilePicker(data=picker_key)
    page.services.append(picker)
    return picker
