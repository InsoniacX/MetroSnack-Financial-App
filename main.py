import flet as ft

def main(page: ft.page):
    page.title = "MetroSnack"
    page.add(ft.Text("Halo, Flet is Successfully Running"))

ft.app(target=main)