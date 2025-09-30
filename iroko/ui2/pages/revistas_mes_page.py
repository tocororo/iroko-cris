import flet as ft
from iroko.ui2.components import BasePage

class RevistasMESPage(BasePage):
    def __init__(self, page: ft.Page):
        super().__init__(page, "Revistas MES", "revistas_mes.md")
        
    def get_view(self):
        content = self.load_markdown_content()
        
        return ft.View(
            route="/revistas-mes",
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
                            "Ver Revistas",
                            icon=ft.Icons.LIST_ALT,
                            on_click=lambda e: self.navigate_to_list(e, "revistas")
                        )
                    ], scroll=ft.ScrollMode.ADAPTIVE),
                    padding=20,
                    expand=True
                )
            ]
        )