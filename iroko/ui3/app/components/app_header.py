# app/components/app_header.py
import flet as ft

def AppHeader(page: ft.Page, title: str) -> ft.AppBar:
    """
    Creates a reusable AppBar for the application.
    It includes a drawer button, back button (if applicable),
    an app icon, and the current page title.
    """
    def handle_back(e):
        page.go("/") # Always go to home on back from a main section

    return ft.AppBar(
        leading=ft.IconButton(ft.Icons.MENU, on_click=lambda e: page.open(page.drawer)),
        leading_width=40,
        title=ft.Row(
            [
                ft.Icon(ft.Icons.LIBRARY_BOOKS),
                ft.Text(title, size=20, weight=ft.FontWeight.BOLD),
            ]
        ),
        center_title=False,
        bgcolor=ft.Colors.ON_INVERSE_SURFACE,
        actions=[
            ft.IconButton(ft.Icons.ARROW_BACK, on_click=handle_back) 
            if page.route != "/" else ft.Container() # Show back button only if not on home
        ]
    )