import flet as ft
import os

class BasePage:
    """Base class for all content pages"""
    
    def __init__(self, page: ft.Page, title: str, markdown_file: str):
        self.page = page
        self.title = title
        self.markdown_file = markdown_file
        
    def load_markdown_content(self):
        """Load markdown content from file"""
        try:
            file_path = os.path.join("assets", "markdown", self.markdown_file)
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except FileNotFoundError:
            return f"# {self.title}\n\nContenido no disponible."
    
    def create_app_bar(self):
        """Create consistent app bar"""
        return ft.AppBar(
            leading=ft.IconButton(
                icon=ft.Icons.MENU,
                on_click=self.toggle_drawer,
            ),
            leading_width=40,
            title=ft.Row([
                ft.Icon(name=ft.Icons.APPS, color=ft.Colors.BLUE),
                ft.Text(self.title, size=20, weight=ft.FontWeight.BOLD),
            ]),
            actions=[
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    on_click=self.go_back,
                    tooltip="Atrás"
                ),
            ],
            bgcolor=ft.Colors.ON_SURFACE_VARIANT,
        )
    
    def toggle_drawer(self, e):
        """Toggle navigation drawer"""
        if hasattr(self.page, 'drawer') and self.page.drawer:
            self.page.drawer.open = not self.page.drawer.open
            self.page.update()
    
    def go_back(self, e):
        """Navigate back"""
        if len(self.page.views) > 1:
            self.page.views.pop()
            top_view = self.page.views[-1]
            self.page.go(top_view.route)
    
    def navigate_to_list(self, e, entity_type: str):
        """Navigate to list page for specific entity type"""
        self.page.go(f"/list/{entity_type}")