import flet as ft

class EvaluacionesPage(ft.Column):
    def __init__(self):
        super().__init__()
        self.expand = True
        self.scroll = ft.ScrollMode.AUTO
        self.controls = [
            ft.Text("Evaluaciones", size=24, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            self.build_content(),
        ]
        
    def build_content(self):
        return ft.Column([
            ft.Text("Sistema de evaluaciones", size=18),
            ft.Text("Resultados de evaluaciones y métricas de calidad."),
            ft.Row([
                ft.Dropdown(
                    label="Seleccionar métrica",
                    options=[
                        ft.dropdown.Option("Calidad"),
                        ft.dropdown.Option("Impacto"),
                        ft.dropdown.Option("Originalidad"),
                    ],
                    value="Calidad",
                    width=200
                ),
                ft.Dropdown(
                    label="Período",
                    options=[
                        ft.dropdown.Option("Último mes"),
                        ft.dropdown.Option("Último trimestre"),
                        ft.dropdown.Option("Último año"),
                    ],
                    value="Último año",
                    width=200
                ),
            ]),
            ft.LineChart(
                data_series=[
                    ft.LineChartData(
                        data_points=[
                            ft.LineChartDataPoint(1, 5),
                            ft.LineChartDataPoint(2, 6.5),
                            ft.LineChartDataPoint(3, 8),
                            ft.LineChartDataPoint(4, 7.2),
                            ft.LineChartDataPoint(5, 9),
                        ],
                        stroke_width=3,
                        color=ft.Colors.BLUE,
                        curved=True,
                        stroke_cap_round=True,
                    )
                ],
                left_axis=ft.ChartAxis(labels_size=40),
                bottom_axis=ft.ChartAxis(labels_size=40),
                tooltip_bgcolor=ft.Colors.with_opacity(0.8, ft.Colors.WHITE),
                expand=True,
                height=200
            )
        ], spacing=20)