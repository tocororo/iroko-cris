import flet as ft
from typing import Dict

class MultilingualApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Research Portal"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.vertical_alignment = ft.MainAxisAlignment.CENTER
        self.page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        
        # Available languages
        self.languages = {
            "en": "English",
            "es": "Español",
            "fr": "Français",
            "de": "Deutsch"
        }
        self.current_lang = "en"
        
        # Translations
        self.translations = {
            "en": {
                "home": "Home",
                "sources": "Sources",
                "organizations": "Organizations",
                "projects": "Projects",
                "persons": "Persons",
                "research_outputs": "Research Outputs",
                "welcome": "Welcome to the Research Portal",
                "content_home": "This is the home page of your research portal.",
                "content_sources": "Manage and browse your research sources here.",
                "content_orgs": "View and edit organizations involved in research.",
                "content_projects": "Track and manage research projects.",
                "content_persons": "Search and manage researchers and contributors.",
                "content_outputs": "Browse research papers, articles, and other outputs.",
                "language": "Language"
            },
            "es": {
                "home": "Inicio",
                "sources": "Fuentes",
                "organizations": "Organizaciones",
                "projects": "Proyectos",
                "persons": "Personas",
                "research_outputs": "Resultados de investigación",
                "welcome": "Bienvenido al Portal de Investigación",
                "content_home": "Esta es la página de inicio de su portal de investigación.",
                "content_sources": "Administre y explore sus fuentes de investigación aquí.",
                "content_orgs": "Ver y editar organizaciones involucradas en la investigación.",
                "content_projects": "Seguir y gestionar proyectos de investigación.",
                "content_persons": "Buscar y gestionar investigadores y colaboradores.",
                "content_outputs": "Examinar trabajos de investigación, artículos y otros resultados.",
                "language": "Idioma"
            },
            "fr": {
                "home": "Accueil",
                "sources": "Sources",
                "organizations": "Organisations",
                "projects": "Projets",
                "persons": "Personnes",
                "research_outputs": "Résultats de recherche",
                "welcome": "Bienvenue sur le Portail de Recherche",
                "content_home": "Ceci est la page d'accueil de votre portail de recherche.",
                "content_sources": "Gérez et parcourez vos sources de recherche ici.",
                "content_orgs": "Afficher et modifier les organisations impliquées dans la recherche.",
                "content_projects": "Suivre et gérer les projets de recherche.",
                "content_persons": "Rechercher et gérer les chercheurs et collaborateurs.",
                "content_outputs": "Parcourir les articles de recherche, les documents et autres résultats.",
                "language": "Langue"
            },
            "de": {
                "home": "Startseite",
                "sources": "Quellen",
                "organizations": "Organisationen",
                "projects": "Projekte",
                "persons": "Personen",
                "research_outputs": "Forschungsergebnisse",
                "welcome": "Willkommen im Forschungsportal",
                "content_home": "Dies ist die Startseite Ihres Forschungsportals.",
                "content_sources": "Verwalten und durchsuchen Sie hier Ihre Forschungsquellen.",
                "content_orgs": "Organisationen anzeigen und bearbeiten, die an der Forschung beteiligt sind.",
                "content_projects": "Forschungsprojekte verfolgen und verwalten.",
                "content_persons": "Forscher und Mitarbeiter suchen und verwalten.",
                "content_outputs": "Durchsuchen Sie Forschungsarbeiten, Artikel und andere Ergebnisse.",
                "language": "Sprache"
            }
        }
        
        # UI Elements
        self.title = ft.Text(self.translations[self.current_lang]["welcome"], size=24)
        self.content = ft.Text(self.translations[self.current_lang]["content_home"])
        
        # Navigation Rail (Menu)
        self.nav_rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=100,
            min_extended_width=200,
            leading=ft.FloatingActionButton(
                icon=ft.Icons.LANGUAGE,
                text=self.translations[self.current_lang]["language"],
                on_click=self.open_language_dialog
            ),
            group_alignment=-0.9,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.HOME_OUTLINED,
                    selected_icon=ft.Icons.HOME,
                    label=self.translations[self.current_lang]["home"]
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.SOURCE_OUTLINED,
                    selected_icon=ft.Icons.SOURCE,
                    label=self.translations[self.current_lang]["sources"]
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.ACCOUNT_BALANCE_OUTLINED,
                    selected_icon=ft.Icons.ACCOUNT_BALANCE,
                    label=self.translations[self.current_lang]["organizations"]
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.ASSIGNMENT_OUTLINED,
                    selected_icon=ft.Icons.ASSIGNMENT,
                    label=self.translations[self.current_lang]["projects"]
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.PERSON_OUTLINED,
                    selected_icon=ft.Icons.PERSON,
                    label=self.translations[self.current_lang]["persons"]
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.ARTICLE_OUTLINED,
                    selected_icon=ft.Icons.ARTICLE,
                    label=self.translations[self.current_lang]["research_outputs"]
                ),
            ],
            on_change=self.navigate
        )
        
        # Language dialog
        self.lang_dialog = ft.AlertDialog(
            title=ft.Text("Select Language"),
            content=ft.Column(
                controls=[
                    ft.RadioGroup(
                        content=ft.Column(
                            [ft.Radio(value=code, label=name) 
                             for code, name in self.languages.items()]
                        ),
                        on_change=self.change_language
                    )
                ],
                tight=True
            )
        )
        
        # Main layout
        self.main_view = ft.Row(
            [
                self.nav_rail,
                ft.VerticalDivider(width=1),
                ft.Column(
                    [
                        self.title,
                        self.content
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    expand=True,
                ),
            ],
            expand=True,
        )
        
        self.page.add(self.main_view)
    
    def navigate(self, e):
        index = e.control.selected_index
        if index == 0:  # Home
            self.title.value = self.translations[self.current_lang]["welcome"]
            self.content.value = self.translations[self.current_lang]["content_home"]
        elif index == 1:  # Sources
            self.title.value = self.translations[self.current_lang]["sources"]
            self.content.value = self.translations[self.current_lang]["content_sources"]
        elif index == 2:  # Organizations
            self.title.value = self.translations[self.current_lang]["organizations"]
            self.content.value = self.translations[self.current_lang]["content_orgs"]
        elif index == 3:  # Projects
            self.title.value = self.translations[self.current_lang]["projects"]
            self.content.value = self.translations[self.current_lang]["content_projects"]
        elif index == 4:  # Persons
            self.title.value = self.translations[self.current_lang]["persons"]
            self.content.value = self.translations[self.current_lang]["content_persons"]
        elif index == 5:  # Research Outputs
            self.title.value = self.translations[self.current_lang]["research_outputs"]
            self.content.value = self.translations[self.current_lang]["content_outputs"]
        
        self.page.update()
    
    def open_language_dialog(self, e):
        self.page.dialog = self.lang_dialog
        self.lang_dialog.open = True
        self.page.update()
    
    def change_language(self, e):
        self.current_lang = e.control.value
        self.update_ui_for_language()
        self.lang_dialog.open = False
        self.page.update()
    
    def update_ui_for_language(self):
        # Update navigation rail labels
        for i, dest in enumerate(self.nav_rail.destinations):
            if i == 0:
                dest.label = self.translations[self.current_lang]["home"]
            elif i == 1:
                dest.label = self.translations[self.current_lang]["sources"]
            elif i == 2:
                dest.label = self.translations[self.current_lang]["organizations"]
            elif i == 3:
                dest.label = self.translations[self.current_lang]["projects"]
            elif i == 4:
                dest.label = self.translations[self.current_lang]["persons"]
            elif i == 5:
                dest.label = self.translations[self.current_lang]["research_outputs"]
        
        # Update FAB text
        self.nav_rail.leading.text = self.translations[self.current_lang]["language"]
        
        # Update current page content based on selected index
        index = self.nav_rail.selected_index
        if index == 0:
            self.title.value = self.translations[self.current_lang]["welcome"]
            self.content.value = self.translations[self.current_lang]["content_home"]
        elif index == 1:
            self.title.value = self.translations[self.current_lang]["sources"]
            self.content.value = self.translations[self.current_lang]["content_sources"]
        elif index == 2:
            self.title.value = self.translations[self.current_lang]["organizations"]
            self.content.value = self.translations[self.current_lang]["content_orgs"]
        elif index == 3:
            self.title.value = self.translations[self.current_lang]["projects"]
            self.content.value = self.translations[self.current_lang]["content_projects"]
        elif index == 4:
            self.title.value = self.translations[self.current_lang]["persons"]
            self.content.value = self.translations[self.current_lang]["content_persons"]
        elif index == 5:
            self.title.value = self.translations[self.current_lang]["research_outputs"]
            self.content.value = self.translations[self.current_lang]["content_outputs"]

def main(page: ft.Page):
    app = MultilingualApp(page)

ft.app(target=main)