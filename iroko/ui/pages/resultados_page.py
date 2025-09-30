import flet as ft

from iroko.ui.components.paginated_node_list import PaginatedNodeList

class ResultadosPage(ft.Column):
    def __init__(self, 
                #  page: ft.Page, 
                 api_query_enpoint: str):
        super().__init__()
        # self.page = page
        self.api_query_enpoint = api_query_enpoint
        self.expand = True
        self.padding = 20
        self.controls = [
            ft.Text("Resultados de Investigación", size=28, weight=ft.FontWeight.BOLD),
            ft.Divider(height=20),
            PaginatedNodeList(
                # page= self.page,
                label="Output",
                attributes=[
                    "title",
                    "`identifier#url`",
                    "description"
                ],
                sort_attributes=["title"],
                page_size=10,
                api_url=self.api_query_enpoint 
            )
        ]