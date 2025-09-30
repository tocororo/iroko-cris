import flet as ft
from iroko.ui2.components import BasePage

class ResultadosPage(BasePage):
    def __init__(self, page: ft.Page):
        super().__init__(page, "Resultados", "resultados.md")
        
    def get_view(self):
        content = self.load_markdown_content()
        
        return ft.View(
            route="/resultados",
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
                                on_click=lambda e: self.navigate_to_list(e, "resultados_publicaciones")
                            ),
                            ft.ElevatedButton(
                                "Ver Patentes",
                                icon=ft.Icons.PATENT,
                                on_click=lambda e: self.navigate_to_list(e, "patentes")
                            ),
                            ft.ElevatedButton(
                                "Ver Productos",
                                icon=ft.Icons.INVENTORY,
                                on_click=lambda e: self.navigate_to_list(e, "productos")
                            ),
                        ])
                    ], scroll=ft.ScrollMode.ADAPTIVE),
                    padding=20,
                    expand=True
                )
            ]
        )