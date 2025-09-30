import flet as ft

from iroko.ui.components.paginated_node_list import PaginatedNodeList

class OrganizacionesPage(ft.Column):
    def __init__(self, 
                #  page: ft.Page, 
                 api_query_enpoint: str):
        super().__init__()
        # self.page = page
        self.api_query_enpoint = api_query_enpoint
        self.expand = True
        self.padding = 20
        self.controls = [
            ft.Text("Organizaciones", size=28, weight=ft.FontWeight.BOLD),
            ft.Divider(height=20),
            PaginatedNodeList(
                # page= self.page,
                label="Organization",
                attributes=[
                    "name",
                    "organizationType",
                    "acronyms",
                    "aliases",
                    "`identifier#grid`",
                    "`identifier#isni`",
                    "`identifier#ror`",
                    "`identifier#wkdata`",
                    "links"
                ],
                sort_attributes=["name", "organizationType"],
                page_size=10,
                api_url=self.api_query_enpoint 
            ),
            # ft.Text(f"Initial route: {self.page.route}")
        ]
    
    def did_mount(self):
        self.controls.append(ft.Text(f"FFFFFFFF: {self.page.route}"))
