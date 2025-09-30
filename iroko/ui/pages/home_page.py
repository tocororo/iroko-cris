from turtle import end_poly
import flet as ft
import httpx  # Make sure to install: pip install httpx


class HomePage(ft.Column):
    def __init__(self, 
                #  page: ft.Page, 
                 api_query_enpoint: str):
        super().__init__()
        self.api_query_enpoint = api_query_enpoint
        self.expand = True
        self.scroll = ft.ScrollMode.AUTO
        # self.page = page  # Keep reference to page for run_task

        # Placeholder controls before data is loaded
        self.controls = [
            ft.Text("Inicio", size=24, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            ft.ProgressRing(),  # Show loading while fetching
            ft.Divider(),
        ]


    def did_mount(self):
        self.running = True
        self.page.run_task(self.load_data)

    async def load_data(self):
        try:
            counts = await self.fetch_node_counts()
            # Rebuild stats section with real data
            stats_section = self.build_stats(counts)
            # Replace controls: keep header, replace loading with stats
            self.controls = [
                ft.Text("Inicio", size=24, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                stats_section,
                ft.Divider(),
            ]
            self.update()
        except Exception as e:
            print(f"Error loading data: {e}")
            self.controls.append(ft.Text(f"Error: {str(e)}", color=ft.Colors.RED))
            self.update()

    async def fetch_node_counts(self):
        # Define mapping from UI label to Neo4j label
        LABELS = {
            "Revistas MES": "Source",
            "Publicaciones": "Source",             # Also counts Source nodes
            "Autores": "Author",
            "Organizaciones": "Organization",
            "Resultados de Investigación": "Output",
        }

        counts = {}
        
        async with httpx.AsyncClient() as client:
            for ui_label, neo4j_label in LABELS.items():
                payload = {
                    "parameters": {},
                    "query": f"MATCH (n:`{neo4j_label}`) RETURN count(n) AS count",
                    "readonly": True
                }

                try:
                    response = await client.post(self.api_query_enpoint, json=payload, timeout=10.0)
                    response.raise_for_status()
                    data = response.json()

                    # Assuming response format: [{"count": 123}]
                    if isinstance(data, list) and len(data) > 0 and "count" in data[0]:
                        counts[ui_label] = data[0]["count"]
                    else:
                        counts[ui_label] = 0
                except Exception as e:
                    print(f"Error fetching {ui_label}: {e}")
                    counts[ui_label] = 0  # fallback

        return counts

    def build_stats(self, counts):
        # Safely get counts with fallback to 0
        def get_count(key):
            return str(counts.get(key, 0))

        return ft.Column(
            [
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Column([
                                ft.Icon(ft.Icons.BOOK, size=40, color=ft.Colors.BLUE),
                                ft.Text(get_count("Revistas MES"), size=24, weight=ft.FontWeight.BOLD),
                                ft.Text("Revistas MES", size=14),
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                            padding=20,
                            bgcolor=ft.Colors.BLUE_50,
                            border_radius=10,
                            expand=True,
                        ),
                        ft.Container(
                            content=ft.Column([
                                ft.Icon(ft.Icons.PEOPLE, size=40, color=ft.Colors.GREEN),
                                ft.Text(get_count("Autores"), size=24, weight=ft.FontWeight.BOLD),
                                ft.Text("Autores", size=14),
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                            padding=20,
                            bgcolor=ft.Colors.GREEN_50,
                            border_radius=10,
                            expand=True,
                        ),
                        ft.Container(
                            content=ft.Column([
                                ft.Icon(ft.Icons.BUSINESS, size=40, color=ft.Colors.ORANGE),
                                ft.Text(get_count("Organizaciones"), size=24, weight=ft.FontWeight.BOLD),
                                ft.Text("Organizaciones", size=14),
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                            padding=20,
                            bgcolor=ft.Colors.ORANGE_50,
                            border_radius=10,
                            expand=True,
                        ),
                    ],
                    spacing=20,
                    expand=True,
                ),
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Column([
                                ft.Icon(ft.Icons.BOOK, size=40, color=ft.Colors.BLUE),
                                ft.Text(get_count("Publicaciones"), size=24, weight=ft.FontWeight.BOLD),
                                ft.Text("Publicaciones", size=14),
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                            padding=20,
                            bgcolor=ft.Colors.BLUE_50,
                            border_radius=10,
                            expand=True,
                        ),
                        ft.Container(
                            content=ft.Column([
                                ft.Icon(ft.Icons.BUSINESS, size=40, color=ft.Colors.ORANGE),
                                ft.Text(get_count("Resultados de Investigación"), size=24, weight=ft.FontWeight.BOLD),
                                ft.Text("Resultados de Investigación", size=14),
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                            padding=20,
                            bgcolor=ft.Colors.ORANGE_50,
                            border_radius=10,
                            expand=True,
                        ),
                    ],
                    spacing=20,
                    expand=True,
                ),
            ],
            spacing=20,
            expand=True,
        )