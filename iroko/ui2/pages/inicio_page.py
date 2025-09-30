import flet as ft
from iroko.ui2.components import BasePage

class InicioPage(BasePage):
    def __init__(self, page: ft.Page):
        super().__init__(page, "Inicio", "inicio.md")
        
    def get_view(self):
        content = self.load_markdown_content()
        
        return ft.View(
            route="/inicio",
            controls=[
                self.create_app_bar(),
                ft.Container(
                    content=ft.Column([
                        ft.Markdown(
                            content,
                            selectable=True,
                            extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                        ),
                        ft.ElevatedButton(
                            "Ver Lista de Ejemplo",
                            icon=ft.Icons.LIST,
                            on_click=lambda e: self.navigate_to_list(e, "ejemplo")
                        )
                    ], scroll=ft.ScrollMode.ADAPTIVE),
                    padding=20,
                    expand=True
                )
            ]
        )