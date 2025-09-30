# main-app.py
import flet as ft
from app.router import AppRouter

def main(page: ft.Page):
    page.title = "Mi Aplicación Flet"
    page.window_width = 450
    page.window_height = 750
    page.theme_mode = ft.ThemeMode.LIGHT

    # Initialize the router
    router = AppRouter(page)
    
    # Start at the home page
    page.go("/")

if __name__ == "__main__":
    ft.app(target=main, assets_dir='assets')