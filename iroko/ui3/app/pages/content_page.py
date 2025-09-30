# app/pages/content_page.py
import flet as ft
from app.utils import read_markdown_file

def ContentPage(page: ft.Page, data: dict, list_route: str) -> list[ft.Control]:
    """
    Returns a generic list of controls for a content page,
    loading markdown from the file specified in the data dictionary.
    """
    markdown_filename = data.get("markdown_file", "not_found.md")
    content = read_markdown_file(markdown_filename)

    return [
        ft.Markdown(content),
        ft.ElevatedButton(
            f"Ver lista de {data.get('title', 'elementos')}",
            icon=ft.Icons.LIST_ALT,
            on_click=lambda _: page.go(list_route)
        )
    ]