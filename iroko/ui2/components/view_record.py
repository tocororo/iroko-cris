import flet as ft
from iroko.ui2.components.base_page import BasePage

class ViewRecord(BasePage):
    def __init__(self, page: ft.Page, entity_type: str, record_id: str):
        super().__init__(page, f"Detalles de {entity_type.title()}", "")
        self.entity_type = entity_type
        self.record_id = record_id
        self.record = self.load_record()
        
    def load_record(self):
        """Load specific record data"""
        all_records = {
            "revistas": {
                1: {"id": 1, "nombre": "Revista Cubana de Química", "issn": "0258-5995", 
                    "categoria": "A1", "fundacion": 1985, "periodicidad": "Trimestral",
                    "editor": "Universidad de La Habana", "indexaciones": "SciELO, Redalyc"},
                2: {"id": 2, "nombre": "Revista Cubana de Física", "issn": "0258-5936", 
                    "categoria": "A2", "fundacion": 1984, "periodicidad": "Semestral",
                    "editor": "Instituto de Cibernética", "indexaciones": "SciELO"},
                3: {"id": 3, "nombre": "Revista Cubana de Medicina", "issn": "0258-641X", 
                    "categoria": "A1", "fundacion": 1962, "periodicidad": "Trimestral",
                    "editor": "Ministerio de Salud Pública", "indexaciones": "SciELO, MEDLINE"},
            },
            "investigadores": {
                1: {"id": 1, "nombre": "Dr. Carlos Martínez", "categoria": "Investigador Titular", 
                    "institucion": "Universidad de La Habana", "orcid": "0000-0001-2345-6789",
                    "especialidad": "Química Orgánica", "publicaciones": 45, "proyectos": 12},
                2: {"id": 2, "nombre": "Dra. Ana López", "categoria": "Investigador Auxiliar", 
                    "institucion": "Instituto de Cibernética", "orcid": "0000-0002-3456-7890",
                    "especialidad": "Inteligencia Artificial", "publicaciones": 23, "proyectos": 8},
            },
            "proyectos_activos": {
                1: {"id": 1, "titulo": "Desarrollo de Energías Renovables", "codigo": "P123", 
                    "fecha_inicio": "2024-01-01", "estado": "En ejecución", "presupuesto": "500,000 USD",
                    "investigador_principal": "Dr. Carlos Martínez", "duracion": "36 meses",
                    "objetivo": "Desarrollar tecnologías para energía solar y eólica"},
                2: {"id": 2, "titulo": "Inteligencia Artificial Aplicada", "codigo": "P124", 
                    "fecha_inicio": "2024-03-15", "estado": "En ejecución", "presupuesto": "300,000 USD",
                    "investigador_principal": "Dra. Ana López", "duracion": "24 meses",
                    "objetivo": "Aplicar IA en diagnóstico médico y optimización industrial"},
            }
        }
        
        # Default record if not found
        default_record = {
            "id": self.record_id,
            "nombre": f"Registro {self.record_id}",
            "tipo": self.entity_type,
            "descripcion": "Información detallada del registro seleccionado",
            "estado": "Activo",
            "fecha_creacion": "2024-01-01"
        }
        
        return all_records.get(self.entity_type, {}).get(int(self.record_id), default_record)
    
    def get_view(self):
        if not self.record:
            return ft.View(
                route=f"/view/{self.entity_type}/{self.record_id}",
                controls=[
                    self.create_app_bar(),
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.Icons.ERROR, size=48, color=ft.Colors.RED),
                            ft.Text("Registro no encontrado", size=20),
                            ft.ElevatedButton(
                                "Volver a la lista",
                                on_click=lambda e: self.page.go(f"/list/{self.entity_type}")
                            )
                        ], alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        alignment=ft.alignment.center,
                        expand=True
                    )
                ]
            )
        
        return ft.View(
            route=f"/view/{self.entity_type}/{self.record_id}",
            controls=[
                self.create_app_bar(),
                ft.Container(
                    content=ft.Column([
                        self.create_header_card(),
                        self.create_details_card(),
                        self.create_actions_row()
                    ], scroll=ft.ScrollMode.ADAPTIVE),
                    padding=20,
                    expand=True
                )
            ]
        )
    
    def create_header_card(self):
        """Create header card with main information"""
        title = self.record.get('nombre', self.record.get('titulo', 'Registro'))
        return ft.Card(
            content=ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.INFO, size=40, color=ft.Colors.BLUE),
                    ft.Column([
                        ft.Text(title, size=24, weight=ft.FontWeight.BOLD),
                        ft.Text(f"ID: {self.record.get('id', 'N/A')} • Tipo: {self.entity_type}", 
                               size=14, color=ft.Colors.GREY),
                    ], expand=True)
                ]),
                padding=20
            )
        )
    
    def create_details_card(self):
        """Create card with detailed information"""
        detail_rows = []
        for key, value in self.record.items():
            if key != 'id' and value:
                detail_rows.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Text(f"{self.format_key(key)}:", 
                                   weight=ft.FontWeight.BOLD, 
                                   width=200,
                                   color=ft.Colors.BLUE_GREY),
                            ft.Text(str(value), expand=True),
                        ]),
                        padding=ft.padding.symmetric(vertical=5)
                    )
                )
        
        return ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.DETAILS),
                        title=ft.Text("Información Detallada", 
                                     weight=ft.FontWeight.BOLD),
                    ),
                    ft.Divider(),
                    *detail_rows
                ]),
                padding=20
            )
        )
    
    def format_key(self, key):
        """Format key for display"""
        key_map = {
            'nombre': 'Nombre',
            'titulo': 'Título',
            'issn': 'ISSN',
            'categoria': 'Categoría',
            'fundacion': 'Año de Fundación',
            'periodicidad': 'Periodicidad',
            'editor': 'Editor',
            'indexaciones': 'Indexaciones',
            'institucion': 'Institución',
            'orcid': 'ORCID',
            'especialidad': 'Especialidad',
            'publicaciones': 'Publicaciones',
            'proyectos': 'Proyectos',
            'codigo': 'Código',
            'fecha_inicio': 'Fecha de Inicio',
            'estado': 'Estado',
            'presupuesto': 'Presupuesto',
            'investigador_principal': 'Investigador Principal',
            'duracion': 'Duración',
            'objetivo': 'Objetivo'
        }
        return key_map.get(key, key.title())
    
    def create_actions_row(self):
        """Create action buttons row"""
        return ft.Row([
            ft.ElevatedButton(
                "Editar",
                icon=ft.Icons.EDIT,
                on_click=self.edit_record
            ),
            ft.OutlinedButton(
                "Eliminar",
                icon=ft.Icons.DELETE,
                on_click=self.delete_record
            ),
            ft.TextButton(
                "Volver a la lista",
                icon=ft.Icons.ARROW_BACK,
                on_click=lambda e: self.page.go(f"/list/{self.entity_type}")
            ),
        ], alignment=ft.MainAxisAlignment.END)
    
    def edit_record(self, e):
        """Handle edit record action"""
        self.page.show_snack_bar(
            ft.SnackBar(content=ft.Text("Función de edición en desarrollo"))
        )
    
    def delete_record(self, e):
        """Handle delete record action"""
        self.page.show_snack_bar(
            ft.SnackBar(content=ft.Text("Función de eliminación en desarrollo"))
        )