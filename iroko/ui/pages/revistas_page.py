import flet as ft

class RevistasPage(ft.Column):
    def __init__(self):
        super().__init__()
        self.expand = True
        self.scroll = ft.ScrollMode.AUTO
        self.controls = [
            ft.Text("Revistas MES", size=24, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            self.build_content(),
        ]
        
    def build_content(self):
        return ft.Column([
            ft.Text("Revistas del Ministerio de Educación Superior", size=18),
            ft.Text("Lista de revistas académicas indexadas."),
            ft.Row([
                ft.ElevatedButton("Todas las revistas", icon=ft.Icons.LIST),
                ft.ElevatedButton("Por categoría", icon=ft.Icons.CATEGORY),
                ft.ElevatedButton("Buscar", icon=ft.Icons.SEARCH),
            ], spacing=10),
            ft.GridView(
                expand=True,
                max_extent=150,
                child_aspect_ratio=0.8,
                controls=[
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.Icons.BOOK, size=40),
                            ft.Text("Revista Cubana")
                        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=10,
                        bgcolor=ft.Colors.BLUE_50,
                        border_radius=10,
                    ),
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.Icons.BOOK, size=40),
                            ft.Text("Ciencias Médicas")
                        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=10,
                        bgcolor=ft.Colors.GREEN_50,
                        border_radius=10,
                    ),
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.Icons.BOOK, size=40),
                            ft.Text("Tecnología")
                        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=10,
                        bgcolor=ft.Colors.ORANGE_50,
                        border_radius=10,
                    ),
                ]
            )
        ], spacing=20)