
import flet as ft
import asyncio
import httpx
from typing import List, Tuple, Dict, Any, Optional

from networkx import selfloop_edges

relation_types = {
    'Author': [
        ('Output','CREATED_BY','Author')
    ],
    'Output': [
        ('Output','CREATED_BY','Author'),
        ('Output','CLASSIFIED_BY','Term'),
        ('Output','RELATED_TO','Organization')
    ], 
}


class NodeViewerCard(ft.Container):
    def __init__(
        self,
        node: Dict[str, Any],
        label: str,
        sort_attributes: List[str],
        attributes: List[str],
        on_node_selected=None,  # Callback when card is clicked
    ):
        
        print('000000000000')
        print(node)
        self.node = node

        self.sort_attributes = sort_attributes
        self.attributes = attributes
        self.on_node_selected = on_node_selected
        
        # Extract node properties
        self.node_id = node.get('id', '')
        self.node_label = label # self._extract_label()
        # self.build()
        super().__init__(
            content=self.build(), 
        )
        
    def _extract_label(self):
        # Extract label from node data (this depends on how your node data is structured)
        # If node has labels property:
        if 'labels' in self.node and isinstance(self.node['labels'], list):
            return self.node['labels'][0] if self.node['labels'] else 'Node'
        # If node structure is different, adjust accordingly
        return 'Node'

    def build(self):
        # Create chips for sort attributes
        attribute_chips = []
        for attr in self.sort_attributes:
            if attr in self.node:
                chip = ft.Chip(
                    label=ft.Text(f"{attr}: {self.node[attr]}"),
                    bgcolor=ft.Colors.PRIMARY_CONTAINER,
                )
                attribute_chips.append(chip)

        # Create the card
        self.card = ft.Card(
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(
                            f"{self.node_label} (ID: {self.node_id})",
                            size=16,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Row(
                            controls=attribute_chips,
                            wrap=True,
                        ),
                    ],
                    spacing=10,
                ),
                padding=15,
            ),
            elevation=2,
        )
        
        # Wrap in GestureDetector to handle click
        return ft.GestureDetector(
            content=self.card,
            on_tap=self.handle_card_click,
        )
    
    def handle_card_click(self, e):
        if self.on_node_selected:
            self.on_node_selected(self.node_id, self.node_label)


class NodeViewer(ft.Container):
    def __init__(
        self,
        api_url: str,
        node_id: str,
        node_label: str,
        on_back=None, 
        on_error=None,
    ):
        
        self.api_url = api_url

        self.node_id = node_id
        self.node_label = node_label
        if self.node_label  in relation_types:
            self.relations = relation_types[self.node_label]
        self.on_error = on_error
        self.on_back = on_back
        self.attributes = []
        self.src_relation_counts = []
        self.dst_relation_counts = []
        
        super().__init__(
            content=self.build()
        )
        
    def build(self):
        self.title = ft.Text("", size=20, weight=ft.FontWeight.BOLD)
        self.attributes_container = ft.Column(spacing=5)
        self.relations_container = ft.Column(spacing=10)
        
        # Back button
        back_button = ft.IconButton(
            icon=ft.Icons.ARROW_BACK,
            on_click=self.handle_back,
        )
        
        return ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        back_button,
                        self.title,
                    ],
                    alignment=ft.MainAxisAlignment.START,
                ),
                ft.Divider(),
                ft.Text("Attributes:", weight=ft.FontWeight.W_500),
                self.attributes_container,
                ft.Divider(),
                ft.Text("Relationships:", weight=ft.FontWeight.W_500),
                self.relations_container,
            ],
            spacing=10,
        )

    def handle_back(self, e):
        if self.on_back:
            self.on_back()
    
    async def fetch_node_data(self):
        try:
            # Query to get node attributes
            query = f"""
                MATCH (n:{self.node_label} {{id: $node_id}})
                RETURN n
            """
            parameters = {"node_id": self.node_id}
            
            payload = {
                "parameters": parameters,
                "query": query,
                "readonly": True
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(self.api_url, json=payload, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                if len(data) == 1:
                    node_data = data[0]['n']
                    # Exclude the id property as it's used for matching
                    self.attributes = {k: v for k, v in node_data.items() if k != 'id'}
                else:
                    self.attributes = {}
                    
        except Exception as e:
            if self.on_error:
                self.on_error(f"Error fetching node data: {str(e)}")
            else:
                print(f"Error fetching node data: {str(e)}")
    
    async def fetch_relation_counts(self):
        try:
            for label1, relation, label2 in self.relations:
                # Query to count relationships
                query = f"""
                    MATCH (n:{label1}) - [:{relation}] -> (m:{label2})
                    where n.id = $node_id
                    RETURN count(m) as count
                """
                parameters = {"node_id": self.node_id}
                
                payload = {
                    "parameters": parameters,
                    "query": query,
                    "readonly": True
                }
                print(query)
                print(parameters)
                async with httpx.AsyncClient() as client:
                    response = await client.post(self.api_url, json=payload, timeout=10.0)
                    response.raise_for_status()
                    data = response.json()
                    print('DATAAAAAAAA',data)

                    if len(data) == 1:
                        count = data[0]['count']
                        self.src_relation_counts.append((label1, relation, label2, count))

            for label1, relation, label2 in self.relations:
                # Query to count relationships
                query = f"""
                    MATCH (n:{label1}) <- [:{relation}] - (m:{label2})
                    where m.id = $node_id
                    RETURN count(n) as count
                """
                parameters = {"node_id": self.node_id}
                
                payload = {
                    "parameters": parameters,
                    "query": query,
                    "readonly": True
                }
                print(query)
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(self.api_url, json=payload, timeout=10.0)
                    response.raise_for_status()
                    data = response.json()
                    print('DATAAAAAAAA',data)
                    if len(data) == 1:
                        count = data[0]['count']
                        self.dst_relation_counts.append((label1, relation, label2, count))
                    

        except Exception as e:
            if self.on_error:
                self.on_error(f"Error fetching relation counts: {str(e)}")
            else:
                print(f"Error fetching relation counts: {str(e)}")
    
    def _create_attribute_chips(self):
        chips = []
        print(self.attributes)
        for key, value in self.attributes.items():
            chip = ft.Chip(
                label=ft.Text(f"{key}: {value}"),
                bgcolor=ft.Colors.PRIMARY_CONTAINER,
            )
            chips.append(chip)
            print(chip.label)
        print(chips)
        return chips
    
    def _create_relation_chips(self):
        chips = []
        print('AAAAAAAAAAAAAAAAAAa',self.src_relation_counts)
        print('AAAAAAAAAAAAAAAAAAa',self.dst_relation_counts)
        for (label1, relation, label2, count) in self.src_relation_counts:
            chip = ft.Chip(
                label=ft.Text(f"{relation} -> {label2}: {count}"),
                bgcolor=ft.Colors.SECONDARY_CONTAINER,
            )
            chips.append(chip)
        for (label1, relation, label2, count) in self.dst_relation_counts:
            chip = ft.Chip(
                label=ft.Text(f"{label2} -> {relation}: {count}"),
                bgcolor=ft.Colors.SECONDARY_CONTAINER,
            )
            chips.append(chip)
        return chips
    
    async def load_data(self):
        await self.fetch_node_data()
        await self.fetch_relation_counts()
        self.title.value = f"{self.node_label} (ID: {self.node_id})"
        self.attributes_container.controls = self._create_attribute_chips()
        self.relations_container.controls = self._create_relation_chips()
        self.content = self.build()
        self.update()

    def did_mount(self):
        self.page.run_task(self.load_data)
        
        
        # self.update()