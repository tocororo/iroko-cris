# app/router.py
import flet as ft
from app.components.app_header import AppHeader
from app.components.drawer import AppDrawer
from app.components.list_records import ListRecords
from app.components.view_record import ViewRecord
from app.pages.home import HomePage
from app.pages.content_page import ContentPage
from app.data import MOCK_DATA

class AppRouter:
    def __init__(self, page: ft.Page):
        self.page = page
        self.routes = {
            "/": self.get_home_view,
            "/revistas_mes": self.get_content_view,
            "/catalogo": self.get_content_view,
            "/personas": self.get_content_view,
            "/organizaciones": self.get_content_view,
            "/proyectos": self.get_content_view,
            "/resultados": self.get_content_view,
            "/evaluaciones": self.get_content_view,
        }
        self.page.on_route_change = self.handle_route_change
        self.page.on_view_pop = self.handle_view_pop
        self.page.drawer = AppDrawer(self.page)

    def handle_route_change(self, route):
        self.page.views.clear()
        
        # Split route to handle list and view pages
        # Example: /revistas_mes/list/1 -> ['revistas_mes', 'list', '1']
        path_parts = self.page.route.strip("/").split("/")
        
        # Base View (Home or Content Page)
        base_route = f"/{path_parts[0]}" if path_parts[0] else "/"
        view_builder = self.routes.get(base_route)
        if view_builder:
            self.page.views.append(view_builder(base_route))
        else: # Fallback to home if route is unknown
             self.page.views.append(self.get_home_view("/"))

        # List View
        if len(path_parts) > 1 and path_parts[1] == "list":
            self.page.views.append(self.get_list_view(base_route))

        # Record Detail View
        if len(path_parts) > 2:
            try:
                record_id = int(path_parts[2])
                self.page.views.append(self.get_record_view(base_route, record_id))
            except (ValueError, IndexError):
                pass # Ignore if record_id is not a valid integer
        
        self.page.update()

    def handle_view_pop(self, view):
        self.page.views.pop()
        top_view = self.page.views[-1]
        self.page.go(top_view.route)

    def get_home_view(self, route: str) -> ft.View:
        return ft.View(
            route=route,
            controls=HomePage(),
            appbar=AppHeader(self.page, "Inicio"),
            padding=20,
        )

    def get_content_view(self, route: str) -> ft.View:
        data_key = route.strip("/")
        data = MOCK_DATA.get(data_key, {})
        return ft.View(
            route=route,
            controls=ContentPage(self.page, data, f"{route}/list"),
            appbar=AppHeader(self.page, data.get("title", "Página")),
            padding=20,
        )

    def get_list_view(self, base_route: str) -> ft.View:
        data_key = base_route.strip("/")
        data = MOCK_DATA.get(data_key, {})
        records = data.get("records", [])
        title = data.get("title", "Lista")

        def go_to_record(record_id):
            self.page.go(f"{base_route}/list/{record_id}")
            
        return ft.View(
            route=f"{base_route}/list",
            controls=[
                ft.Text(f"Listado de {title}", size=24, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ListRecords(records, on_record_click=go_to_record)
            ],
            appbar=AppHeader(self.page, f"Lista: {title}"),
            padding=20,
        )

    def get_record_view(self, base_route: str, record_id: int) -> ft.View:
        data_key = base_route.strip("/")
        records = MOCK_DATA.get(data_key, {}).get("records", [])
        
        # Find the specific record by its ID
        record = next((r for r in records if r.get("id") == record_id), None)
        title = record.get("title", "Detalle") if record else "No Encontrado"

        return ft.View(
            route=f"{base_route}/list/{record_id}",
            controls=[
                ft.Text(f"Detalle:", size=24, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ViewRecord(record)
            ],
            appbar=AppHeader(self.page, title),
            padding=20,
        )