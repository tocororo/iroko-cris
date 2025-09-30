from re import S
import flet as ft
from pages.home_page import HomePage
from pages.publicaciones_page import PublicacionesPage
from pages.revistas_page import RevistasPage
from pages.personas_page import PersonasPage
from pages.organizaciones_page import OrganizacionesPage
from pages.resultados_page import ResultadosPage
from pages.evaluaciones_page import EvaluacionesPage

from dotenv import load_dotenv
import os

load_dotenv()

class MainApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Sceiba"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.padding = 0
        self.page.expand = True
        
        endpoint = os.getenv("FASTAPI_ENDPOINT")
        self.api_query_enpoint = f"{endpoint}/v1/query"

        # Create pages
        self.pages = {
            "Inicio": HomePage(api_query_enpoint=self.api_query_enpoint),
            "Revistas MES": RevistasPage(),
            "Personas": PersonasPage(api_query_enpoint=self.api_query_enpoint),
            "Organizaciones": OrganizacionesPage(api_query_enpoint=self.api_query_enpoint),
            "Publicaciones": PublicacionesPage(api_query_enpoint=self.api_query_enpoint),
            "Resultados de Investigacion": ResultadosPage(api_query_enpoint=self.api_query_enpoint),
            "Evaluaciones": EvaluacionesPage(),
        }
        
        # Set up UI
        self.setup_ui()
        
    def setup_ui(self):
        # Navigation Drawer with custom icons
        self.nav_drawer = ft.NavigationDrawer(
            on_change=self.on_navigation_change,
            controls=[
                ft.Container(height=12),
                ft.NavigationDrawerDestination(
                    label="Inicio",
                    icon=ft.Image(src="sceiba.svg", width=24, height=24),
                    selected_icon=ft.Image(src="sceiba.svg", width=24, height=24, color=ft.Colors.GREEN),
                ),
                ft.Divider(thickness=1),
                ft.NavigationDrawerDestination(
                    label="Revistas MES",
                    icon=ft.Image(src="revistasmes.png", width=24, height=24),
                    selected_icon=ft.Image(src="revistasmes.png", width=24, height=24, color=ft.Colors.GREEN),
                ),
                ft.NavigationDrawerDestination(
                    label="Personas",
                    icon=ft.Image(src="persons.svg", width=24, height=24),
                    selected_icon=ft.Image(src="persons.svg", width=24, height=24, color=ft.Colors.GREEN),
                ),
                ft.NavigationDrawerDestination(
                    label="Organizaciones",
                    icon=ft.Image(src="organizaciones.svg", width=24, height=24),
                    selected_icon=ft.Image(src="organizaciones.svg", width=24, height=24, color=ft.Colors.GREEN),
                ),
                ft.NavigationDrawerDestination(
                    label="Publicaciones",
                    icon=ft.Image(src="publication.svg", width=24, height=24),
                    selected_icon=ft.Image(src="publication.svg", width=24, height=24, color=ft.Colors.GREEN),
                ),
                ft.NavigationDrawerDestination(
                    label="Resultados de Investigación",
                    icon=ft.Image(src="publishing.svg", width=24, height=24),
                    selected_icon=ft.Image(src="publishing.svg", width=24, height=24, color=ft.Colors.GREEN),
                ),
                ft.NavigationDrawerDestination(
                    label="Evaluaciones",
                    icon=ft.Image(src="vocabs.svg", width=24, height=24),
                    selected_icon=ft.Image(src="vocabs.svg", width=24, height=24, color=ft.Colors.GREEN),
                ),
            ],
        )

        # AppBar with menu button to open drawer
        appbar = ft.AppBar(
            leading=ft.IconButton(
                icon=ft.Icons.MENU,
                on_click=lambda e: self.page.open(self.nav_drawer),
            ),
            title=ft.Text("Sceiba"),
            # bgcolor=ft.Colors.GREEN,
        )

        # Content area
        self.content_area = ft.Container(
            content=list(self.pages.values())[0],
            padding=20,
            expand=True,
        )
        
        # Set page appbar and drawer
        self.page.appbar = appbar
        self.page.drawer = self.nav_drawer

        # Set up the main layout (only content area now)
        self.page.add(
            self.content_area
        )
    
    def on_navigation_change(self, e):
        selected_index = e.control.selected_index
        page_name = list(self.pages.keys())[selected_index]
        self.content_area.content = self.pages[page_name]
        self.content_area.update()
        self.page.close(self.nav_drawer)  # Close drawer after selection

# Run the app
def main(page: ft.Page):
    app = MainApp(page)

if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets")