# app/components/list_records.py
import flet as ft

class ListRecords(ft.Container):
    def __init__(self, records: list[dict], on_record_click):
        super().__init__()
        self.records = records
        self.on_record_click = on_record_click

    def build(self):
        def handle_click(e):
            record_id = e.control.data
            self.on_record_click(record_id)

        return ft.ListView(
            controls=[
                ft.ListTile(
                    title=ft.Text(record.get("title", "No Title")),
                    subtitle=ft.Text(record.get("subtitle", "")),
                    leading=ft.Icon(ft.Icons.ARTICLE),
                    data=record.get("id"),
                    on_click=handle_click,
                )
                for record in self.records
            ]
        )