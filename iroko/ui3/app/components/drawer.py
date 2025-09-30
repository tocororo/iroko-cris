# app/components/drawer.py
import flet as ft

def AppDrawer(page: ft.Page) -> ft.NavigationDrawer:
    """
    Creates the main navigation drawer for the application.
    """
    menu_items = [
        "Inicio", "Revistas MES", "Catalogo", "Personas",
        "Organizaciones", "Proyectos", "Resultados", "Evaluaciones"
    ]
    
    # Simple function to create a route from a menu item name
    def create_route(item_name):
        if item_name == "Inicio":
            return "/"
        return f"/{item_name.lower().replace(' ', '_')}"

    def close_drawer_and_go(route):
        page.drawer.open = False
        page.go(route)
        page.update()
    
    def on_navigation_change(e):
        selected_index = e.control.selected_index
        page_name = menu_items[selected_index]
        route = create_route(page_name)
        page.drawer.open = False
        page.go(route)
        page.update()

    return ft.NavigationDrawer(
        on_change=on_navigation_change,
        controls=[
            ft.Container(height=12),
            *[ # Unpack the list of controls
                ft.NavigationDrawerDestination(
                    label=item,
                    icon=ft.Icons.ARROW_RIGHT_OUTLINED,
                    selected_icon=ft.Icons.ARROW_RIGHT,
                ) for item in menu_items
            ],
        ]
    )