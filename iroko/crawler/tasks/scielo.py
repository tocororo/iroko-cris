import asyncio
import json
import logging
from abc import abstractmethod
from typing import Dict, Any
import httpx
from lxml import html 

from iroko.storage import neo4j_db
from iroko.crawler.schemas import TaskExecution
from iroko.crawler.task import CrawlerTask
from random import randint

import re

def _convert_x_to_10(x):
    """Convert char to int with X being converted to 10."""
    return int(x) if x != "X" else 10


class ScieloProcessingTask(CrawlerTask):
    """Task to process Scielo journal data and update Neo4j database."""

    def __init__(self, task_id: str, name: str, config: Dict[str, Any] = None):
        super().__init__(task_id, name, config)
        self.output_path = self.config.get('output_json_path')
        if not self.output_path:
            raise ValueError("Config must contain 'output_json_path'.")



    async def execute(self, execution: TaskExecution) -> Dict[str, Any]:
        """
        Execute the Scielo processing task.
        """
        self.logger.info(f"Starting Scielo processing task {self.task_id}")

        # --- Step 1: Collect journal list from Scielo website ---
        url = "http://scielo.sld.cu/scielo.php?script=sci_alphabetic&lng=es&nrm=iso"
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()

        tree = html.fromstring(response.content)

        data = {"present": [], "no_present": [], "not_found": []}
        all_journals = []

        # Find the section for "Títulos vigentes"
        present_header = tree.xpath("//p[contains(text(), 'Títulos vigentes')]")[0]
        present_list = present_header.getnext() # The following <ul> element
        for li in present_list.xpath(".//li"):
             # Extract title and link
             link_element = li.xpath(".//a")[0]
             title = link_element.text_content().strip()
             link = link_element.get("href")
             # Extract numbers
             numbers_text = li.text_content()
             numbers_match = re.search(r'(\d+)\s*números?', numbers_text)
             numbers = int(numbers_match.group(1)) if numbers_match else None
             data["present"].append({"title": title, "link": link, "numbers": numbers, "date": 2025})
             all_journals.append({"title": title, "link": link, "numbers": numbers, "date": 2025})

        # Find the section for "Títulos no vigentes"
        no_present_header = tree.xpath("//p[contains(text(), 'Títulos no vigentes')]")[0]
        no_present_list = no_present_header.getnext() # The following <ul> element
        for li in no_present_list.xpath(".//li"):
             # Extract title and link
             link_element = li.xpath(".//a")[0]
             title = link_element.text_content().strip()
             link = link_element.get("href")
             # Extract numbers
             numbers_text = li.text_content()
             numbers_match = re.search(r'(\d+)\s*números?', numbers_text)
             numbers = int(numbers_match.group(1)) if numbers_match else None
             # Extract date
             date_text = li.text_content()
             # Look for year after common phrases like "Indización interrumpida", "Terminado"
             date_match = re.search(r'(?:Indización interrumpida|Terminado)\s+por?\s+el?\s+comité?\s+.*?(\d{4})|(\d{4})\s*:\s*(?:Indización interrumpida|Terminado)', date_text)
             date = int(date_match.group(1) or date_match.group(2)) if date_match else None
             data["no_present"].append({"title": title, "link": link, "numbers": numbers, "date": date})
             all_journals.append({"title": title, "link": link, "numbers": numbers, "date": date})

        self.logger.info(f"Collected {len(data['present'])} present and {len(data['no_present'])} no present journals.")

        # --- Step 2 & 3: Process each present journal ---
        # Get Neo4j session
        session = await neo4j_db.get_session()

        try:
            # Find Scielo Index node once
            query_find_scielo_index = (
                "MATCH (i:Index { name: 'Scielo' }) RETURN i LIMIT 1"
            )
            result_scielo = await session.run(query_find_scielo_index)
            scielo_index_record = await result_scielo.single()
            if not scielo_index_record:
                 self.logger.error("Index node with name 'Scielo' not found in Neo4j.")
                 raise ValueError("Required Index 'Scielo' not found in database.")
            scielo_index_id = scielo_index_record["i"]._id

            for journal_info in all_journals:
                sleep_time = randint(1, 4)
                self.logger.info(f'sleep {sleep_time}')
                await asyncio.sleep(sleep_time)
                
                link = journal_info["link"]
                async with httpx.AsyncClient() as client:
                    response = await client.get(link)
                    response.raise_for_status()

                inner_tree = html.fromstring(response.content)
                # Look for the specific span element containing the ISSN
                issn_elements = inner_tree.xpath("//span[@class='issn']")
                found_issn = None
                if issn_elements:
                     # The text content of the span often contains the ISSN directly
                    issn_text_node = issn_elements[0].xpath("./font/following-sibling::text()[1]")
                    if issn_text_node:
                        full_text = issn_text_node[0].strip() # Get the first matching text node
                        val = full_text.replace("-", "").replace(" ", "").upper()
                        if len(val) == 8:
                            r = sum([(8 - i) * (_convert_x_to_10(x)) for i, x in enumerate(val)])
                            self.logger.warning(r)
                            if not (r % 11):found_issn = full_text
                if found_issn:
                    # Query 1: Find by ISSN
                    query_find_by_issn = (
                        "MATCH (p:Publication) WHERE "
                        "p.`identifier#issn_p` = $issn OR "
                        "p.`identifier#issn_e` = $issn OR "
                        "p.`identifier#issn_l` = $issn OR "
                        "p.`identifier#issn_o` = $issn OR "
                        "p.`identifier#issn_c` = $issn "
                        "RETURN p LIMIT 1"
                    )
                    result_issn = await session.run(query_find_by_issn, issn=found_issn)
                    pub_record = await result_issn.single()

                    if not pub_record:
                        title = journal_info["title"]
                        query_by_name = (
                            "MATCH (p:Publication) WHERE p.name=$title return p"
                        )
                        result_name = await session.run(query_by_name, title=title)
                        pub_record = await result_name.single()

                    if pub_record:
                        pub_node_id = pub_record["p"]._id
                        # Add ISSNs to the journal info dict
                        journal_info["issn"] = found_issn
                        # Step 3: Create or update IN_INDEX relationship
                        # Query to check for existing relationship
                        query_check_rel = (
                            "MATCH (p) WHERE id(p) = $pub_id "
                            "MATCH (i) WHERE id(i) = $index_id "
                            "OPTIONAL MATCH (p)-[r:IN_INDEX]->(i) "
                            "RETURN r"
                        )
                        result_rel = await session.run(query_check_rel, pub_id=pub_node_id, index_id=scielo_index_id)
                        rel_record = await result_rel.single()

                        if rel_record and rel_record["r"] is not None:
                            # Relationship exists, update its properties
                            rel_id = rel_record["r"]._id
                            query_update_rel = (
                                "MATCH ()-[r:IN_INDEX]->() WHERE id(r) = $rel_id "
                                "SET r.source = $source, r.numbers = $numbers, r.date = $date"
                            )
                            await session.run(query_update_rel, rel_id=rel_id, source="Scielo", numbers=journal_info.get("numbers"), date=journal_info.get("date"))
                            self.logger.debug(f"Updated existing IN_INDEX relationship for {journal_info['title']} ({found_issn}).")
                        else:
                            # Relationship does not exist, create it
                            query_create_rel = (
                                "MATCH (p) WHERE id(p) = $pub_id "
                                "MATCH (i) WHERE id(i) = $index_id "
                                "CREATE (p)-[:IN_INDEX {source: $source, numbers: $numbers, date: $date}]->(i)"
                            )
                            await session.run(query_create_rel, pub_id=pub_node_id, index_id=scielo_index_id, source="Scielo", numbers=journal_info.get("numbers"), date=journal_info.get("date"))
                            self.logger.debug(f"Created new IN_INDEX relationship for {journal_info['title']} ({found_issn}).")
                    else:
                        # Publication not found in DB based on ISSN
                        journal_info["issn"] = found_issn
                        data["not_found"].append(journal_info)
                        self.logger.warning(f"Publication with ISSN {found_issn} (from {journal_info['title']}) not found in Neo4j database.")
                else:
                    # Could not parse ISSN from the page
                    journal_info["issn"] = None
                    data["not_found"].append(journal_info)
                    self.logger.warning(f"Could not find ISSN for journal {journal_info['title']} at {link}.")

        finally:
            await session.close() # Ensure session is closed

        # --- Step 4: Save data dict to output file ---
        try:
            with open(self.output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Output results written to {self.output_path}")
        except Exception as e:
            self.logger.error(f"Failed to write output file {self.output_path}: {e}")
            raise # Re-raise to fail the task

        self.logger.info(f"Completed Scielo processing task {self.task_id}")
        return data


    def validate_config(self) -> bool:
        """
        Validate task configuration.
        Requires 'output_json_path'
        """
        required_keys = ['output_json_path']
        for key in required_keys:
            if key not in self.config or not self.config[key]:
                self.logger.error(f"Missing or empty required config key: {key}")
                return False
        # Validate path is a string
        if not isinstance(self.config['output_json_path'], str):
             self.logger.error("Config key 'output_json_path' must be a string.")
             return False

        return True

