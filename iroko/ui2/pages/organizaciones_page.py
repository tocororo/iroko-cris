import flet as ft
from iroko.ui2.components import BasePage

class OrganizacionesPage(BasePage):
    def __init__(self, page: ft.Page):
        super().__init__(page, "Organizaciones", "organizaciones.md")
        
    def get_view(self):
        content = self.load_markdown_content()
        
        return ft.View(
            route="/organizaciones",
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
                                "Ver Instituciones",
                                icon=ft.Icons.ACCOUNT_BALANCE,
                                on_click=lambda e: self.navigate_to_list(e, "instituciones")
                            ),
                            ft.ElevatedButton(
                                "Ver Centros de Investigación",
                                icon=ft.Icons.BUSINESS_CENTER,
                                on_click=lambda e: self.navigate_to_list(e, "centros")
                            ),
                        ])
                    ], scroll=ft.ScrollMode.ADAPTIVE),
                    padding=20,
                    expand=True
                )
            ]
        )