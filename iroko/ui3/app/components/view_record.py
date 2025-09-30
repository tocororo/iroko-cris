# app/components/view_record.py
import flet as ft

class ViewRecord(ft.Container):
    def __init__(self, record: dict):
        super().__init__()
        self.record = record

    def build(self):
        if not self.record:
            return ft.Text("Registro no encontrado.", size=18)
            
        record_details = [
            ft.Row(
                [
                    ft.Text(f"{str(key).capitalize()}:", weight=ft.FontWeight.BOLD, width=150),
                    ft.Text(value, selectable=True),
                ],
                alignment=ft.MainAxisAlignment.START,
            )
            for key, value in self.record.items()
        ]
        
        return ft.Column(
            controls=record_details,
            spacing=10
        )