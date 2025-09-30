# components/paginated_node_list.py

import flet as ft
import httpx
import asyncio
from iroko.ui.components.node_card import NodeCard
from iroko.ui.components.node_viewer import NodeViewer, NodeViewerCard

class PaginatedNodeList(ft.Column):
    """
    Reusable component to display paginated list of Neo4j nodes via FastAPI.

    Args:
        label: str - Neo4j node label (e.g., "Person", "Source")
        attributes: list[str] - List of property names to display for each node
        page_size: int - Number of items per page
        api_url: str - FastAPI endpoint URL (default: "http://localhost:8000/query")
    """

    def __init__(
        self,
        # page: ft.Page,
        label: str,
        attributes: list[str],
        sort_attributes: list[str] = None,
        page_size: int = 10,
        api_url: str = "http://localhost:8000/query", 
        default_sort: str = None,
        default_sort_order: str = "ASC" 
    ):
        super().__init__()
        # self.page = page
        self.label = label
        self.attributes = attributes
        self.sort_attributes = sort_attributes or attributes
        self.page_size = page_size
        self.api_url = api_url
        self.current_page = 0
        self.total_count = 0
        self.nodes = []
        self.search_term = ""
        self.debounce_task = None

        if default_sort and default_sort in sort_attributes:
            self.sort_by = (default_sort, default_sort_order.upper())
            self.initial_sort_value = default_sort
        else:
            self.sort_by = (self.sort_attributes[0], default_sort_order.upper())
            self.initial_sort_value = self.sort_attributes[0]

        # UI Controls
        self.search_field = ft.TextField(
            hint_text="Buscar...",
            on_change=self.on_search_change,
            prefix_icon=ft.Icons.SEARCH,
            expand=True,
            dense=True,
            content_padding=10,
        )

        self.clear_search_btn = ft.IconButton(
            icon=ft.Icons.CLEAR,
            tooltip="Clear search",
            on_click=self.clear_search,
            visible=False,
        )

        self.sort_dropdown = ft.Dropdown(
            width=200,
            dense=True,
            options=[
                ft.dropdown.Option("none", "Ordenar por..."),
                *[ft.dropdown.Option(attr, f"Ordenar por {attr}") for attr in sort_attributes],
            ],
            value=self.initial_sort_value,
            on_change=self.on_sort_change,
        )


        # Set initial sort direction
        initial_direction = default_sort_order.upper() if default_sort else "ASC"
        self.current_sort_direction = initial_direction

        self.sort_order_icon_container = ft.Container(
            content=ft.Icon(
                name=ft.Icons.ARROW_UPWARD if initial_direction == "ASC" else ft.Icons.ARROW_DOWNWARD,
                tooltip="Ascendente" if initial_direction == "ASC" else "Descendente",
                size=18,
            ),
            tooltip="Cambiar el orden",
            padding=6,
            border_radius=4,
            on_click=self.toggle_sort_order,  # 👈 Handle click to toggle
            visible=bool(default_sort or self.sort_attributes),
            ink=True,  # Ripple effect on click
        )

        self.list_view = ft.ListView(expand=True, spacing=10, padding=10)
        self.list_container = ft.Container(content=self.list_view, expand=True)
        self.pagination_row = ft.Row(alignment=ft.MainAxisAlignment.CENTER, spacing=10)
        self.loading_indicator = ft.ProgressRing(visible=True)
        self.error_text = ft.Text(color=ft.Colors.RED, visible=False)

        # pagination info label
        self.pagination_info = ft.Text(
            value="Cargando...",
            size=13,
            italic=True,
            color=ft.Colors.ON_SURFACE_VARIANT,
        )

        # Build UI
        self.controls = [
            ft.Row(
                [
                    self.search_field,
                    self.clear_search_btn,
                    ft.Container(width=20),
                    ft.Row([self.sort_dropdown, self.sort_order_icon_container], spacing=5),
                ],
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Divider(height=20),
            self.pagination_info,
            ft.Divider(height=10),
            self.loading_indicator,
            self.error_text,
            self.list_container,
            ft.Divider(),
            self.pagination_row,
            
        ]
        self.expand = True
        

    def did_mount(self):
        self.page.run_task(self.load_page, 0)

    async def load_page(self, page: int):
        self.current_page = page
        offset = page * self.page_size

        self.loading_indicator.visible = True
        self.error_text.visible = False
        self.update()

        try:
            if page == 0:
                self.total_count = await self.fetch_total_count()
                print(self.total_count)

            self.nodes = await self.fetch_nodes(offset, self.page_size)

            start_idx = self.current_page * self.page_size + 1
            end_idx = min(start_idx + len(self.nodes) - 1, self.total_count)
            total_pages = (self.total_count + self.page_size - 1) // self.page_size or 1
            # Format text
            if self.total_count == 0:
                info_text = "No hay resultados."
            else:
                info_text = f"Mostrando {start_idx}–{end_idx} de {self.total_count} elementos — Página {self.current_page + 1} de {total_pages}"
            self.pagination_info.value = info_text

            self.render_list()
            self.render_pagination()

        except Exception as e:
            self.error_text.value = f"Error: {str(e)}"
            self.error_text.visible = True
            print(f"Error loading page {page}: {e}")
        finally:
            self.loading_indicator.visible = False
            self.update()

    async def fetch_total_count(self) -> int:
        where_clause = self._build_where_clause()
        query = f"MATCH (n:`{self.label}`) {where_clause} RETURN count(n) AS count"
        payload = {
            "parameters": self._build_parameters(),
            "query": query,
            "readonly": True
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(self.api_url, json=payload, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            return data[0]["count"] if data and "count" in data[0] else 0

    async def fetch_nodes(self, offset: int, limit: int) -> list:
        where_clause = self._build_where_clause()
        order_clause = self._build_order_clause()
        # return_clause = ", ".join([f"n.{attr} AS {attr}" for attr in self.attributes])
        return_clause = "n"

        query = f"""
            MATCH (n:`{self.label}`)
            {where_clause}
            RETURN {return_clause}
            {order_clause}
            SKIP $offset
            LIMIT $limit
        """

        params = self._build_parameters()
        params["offset"] = offset
        params["limit"] = limit

        payload = {
            "parameters": params,
            "query": query,
            "readonly": True
        }
        print(query)
        async with httpx.AsyncClient() as client:
            response = await client.post(self.api_url, json=payload, timeout=10.0)
            response.raise_for_status()
            return response.json()

    def _build_where_clause(self) -> str:
        if not self.search_term:
            return ""

        # Use apoc.text.join — safe for strings and lists
        parts = [
            f"coalesce(apoc.text.join(n.{attr}, ' '), '')"
            for attr in self.sort_attributes
        ]

        concat_expr = " + ' ' + ".join(parts)
        where_clause = f"WHERE toLower({concat_expr}) CONTAINS toLower($search_term)"

        return where_clause

    def _build_order_clause(self) -> str:
        if not self.sort_by:
            return ""
        attr, direction = self.sort_by
        return f"ORDER BY n.{attr} {direction}"

    def _build_parameters(self) -> dict:
        params = {}
        if self.search_term:
            params["search_term"] = self.search_term
        return params

    # def __render_list(self):

    def render_list(self):
        self.list_view.controls.clear()

        if not self.nodes:
            self.list_view.controls.append(
                ft.Container(
                    ft.Text("No data available", italic=True, size=16, weight=ft.FontWeight.W_500),
                    padding=40,
                    alignment=ft.alignment.center,
                )
            )
            self.list_container.update()
            return

        for node in self.nodes:
            # Create NodeCard — pass node, attributes to display, and all attributes for modal
            try:
                card = NodeViewerCard(
                    node=node['n'],
                    label=self.label,
                    sort_attributes=self.sort_attributes,
                    attributes=self.attributes,
                    # page=self.page,
                    on_node_selected=self.handle_node_selected
                )
                self.list_view.controls.append(card)
            except Exception as e:
                print(f"[ERROR] Failed to create NodeCard: {e}")
                self.list_view.controls.append(ft.Text(f"Error: {e}"))


        self.list_container.update()
        
        # self.update()


    def handle_node_selected(self, node_id: str, node_label: str):
        # Define your relations here (this might come from your app configuration)
        # For example, you might have different relations based on node label
        # relations = self.get_relations_for_label(node_label)
        
        # Create and show the node viewer
        self.node_viewer = NodeViewer(
            api_url=self.api_url,  # Make sure this is available in your class
            node_id=node_id,
            node_label=node_label,
            on_back=self.show_node_list,  # Go back to list view
            on_error=self.handle_viewer_error,
        )
        
        # Replace list view with node viewer
        self.list_container.content = self.node_viewer
        self.list_container.update()

    # Method to go back to node list
    def show_node_list(self):
        # Re-render the list
        print(self.nodes)
        
        self.render_list()
        self.list_container.content = content=self.list_view
        self.list_container.update()
        self.render_pagination()
        
    def handle_viewer_error(self, error_message: str):
        self.error_text = error_message
        print(f"Node viewer error: {error_message}")

    def render_pagination(self):
        self.pagination_row.controls.clear()

        total_pages = (self.total_count + self.page_size - 1) // self.page_size
        if total_pages <= 1:
            return

        if self.current_page > 0:
            self.pagination_row.controls.append(
                ft.IconButton(
                    icon=ft.Icons.CHEVRON_LEFT,
                    on_click=lambda e: self.page.run_task(self.load_page, self.current_page - 1),
                    tooltip="Previous Page"
                )
            )

        start_page = max(0, self.current_page - 2)
        end_page = min(total_pages, start_page + 5)
        start_page = max(0, end_page - 5)

        for p in range(start_page, end_page):
            is_current = p == self.current_page
            btn = ft.TextButton(
                text=str(p + 1),
                style=ft.ButtonStyle(
                    color={
                        ft.ControlState.DEFAULT: ft.Colors.BLUE if is_current else ft.Colors.ON_SURFACE_VARIANT,
                        ft.ControlState.HOVERED: ft.Colors.BLUE_700,
                    },
                    padding=8,
                ),
                on_click=lambda e, p=p: self.page.run_task(self.load_page, p),
            )
            self.pagination_row.controls.append(btn)

        if self.current_page < total_pages - 1:
            self.pagination_row.controls.append(
                ft.IconButton(
                    icon=ft.Icons.CHEVRON_RIGHT,
                    on_click=lambda e: self.page.run_task(self.load_page, self.current_page + 1),
                    tooltip="Next Page"
                )
            )

        self.pagination_row.update()

    def on_search_change(self, e):
        self.search_term = e.control.value.strip()
        self.clear_search_btn.visible = bool(self.search_term)

        # Cancel previous debounce task if exists
        if self.debounce_task:
            self.debounce_task.cancel()
            self.debounce_task = None

        async def delayed_load():
            try:
                await asyncio.sleep(0.5)  # Debounce delay
                await self.load_page(0)   # Reload page 0 with new filter
            except asyncio.CancelledError:
                # Expected if user types again before delay ends
                return
            except Exception as ex:
                print(f"[Search Error] {ex}")

        # Schedule the async task safely on Flet's event loop
        self.debounce_task = self.page.run_task(delayed_load)

        # Update UI to show clear button, etc.
        self.update()

    def clear_search(self, e):
        self.search_field.value = ""
        self.search_term = ""
        self.clear_search_btn.visible = False
        self.page.run_task(self.load_page, 0)
        self.update()

    def _update_sort_icon(self, direction: str):
        icon = self.sort_order_icon_container.content
        icon.name = ft.Icons.ARROW_UPWARD if direction == "ASC" else ft.Icons.ARROW_DOWNWARD
        icon.tooltip = "Ascending" if direction == "ASC" else "Descending"

    def on_sort_change(self, e):
        if e.control.value == "none":
            self.sort_by = None
            self.sort_order_icon_container.visible = False
        else:
            current_attr = e.control.value
            if self.sort_by and self.sort_by[0] == current_attr:
                new_dir = "DESC" if self.sort_by[1] == "ASC" else "ASC"
            else:
                new_dir = "ASC"

            self.sort_by = (current_attr, new_dir)
            self.sort_order_icon_container.visible = True
            self._update_sort_icon(new_dir)  # 👈 Cleaner!

        self.page.run_task(self.load_page, 0)
        self.update()

    def toggle_sort_order(self, e):
        if not self.sort_by:
            return

        current_attr, current_dir = self.sort_by
        new_dir = "DESC" if current_dir == "ASC" else "ASC"
        self.sort_by = (current_attr, new_dir)

        self._update_sort_icon(new_dir)  # 👈 Reuse same logic

        self.page.run_task(self.load_page, 0)
        self.update()