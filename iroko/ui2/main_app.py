import flet as ft
from iroko.ui2.main import main

if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.FLET_APP, assets_dir="assets")