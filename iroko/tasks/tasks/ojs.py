import json
import logging
from abc import abstractmethod
from typing import Dict, Any, List
import httpx
from lxml import html
from iroko.tasks.schemas import TaskExecution
from iroko.tasks.task import CrawlerTask
from iroko.tasks.task import http_task_headers
from iroko.storage import neo4j_db

logger = logging.getLogger('iroko-cris')

class OjsProcessingTask(CrawlerTask):
    """Task to process Publication nodes and identify OJS systems."""

    def __init__(self, task_id: str, name: str, config: Dict[str, Any] = None):
        super().__init__(task_id, name, config)
        self.output_path = self.config.get('output_json_path')
        if not self.output_path:
            raise ValueError("Config must contain 'output_json_path'.")

    async def execute(self, execution: TaskExecution) -> Dict[str, Any]:
        """
        Execute the OJS processing task.
        Iterates through Publication nodes, checks their URL, identifies OJS,
        and updates node properties accordingly.
        """
        self.logger.info(f"Starting OJS processing task {self.task_id}")

        # Get Neo4j session
        session = await neo4j_db.get_session()

        # Result counters
        results = {
            "processed": 0,
            "url_not_active": 0,
            "redirected": 0,
            "no_generator": 0,
            "not_ojs": 0,
            "ojs_found": 0,
            "oai_endpoint_found": 0,
            "oai_endpoint_found_list": [],
            "oai_endpoint_not_active": 0,
            "errors": 0
        }

        try:
            # Query to find Publication nodes with required attributes
            query_find_pubs = (
                """MATCH (p:Publication) 
                WHERE p.`identifier#url` IS NOT NULL AND (
                p.`identifier#issn_p` IS NOT NULL OR 
                p.`identifier#issn_e` IS NOT NULL OR 
                p.`identifier#issn_l` IS NOT NULL OR 
                p.`identifier#issn_o` IS NOT NULL OR 
                p.`identifier#issn_c` IS NOT NULL
                ) 
                RETURN p, p.id AS node_id"""
            )
            result_pubs = await session.run(query_find_pubs)
            
            # Create a single HTTP client for all requests
            async with httpx.AsyncClient(headers=http_task_headers,timeout=30.0, follow_redirects=True) as client:
                async for record in result_pubs:
                    pub_node = record["p"]
                    pub_node_id = record["node_id"]
                    results["processed"] += 1

                    original_url = pub_node.get("identifier#url")
                    self.logger.debug(f"Processing Publication node {pub_node_id} with URL: {original_url}")

                    # --- Task 1: Check if URL is active and collect homepage ---
                    try:
                        response = await client.get(original_url, timeout=10.0)
                        response.raise_for_status()
                        
                        # Check if there was a redirect
                        final_url = str(response.url)
                        homepage_content = response.text
                        
                        # If the final URL is different from the original URL, we have a redirect
                        if final_url != original_url:
                            self.logger.info(f"URL redirected from {original_url} to {final_url}")
                            results["redirected"] += 1
                            
                            # Update the node with the final URL
                            query_update_url = (
                                "MATCH (p) WHERE elementId(p) = $node_id "
                                "SET p.`identifier#url` = $final_url"
                            )
                            await session.run(query_update_url, node_id=pub_node_id, final_url=final_url)
                            self.logger.info(f"Updated node {pub_node_id} URL from {original_url} to {final_url}")
                        
                        self.logger.debug(f"Successfully fetched homepage for {final_url}.")
                        
                    except (httpx.HTTPStatusError, httpx.RequestError) as e:
                        self.logger.warning(f"URL {original_url} for node {pub_node_id} is not active: {e}")
                        results["url_not_active"] += 1
                        continue
                    except Exception as e:
                        self.logger.error(f"Unexpected error fetching URL {original_url} for node {pub_node_id}: {e}")
                        results["errors"] += 1
                        continue

                    # Use the final URL (which might be the original or redirected) for further processing
                    current_url = final_url if 'final_url' in locals() else original_url

                    # --- Task 2: Determine system generator ---
                    tree = html.fromstring(homepage_content)
                    generator_element = tree.xpath("//meta[@name='generator']")
                    if generator_element:
                        generator_content = generator_element[0].get("content", "").lower()
                        self.logger.debug(f"Found generator meta tag: {generator_content}")
                        # Check if it's OJS
                        if "open journal systems" in generator_content or "ojs" in generator_content:
                            self.logger.info(f"Identified OJS system for {current_url} (node {pub_node_id}).")
                            # Update node attribute
                            query_update_source = (
                                "MATCH (p) WHERE elementId(p) = $node_id "
                                "SET p.sourceSystem = $source_system"
                            )
                            await session.run(query_update_source, node_id=pub_node_id, source_system="OJS")
                            results["ojs_found"] += 1

                            # --- Task 3: Determine OAI-PMH endpoint if OJS ---
                            # Common OAI-PMH endpoint patterns for OJS
                            oai_endpoints_to_check = [
                                f"{current_url.rstrip('/')}/oai",
                                f"{current_url.rstrip('/')}/index.php/oai",
                                f"{current_url.rstrip('/')}/pub/index.php/oai"
                            ]
                            oai_url_found = None
                            for endpoint in oai_endpoints_to_check:
                                try:
                                    oai_response = await client.get(endpoint, timeout=10.0)
                                    if oai_response.status_code == 200:
                                        # Basic check if response contains OAI-PMH XML structure
                                        if "OAI-PMH" in oai_response.text:
                                            oai_url_found = endpoint
                                            self.logger.info(f"Found active OAI-PMH endpoint: {endpoint} for {current_url}.")
                                            break
                                        else:
                                            self.logger.debug(f"Endpoint {endpoint} for {current_url} returned 200 but not OAI-PMH XML.")
                                except (httpx.HTTPStatusError, httpx.RequestError) as e:
                                    self.logger.debug(f"OAI endpoint {endpoint} for {current_url} is not active: {e}")
                                    continue

                            if oai_url_found:
                                # Update node attribute
                                query_update_oai = (
                                    "MATCH (p) WHERE elementId(p) = $node_id "
                                    "SET p.`identifier#oaiurl` = $oai_url"
                                )
                                await session.run(query_update_oai, node_id=pub_node_id, oai_url=oai_url_found)
                                results['oai_endpoint_found_list'].append(oai_url_found)
                                results["oai_endpoint_found"] += 1
                            else:
                                self.logger.warning(f"No active OAI-PMH endpoint found for OJS site {current_url} (node {pub_node_id}).")
                                results["oai_endpoint_not_active"] += 1
                        else:
                            self.logger.debug(f"Generator {generator_content} is not OJS for {current_url} (node {pub_node_id}).")
                            results["not_ojs"] += 1
                    else:
                        self.logger.debug(f"No generator meta tag found for {current_url} (node {pub_node_id}).")
                        results["no_generator"] += 1

        finally:
            await session.close()

        self.logger.info(f"Completed OJS processing task {self.task_id}. Results: {results}")
        
        # --- Step 4: Save data dict to output file ---
        try:
            with open(self.output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Output results written to {self.output_path}")
        except Exception as e:
            self.logger.error(f"Failed to write output file {self.output_path}: {e}")
            raise
        
        return results

    def validate_config(self) -> bool:
        """
        Validate task configuration.
        Requires 'neo4j_db'.
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