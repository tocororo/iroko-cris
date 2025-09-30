import flet as ft
from iroko.ui2.components.base_page import BasePage

class ListRecords(BasePage):
    def __init__(self, page: ft.Page, entity_type: str):
        super().__init__(page, f"Lista de {self.get_entity_title(entity_type)}", "")
        self.entity_type = entity_type
        self.records = self.load_sample_data()
        
    def get_entity_title(self, entity_type):
        """Get proper title for entity type"""
        titles = {
            "revistas": "Revistas MES",
            "publicaciones": "Publicaciones",
            "articulos": "Artículos",
            "investigadores": "Investigadores",
            "autores": "Autores",
            "instituciones": "Instituciones",
            "centros": "Centros de Investigación",
            "proyectos_activos": "Proyectos Activos",
            "proyectos_finalizados": "Proyectos Finalizados",
            "resultados_publicaciones": "Publicaciones Científicas",
            "patentes": "Patentes",
            "productos": "Productos",
            "evaluaciones_proyectos": "Evaluaciones de Proyectos",
            "evaluaciones_revistas": "Evaluaciones de Revistas"
        }
        return titles.get(entity_type, entity_type.title())
        
    def load_sample_data(self):
        """Load sample data based on entity type"""
        sample_data = {
            "revistas": [
                {"id": 1, "nombre": "Revista Cubana de Química", "issn": "0258-5995", "categoria": "A1"},
                {"id": 2, "nombre": "Revista Cubana de Física", "issn": "0258-5936", "categoria": "A2"},
                {"id": 3, "nombre": "Revista Cubana de Medicina", "issn": "0258-641X", "categoria": "A1"},
            ],
            "publicaciones": [
                {"id": 1, "titulo": "Avances en Nanotecnología", "año": 2024, "editorial": "Editorial Científico-Técnica"},
                {"id": 2, "titulo": "Medio Ambiente y Desarrollo", "año": 2023, "editorial": "Editorial Academia"},
            ],
            "articulos": [
                {"id": 1, "titulo": "Nuevo método para la síntesis de compuestos", "revista": "Revista Cubana de Química", "año": 2024},
                {"id": 2, "titulo": "Estudio sobre cambio climático en Cuba", "revista": "Revista Cubana de Meteorología", "año": 2023},
            ],
            "investigadores": [
                {"id": 1, "nombre": "Dr. Carlos Martínez", "categoria": "Investigador Titular", "institucion": "Universidad de La Habana"},
                {"id": 2, "nombre": "Dra. Ana López", "categoria": "Investigador Auxiliar", "institucion": "Instituto de Cibernética"},
            ],
            "autores": [
                {"id": 1, "nombre": "Prof. Juan García", "orcid": "0000-0001-2345-6789", "publicaciones": 15},
                {"id": 2, "nombre": "Dr. María Rodríguez", "orcid": "0000-0002-3456-7890", "publicaciones": 23},
            ],
            "instituciones": [
                {"id": 1, "nombre": "Universidad de La Habana", "tipo": "Universidad", "provincia": "La Habana"},
                {"id": 2, "nombre": "Centro Nacional de Investigaciones Científicas", "tipo": "Centro de Investigación", "provincia": "La Habana"},
            ],
            "centros": [
                {"id": 1, "nombre": "Instituto de Ciencia y Tecnología de Materiales", "director": "Dr. Pedro Pérez", "area": "Ciencias de Materiales"},
                {"id": 2, "nombre": "Instituto de Neurociencias", "director": "Dra. Laura Fernández", "area": "Ciencias Biomédicas"},
            ],
            "proyectos_activos": [
                {"id": 1, "titulo": "Desarrollo de Energías Renovables", "codigo": "P123", "fecha_inicio": "2024-01-01", "estado": "En ejecución"},
                {"id": 2, "titulo": "Inteligencia Artificial Aplicada", "codigo": "P124", "fecha_inicio": "2024-03-15", "estado": "En ejecución"},
            ],
            "proyectos_finalizados": [
                {"id": 1, "titulo": "Estudio de Biodiversidad", "codigo": "P100", "fecha_fin": "2023-12-31", "resultados": "5 publicaciones"},
                {"id": 2, "titulo": "Desarrollo de Vacunas", "codigo": "P101", "fecha_fin": "2023-06-30", "resultados": "2 patentes"},
            ],
            "resultados_publicaciones": [
                {"id": 1, "titulo": "Nuevo algoritmo de machine learning", "tipo": "Artículo", "impacto": "Q1", "año": 2024},
                {"id": 2, "titulo": "Estudio clínico fase III", "tipo": "Artículo", "impacto": "Q2", "año": 2023},
            ],
            "patentes": [
                {"id": 1, "titulo": "Dispositivo para purificación de agua", "numero": "CU12345", "fecha": "2024-01-15", "inventores": "3"},
                {"id": 2, "titulo": "Compuesto farmacéutico novedoso", "numero": "CU12346", "fecha": "2023-11-20", "inventores": "5"},
            ],
            "productos": [
                {"id": 1, "nombre": "Software de gestión científica", "tipo": "Software", "estado": "Comercializado", "año": 2024},
                {"id": 2, "nombre": "Kit de diagnóstico rápido", "tipo": "Producto biotecnológico", "estado": "Validado", "año": 2023},
            ],
            "evaluaciones_proyectos": [
                {"id": 1, "proyecto": "Desarrollo de Energías Renovables", "evaluador": "Comisión Nacional", "calificacion": "Excelente", "fecha": "2024-06-01"},
                {"id": 2, "proyecto": "Inteligencia Artificial Aplicada", "evaluador": "Comité Científico", "calificacion": "Muy Bueno", "fecha": "2024-05-15"},
            ],
            "evaluaciones_revistas": [
                {"id": 1, "revista": "Revista Cubana de Química", "indice_h": 15, "categoria_actual": "A1", "proxima_evaluacion": "2025-01-01"},
                {"id": 2, "revista": "Revista Cubana de Física", "indice_h": 12, "categoria_actual": "A2", "proxima_evaluacion": "2025-01-01"},
            ]
        }
        return sample_data.get(self.entity_type, [{"id": 1, "nombre": "Ejemplo 1", "descripcion": "Datos de ejemplo"}])
    
    def get_view(self):
        return ft.View(
            route=f"/list/{self.entity_type}",
            controls=[
                self.create_app_bar(),
                ft.Container(
                    content=ft.Column([
                        ft.Text(f"Total de registros: {len(self.records)}", 
                               size=16, weight=ft.FontWeight.BOLD),
                        ft.ListView(
                            controls=[self.create_record_item(record) for record in self.records],
                            expand=True,
                            spacing=10,
                            padding=20
                        )
                    ]),
                    expand=True
                )
            ]
        )
    
    def create_record_item(self, record):
        """Create a list item for a record"""
        # Determine icon based on entity type
        icon_map = {
            "revistas": ft.Icons.BOOK,
            "publicaciones": ft.Icons.LIBRARY_BOOKS,
            "articulos": ft.Icons.ARTICLE,
            "investigadores": ft.Icons.SCIENCE,
            "autores": ft.Icons.PERSON,
            "instituciones": ft.Icons.ACCOUNT_BALANCE,
            "centros": ft.Icons.BUSINESS_CENTER,
            "proyectos": ft.Icons.WORK,
            "resultados": ft.Icons.ASSESSMENT,
            "patentes": ft.Icons.PATENT,
            "productos": ft.Icons.INVENTORY,
            "evaluaciones": ft.Icons.STAR
        }
        
        icon = ft.Icons.LIST
        for key, value in icon_map.items():
            if key in self.entity_type:
                icon = value
                break
        
        return ft.Card(
            content=ft.Container(
                content=ft.ListTile(
                    leading=ft.Icon(icon, color=ft.Colors.BLUE),
                    title=ft.Text(record.get('nombre', record.get('titulo', record.get('proyecto', 'Sin título')))),
                    subtitle=ft.Text(self.get_subtitle(record)),
                    trailing=ft.IconButton(
                        icon=ft.Icons.VISIBILITY,
                        on_click=lambda e, r=record: self.view_record(r),
                        tooltip="Ver detalles"
                    ),
                    on_click=lambda e, r=record: self.view_record(r)
                ),
                padding=10
            )
        )
    
    def get_subtitle(self, record):
        """Generate subtitle based on record content"""
        if 'issn' in record:
            return f"ISSN: {record['issn']} - Categoría: {record.get('categoria', 'N/A')}"
        elif 'año' in record:
            return f"Año: {record['año']}"
        elif 'categoria' in record:
            return f"Categoría: {record['categoria']}"
        elif 'tipo' in record:
            return f"Tipo: {record['tipo']}"
        elif 'estado' in record:
            return f"Estado: {record['estado']}"
        return "Haga clic para ver detalles"
    
    def view_record(self, record):
        """Navigate to view record page"""
        self.page.go(f"/view/{self.entity_type}/{record['id']}")