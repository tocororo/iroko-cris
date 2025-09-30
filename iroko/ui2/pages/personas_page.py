import flet as ft
from iroko.ui2.components import BasePage

class PersonasPage(BasePage):
    def __init__(self, page: ft.Page):
        super().__init__(page, "Personas", "personas.md")
        
    def get_view(self):
        content = self.load_markdown_content()
        
        return ft.View(
            route="/personas",
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
                                "Ver Investigadores",
                                icon=ft.Icons.SCIENCE,
                                on_click=lambda e: self.navigate_to_list(e, "investigadores")
                            ),
                            ft.ElevatedButton(
                                "Ver Autores",
                                icon=ft.Icons.PERSON,
                                on_click=lambda e: self.navigate_to_list(e, "autores")
                            ),
                        ])
                    ], scroll=ft.ScrollMode.ADAPTIVE),
                    padding=20,
                    expand=True
                )
            ]
        )