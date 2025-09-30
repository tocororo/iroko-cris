import flet as ft

class HomePage:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.drawer = self.create_drawer()
        
    def create_drawer(self):
        """Create the navigation drawer"""
        return ft.NavigationDrawer(
            controls=[
                ft.Container(height=12),
                ft.NavigationDrawerDestination(
                    label="Inicio",
                    icon=ft.Icons.HOME,
                    selected_icon=ft.Icons.HOME_OUTLINED,
                ),
                ft.NavigationDrawerDestination(
                    label="Revistas MES",
                    icon=ft.Icons.BOOK,
                    selected_icon=ft.Icons.BOOK_OUTLINED,
                ),
                ft.NavigationDrawerDestination(
                    label="Catalogo",
                    icon=ft.Icons.LIST_ALT,
                    selected_icon=ft.Icons.LIST_ALT_OUTLINED,
                ),
                ft.NavigationDrawerDestination(
                    label="Personas",
                    icon=ft.Icons.PEOPLE,
                    selected_icon=ft.Icons.PEOPLE_OUTLINED,
                ),
                ft.NavigationDrawerDestination(
                    label="Organizaciones",
                    icon=ft.Icons.BUSINESS,
                    selected_icon=ft.Icons.BUSINESS_OUTLINED,
                ),
                ft.NavigationDrawerDestination(
                    label="Proyectos",
                    icon=ft.Icons.WORK,
                    selected_icon=ft.Icons.WORK_OUTLINED,
                ),
                ft.NavigationDrawerDestination(
                    label="Resultados",
                    icon=ft.Icons.ASSESSMENT,
                    selected_icon=ft.Icons.ASSESSMENT_OUTLINED,
                ),
                ft.NavigationDrawerDestination(
                    label="Evaluaciones",
                    icon=ft.Icons.GRADE,
                    selected_icon=ft.Icons.GRADE_OUTLINED,
                ),
            ],
            on_change=self.navigate_to_page
        )
    
    def navigate_to_page(self, e):
        """Navigate to selected page"""
        route_map = {
            0: "/inicio",
            1: "/revistas-mes", 
            2: "/catalogo",
            3: "/personas",
            4: "/organizaciones",
            5: "/proyectos",
            6: "/resultados",
            7: "/evaluaciones"
        }
        
        if e.control.selected_index in route_map:
            self.page.go(route_map[e.control.selected_index])
    
    def get_view(self):
        """Return the view for this page"""
        return ft.View(
            route="/",
            controls=[
                self.create_app_bar("Página Principal"),
                ft.Container(
                    content=ft.Column([
                        ft.Text("Bienvenido al Sistema MES", 
                               size=24, weight=ft.FontWeight.BOLD),
                        ft.Text("Seleccione una opción del menú para comenzar",
                               size=16),
                    ], alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    expand=True,
                    alignment=ft.alignment.center
                )
            ],
            drawer=self.drawer
        )
    
    def create_app_bar(self, title):
        """Create consistent app bar across pages"""
        return ft.AppBar(
            leading=ft.IconButton(
                icon=ft.Icons.MENU,
                on_click=lambda e: self.drawer.open,
            ),
            leading_width=40,
            title=ft.Row([
                ft.Icon(name=ft.Icons.APPS, color=ft.Colors.BLUE),
                ft.Text(title, size=20, weight=ft.FontWeight.BOLD),
            ]),
            actions=[
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    on_click=lambda e: self.page.views.pop() if len(self.page.views) > 1 else None,
                    tooltip="Atrás"
                ),
            ],
            bgcolor=ft.Colors.ON_SURFACE_VARIANT,
        )