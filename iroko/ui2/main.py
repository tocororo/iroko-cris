import flet as ft
from pages.home_page import HomePage
from pages.inicio_page import InicioPage
from pages.revistas_mes_page import RevistasMESPage
from pages.catalogo_page import CatalogoPage
from pages.personas_page import PersonasPage
from pages.organizaciones_page import OrganizacionesPage
from pages.proyectos_page import ProyectosPage
from pages.resultados_page import ResultadosPage
from pages.evaluaciones_page import EvaluacionesPage

class MainApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.setup_page()
        self.setup_navigation()
        
    def setup_page(self):
        """Configure the main page settings"""
        self.page.title = "Sistema MES"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.padding = 0
        self.page.spacing = 0
        
    def setup_navigation(self):
        """Setup navigation routes"""
        self.page.on_route_change = self.route_change
        self.page.on_view_pop = self.view_pop
        
        # Initial route
        self.page.go('/')
        
    def route_change(self, route):
        """Handle route changes"""
        self.page.views.clear()
        
        # Home page with drawer
        if self.page.route == "/":
            home_page = HomePage(self.page)
            self.page.views.append(home_page.get_view())
            
        # Other pages
        elif self.page.route == "/inicio":
            inicio_page = InicioPage(self.page)
            self.page.views.append(inicio_page.get_view())
            
        elif self.page.route == "/revistas-mes":
            revistas_page = RevistasMESPage(self.page)
            self.page.views.append(revistas_page.get_view())
            
        elif self.page.route == "/catalogo":
            catalogo_page = CatalogoPage(self.page)
            self.page.views.append(catalogo_page.get_view())
            
        elif self.page.route == "/personas":
            personas_page = PersonasPage(self.page)
            self.page.views.append(personas_page.get_view())
            
        elif self.page.route == "/organizaciones":
            organizaciones_page = OrganizacionesPage(self.page)
            self.page.views.append(organizaciones_page.get_view())
            
        elif self.page.route == "/proyectos":
            proyectos_page = ProyectosPage(self.page)
            self.page.views.append(proyectos_page.get_view())
            
        elif self.page.route == "/resultados":
            resultados_page = ResultadosPage(self.page)
            self.page.views.append(resultados_page.get_view())
            
        elif self.page.route == "/evaluaciones":
            evaluaciones_page = EvaluacionesPage(self.page)
            self.page.views.append(evaluaciones_page.get_view())
            
        elif self.page.route.startswith("/list/"):
            # Handle list pages
            entity_type = self.page.route.split("/")[2]
            from components.list_records import ListRecords
            list_page = ListRecords(self.page, entity_type)
            self.page.views.append(list_page.get_view())
            
        elif self.page.route.startswith("/view/"):
            # Handle view record pages
            parts = self.page.route.split("/")
            entity_type = parts[2]
            record_id = parts[3] if len(parts) > 3 else None
            from components.view_record import ViewRecord
            view_page = ViewRecord(self.page, entity_type, record_id)
            self.page.views.append(view_page.get_view())
            
        self.page.update()
        
    def view_pop(self, view):
        """Handle back navigation"""
        self.page.views.pop()
        top_view = self.page.views[-1]
        self.page.go(top_view.route)

def main(page: ft.Page):
    app = MainApp(page)
