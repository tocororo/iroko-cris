import flet as ft
from iroko.ui2.components import BasePage

class CatalogoPage(BasePage):
    def __init__(self, page: ft.Page):
        super().__init__(page, "Catálogo", "catalogo.md")
        
    def get_view(self):
        content = self.load_markdown_content()
        
        return ft.View(
            route="/catalogo",
            controls=[
                self.create_app_bar(),
                ft.Container(
                    content=ft.Column([
                        ft.Markdown(
                            content,
                            selectable=True,
                            extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                        ),
                        ft.Row([
                            ft.ElevatedButton(
                                "Ver Publicaciones",
                                icon=ft.Icons.BOOK,
                                on_click=lambda e: self.navigate_to_list(e, "publicaciones")
                            ),
                            ft.ElevatedButton(
                                "Ver Artículos",
                                icon=ft.Icons.ARTICLE,
                                on_click=lambda e: self.navigate_to_list(e, "articulos")
                            ),
                        ])
                    ], scroll=ft.ScrollMode.ADAPTIVE),
                    padding=20,
                    expand=True
                )
            ]
        )