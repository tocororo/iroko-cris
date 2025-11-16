from abc import ABC, abstractmethod
import json
from typing import Dict, Any, List, Optional
import logging
import os
from pathlib import Path
from lxml import etree
import shutil

import uuid
import xml.etree.ElementTree as ET


from iroko.crawler.schemas import TaskExecution
from iroko.crawler.task import CrawlerTask
from iroko.storage import neo4j_db

logger = logging.getLogger('iroko-cris')






class OrcidDumpProcessingTask(CrawlerTask):
    """
    A crawler task to process ORCID public data dump and identify Cuban researchers
    or researchers working in Cuba, saving their XML files to an output directory.
    """
    
    def __init__(self, task_id: str, name: str, config: Dict[str, Any] = None):
        super().__init__(task_id, name, config)
        self.base_path = self.config.get('orcid_dump_path', '')
        self.output_path = self.config.get('output_dir', '')
        self.output_json = self.config.get('output_json')
        self.processed_count = 0
        self.cuban_researchers_count = 0
        
    async def execute(self, execution: TaskExecution) -> Dict[str, Any]:
        """
        Execute the ORCID processing task by traversing the dump folder structure
        and processing each XML file to identify Cuban researchers.
        """
        self.logger.info(f"Starting ORCID processing task with base path: {self.base_path}")
        self.logger.info(f"Output directory for Cuban researchers: {self.output_path}")
        
        if not self.validate_config():
            raise ValueError("Invalid configuration for ORCID processing task")
            
        # Create output directory if it doesn't exist
        os.makedirs(self.output_path, exist_ok=True)
        self.logger.info(f"Output directory created/verified: {self.output_path}")
            
        try:
            # Get Neo4j session for database operations
            session = await neo4j_db.get_session()
            
            # Process all ORCID files in the dump structure
            results = await self._process_orcid_dump(session)
            
            self.logger.info(
                f"ORCID processing completed. Processed {self.processed_count} records, "
                f"found {self.cuban_researchers_count} Cuban researchers"
            )
            output = {
                "status": "completed",
                "processed_records": self.processed_count,
                "cuban_researchers_found": self.cuban_researchers_count,
                "output_directory": self.output_path,
                "details": results
            }
            try:
                with open(self.output_json, 'w', encoding='utf-8') as f:
                    json.dump(output, f, indent=2, ensure_ascii=False)
                self.logger.info(f"Output results written to {self.output_json}")
            except Exception as e:
                self.logger.error(f"Failed to write output file {self.output_json}: {e}")
                raise
            return output
            
        except Exception as e:
            self.logger.error(f"Error executing ORCID processing task: {str(e)}")
            raise
        finally:
            if 'session' in locals():
                await session.close()
    
    def validate_config(self) -> bool:
        """
        Validate that the ORCID dump path and output directory are configured.
        """
        if not self.base_path:
            self.logger.error("ORCID dump path not configured")
            return False
            
        if not self.output_path:
            self.logger.error("Output directory not configured")
            return False
            
        path = Path(self.base_path)
        if not path.exists():
            self.logger.error(f"ORCID dump path does not exist: {self.base_path}")
            return False
            
        if not path.is_dir():
            self.logger.error(f"ORCID dump path is not a directory: {self.base_path}")
            return False
            
        return True
    
    async def _process_orcid_dump(self, session) -> Dict[str, Any]:
        """
        Process the entire ORCID dump folder structure.
        The structure follows ORCID's pattern with folders 000-999 based on last digits.
        """
        base_path = Path(self.base_path)
        results = {
            "total_files_processed": 0,
            "cuban_researchers": [],
            "saved_files": [],
            "errors": []
        }
        
        # ORCID dump structure has folders 000, 001, ..., 999 
        for folder_name in os.listdir(base_path):
            folder_path = base_path / folder_name
            
            if not folder_path.exists():
                continue
                
            self.logger.debug(f"Processing folder: {folder_name}")
            
            # Process each XML file in the folder
            for xml_file in folder_path.glob("*.xml"):
                try:
                    await self._process_orcid_file(xml_file, session, results)
                except Exception as e:
                    error_msg = f"Error processing file {xml_file}: {str(e)}"
                    self.logger.error(error_msg)
                    results["errors"].append(error_msg)
        
        return results
    
    async def _process_orcid_file(self, xml_file: Path, session, results: Dict[str, Any]):
        """
        Process a single ORCID XML file and check if it belongs to a Cuban researcher.
        If it is, save the XML file to the output directory.
        """
        self.logger.debug(f"Processing ORCID file: {xml_file}")
        
        try:
            # Parse XML using lxml 
            tree = etree.parse(str(xml_file))
            root = tree.getroot()
            
            # Extract ORCID iD from the file 
            orcid_element = root.find(".//{http://www.orcid.org/ns/common}orcid-identifier")
            orcid_id = None
            
            if orcid_element is not None:
                path_element = orcid_element.find("{http://www.orcid.org/ns/common}path")
                if path_element is not None:
                    orcid_id = path_element.text
            
            # If we can't get ORCID iD from XML, try to extract from filename
            if not orcid_id:
                orcid_id = xml_file.stem  # Use filename without extension
            
            # Check if this record belongs to a Cuban researcher
            is_cuban_researcher = await self._is_cuban_researcher(root, orcid_id, session)
            
            self.processed_count += 1
            results["total_files_processed"] += 1
            
            if is_cuban_researcher:
                self.cuban_researchers_count += 1
                
                # Save the XML file to output directory
                saved_file_path = await self._save_cuban_researcher_file(xml_file, orcid_id, is_cuban_researcher)
                
                researcher_data = {
                    "orcid_id": orcid_id,
                    "file_path": str(xml_file),
                    "saved_file_path": saved_file_path,
                    "identification_method": is_cuban_researcher["method"],
                    "confidence": is_cuban_researcher.get("confidence", "medium")
                }
                results["cuban_researchers"].append(researcher_data)
                results["saved_files"].append(saved_file_path)
                
                # Store in Neo4j
                # await self._store_researcher_in_neo4j(session, orcid_id, researcher_data, 
                #                                     is_cuban_researcher)
                
                self.logger.info(f"Found Cuban researcher: {orcid_id}, saved to: {saved_file_path}")
                
        except etree.XMLSyntaxError as e:
            self.logger.warning(f"XML syntax error in file {xml_file}: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error processing file {xml_file}: {str(e)}")
            raise
    
    async def _save_cuban_researcher_file(self, xml_file: Path, orcid_id: str, 
                                        cuban_indicator: Dict[str, Any]) -> str:
        """
        Save the XML file of a Cuban researcher to the output directory.
        
        Args:
            xml_file: Path to the original XML file
            orcid_id: ORCID identifier
            cuban_indicator: Dictionary with identification details
            
        Returns:
            Path to the saved file
        """
        # Create filename with identification method and confidence for easier filtering
        method = cuban_indicator["method"]
        confidence = cuban_indicator.get("confidence", "medium")
        
        # Option 1: Simple filename with just ORCID iD
        output_filename = f"{orcid_id}.xml"
        
        # Option 2: Filename with method and confidence for better organization
        # output_filename = f"{orcid_id}_{method}_{confidence}.xml"
        
        
        # Option 3: Preserve folder structure from original dump
        # relative_path = xml_file.relative_to(self.base_path)
        # output_path = Path(self.output_path) / relative_path
        # output_path.parent.mkdir(parents=True, exist_ok=True)
        
        output_path = Path(self.output_path) / output_filename
        
        try:
            # Copy the original XML file to output directory
            shutil.copy2(xml_file, output_path)
            
            # Alternatively, we could create a modified XML with metadata about the identification
            # But for now, we'll keep the original file intact
            self.logger.debug(f"Saved Cuban researcher XML to: {output_path}")
            
            return str(output_path)
            
        except Exception as e:
            self.logger.error(f"Failed to save XML file {xml_file} to {output_path}: {str(e)}")
            raise
    
    async def _is_cuban_researcher(self, root, orcid_id: str, session) -> Dict[str, Any]:
        """
        Determine if the ORCID record belongs to a Cuban researcher or someone 
        researching in Cuba using multiple criteria.
        
        Returns a dictionary with identification method and confidence level.
        """
        cuban_indicators = []
        
        # 1. Check address information for Cuba 
        cuban_address = self._check_cuban_address(root)
        if cuban_address:
            cuban_indicators.append({
                "method": "address",
                "details": cuban_address,
                "confidence": "high"
            })
        
        # 2. Check employment affiliations with Cuban institutions
        cuban_employment = self._check_cuban_employment(root)
        if cuban_employment:
            cuban_indicators.append({
                "method": "employment",
                "details": cuban_employment,
                "confidence": "high"
            })
        
        # 3. Check education history in Cuban institutions
        cuban_education = self._check_cuban_education(root)
        if cuban_education:
            cuban_indicators.append({
                "method": "education", 
                "details": cuban_education,
                "confidence": "medium"
            })
        
        # 4. Check for Cuban nationality in personal details
        cuban_nationality = self._check_cuban_nationality(root)
        if cuban_nationality:
            cuban_indicators.append({
                "method": "nationality",
                "details": cuban_nationality,
                "confidence": "high"
            })
        
        if cuban_indicators:
            # Return the highest confidence indicator
            confidence_order = {"high": 3, "medium": 2, "low": 1}
            best_indicator = max(cuban_indicators, 
                               key=lambda x: confidence_order.get(x["confidence"], 0))
            return best_indicator
        
        return None
    
    def _check_cuban_address(self, root) -> Dict[str, Any]:
        """
        Check address information for Cuban locations using ORCID address format.
        """
        addresses = root.findall(".//{http://www.orcid.org/ns/common}address")
        
        for address in addresses:
            country_element = address.find("{http://www.orcid.org/ns/common}country")
            if country_element is not None and country_element.text:
                country = country_element.text.upper()
                
                # Check for Cuba country code or variations
                if country in ["CU", "CUB", "CUBA"]:
                    return {
                        "country": country,
                        "raw_address": etree.tostring(address, encoding='unicode', 
                                                    method='text').strip()[:100]  # First 100 chars
                    }
        
        return None
    
    def _check_cuban_employment(self, root) -> List[Dict[str, Any]]:
        """
        Check employment affiliations for Cuban institutions.
        """
        cuban_employers = []
        
        # Look for employment activities with Cuban organizations
        employment_items = root.findall(".//{http://www.orcid.org/ns/activities}employment-summary")
        
        for employment in employment_items:
            organization = employment.find(".//{http://www.orcid.org/ns/common}organization")
            if organization is not None:
                org_name = organization.find("{http://www.orcid.org/ns/common}name")
                org_address = organization.find(".//{http://www.orcid.org/ns/common}address")
                
                # Check organization name for Cuban indicators
                org_text = org_name.text.lower() if org_name is not None and org_name.text else ""
                cuban_keywords = ["cuba", "cubana", "habana", "havana", "pinar del rio",
                    "la habana",
                    "mayabeque",
                    "matanzas",
                    "villa clara",
                    "cienfuegos",
                    "sancti spiritus",
                    "ciego de avila",
                    "camaguey",
                    "las tunas",
                    "holguin",
                    "granma",
                    "santiago de cuba",
                    "guantanamo",
                    "isla de la juventud"]
                                    
                if any(keyword in org_text for keyword in cuban_keywords):
                    cuban_employers.append({
                        "organization_name": org_name.text if org_name is not None else "",
                        "reason": "organization_name_contains_cuban_reference"
                    })
                    continue
                
                # Check address for Cuba
                if org_address is not None:
                    country_element = org_address.find("{http://www.orcid.org/ns/common}country")
                    if country_element is not None and country_element.text:
                        country = country_element.text.upper()
                        if country in ["CU", "CUB", "CUBA"]:
                            cuban_employers.append({
                                "organization_name": org_name.text if org_name is not None else "",
                                "reason": "organization_country_is_cuba"
                            })
        
        return cuban_employers if cuban_employers else None
    
    def _check_cuban_education(self, root) -> List[Dict[str, Any]]:
        """
        Check education history for Cuban institutions.
        Uses similar logic to employment checking.
        """
        cuban_education = []
        
        education_items = root.findall(".//{http://www.orcid.org/ns/activities}education-summary")
        
        for education in education_items:
            organization = education.find(".//{http://www.orcid.org/ns/common}organization")
            if organization is not None:
                org_name = organization.find("{http://www.orcid.org/ns/common}name")
                org_address = organization.find(".//{http://www.orcid.org/ns/common}address")
                
                # Check for Cuban educational institutions
                org_text = org_name.text.lower() if org_name is not None and org_name.text else ""
                cuban_education_keywords = [
                    "cuba", "cubana", "habana", "havana", "pinar del rio",
                    "la habana",
                    "mayabeque",
                    "matanzas",
                    "villa clara",
                    "cienfuegos",
                    "sancti spiritus",
                    "ciego de avila",
                    "camaguey",
                    "las tunas",
                    "holguin",
                    "granma",
                    "santiago de cuba",
                    "guantanamo",
                    "isla de la juventud"
                ]
                
                if any(keyword in org_text for keyword in cuban_education_keywords):
                    cuban_education.append({
                        "institution_name": org_name.text if org_name is not None else "",
                        "reason": "cuban_educational_institution"
                    })
                    continue
                
                # Check address
                if org_address is not None:
                    country_element = org_address.find("{http://www.orcid.org/ns/common}country")
                    if country_element is not None and country_element.text:
                        country = country_element.text.upper()
                        if country in ["CU", "CUB", "CUBA"]:
                            cuban_education.append({
                                "institution_name": org_name.text if org_name is not None else "",
                                "reason": "institution_country_is_cuba"
                            })
        
        return cuban_education if cuban_education else None
    
    def _check_cuban_nationality(self, root) -> List[str]:
        """
        Check personal details for Cuban nationality.
        """
        # Note: Nationality information might be in personal details section
        # This is a simplified check - you may need to adjust based on actual ORCID schema
        personal_details = root.find(".//{http://www.orcid.org/ns/personal}personal-details")
        
        if personal_details is not None:
            # Look for nationality elements or other personal identifiers
            # This would need to be adapted based on the actual ORCID schema structure
            nationality = personal_details.find(".//{http://www.orcid.org/ns/common}nationality")
            if nationality is not None and nationality.text:
                nationality_text = nationality.text.upper()
                if "CUBA" in nationality_text or "CUBAN" in nationality_text:
                    return [nationality.text]
        
        return None
    
    async def _store_researcher_in_neo4j(self, session, orcid_id: str, 
                                       researcher_data: Dict[str, Any], 
                                       cuban_indicator: Dict[str, Any]):
        """
        Store identified Cuban researcher in Neo4j database.
        """
        query = """
        MERGE (r:Researcher {orcid_id: $orcid_id})
        SET r.identification_method = $identification_method,
            r.confidence = $confidence,
            r.file_path = $file_path,
            r.saved_file_path = $saved_file_path,
            r.last_updated = datetime()
        
        WITH r
        UNWIND $cuban_indicators AS indicator
        MERGE (ci:CubanIndicator {type: indicator.method})
        MERGE (r)-[rel:HAS_INDICATOR]->(ci)
        SET rel.details = indicator.details,
            rel.confidence = indicator.confidence
        """
        
        parameters = {
            "orcid_id": orcid_id,
            "identification_method": cuban_indicator["method"],
            "confidence": cuban_indicator.get("confidence", "medium"),
            "file_path": researcher_data["file_path"],
            "saved_file_path": researcher_data["saved_file_path"],
            "cuban_indicators": [cuban_indicator]  # Can be expanded for multiple indicators
        }
        
        await session.run(query, parameters)
    
    def get_dependencies(self) -> List[str]:
        """
        This task doesn't depend on other tasks.
        """
        return []
    

class OrcidMappingTask(CrawlerTask):
    """
    A crawler task to map ORCID XML records to Iroko Person JSON schema.
    Processes Cuban researcher XML files and transforms them to standardized JSON format.
    """
    
    # ORCID namespaces from the XML schema[citation:3]
    NAMESPACES = {
        'common': 'http://www.orcid.org/ns/common',
        'person': 'http://www.orcid.org/ns/person',
        'personal-details': 'http://www.orcid.org/ns/personal-details',
        'activities': 'http://www.orcid.org/ns/activities',
        'employment': 'http://www.orcid.org/ns/employment',
        'education': 'http://www.orcid.org/ns/education',
        'address': 'http://www.orcid.org/ns/address',
        'email': 'http://www.orcid.org/ns/email',
        'record': 'http://www.orcid.org/ns/record',
        'researcher-url': 'http://www.orcid.org/ns/researcher-url',
        'keyword': 'http://www.orcid.org/ns/keyword'
    }
    
    def __init__(self, task_id: str, name: str, config: Dict[str, Any] = None):
        super().__init__(task_id, name, config)
        self.input_dir = self.config.get('input_dir', '')  # Directory with Cuban researcher XML files
        self.output_dir = self.config.get('output_dir', '')  # Directory for JSON output
        self.mapped_count = 0
        self.failed_count = 0
        
    async def execute(self, execution: TaskExecution) -> Dict[str, Any]:
        """
        Execute the ORCID mapping task by processing XML files and converting to JSON schema.
        """
        self.logger.info(f"Starting ORCID mapping task with input directory: {self.input_dir}")
        
        if not self.validate_config():
            raise ValueError("Invalid configuration for ORCID mapping task")
            
        # Create output directory if it doesn't exist
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        
        try:
            session = await neo4j_db.get_session()
            results = await self._process_orcid_files(session)
            
            self.logger.info(
                f"ORCID mapping completed. Mapped {self.mapped_count} records, "
                f"failed {self.failed_count} records"
            )
            
            return {
                "status": "completed",
                "mapped_records": self.mapped_count,
                "failed_records": self.failed_count,
                "output_directory": self.output_dir,
                "details": results
            }
            
        except Exception as e:
            self.logger.error(f"Error executing ORCID mapping task: {str(e)}")
            raise
        finally:
            if 'session' in locals():
                await session.close()
    
    def validate_config(self) -> bool:
        """
        Validate that input and output directories are configured and accessible.
        """
        if not self.input_dir:
            self.logger.error("Input directory not configured")
            return False
            
        if not self.output_dir:
            self.logger.error("Output directory not configured")
            return False
            
        input_path = Path(self.input_dir)
        if not input_path.exists():
            self.logger.error(f"Input directory does not exist: {self.input_dir}")
            return False
            
        return True
    
    async def _process_orcid_files(self, session) -> Dict[str, Any]:
        """
        Process all ORCID XML files in the input directory.
        """
        input_path = Path(self.input_dir)
        results = {
            "processed_files": 0,
            "successful_mappings": [],
            "failed_mappings": [],
            "errors": []
        }
        
        # Process all XML files in the input directory
        for xml_file in input_path.glob("*.xml"):
            try:
                success = await self._process_single_file(xml_file, session, results)
                if success:
                    self.mapped_count += 1
                    results["successful_mappings"].append(str(xml_file))
                else:
                    self.failed_count += 1
                    results["failed_mappings"].append(str(xml_file))
                    
                results["processed_files"] += 1
                
            except Exception as e:
                error_msg = f"Error processing file {xml_file}: {str(e)}"
                self.logger.error(error_msg)
                results["errors"].append(error_msg)
                self.failed_count += 1
                results["failed_mappings"].append(str(xml_file))
        
        return results
    
    async def _process_single_file(self, xml_file: Path, session, results: Dict[str, Any]) -> bool:
        """
        Process a single ORCID XML file and map it to the JSON schema.
        """
        self.logger.debug(f"Mapping ORCID file: {xml_file}")
        
        try:
            # Parse XML using lxml
            tree = etree.parse(str(xml_file))
            root = tree.getroot()
            
            # Map ORCID record to JSON schema
            person_data = await self._map_orcid_to_schema(root, xml_file)
            
            if person_data:
                # Save as JSON file
                output_filename = f"{person_data['id']}.json"
                output_path = Path(self.output_dir) / output_filename
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(person_data, f, indent=2, ensure_ascii=False)
                
                # Store mapping in Neo4j
                await self._store_mapping_in_neo4j(session, person_data, str(xml_file))
                
                self.logger.debug(f"Successfully mapped ORCID record to: {output_path}")
                return True
            else:
                self.logger.warning(f"Failed to map ORCID record from file: {xml_file}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error mapping file {xml_file}: {str(e)}")
            return False
    
    async def _map_orcid_to_schema(self, root, xml_file: Path) -> Optional[Dict[str, Any]]:
        """
        Map ORCID XML data to the Iroko Person JSON schema.
        """
        try:
            person_data = {
                "id": str(uuid.uuid4()),  # Generate Iroko UUID
                "identifiers": self._extract_identifiers(root),
                "name": self._extract_full_name(root),
                "last_name": self._extract_family_name(root),
                "public": self._extract_visibility_status(root),
                "gender": self._extract_gender(root),
                "country": self._extract_country(root),
                "email_addresses": self._extract_emails(root),
                "aliases": self._extract_aliases(root),
                "academic_titles": self._extract_academic_titles(root),
                "affiliations": self._extract_affiliations(root)
            }
            
            # Validate required fields are present
            if not all([person_data["id"], person_data["identifiers"], person_data["name"]]):
                self.logger.warning(f"Missing required fields in ORCID record from {xml_file}")
                return None
                
            return person_data
            
        except Exception as e:
            self.logger.error(f"Error mapping ORCID to schema for {xml_file}: {str(e)}")
            return None
    
    def _extract_identifiers(self, root) -> List[Dict[str, str]]:
        """
        Extract person identifiers from ORCID record[citation:1][citation:7].
        """
        identifiers = []
        
        # ORCID iD itself[citation:1]
        orcid_element = root.find('.//common:orcid-identifier', self.NAMESPACES)
        if orcid_element is not None:
            path_element = orcid_element.find('common:path', self.NAMESPACES)
            if path_element is not None and path_element.text:
                identifiers.append({
                    "idtype": "orcid",
                    "value": path_element.text
                })
        
        # External identifiers from researcher URLs[citation:7]
        researcher_urls = root.findall('.//researcher-url:researcher-urls/researcher-url:researcher-url', self.NAMESPACES)
        for url in researcher_urls:
            url_name = url.find('common:url-name', self.NAMESPACES)
            url_value = url.find('common:url', self.NAMESPACES)
            
            if url_name is not None and url_name.text and url_value is not None and url_value.text:
                # Map common external identifier types
                id_type = self._map_identifier_type(url_name.text.lower())
                if id_type:
                    identifiers.append({
                        "idtype": id_type,
                        "value": url_value.text
                    })
        
        # Other external IDs[citation:1]
        external_ids = root.findall('.//common:external-id', self.NAMESPACES)
        for ext_id in external_ids:
            id_type_elem = ext_id.find('common:external-id-type', self.NAMESPACES)
            id_value_elem = ext_id.find('common:external-id-value', self.NAMESPACES)
            
            if (id_type_elem is not None and id_type_elem.text and 
                id_value_elem is not None and id_value_elem.text):
                identifiers.append({
                    "idtype": id_type_elem.text.lower(),
                    "value": id_value_elem.text
                })
        
        return identifiers
    
    def _map_identifier_type(self, url_name: str) -> Optional[str]:
        """
        Map URL names to standardized identifier types[citation:7].
        """
        mapping = {
            'scopus': 'scopus',
            'researcherid': 'wos',
            'web of science': 'wos',
            'linkedin': 'linkedin',
            'google scholar': 'google_scholar',
            'github': 'github',
            'researchgate': 'researchgate',
            'isni': 'isni',
            'gnd': 'gnd',
            'loop': 'loop'
        }
        
        for key, value in mapping.items():
            if key in url_name:
                return value
        return None
    
    def _extract_full_name(self, root) -> str:
        """
        Extract full name from ORCID personal details[citation:3].
        """
        given_names_elem = root.find('.//personal-details:given-names', self.NAMESPACES)
        family_name_elem = root.find('.//personal-details:family-name', self.NAMESPACES)
        
        given_names = given_names_elem.text if given_names_elem is not None else ""
        family_name = family_name_elem.text if family_name_elem is not None else ""
        
        full_name = f"{given_names} {family_name}".strip()
        return full_name if full_name else "Unknown"
    
    def _extract_family_name(self, root) -> str:
        """
        Extract family name from ORCID record.
        """
        family_name_elem = root.find('.//personal-details:family-name', self.NAMESPACES)
        return family_name_elem.text if family_name_elem is not None else ""
    
    def _extract_visibility_status(self, root) -> bool:
        """
        Extract public visibility status from ORCID record[citation:1].
        """
        # Check name visibility as proxy for overall record visibility
        name_element = root.find('.//person:name', self.NAMESPACES)
        if name_element is not None:
            visibility = name_element.get('visibility')
            return visibility == 'public'
        return True  # Default to public if not specified
    
    def _extract_gender(self, root) -> str:
        """
        Extract gender information if available.
        Note: ORCID schema may not always include gender information.
        """
        # This would need to be adapted based on actual ORCID schema structure
        # Currently returns empty string as gender might not be in public data
        return ""
    
    def _extract_country(self, root) -> Dict[str, str]:
        """
        Extract country information from addresses[citation:1].
        """
        addresses = root.findall('.//address:address', self.NAMESPACES)
        for address in addresses:
            country_elem = address.find('common:country', self.NAMESPACES)
            if country_elem is not None and country_elem.text:
                return {
                    "code": country_elem.text,
                    "name": self._get_country_name(country_elem.text)
                }
        return {}
    
    def _get_country_name(self, country_code: str) -> str:
        """
        Map country code to country name.
        """
        country_map = {
            "CU": "Cuba",
            "US": "United States",
            "ES": "Spain",
            "MX": "Mexico",
            "FR": "France",
            "DE": "Germany",
            "GB": "United Kingdom",
            "CA": "Canada",
            "BR": "Brazil",
            "AR": "Argentina"
            # Add more country mappings as needed
        }
        return country_map.get(country_code.upper(), country_code)
    
    def _extract_emails(self, root) -> List[str]:
        """
        Extract email addresses from ORCID record.
        """
        emails = []
        email_elements = root.findall('.//email:emails/email:email', self.NAMESPACES)
        
        for email_elem in email_elements:
            email = email_elem.find('common:email', self.NAMESPACES)
            if email is not None and email.text:
                emails.append(email.text)
        
        return emails
    
    def _extract_aliases(self, root) -> List[str]:
        """
        Extract other names/aliases from ORCID record.
        """
        aliases = []
        other_names = root.findall('.//other-name:other-names/other-name:other-name', self.NAMESPACES)
        
        for name_elem in other_names:
            if name_elem.text:
                aliases.append(name_elem.text)
        
        return aliases
    
    def _extract_academic_titles(self, root) -> List[str]:
        """
        Extract academic titles from education and qualifications.
        """
        titles = []
        
        # Extract from education records
        education_items = root.findall('.//education:education-summary', self.NAMESPACES)
        for education in education_items:
            role_elem = education.find('common:role-title', self.NAMESPACES)
            if role_elem is not None and role_elem.text:
                titles.append(role_elem.text)
        
        # Extract from qualifications
        qualification_items = root.findall('.//activities:qualification-summary', self.NAMESPACES)
        for qualification in qualification_items:
            title_elem = qualification.find('common:title', self.NAMESPACES)
            if title_elem is not None and title_elem.text:
                titles.append(title_elem.text)
        
        return titles
    
    def _extract_affiliations(self, root) -> List[Dict[str, Any]]:
        """
        Extract employment and education affiliations[citation:1].
        """
        affiliations = []
        
        # Employment affiliations
        employment_items = root.findall('.//employment:employment-summary', self.NAMESPACES)
        for employment in employment_items:
            affiliation = self._extract_affiliation_data(employment, "employment")
            if affiliation:
                affiliations.append(affiliation)
        
        # Education affiliations
        education_items = root.findall('.//education:education-summary', self.NAMESPACES)
        for education in education_items:
            affiliation = self._extract_affiliation_data(education, "education")
            if affiliation:
                affiliations.append(affiliation)
        
        return affiliations
    
    def _extract_affiliation_data(self, item, affiliation_type: str) -> Optional[Dict[str, Any]]:
        """
        Extract common affiliation data from employment or education items.
        """
        try:
            organization = item.find('.//common:organization', self.NAMESPACES)
            if organization is None:
                return None
            
            org_name_elem = organization.find('common:name', self.NAMESPACES)
            org_name = org_name_elem.text if org_name_elem is not None else "Unknown Organization"
            
            # Extract organization identifiers[citation:1]
            identifiers = []
            disambiguated = organization.find('common:disambiguated-organization', self.NAMESPACES)
            if disambiguated is not None:
                org_id_elem = disambiguated.find('common:disambiguated-organization-identifier', self.NAMESPACES)
                source_elem = disambiguated.find('common:disambiguation-source', self.NAMESPACES)
                if org_id_elem is not None and org_id_elem.text and source_elem is not None and source_elem.text:
                    identifiers.append({
                        "idtype": source_elem.text.lower(),
                        "value": org_id_elem.text
                    })
            
            # Extract dates
            start_date = self._extract_date(item.find('common:start-date', self.NAMESPACES))
            end_date = self._extract_date(item.find('common:end-date', self.NAMESPACES))
            
            # Extract role
            role_elem = item.find('common:role-title', self.NAMESPACES)
            role = role_elem.text if role_elem is not None else affiliation_type.title()
            
            return {
                "id": str(uuid.uuid4()),  # Generate organization relationship UUID
                "identifiers": identifiers,
                "start_date": start_date,
                "end_date": end_date,
                "label": org_name,
                "roles": [role]
            }
            
        except Exception as e:
            self.logger.warning(f"Error extracting affiliation data: {str(e)}")
            return None
    
    def _extract_date(self, date_element) -> str:
        """
        Extract and format date from ORCID date elements[citation:1].
        """
        if date_element is None:
            return ""
        
        year_elem = date_element.find('common:year', self.NAMESPACES)
        month_elem = date_element.find('common:month', self.NAMESPACES)
        day_elem = date_element.find('common:day', self.NAMESPACES)
        
        year = year_elem.text if year_elem is not None else "0000"
        month = month_elem.text if month_elem is not None else "01"
        day = day_elem.text if day_elem is not None else "01"
        
        # Format as ISO 8601 date-time string
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}T00:00:00Z"
    
    async def _store_mapping_in_neo4j(self, session, person_data: Dict[str, Any], xml_file_path: str):
        """
        Store the mapping results in Neo4j database.
        """
        query = """
        MERGE (p:Person {iroko_id: $iroko_id})
        SET p.orcid_id = $orcid_id,
            p.name = $name,
            p.last_name = $last_name,
            p.public = $public,
            p.gender = $gender,
            p.country_code = $country_code,
            p.country_name = $country_name,
            p.email_count = $email_count,
            p.alias_count = $alias_count,
            p.affiliation_count = $affiliation_count,
            p.mapped_at = datetime(),
            p.source_file = $source_file
        
        WITH p
        UNWIND $identifiers AS identifier
        MERGE (id:Identifier {type: identifier.idtype, value: identifier.value})
        MERGE (p)-[r:HAS_IDENTIFIER]->(id)
        SET r.mapped_at = datetime()
        """
        
        # Extract ORCID ID from identifiers
        orcid_id = ""
        for identifier in person_data["identifiers"]:
            if identifier["idtype"] == "orcid":
                orcid_id = identifier["value"]
                break
        
        parameters = {
            "iroko_id": person_data["id"],
            "orcid_id": orcid_id,
            "name": person_data["name"],
            "last_name": person_data.get("last_name", ""),
            "public": person_data.get("public", True),
            "gender": person_data.get("gender", ""),
            "country_code": person_data.get("country", {}).get("code", ""),
            "country_name": person_data.get("country", {}).get("name", ""),
            "email_count": len(person_data.get("email_addresses", [])),
            "alias_count": len(person_data.get("aliases", [])),
            "affiliation_count": len(person_data.get("affiliations", [])),
            "source_file": xml_file_path,
            "identifiers": person_data["identifiers"]
        }
        
        await session.run(query, parameters)
    
    def get_dependencies(self) -> List[str]:
        """
        This task depends on the OrcidProcessingTask.
        """
        return self.config.get('dependencies', ['orcid-processing-task'])