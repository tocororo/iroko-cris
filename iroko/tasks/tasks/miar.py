from abc import ABC
import json
from pathlib import Path
import traceback
from typing import Dict, Any, List, Optional
import asyncio
import logging
from urllib.parse import urljoin

from uuid import UUID

from iroko.storage import neo4j_db
from iroko.database import AsyncSessionLocal
from iroko.nodes.service import NodeService

import httpx
from lxml import html
from neo4j.graph import Node 

from iroko.tasks.schemas import TaskExecution
from iroko.tasks.task import CrawlerTask
from iroko.tasks.task import http_task_headers
from random import randint

logger = logging.getLogger('iroko-cris.tasks')


class FixMiarIndexs(CrawlerTask):

    async def execute(self, execution: TaskExecution) -> Dict[str, Any]:
        execution.execution_log.append("load data")
        session = neo4j_db.get_session()
        async with AsyncSessionLocal() as pg_session:
            service = NodeService(pg_session, session)
            data_file = self.config.get("data_file")        
            
            with open(data_file, 'r') as f:
                data = json.load(f)
            
            try:
                db_entries = []
                for group in data:
                    db_entries.append({"name": group["name"], "url": group["url"]})
                    for db in group.get("dbs", []):
                        db_entries.append({"name": db["name"], "url": db["url"]})
                
                total_updated = 0
                execution.execution_log.append("build query")
                for entry in db_entries:
                    result = await session.run(
                        "MATCH (n:Index {name: $name}) RETURN n.iroko_uuid as uuid LIMIT 1",
                        name=entry["name"]
                    )
                    record = await result.single()
                    if record and record.get("uuid"):
                        await service.set_node_properties(UUID(record["uuid"]), {"identifier#url": entry["url"]})
                        total_updated += 1

                execution.execution_log.append(f"""
                    "status": "success",
                    "total_updated": {total_updated},
                    "total_processed": {len(db_entries)}""")

            except Exception as e:
                return {"status": "error", "error": str(e)}
            finally:
                await session.close()
                return {"status": "success", "total_updated": total_updated, "total_processed": len(db_entries)}

    def validate_config(self) -> bool:
        """
        Validate task configuration
        
        Returns:
            True if configuration is valid
        """
        return "data_file" in self.config

    def get_dependencies(self) -> List[str]:
        """
        Get list of task IDs that this task depends on
        
        Returns:
            List of task IDs
        """
        return []


class ColectMiarIndexes(CrawlerTask):
    """Abstract base class for all crawler tasks"""


    async def extract_databases_from_miar(self, client, url):
        """
        Extract database names and URLs from MIAR database page, considering pagination.
        Attempts to get the full list by setting ini=0 and rgs=1000 (or the total number of records).
        """
        # First, get the initial page to understand the total number of records and structure
        response = await client.get(url)
        if response.status_code != 200:
            self.logger.info(f"Failed to retrieve initial page {url}: {response.status_code}")
            return []

        tree = html.fromstring(response.content)
        sleep_time = randint(1, 5)
        logger.info(f'sleep {sleep_time}')
        await asyncio.sleep(sleep_time)

        # Check for the "show all records" link or form parameters
        # The form name is 'f_actual' based on the HTML
        # Hidden inputs: ini (start index), rgs (records per page)
        # The link "show 13 rgs." suggests we can set ini=0 and rgs=total_count
        total_records_text = tree.xpath('//span[@id="total_registros"]/text()')
        total_count = 0
        if total_records_text:
            # Extract number from "13 sources" or similar
            import re
            match = re.search(r'(\d+)', total_records_text[0])
            if match:
                total_count = int(match.group(1))
        
        self.logger.info(f"Found {total_count} total records for {url}")

        # Construct URL to get all records at once
        # The form action seems to be the same as the current URL
        full_list_params = {
            'ini': 0,
            'rgs': total_count if total_count > 0 else 1000  # Fallback if parsing failed
        }
        
        full_list_url = url
        if total_count > 0: # Only add params if we know the count
            full_list_url = f"{url}?ini={full_list_params['ini']}&rgs={full_list_params['rgs']}"
        
        self.logger.info(f"Fetching full list from: {full_list_url}")
        full_response = await client.get(full_list_url)
        if full_response.status_code != 200:
            self.logger.info(f"Failed to retrieve full list page {full_list_url}: {full_response.status_code}")
            return [] # Return empty list if we can't get the full list

        full_tree = html.fromstring(full_response.content)

        databases = []

        # Extract database entries from the table in the full list page
        table_rows = full_tree.xpath('//table[@id="tabla-0"]//tbody/tr')

        for row in table_rows:
            # Find the link in the first column (td[1] in xpath, which is index 0)
            name_cell = row.xpath('./td[1]')[0] if row.xpath('./td[1]') else None
            if name_cell is not None:
                link_elements = name_cell.xpath('.//a')
                if link_elements:
                    link_element = link_elements[0]
                    name = link_element.text_content().strip()
                    relative_url = link_element.get('href', '')
                    
                    # Convert relative URL to absolute URL
                    if relative_url.startswith('/'):
                        absolute_url = 'https://miar.ub.edu' + relative_url
                    elif relative_url.startswith('http'):
                        absolute_url = relative_url
                    else:
                        absolute_url = url.rsplit('/', 1)[0] + '/' + relative_url
                    
                    databases.append({
                        "name": name,
                        "url": absolute_url
                    })
                else:
                    # If there's no link, just get the text content as name
                    # This shouldn't happen based on the example HTML, but let's handle it
                    name = name_cell.text_content().strip()
                    # For databases without individual pages, we'll use the group URL as their identifier
                    databases.append({
                        "name": name,
                        "url": url  # Using the group URL as the identifier for databases without individual pages
                    })

        self.logger.info(f"Extracted {len(databases)} databases from {url}")
        return databases

    async def extract_and_add_databases_to_neo4j(self, session, service, client, url, group_name):
        """
        Extract database names and URLs from MIAR database page and add/update nodes via NodeService
        """
        databases = []
        if "input" in self.config:
            with open(self.config['input'], 'r') as f:
                groups = json.load(f)
                for g in groups.keys():
                    for db in groups[g]:
                        databases.append(db)

        else:
            databases = await self.extract_databases_from_miar(client, url)

            sleep_time = randint(1, 5)
            logger.info(f'sleep {sleep_time}')
            await asyncio.sleep(sleep_time)

        # Get group node uuid
        g_result = await session.run(
            "MATCH (g:Index {`identifier#url`: $group_url}) RETURN g.iroko_uuid as uuid",
            group_url=url
        )
        g_record = await g_result.single()
        if not g_record or not g_record.get("uuid"):
            logger.warning(f"Group Index node not found for URL: {url}")
            return databases
        group_uuid = UUID(g_record["uuid"])

        for db in databases:
            node = await service.merge_node(
                name=db["name"],
                labels=['Index', 'Term'],
                data={'identifier#url': db["url"], 'vocabulary': 'INDEXES'}
            )
            await service.merge_relationship(node.iroko_uuid, group_uuid, "IN_GROUP")

        return databases

    async def execute(self, execution: TaskExecution) -> Dict[str, Any]:
        execution.execution_log.append("load data")
        session = neo4j_db.get_session()
        async with AsyncSessionLocal() as pg_session:
            service = NodeService(pg_session, session)
            async with httpx.AsyncClient(headers=http_task_headers, timeout=30.0) as client:
                try:
                    groups = {
                        "Citation databases": "https://miar.ub.edu/databases/GRUPO/G",
                        "Multidisciplinary databases": "https://miar.ub.edu/databases/GRUPO/S", 
                        "Specialized databases": "https://miar.ub.edu/databases/GRUPO/E",
                        "Evaluation resources": "https://miar.ub.edu/databases/GRUPO/M"
                    }
                    
                    all_databases = {}
                    for group_name, group_url in groups.items():
                        print(f"Processing {group_name}...")
                        databases = await self.extract_and_add_databases_to_neo4j(session, service, client, group_url, group_name)
                        all_databases[group_name] = databases
                        print(f"Found {len(databases)} databases in {group_name}")

                    with open(self.config["output"], "w", encoding="utf-8") as f:
                        json.dump(all_databases, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    print(traceback.format_exc())
                    return {"status": "error", "error": str(e)}
                finally:
                    await session.close()
            return {"status": "success", "miar_databases": all_databases, "total_processed": len(all_databases)}

    def validate_config(self) -> bool:
        """
        Validate task configuration
        
        Returns:
            True if configuration is valid
        """
        return "output" in self.config

    def get_dependencies(self) -> List[str]:
        """
        Get list of task IDs that this task depends on
        
        Returns:
            List of task IDs
        """
        return []


class MiarCubaJournalsCrawler(CrawlerTask):
    """Crawler to extract Cuban journals from MIAR and their diffusion metadata."""

    BASE_URL = "https://miar.ub.edu"

    def __init__(self, task_id: str, name: str, config: Dict[str, Any] = None):
        super().__init__(task_id, name, config)
        self.session: Optional[httpx.AsyncClient] = None

    def validate_config(self) -> bool:
        return "output" in self.config

    def get_dependencies(self) -> List[str]:
        return []

    async def _fetch_html(self, url: str) -> html.HtmlElement:
        """Fetch URL and return parsed lxml HtmlElement."""
        if not self.session:
            raise RuntimeError("HTTP session not initialized")
        response = await self.session.get(url)
        response.raise_for_status()
        return html.fromstring(response.text, base_url=url)

    async def _extract_journal_list(self) -> List[Dict[str, str]]:
        """Extract full list of Cuban journals using POST with rgs=215."""
        list_url = f"{self.BASE_URL}/lista/PAIS/--Q1U"
        
        # POST data to get all 215 records at once
        form_data = {
            "directorio": "miar",
            "letra": "",
            "ini": "0",
            "rgs": "215"
        }

        if not self.session:
            raise RuntimeError("HTTP session not initialized")
        
        response = await self.session.post(list_url, data=form_data)
        response.raise_for_status()
        tree = html.fromstring(response.text, base_url=self.BASE_URL)

        journals = []
        rows = tree.xpath('//table[@id="tabla-0"]//tbody/tr')
        
        for row in rows:
            issn_cell = row.xpath('.//td[contains(@class, "issn")]/a')
            title_cell = row.xpath('.//td[contains(@class, "TITLE")]')
            if issn_cell and title_cell:
                issn = issn_cell[0].text_content().strip()
                title = title_cell[0].text_content().strip()
                detail_url = f"{self.BASE_URL}/issn/{issn}"
                journals.append({
                    "issn": issn,
                    "title": title,
                    "url": detail_url
                })

        self.logger.info(f"Successfully extracted {len(journals)} Cuban journals (out of 215 expected).")
        return journals

    async def _extract_diffusion_data(self, tree: html.HtmlElement) -> Dict[str, List[str]]:
        """Extract diffusion info from the 'Diffusion' tab content in #Revista section."""
        diffusion = {
            "citation_databases": [],
            "multidisciplinary_databases": [],
            "specialized_databases": [],
            "evaluation_resources": []
        }

        # Specialized databases (table id: tabla-tblE)
        specialized_rows = tree.xpath('//table[@id="tabla-tblE"]//tr[td/i[@class="glyphicon glyphicon-ok"]]')
        for row in specialized_rows:
            db_name = row.xpath('./td[1]/text()')
            if db_name:
                diffusion["specialized_databases"].append(db_name[0].strip())

        # Multidisciplinary databases (table id: tabla-tblS)
        multidisciplinary_rows = tree.xpath('//table[@id="tabla-tblS"]//tr[td/i[@class="glyphicon glyphicon-ok"]]')
        for row in multidisciplinary_rows:
            db_name = row.xpath('./td[1]/text()')
            if db_name:
                diffusion["multidisciplinary_databases"].append(db_name[0].strip())

        # Citation databases (table id: tabla-tblG)
        citation_rows = tree.xpath('//table[@id="tabla-tblG"]//tr[td/i[@class="glyphicon glyphicon-ok"]]')
        for row in citation_rows:
            db_name = row.xpath('./td[1]/text()')
            if db_name:
                diffusion["citation_databases"].append(db_name[0].strip())

        # Evaluation resources (table id: tabla-tblM)
        evaluation_rows = tree.xpath('//table[@id="tabla-tblM"]//tr[td/i[@class="glyphicon glyphicon-ok"]]')
        for row in evaluation_rows:
            db_name = row.xpath('./td[1]/text()')
            if db_name:
                diffusion["evaluation_resources"].append(db_name[0].strip())

        return diffusion

    async def _extract_journal_details(self, journal: Dict[str, str]) -> Dict[str, Any]:
        """Extract full metadata from a journal's detail page."""
        tree = await self._fetch_html(journal["url"])

        # Basic metadata from #Revista tab
        title_elem = tree.xpath('//h2[@id="pagina_titulo"]/text()')
        title = title_elem[0].strip() if title_elem else journal["title"]

        country_elem = tree.xpath('//span[@id="PAIS"]/a/text()')
        country = country_elem[0].strip() if country_elem else "Cuba"

        url_elem = tree.xpath('//div[@id="divtxt_Revista_7"]/a/@href')
        url = url_elem[0] if url_elem else ''

        subject_elem = tree.xpath('//span[@id="AMBITO0"]/a/text()')
        subject = subject_elem[0].strip() if subject_elem else ""

        academic_fields = "; ".join([
            el.strip() for el in tree.xpath('//div[@id="divtxt_Revista_10"]//a/text()')
        ])

        # Diffusion data
        diffusion = await self._extract_diffusion_data(tree)
        print(url)
        print('AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAaaa')
        return {
            "issn": journal["issn"],
            "title": title,
            "url": url,
            "country": country,
            "subject": subject,
            "academic_fields": academic_fields,
            "diffusion": diffusion
        }

    async def execute(self, execution: TaskExecution) -> Dict[str, Any]:
        """Main execution method."""
        self.logger.info("Starting MIAR Cuba journals crawl task")

        self.session = httpx.AsyncClient(headers=http_task_headers,timeout=30.0, follow_redirects=True)

        try:
            # Step 1: Get list of journals
            journals_list = await self._extract_journal_list()
            if not journals_list:
                self.logger.warning("No journals found on list page")
                return {"success": False, "error": "No journals found"}

            # Step 2: Crawl each journal detail page
            results = []
            total = len(journals_list)
            for i, journal in enumerate(journals_list, 1):
                self.logger.info(f"Processing {i}/{total}: {journal['issn']} - {journal['title']}")
                try:
                    details = await self._extract_journal_details(journal)
                    results.append(details)
                except Exception as e:
                    self.logger.error(f"Error processing {journal['issn']}: {e}")
                    continue

                # Be respectful: small delay between requests
                sleep_time = randint(1, 4)
                self.logger.info(f'sleep {sleep_time}')
                await asyncio.sleep(sleep_time)


            result = {
                "success": True,
                "journals_count": len(results),
                "journals": results,
                
            }
            self.logger.info(f"Successfully extracted data for {len(results)} journals")
            with open(self.config["output"], "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            return result

        finally:
            if self.session:
                await self.session.aclose()


class MiarJournalsProcessingTask(CrawlerTask):
    """Task to process MIAR journal data and update Neo4j database."""

    def __init__(self, task_id: str, name: str, config: Dict[str, Any] = None):
        super().__init__(task_id, name, config)
        self.output_path = self.config.get('output_json_path')
        self.input_path = self.config.get('input_json_path')
        if not self.output_path or not self.input_path:
            raise ValueError("Config must contain 'output_json_path' and 'input_json_path'.")

    async def execute(self, execution: TaskExecution) -> Dict[str, Any]:
        self.logger.info(f"Starting MIAR data processing task {self.task_id}")

        try:
            with open(self.input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            self.logger.error(f"Input file not found: {self.input_path}")
            raise
        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON in input file: {self.input_path}")
            raise

        if not data.get("success", False):
            self.logger.error(f"Input data indicates failure: {self.input_path}")
            raise ValueError("Input data indicates failure.")

        journals = data.get("journals", [])
        self.logger.info(f"Processing {len(journals)} journals from input data.")

        output_results = {
            "issn": [], "name": [], "new": [],
            "index_not_found": [], "old_index": []
        }

        session = neo4j_db.get_session()
        async with AsyncSessionLocal() as pg_session:
            service = NodeService(pg_session, session)
            try:
                for journal in journals:
                    issn = journal.get("issn")
                    title = journal.get("title")
                    url = journal.get("url")
                    pub_uuid = None

                    if not issn:
                        self.logger.warning(f"Journal missing ISSN, skipping: {title}")
                        continue

                    # Find by ISSN
                    r1 = await session.run(
                        "MATCH (p:Publication) WHERE "
                        "p.`identifier#issn_p` = $issn OR p.`identifier#issn_e` = $issn OR "
                        "p.`identifier#issn_l` = $issn OR p.`identifier#issn_o` = $issn OR "
                        "p.`identifier#issn_c` = $issn "
                        "RETURN p.iroko_uuid as uuid", issn=issn)
                    record = await r1.single()
                    if record:
                        output_results["issn"].append(issn)
                        pub_uuid = record["uuid"]
                    else:
                        # Find by name
                        r2 = await session.run(
                            "MATCH (p:Publication) WHERE p.name = $title RETURN p.iroko_uuid as uuid",
                            title=title)
                        record = await r2.single()
                        if record:
                            output_results["name"].append(issn)
                            pub_uuid = record["uuid"]
                        else:
                            # Create via NodeService
                            node = await service.merge_node(
                                name=title,
                                labels=['Publication'],
                                data={'identifier#issn_e': issn, 'identifier#issn_l': issn, 'identifier#url': url}
                            )
                            output_results["new"].append(issn)
                            pub_uuid = str(node.iroko_uuid)

                    if pub_uuid:
                        if url and url.strip():
                            r3 = await session.run(
                                "MATCH (p:Publication {iroko_uuid: $uuid}) "
                                "RETURN p.`identifier#url` as url", uuid=pub_uuid)
                            existing = await r3.single()
                            if existing and existing.get("url") in (None, ""):
                                await service.set_node_properties(UUID(pub_uuid), {"identifier#url": url})

                        diffusion = journal.get("diffusion", {})
                        all_idx_names = []
                        for cat, lst in diffusion.items():
                            if isinstance(lst, list):
                                all_idx_names.extend(lst)

                        for idx_name in all_idx_names:
                            r4 = await session.run(
                                "MATCH (i:Index) WHERE i.name = $n RETURN i.iroko_uuid as uuid",
                                n=idx_name)
                            idx_rec = await r4.single()
                            if idx_rec and idx_rec.get("uuid"):
                                await service.merge_relationship(
                                    UUID(pub_uuid), UUID(idx_rec["uuid"]), "IN_INDEX",
                                    {"source": "MIAR", "date": 2025})
                            else:
                                if idx_name not in output_results["index_not_found"]:
                                    output_results["index_not_found"].append(idx_name)

                # Step 3: Fix old IN_INDEX relationships missing source/date
                r5 = await session.run(
                    "MATCH (p:Publication)-[r:IN_INDEX]->(i:Index) "
                    "WHERE r.source IS NULL OR r.date IS NULL "
                    "RETURN p.iroko_uuid as pub_uuid, i.iroko_uuid as idx_uuid")
                async for rec in r5:
                    output_results["old_index"].append(rec["idx_uuid"])
                    await service.merge_relationship(
                        UUID(rec["pub_uuid"]), UUID(rec["idx_uuid"]), "IN_INDEX",
                        {"source": "MIAR", "date": 2022})

            finally:
                await session.close()

        try:
            with open(self.output_path, 'w', encoding='utf-8') as f:
                json.dump(output_results, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Failed to write output file {self.output_path}: {e}")
            raise

        self.logger.info(f"Completed MIAR data processing task {self.task_id}")
        return output_results


    def validate_config(self) -> bool:
        """
        Validate task configuration.
        Requires 'output_json_path' and 'input_json_path'.
        """
        required_keys = ['output_json_path', 'input_json_path']
        for key in required_keys:
            if key not in self.config or not self.config[key]:
                self.logger.error(f"Missing or empty required config key: {key}")
                return False
        # Validate paths are strings
        if not isinstance(self.config['output_json_path'], str) or not isinstance(self.config['input_json_path'], str):
             self.logger.error("Config keys 'output_json_path' and 'input_json_path' must be strings.")
             return False
        return True
    def get_dependencies(self) -> List[str]:
            return []

