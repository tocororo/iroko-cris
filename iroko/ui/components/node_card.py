# components/node_card.py

import flet as ft

class NodeCard(ft.Container):
    """
    Custom control to display a node with selected attributes.
    Clicking it opens a modal with full details.
    Compatible with all Flet versions.
    """

    def __init__(
        self,
        node: dict,
        sort_attributes: list[str],
        attributes: list[str] = None,
        on_click=None,
        page: ft.Page = None,
        **kwargs
    ):
        # STEP 1: Store raw data (safe to do before super().__init__)
        self.node = node or {}
        self.full_attributes = list(self.node)
        self.sort_attributes = sort_attributes or []
        self.attributes = attributes or self.sort_attributes
        self.user_on_click = on_click  # Save user callback
        self.page = page

        # STEP 2: Build display content (pure data → no Flet controls yet)
        display_fields = self._build_display_fields()

        # STEP 3: Initialize Flet Container FIRST — before any event handlers
        super().__init__(
            content=ft.Column(
                display_fields,
                spacing=4,
                tight=True,
            ),
            padding=15,
            border_radius=10,
            bgcolor=ft.Colors.BLUE_50,
            shadow=ft.BoxShadow(
                blur_radius=10,
                color=ft.Colors.BLACK12,
                spread_radius=1,
            ),
            ink=True,
            tooltip="Ver",
            width="100%",
            **kwargs
        )

        # STEP 4: NOW it's safe to assign event handlers
        self.on_click = self._handle_click

    def _build_display_fields(self):
        """Build display fields without touching Flet event system."""
        fields = []
        if not self.attributes:
            fields.append(ft.Text("No  hay atributos para mostrar", italic=True, size=12))
        else:
            for attr in self.attributes:
                value = str(self.node.get(attr, "—"))
                fields.append(
                    ft.Text(
                        f"{attr.replace('_', ' ').title()}: {value}",
                        size=13,
                        selectable=True,
                    )
                )
        return fields

    def _handle_click(self, e):
        """Open modal dialog with full node details."""
        if not self.page:
            print("[NodeCard ERROR] No page reference — cannot open dialog")
            return

        full_fields = []
        print(self.node)
        for attr in self.full_attributes:
            value = str(self.node.get(attr.replace("`", ""), "—"))
            full_fields.append(
                ft.Row(
                    [
                        ft.Text(
                            f"{attr.replace('_', ' ').title()}:",
                            weight=ft.FontWeight.BOLD,
                            size=14,
                            expand=1,
                        ),
                        ft.Text(
                            value,
                            size=14,
                            selectable=True,
                            text_align=ft.TextAlign.RIGHT,
                            expand=2,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                )
            )

        dialog = ft.AlertDialog(
            title=ft.Text("Detalles", weight=ft.FontWeight.BOLD),
            content=ft.Column(
                full_fields,
                spacing=10,
                scroll=ft.ScrollMode.AUTO,
                height=400,
            ),
            actions=[
                ft.TextButton("Close", on_click=lambda e: self.page.close(dialog)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self.page.open(dialog)

        # Trigger user callback if provided
        if self.user_on_click:
            self.user_on_click(self.node)