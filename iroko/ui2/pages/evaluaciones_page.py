import flet as ft
from iroko.ui2.components import BasePage

class EvaluacionesPage(BasePage):
    def __init__(self, page: ft.Page):
        super().__init__(page, "Evaluaciones", "evaluaciones.md")
        
    def get_view(self):
        content = self.load_markdown_content()
        
        return ft.View(
            route="/evaluaciones",
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
                                "Ver Evaluaciones de Proyectos",
                                icon=ft.Icons.ASSESSMENT,
                                on_click=lambda e: self.navigate_to_list(e, "evaluaciones_proyectos")
                            ),
                            ft.ElevatedButton(
                                "Ver Evaluaciones de Revistas",
                                icon=ft.Icons.STAR,
                                on_click=lambda e: self.navigate_to_list(e, "evaluaciones_revistas")
                            ),
                        ])
                    ], scroll=ft.ScrollMode.ADAPTIVE),
                    padding=20,
                    expand=True
                )
            ]
        )