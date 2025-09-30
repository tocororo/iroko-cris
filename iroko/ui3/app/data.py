# app/data.py

# This is a central place for mock data.
# It now points to markdown files for its content.

MOCK_DATA = {
    "revistas_mes": {
        "title": "Revistas MES",
        "markdown_file": "markdown/revistas_mes.md",
        "records": [
            {"id": 1, "title": "Revista Cubana de Educación Superior", "subtitle": "Vol. 40, No. 1", "year": 2021},
            {"id": 2, "title": "Pedagogía Universitaria", "subtitle": "Vol. 25, No. 2", "year": 2020},
            {"id": 3, "title": "Revista de Arquitectura", "subtitle": "Vol. 15, No. 1", "year": 2022},
        ]
    },
    "catalogo": {
        "title": "Catálogo",
        "markdown_file": "markdown/catalogo.md",
        "records": [
            {"id": 1, "title": "Introducción a la Inteligencia Artificial", "subtitle": "Autor: Dr. A. Valdés", "type": "Libro"},
            {"id": 2, "title": "Historia de la Universidad de La Habana", "subtitle": "Autor: Dr. E. Torres", "type": "Libro"},
        ]
    },
    "personas": {
        "title": "Personas",
        "markdown_file": "markdown/personas.md",
        "records": [
            {"id": 1, "title": "Dr. Juan Pérez García", "subtitle": "Facultad de Ciencias", "role": "Profesor Titular"},
            {"id": 2, "title": "MSc. Ana Rodríguez López", "subtitle": "Departamento de Informática", "role": "Asistente"},
        ]
    },
    "organizaciones": {"title": "Organizaciones", "markdown_file": "markdown/organizaciones.md", "records": []},
    "proyectos": {"title": "Proyectos", "markdown_file": "markdown/proyectos.md", "records": []},
    "resultados": {"title": "Resultados", "markdown_file": "markdown/resultados.md", "records": []},
    "evaluaciones": {"title": "Evaluaciones", "markdown_file": "markdown/evaluaciones.md", "records": []},
}