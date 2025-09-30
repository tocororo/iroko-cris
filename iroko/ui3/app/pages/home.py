# app/pages/home.py
import flet as ft
from app.utils import read_markdown_file

def HomePage() -> list[ft.Control]:
    """
    Returns the list of controls for the Home Page,
    loading its content from an external markdown file.
    """
    content = read_markdown_file("markdown/inicio.md")

    return [
        ft.Markdown(
            content,
            selectable=True,
            extension_set="markdown",
            on_tap_link=lambda e: e.page.launch_url(e.data),
        )
    ]