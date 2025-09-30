import flet as ft
from iroko.ui2.components import BasePage

class ProyectosPage(BasePage):
    def __init__(self, page: ft.Page):
        super().__init__(page, "Proyectos", "proyectos.md")
        
    def get_view(self):
        content = self.load_markdown_content()
        
        return ft.View(
            route="/proyectos",
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
                                "Ver Proyectos Activos",
                                icon=ft.Icons.PLAY_ARROW,
                                on_click=lambda e: self.navigate_to_list(e, "proyectos_activos")
                            ),
                            ft.ElevatedButton(
                                "Ver Proyectos Finalizados",
                                icon=ft.Icons.CHECK_CIRCLE,
                                on_click=lambda e: self.navigate_to_list(e, "proyectos_finalizados")
                            ),
                        ])
                    ], scroll=ft.ScrollMode.ADAPTIVE),
                    padding=20,
                    expand=True
                )
            ]
        )