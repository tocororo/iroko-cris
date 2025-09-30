import flet as ft
from iroko.ui.components.paginated_node_list import PaginatedNodeList

class PersonasPage(ft.Column):
    def __init__(self, 
                #  page: ft.Page, 
                 api_query_enpoint: str):
        super().__init__()
        # self.page = page
        self.api_query_enpoint = api_query_enpoint
        self.expand = True
        self.padding = 20
        self.controls = [
            ft.Text("Autores", size=28, weight=ft.FontWeight.BOLD),
            ft.Divider(height=20),
            PaginatedNodeList(
                # page= self.page,
                label="Author",
                attributes=["`identifier#dni`", "name", "lastName", "emailAddress", "aliases"],
                sort_attributes=["name", "lastName"],
                page_size=10,
                api_url=self.api_query_enpoint 
            ),
            # ft.Text(f"Initial route: {self.page.route}")
        ]

