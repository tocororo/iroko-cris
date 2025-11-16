import asyncio
import json
import logging
from abc import abstractmethod
import traceback
from typing import Dict, Any
import httpx
from lxml import html 

from iroko.storage import neo4j_db
from iroko.tasks.schemas import TaskExecution
from iroko.tasks.task import CrawlerTask
from random import randint
from iroko.tasks.task import http_task_headers
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
        
        # Load or collect journal data
        if "input" in self.config:
            with open(self.config['input'], 'r') as f:
                data = json.load(f)
                all_journals = data['all_journals']
        else: 
            all_journals = await self._collect_journals()
            data = {
                "present": [j for j in all_journals if j.get("date") == 2025],
                "no_present": [j for j in all_journals if j.get("date") != 2025],
                "not_found": [],
                "all_journals": all_journals
            }

        # Process journals and create relationships
        await self._process_journals_to_neo4j(all_journals, data)
        
        # Save output
        await self._save_output(data)
        
        self.logger.info(f"Completed Scielo processing task {self.task_id}")
        return data

    async def _collect_journals(self) -> list:
        """Collect journal list from Scielo website."""
        url = "http://scielo.sld.cu/scielo.php?script=sci_alphabetic&lng=es&nrm=iso"
        async with httpx.AsyncClient(headers=http_task_headers, timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()

        tree = html.fromstring(response.content)
        all_journals = []

        # Find the section for "Títulos vigentes"
        present_header = tree.xpath("//p[contains(text(), 'Títulos vigentes')]")
        if present_header:
            present_list = present_header[0].getnext()
            for li in present_list.xpath(".//li"):
                journal_info = self._extract_journal_info(li)
                if journal_info:
                    journal_info["date"] = 2025
                    all_journals.append(journal_info)

        # Find the section for "Títulos no vigentes"
        no_present_header = tree.xpath("//p[contains(text(), 'Títulos no vigentes')]")
        if no_present_header:
            no_present_list = no_present_header[0].getnext()
            for li in no_present_list.xpath(".//li"):
                journal_info = self._extract_journal_info(li)
                if journal_info:
                    # Extract date for non-present journals
                    date_text = li.text_content()
                    date_match = re.search(r'(?:Indización interrumpida|Terminado)\s+por?\s+el?\s+comité?\s+.*?(\d{4})|(\d{4})\s*:\s*(?:Indización interrumpida|Terminado)', date_text)
                    journal_info["date"] = int(date_match.group(1) or date_match.group(2)) if date_match else None
                    all_journals.append(journal_info)

        self.logger.info(f"Collected {len(all_journals)} journals total.")
        return all_journals

    def _extract_journal_info(self, li_element) -> dict:
        """Extract journal information from list element."""
        link_element = li_element.xpath(".//a")
        if not link_element:
            return None
            
        title = link_element[0].text_content().strip()
        link = link_element[0].get("href")
        
        # Extract numbers
        numbers_text = li_element.text_content()
        numbers_match = re.search(r'(\d+)\s*números?', numbers_text)
        numbers = int(numbers_match.group(1)) if numbers_match else None
        
        return {
            "title": title, 
            "link": link, 
            "numbers": numbers
        }

    async def _process_journals_to_neo4j(self, all_journals: list, data: dict):
        """Process journals and create IN_INDEX relationships in Neo4j."""
        session = neo4j_db.get_session()
        processed_count = 0
        error_count = 0

        try:
            # Find or create Scielo Index node
            scielo_index_id = await self._get_or_create_scielo_index(session)
            if not scielo_index_id:
                self.logger.error("Failed to get or create Scielo index node")
                return

            for journal_info in all_journals:
                try:
                    success = await self._process_single_journal(session, journal_info, scielo_index_id, data)
                    if success:
                        processed_count += 1
                    else:
                        error_count += 1
                except Exception as e:
                    self.logger.error(f"Error processing journal {journal_info.get('title')}: {e}")
                    error_count += 1
                    data["not_found"].append(journal_info)

            self.logger.info(f"Processed {processed_count} journals successfully, {error_count} failed")

        except Exception as e:
            self.logger.error(f"Error in journal processing: {e}")
            print(traceback.format_exc())
        finally:
            await session.close()

    async def _get_or_create_scielo_index(self, session) -> str:
        """Get or create the Scielo index node."""
        # Try to find existing Scielo Index
        query_find = "MATCH (i:Index {name: 'Scielo'}) RETURN i.name as name"
        result = await session.run(query_find)
        record = await result.single()
        
        if record:
            self.logger.info("Found existing Scielo Index node")
            return "Scielo"  # Using name as identifier
        
        # Create new Scielo Index node
        query_create = """
        CREATE (i:Index {name: 'Scielo', vocabulary: 'INDEXES' , source: 'Scielo Cuba'})
        RETURN i.name as name
        """
        result = await session.run(query_create)
        record = await result.single()
        
        if record:
            self.logger.info("Created new Scielo Index node")
            return record["name"]
        
        return None

    async def _process_single_journal(self, session, journal_info: dict, index_id: str, data: dict) -> bool:
        """Process a single journal and create IN_INDEX relationship."""
        link = journal_info["link"]
        match = re.search(r'[?&]pid=([^&#]*)', link)
        found_issn = match.group(1) if match else None

        if not found_issn:
            journal_info["issn"] = None
            self.logger.warning(f"Could not find ISSN for journal {journal_info['title']} at {link}.")
            return False

        journal_info["issn"] = found_issn

        # Find publication by ISSN
        publication = await self._find_publication_by_issn(session, found_issn)
        if not publication:
            # Try to find by title
            publication = await self._find_publication_by_title(session, journal_info["title"])
        
        if not publication:
            self.logger.warning(f"Publication with ISSN {found_issn} (from {journal_info['title']}) not found in Neo4j database.")
            return False

        # Create or update IN_INDEX relationship
        success = await self._create_or_update_relationship(
            session, publication, index_id, journal_info
        )
        
        return success

    async def _find_publication_by_issn(self, session, issn: str) -> dict:
        """Find publication by any ISSN type."""
        query = """
        MATCH (p:Publication) 
        WHERE p.`identifier#issn_p` = $issn OR 
              p.`identifier#issn_e` = $issn OR 
              p.`identifier#issn_l` = $issn OR 
              p.`identifier#issn_o` = $issn OR 
              p.`identifier#issn_c` = $issn 
        RETURN p.name as name, p.`identifier#issn_l` as issn_l
        LIMIT 1
        """
        result = await session.run(query, issn=issn)
        record = await result.single()
        return record if record else None

    async def _find_publication_by_title(self, session, title: str) -> dict:
        """Find publication by title (fuzzy matching)."""
        query = """
        MATCH (p:Publication) 
        WHERE toLower(p.name) CONTAINS toLower($title)
        RETURN p.name as name, p.`identifier#issn_l` as issn_l
        LIMIT 1
        """
        result = await session.run(query, title=title)
        record = await result.single()
        return record if record else None

    async def _create_or_update_relationship(self, session, publication: dict, index_id: str, journal_info: dict) -> bool:
        """Create or update IN_INDEX relationship."""
        # Check if relationship already exists
        query_check = """
        MATCH (p:Publication {name: $pub_name})-[r:IN_INDEX]->(i:Index {name: $index_name})
        RETURN r
        """
        result = await session.run(query_check, pub_name=publication["name"], index_name=index_id)
        existing_rel = await result.single()

        if existing_rel:
            # Update existing relationship
            query_update = """
            MATCH (p:Publication {name: $pub_name})-[r:IN_INDEX]->(i:Index {name: $index_name})
            SET r.source = $source, r.numbers = $numbers, r.date = $date,
                r.updated_at = timestamp()
            """
            await session.run(query_update, 
                            pub_name=publication["name"],
                            index_name=index_id,
                            source="Scielo", 
                            numbers=journal_info.get("numbers"), 
                            date=journal_info.get("date"))
            self.logger.debug(f"Updated IN_INDEX relationship for {journal_info['title']}")
        else:
            # Create new relationship
            query_create = """
            MATCH (p:Publication {name: $pub_name})
            MATCH (i:Index {name: $index_name})
            CREATE (p)-[r:IN_INDEX {source: $source, numbers: $numbers, date: $date, created_at: timestamp()}]->(i)
            """
            await session.run(query_create,
                            pub_name=publication["name"],
                            index_name=index_id,
                            source="Scielo",
                            numbers=journal_info.get("numbers"),
                            date=journal_info.get("date"))
            self.logger.debug(f"Created IN_INDEX relationship for {journal_info['title']}")

        return True

    async def _save_output(self, data: dict):
        """Save output data to JSON file."""
        try:
            with open(self.output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Output results written to {self.output_path}")
        except Exception as e:
            self.logger.error(f"Failed to write output file {self.output_path}: {e}")
            raise

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
        if not isinstance(self.config['output_json_path'], str):
            self.logger.error("Config key 'output_json_path' must be a string.")
            return False
        return True