from abc import ABC, abstractmethod
import json
from typing import Dict, Any, List, Optional, Tuple
import logging
import os
from pathlib import Path
from lxml import etree
import shutil

import uuid
import xml.etree.ElementTree as ET

import unicodedata
from iroko.crawler.schemas import TaskExecution
from iroko.crawler.task import CrawlerTask
from iroko.storage import neo4j_db

logger = logging.getLogger('iroko-cris')

import asyncio
import json
import re
import pandas as pd
from jsonschema import validate, ValidationError
import xmltodict


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
        for folder_name in [f"{i:03d}" for i in range(1000)]:
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
    

# delete persons and persons relationships 
# MATCH (p:Person)-[r]->() delete r
# MATCH (p:Person) delete p
# MATCH ()-[r]->(p:Author) delete r
# MATCH (p:Author)-[r]->() delete r
# MATCH (p:Author) delete p

class OrcidMappingTask(CrawlerTask):
    """Task to map ORCID XML records to the iroko Person JSON schema and ingest into Neo4j."""

    def __init__(self, task_id: str, name: str, config: Dict[str, Any] = None):
        super().__init__(task_id, name, config)
        self.input_folder = None
        self.output_folder = None
        self.diune_path = None
        self.diune_df = None
        self.person_json_schema = None
        self._created_orgs_json = [] # Temporary storage for created organizations

    def validate_config(self) -> bool:
        """Validates the required configuration keys."""
        required_keys = ['input_folder', 'output_folder', 'diune_path', 'person_schema_path']
        for key in required_keys:
            if key not in self.config or not self.config[key]:
                self.logger.error(f"Missing or empty required config key: {key}")
                return False

        if not os.path.isdir(self.config['input_folder']):
            self.logger.error(f"Input folder does not exist: {self.config['input_folder']}")
            return False

        if not os.path.isdir(self.config['output_folder']):
            self.logger.error(f"Output folder does not exist: {self.config['output_folder']}")
            return False

        if not os.path.isfile(self.config['diune_path']):
            self.logger.error(f"DIUNE Excel file does not exist: {self.config['diune_path']}")
            return False

        if not os.path.isfile(self.config['person_schema_path']):
            self.logger.error(f"Person JSON Schema file does not exist: {self.config['person_schema_path']}")
            return False

        try:
            # Test reading the Excel file
            test_df = pd.read_excel(self.config['diune_path'], dtype=str)
            required_columns = ["codigo", "descripcion"]
            if not all(col in test_df.columns for col in required_columns):
                 self.logger.error(f"DIUNE Excel file missing required columns: {required_columns}")
                 return False
             
             # Test loading the JSON schema
            with open(self.config['person_schema_path'], 'r', encoding='utf-8') as f:
                json.load(f) # Will raise an error if invalid JSON
                 
        except Exception as e:
            self.logger.error(f"Error reading DIUNE Excel file or Person Schema: {e}")
            return False

        return True

    async def execute(self, execution: TaskExecution) -> Dict[str, Any]:
        """Executes the ORCID mapping and ingestion process."""
        try:
            self.input_folder = self.config['input_folder']
            self.output_folder = self.config['output_folder']
            self.diune_path = self.config['diune_path']
            self.person_schema_path = self.config['person_schema_path']

            self.logger.info("Loading Person JSON Schema...")
            with open(self.person_schema_path, 'r', encoding='utf-8') as f:
                 self.person_json_schema = json.load(f)

            self.logger.info("Loading DIUNE data...")
            self.diune_df = pd.read_excel(self.diune_path, dtype=str)
            # Use unicodedata for normalization instead of unidecode
            self.diune_df['descripcion_lower'] = self.diune_df['descripcion'].apply(
                lambda x: unicodedata.normalize('NFKD', x.lower()).encode('ascii', 'ignore').decode('ascii') if pd.notna(x) else x
            )

            self.logger.info("Starting ORCID mapping step...")
            await self._step1_mapping()

            # self.logger.info("Starting Neo4j ingestion step...")
            # await self._step2_ingest()

            # self.logger.info("Saving created organizations JSON...")
            # await self._save_created_orgs_json()

            self.logger.info(f"OrcidMappingTask {self.task_id} completed successfully.")
            return {"status": "success", "message": f"Processed ORCID records and ingested into Neo4j. Created {len(self._created_orgs_json)} organizations."}

        except Exception as e:
            self.logger.error(f"Error executing OrcidMappingTask {self.task_id}: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    async def _step1_mapping(self):
        """Maps ORCID XML files to JSON schema and saves them."""
        xml_files = [f for f in os.listdir(self.input_folder) if f.endswith('.xml')]
        total_files = len(xml_files)

        for idx, filename in enumerate(xml_files):
            self.logger.info(f"Processing file {idx + 1}/{total_files}: {filename}")
            input_path = os.path.join(self.input_folder, filename)

            try:
                
                # Parse the XML file
                # tree = ET.parse(input_path)
                # root = tree.getroot()
                
                tree = etree.parse(input_path)
                root = tree.getroot()

                # Define namespaces based on the XSDs provided
                ns = {
                    'record': 'http://www.orcid.org/ns/record',
                    'person': 'http://www.orcid.org/ns/person',
                    'activities': 'http://www.orcid.org/ns/activities',
                    'common': 'http://www.orcid.org/ns/common',
                    'employment': 'http://www.orcid.org/ns/employment',
                    'education': 'http://www.orcid.org/ns/education',
                    'distinction': 'http://www.orcid.org/ns/distinction',
                    'membership': 'http://www.orcid.org/ns/membership',
                    'service': 'http://www.orcid.org/ns/service',
                    'invited-position': 'http://www.orcid.org/ns/invited-position',
                    'qualification': 'http://www.orcid.org/ns/qualification',
                    'peer-review': 'http://www.orcid.org/ns/peer-review',
                    'work': 'http://www.orcid.org/ns/work',
                    'funding': 'http://www.orcid.org/ns/funding',
                    'research-resource': 'http://www.orcid.org/ns/research-resource',
                    'personal-details': 'http://www.orcid.org/ns/personal-details',
                    'other-name': 'http://www.orcid.org/ns/other-name',
                    'email': 'http://www.orcid.org/ns/email',
                    'address': 'http://www.orcid.org/ns/address',
                    'keyword': 'http://www.orcid.org/ns/keyword',
                    'external-identifier': 'http://www.orcid.org/ns/external-identifier',
                    'researcher-url': 'http://www.orcid.org/ns/researcher-url'
                }

                # Extract ORCID from filename
                orcid_value = os.path.splitext(filename)[0]

                # Map the XML structure to the JSON schema
                # mapped_person = self._map_orcid_xml_to_json(root, orcid_value, ns)
                with open(input_path) as fd:
                    mapped_person = xmltodict.parse(fd.read())
                mapped_person['iroko_uuid'] = str(uuid.uuid4())

                # Validate the mapped JSON against the schema
                # validate(instance=mapped_person, schema=self.person_json_schema)

                # Save the mapped JSON file
                output_filename = f"{orcid_value}.json"
                output_path = os.path.join(self.output_folder, output_filename)
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(mapped_person, f, ensure_ascii=False, indent=2)

            except ValidationError as ve:
                self.logger.error(f"Validation error for {filename}: {ve}")
                # Optionally, continue processing other files or raise
                # raise
            except ET.ParseError as pe:
                self.logger.error(f"XML parsing error for {filename}: {pe}")
                # Optionally, continue processing other files or raise
                # raise
            except Exception as e:
                self.logger.error(f"Unexpected error processing {filename}: {e}", exc_info=True)
                # Optionally, continue processing other files or raise
                # raise

    def _map_orcid_xml_to_json(self, root: ET.Element, orcid_value: str, ns: Dict[str, str]) -> Dict[str, Any]:
        """Maps an ORCID XML ElementTree root to the target JSON structure."""
        # Initialize the output dictionary
        person_data = {
            "identifiers": [{"idtype": "orcid", "value": orcid_value}],
            "name": "", # Will try to populate from personal details
            "given_name": "",
            "family_name": "",
            "biography": "",
            "public": True, # Assuming public unless specified otherwise in XML
            "gender": "",
            "country": {"code": "", "name": ""},
            "email_addresses": [],
            "aliases": [],
            "academic_titles": [],
            "distinctions": [], # Note: typo in original schema, keeping as 'distintions'
            "affiliations": [],
            "peer_review": [] # Note: property in schema is "peer-review", key in dict is "peer_review"
        }

        # --- Map Personal Details (from person.xsd) ---
        person_details = root.find(f'.//person:person', ns)
        if person_details is not None:
            # Name (from personal-details.xsd via person.xsd)
            name_details = person_details.find('.//person:name', ns)
            if name_details is not None:
                given_names = name_details.find('.//personal-details:given-names', ns)
                family_names = name_details.find('.//personal-details:family-name', ns)
                if given_names is not None:
                    person_data['given_name'] = given_names.text or ""
                if family_names is not None:
                    person_data['family_name'] = family_names.text or ""
                person_data['name'] = f"{person_data['given_name']} {person_data['family_name']}".strip()

            # Biography (from personal-details.xsd via person.xsd)
            biography_elem = person_details.find('.//person:biography/personal-details:content', ns)
            if biography_elem is not None and biography_elem.text:
                 person_data['biography'] = biography_elem.text

            # Gender (not explicitly in the provided XSDs for personal-details, might be elsewhere or not standard)
            # Assuming it's not directly available in the simplified structure shown

            # Country (from address.xsd via person.xsd)
            country_elem = person_details.find('.//address:address/address:country', ns)
            if country_elem is not None and country_elem.text:
                person_data['country']['code'] = country_elem.text
                # Name would require a lookup, leaving blank for now

            # Emails (from email.xsd via person.xsd)
            email_list = person_details.find('.//email:emails', ns)
            if email_list is not None:
                for email_elem in email_list.findall('.//email:email', ns):
                    email_val = email_elem.find('.//email:email', ns)
                    if email_val is not None and email_val.text:
                        person_data['email_addresses'].append(email_val.text)

            # Other names (aliases) (from other-name.xsd via person.xsd)
            other_names_list = person_details.find('.//other-name:other-names', ns)
            if other_names_list is not None:
                for other_name_elem in other_names_list.findall('.//other-name:other-name', ns):
                    # other-name can be a simple element containing the name
                    if other_name_elem.text:
                        person_data['aliases'].append(other_name_elem.text)


        # --- Map Affiliations (from activities.xsd and common.xsd) ---
        # Affiliations include Employment, Education, Distinction, Membership, Service, Invited Position, Qualification
        activities_summary = root.find('.//activities:activities-summary', ns)
        if activities_summary is not None:
            affiliations = []
            # Iterate through potential affiliation containers
            for container_tag in ['employments', 'educations', 'distinctions', 'memberships', 'services', 'invited-positions', 'qualifications']:
                container = activities_summary.find(f'.//activities:{container_tag}', ns)
                if container is not None:
                    # Each container has 'affiliation-group's which contain summaries
                    for group in container.findall('.//activities:affiliation-group', ns):
                        # Each group can have different types of summaries, find the correct one
                        summary_types = [
                            'employment:employment-summary',
                            'education:education-summary',
                            'distinction:distinction-summary',
                            'membership:membership-summary',
                            'service:service-summary',
                            'invited-position:invited-position-summary',
                            'qualification:qualification-summary'
                        ]
                        for summary_type in summary_types:
                            summary_elem = group.find(f'.//{summary_type}', ns)
                            if summary_elem is not None:
                                # Determine affiliation type based on the summary tag found
                                affiliation_type = container_tag #[:-1] # Remove 's' to get type (e.g., employments -> employment)
                                # if affiliation_type == 'invited-position':
                                #     affiliation_type = 'employment' # Map to a standard type
                                # elif affiliation_type == 'qualification':
                                #     affiliation_type = 'education' # Map to a standard type
                                # elif affiliation_type == 'distinction':
                                #     # Distinctions might be mapped differently, for now treat as employment or add to distinctions list
                                #     pass # Let it use the affiliation structure below

                                affiliation = {
                                    "identifiers": [], # Populate from common:external-ids if present in summary
                                    "start_date": "",
                                    "end_date": "",
                                    "name": "",
                                    "roles": [],
                                    "affiliation_type": affiliation_type
                                }

                                # Extract organization name from summary
                                org_elem = summary_elem.find('.//common:organization/common:name', ns)
                                if org_elem is not None and org_elem.text:
                                    affiliation["name"] = org_elem.text.strip()

                                # Extract role title from summary
                                role_title_elem = summary_elem.find('.//common:role-title', ns)
                                if role_title_elem is not None and role_title_elem.text:
                                    affiliation["roles"].append(role_title_elem.text.strip())

                                # Extract department name from summary
                                dept_name_elem = summary_elem.find('.//common:department-name', ns)
                                if dept_name_elem is not None and dept_name_elem.text:
                                    affiliation["roles"].append(dept_name_elem.text.strip()) # Add department as a role or separate field if needed

                                # Extract dates
                                start_date_elem = summary_elem.find('.//common:start-date', ns)
                                if start_date_elem is not None:
                                    year = start_date_elem.find('.//common:year', ns)
                                    month = start_date_elem.find('.//common:month', ns)
                                    day = start_date_elem.find('.//common:day', ns)
                                    if year is not None:
                                        date_str = year.text or ""
                                        if month is not None:
                                            date_str += f"-{month.text.zfill(2) or '00'}"
                                            if day is not None:
                                                date_str += f"-{day.text.zfill(2) or '00'}"
                                        affiliation["start_date"] = date_str

                                end_date_elem = summary_elem.find('.//common:end-date', ns)
                                if end_date_elem is not None:
                                    year = end_date_elem.find('.//common:year', ns)
                                    month = end_date_elem.find('.//common:month', ns)
                                    day = end_date_elem.find('.//common:day', ns)
                                    if year is not None:
                                        date_str = year.text or ""
                                        if month is not None:
                                            date_str += f"-{month.text.zfill(2) or '00'}"
                                            if day is not None:
                                                date_str += f"-{day.text.zfill(2) or '00'}"
                                        affiliation["end_date"] = date_str

                                # Extract external IDs (identifiers) from the summary
                                external_ids_elem = summary_elem.find('.//common:external-ids', ns)
                                if external_ids_elem is not None:
                                    for ext_id_elem in external_ids_elem.findall('.//common:external-id', ns):
                                        id_type_elem = ext_id_elem.find('.//common:external-id-type', ns)
                                        id_value_elem = ext_id_elem.find('.//common:external-id-value', ns)
                                        if id_type_elem is not None and id_type_elem.text and id_value_elem is not None and id_value_elem.text:
                                            affiliation["identifiers"].append({
                                                "idtype": id_type_elem.text,
                                                "value": id_value_elem.text
                                            })

                                affiliations.append(affiliation)

            person_data['affiliations'] = affiliations

        # --- Map Peer Review (from activities.xsd and peer-review.xsd) ---
        peer_reviews_container = activities_summary.find('.//activities:peer-reviews', ns)
        if peer_reviews_container is not None:
            peer_reviews = []
            for group in peer_reviews_container.findall('.//activities:peer-review-group', ns):
                 # Groups might contain duplicates, iterate through them
                 for duplicate_group in group.findall('.//activities:peer-review-duplicates', ns):
                     for summary_elem in duplicate_group.findall('.//peer-review:peer-review-summary', ns):
                         review = {
                             "identifiers": [],
                             "start_date": "",
                             "end_date": "",
                             "name": "", # e.g., journal name, grant number
                             "roles": [] # e.g., reviewer, editor
                         }
                         # Extract name (e.g., from source name or other relevant field)
                         # Example: journal-title might be under peer-review:journal-title
                         journal_title_elem = summary_elem.find('.//peer-review:journal-title', ns)
                         if journal_title_elem is not None and journal_title_elem.text:
                             review["name"] = journal_title_elem.text.strip()

                         # Extract external IDs
                         external_ids_elem = summary_elem.find('.//common:external-ids', ns)
                         if external_ids_elem is not None:
                             for ext_id_elem in external_ids_elem.findall('.//common:external-id', ns):
                                 id_type_elem = ext_id_elem.find('.//common:external-id-type', ns)
                                 id_value_elem = ext_id_elem.find('.//common:external-id-value', ns)
                                 if id_type_elem is not None and id_type_elem.text and id_value_elem is not None and id_value_elem.text:
                                     review["identifiers"].append({
                                         "idtype": id_type_elem.text,
                                         "value": id_value_elem.text
                                     })

                         # Extract roles (contributor attributes might define roles)
                         # This is often implicit (e.g., reviewer) or defined by the context of the summary type
                         review["roles"] = ["reviewer"] # Default role, can be more specific if available in XML

                         peer_reviews.append(review)
            person_data['peer_review'] = peer_reviews # Using the key 'peer_review' in the dict to match Python convention

        return person_data


    async def _step2_ingest(self):
        """Ingests the mapped JSON files into Neo4j."""
        from iroko.storage import neo4j_db
        session = await neo4j_db.get_session()
        json_files = [f for f in os.listdir(self.output_folder) if f.endswith('.json')]
        total_files = len(json_files)

        try:
            for idx, filename in enumerate(json_files):
                self.logger.info(f"Ingesting file {idx + 1}/{total_files}: {filename}")
                input_path = os.path.join(self.output_folder, filename)

                with open(input_path, 'r', encoding='utf-8') as f:
                    person_data = json.load(f)

                # Upsert Person node
                person_identifiers = person_data.get('identifiers', [])
                orcid_id = next((id_obj['value'] for id_obj in person_identifiers if id_obj.get('idtype') == 'orcid'), None)

                if not orcid_id:
                     self.logger.warning(f"No ORCID found in {filename}, skipping ingestion.")
                     continue

                # Prepare properties, excluding affiliations and peer_review
                person_properties = {k: v for k, v in person_data.items() if k not in ['affiliations', 'peer_review']}
                # Ensure 'name' exists for the Person node, fallback if needed
                person_properties['name'] = person_properties.get('name', f"Person_{orcid_id}")

                # Build the identifier property map for the Person
                identifier_props = {}
                for id_obj in person_identifiers:
                    idtype = id_obj.get('idtype')
                    value = id_obj.get('value')
                    if idtype and value:
                        identifier_props[f"identifier#{idtype}"] = value

                # Cypher query to merge Person node
                merge_person_query = """
                MERGE (p:Person {identifier#orcid: $orcid_value})
                SET p += $properties
                """
                await session.execute_write(
                    lambda tx: tx.run(merge_person_query, orcid_value=orcid_id, properties=person_properties)
                )

                # Process Affiliations
                affiliations = person_data.get('affiliations', [])
                for affiliation in affiliations:
                    await self._create_or_link_affiliation(session, orcid_id, affiliation)

                # Process Peer Reviews
                peer_reviews = person_data.get('peer_review', []) # Using the key from the dict
                for review in peer_reviews:
                    await self._create_or_link_peer_review(session, orcid_id, review)

        finally:
            await session.close()

    async def _create_or_link_affiliation(self, session, person_orcid: str, affiliation_data: Dict[str, Any]):
        """Creates or links an Organization node based on affiliation data and creates the relationship."""
        org_name = affiliation_data.get('name', '').strip()
        if not org_name:
            self.logger.debug("Affiliation has no name, skipping.")
            return

        # Attempt to find Organization in DB first
        org_node = await self._find_organization_in_db(session, affiliation_data)

        # If not found in DB, search DIUNE
        if not org_node:
             org_node = await self._find_organization_in_diune(org_name)

        # If found in DIUNE, create/update in DB
        if org_node and org_node.get('from_diune'):
             await self._create_organization_in_db_from_diune(session, org_node)
             # Append to the list for later saving to JSON
             self._created_orgs_json.append(org_node)
        elif org_node and org_node.get('from_db'):
             # Org already exists in DB, use its iroko_uuid
             pass # org_node already contains the required info
        elif not org_node:
             # Create a new generic Organization
             org_node = await self._create_generic_organization(session, affiliation_data)
             # Append to the list for later saving to JSON
             self._created_orgs_json.append(org_node)


        # Now, org_node should contain the iroko_uuid of the target Organization
        if org_node and 'iroko_uuid' in org_node:
            # Create the relationship
            rel_type = affiliation_data.get('affiliation_type', 'employment').upper() + "_IN"
            roles = affiliation_data.get('roles', [])
            start_date = affiliation_data.get('start_date')
            end_date = affiliation_data.get('end_date')

            # Cypher to merge the relationship
            merge_rel_query = """
            MATCH (p:Person {identifier#orcid: $person_orcid})
            MATCH (o:Organization {iroko_uuid: $org_uuid})
            MERGE (p)-[r:`{rel_type}`]->(o)
            SET r.roles = $roles, r.start_date = $start_date, r.end_date = $end_date
            """.format(rel_type=rel_type) # Format the relationship type into the query string

            await session.execute_write(
                lambda tx: tx.run(
                    merge_rel_query,
                    person_orcid=person_orcid,
                    org_uuid=org_node['iroko_uuid'],
                    roles=roles,
                    start_date=start_date,
                    end_date=end_date
                )
            )
        else:
            self.logger.warning(f"Could not establish affiliation for ORCID {person_orcid} and org '{org_name}', no org node found or created.")


    async def _find_organization_in_db(self, session, affiliation_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Searches for an Organization node in Neo4j using identifiers or name."""
        # Search by identifiers first
        identifiers = affiliation_data.get('identifiers', [])
        for id_obj in identifiers:
            idtype = id_obj.get('idtype')
            value = id_obj.get('value')
            if idtype and value:
                query = f"MATCH (o:Organization) WHERE o.identifier#{idtype} = $value RETURN o.iroko_uuid AS uuid LIMIT 1"
                result = await session.execute_read(lambda tx: tx.run(query, value=value).single())
                if result:
                    return {"iroko_uuid": result['uuid'], "from_db": True}

        # Search by name if identifiers fail
        name = affiliation_data.get('name')
        if name:
            # Use lower() and unicodedata for comparison
            normalized_name = unicodedata.normalize('NFKD', name.lower()).encode('ascii', 'ignore').decode('ascii')
            query = "MATCH (o:Organization) WHERE toLower(o.name) = $name OR toLower(o.alternative_name) = $name RETURN o.iroko_uuid AS uuid LIMIT 1"
            result = await session.execute_read(lambda tx: tx.run(query, name=normalized_name).single())
            if result:
                return {"iroko_uuid": result['uuid'], "from_db": True}

        return None

    async def _find_organization_in_diune(self, org_name: str) -> Optional[Dict[str, Any]]:
        """Searches for an organization name in the DIUNE dataframe."""
        if self.diune_df is None or org_name.strip() == "":
             return None

        # Use lower() and unicodedata for comparison (already done during df loading)
        normalized_name = unicodedata.normalize('NFKD', org_name.lower()).encode('ascii', 'ignore').decode('ascii')
        matching_row = self.diune_df[self.diune_df['descripcion_lower'] == normalized_name]

        if not matching_row.empty:
            row = matching_row.iloc[0] # Assuming first match is sufficient
            return {
                "identifier#onei": f"onei.diune.{row['codigo']}",
                "name": row['descripcion'],
                "descripcion": row['descripcion'],
                "descripcion_nae": row.get('descripcion_nae', ''),
                "descripcion_cnae": row.get('descripcion_cnae', ''),
                "forma_organizativa": row.get('desfo', ''),
                "from_diune": True
            }

        return None

    async def _create_organization_in_db_from_diune(self, session, org_data: Dict[str, Any]):
        """Creates an Organization node in Neo4j using data from DIUNE."""
        # Cypher query to create the Organization node with DIUNE data
        create_query = """
        MERGE (o:Organization {identifier#onei: $onei_id})
        ON CREATE SET
            o.iroko_uuid = toString(randomUUID()),
            o.name = $name,
            o.descripcion = $descripcion,
            o.descripcion_nae = $descripcion_nae,
            o.descripcion_cnae = $descripcion_cnae,
            o.forma_organizativa = $forma_organizativa
        ON MATCH SET
            o.name = CASE WHEN o.name IS NULL THEN $name ELSE o.name END,
            o.descripcion = CASE WHEN o.descripcion IS NULL THEN $descripcion ELSE o.descripcion END,
            o.descripcion_nae = CASE WHEN o.descripcion_nae IS NULL THEN $descripcion_nae ELSE o.descripcion_nae END,
            o.descripcion_cnae = CASE WHEN o.descripcion_cnae IS NULL THEN $descripcion_cnae ELSE o.descripcion_cnae END,
            o.forma_organizativa = CASE WHEN o.forma_organizativa IS NULL THEN $forma_organizativa ELSE o.forma_organizativa END
        RETURN o.iroko_uuid AS uuid
        """
        result = await session.execute_write(
            lambda tx: tx.run(
                create_query,
                onei_id=org_data["identifier#onei"],
                name=org_data["name"],
                descripcion=org_data["descripcion"],
                descripcion_nae=org_data["descripcion_nae"],
                descripcion_cnae=org_data["descripcion_cnae"],
                forma_organizativa=org_data["forma_organizativa"]
            ).single()
        )
        # Update the passed org_data dict with the generated UUID from the DB
        if result:
            org_data['iroko_uuid'] = result['uuid']


    async def _create_generic_organization(self, session, affiliation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Creates a generic Organization node in Neo4j."""
        org_name = affiliation_data.get('name', 'Unknown Organization')
        identifiers = affiliation_data.get('identifiers', [])

        # Prepare properties and identifier map
        org_properties = {"name": org_name}
        identifier_props = {}
        for id_obj in identifiers:
            idtype = id_obj.get('idtype')
            value = id_obj.get('value')
            if idtype and value:
                identifier_props[f"identifier#{idtype}"] = value

        # Cypher query to create the Organization node with identifiers and other properties
        # Use a primary identifier for the MERGE key, fallback to name if none exist
        primary_id_key = next((f"identifier#{id_obj['idtype']}" for id_obj in identifiers if id_obj.get('idtype')), None)
        if primary_id_key:
             primary_id_value = identifier_props[primary_id_key]
             merge_condition = f"{{ {primary_id_key}: $primary_id_value }}"
        else:
             primary_id_value = org_name
             merge_condition = "{ name: $primary_id_value }"

        create_query = f"""
        MERGE (o:Organization {merge_condition})
        ON CREATE SET
            o.iroko_uuid = toString(randomUUID()),
            o += $properties
        ON MATCH SET
            o += $properties
        RETURN o.iroko_uuid AS uuid
        """

        result = await session.execute_write(
            lambda tx: tx.run(
                create_query,
                primary_id_value=primary_id_value,
                properties=org_properties
            ).single()
        )
        uuid = result['uuid'] if result else None
        return {"iroko_uuid": uuid, "name": org_name, "from_generic": True} | identifier_props # Merge dicts


    async def _create_or_link_peer_review(self, session, person_orcid: str, review_data: Dict[str, Any]):
        """Creates or links a Publication node based on peer review data and creates the REVIEWER_IN relationship."""
        pub_name = review_data.get('name', '').strip()
        pub_identifiers = review_data.get('identifiers', [])

        # Attempt to find Publication in DB first
        pub_node_uuid = None
        for id_obj in pub_identifiers:
            idtype = id_obj.get('idtype')
            value = id_obj.get('value')
            if idtype and value:
                query = f"MATCH (p:Publication) WHERE p.identifier#{idtype} = $value RETURN p.iroko_uuid AS uuid LIMIT 1"
                result = await session.execute_read(lambda tx: tx.run(query, value=value).single())
                if result:
                    pub_node_uuid = result['uuid']
                    break

        # If not found by identifier, try by name
        if not pub_node_uuid and pub_name:
            query = "MATCH (p:Publication) WHERE p.name = $name RETURN p.iroko_uuid AS uuid LIMIT 1"
            result = await session.execute_read(lambda tx: tx.run(query, name=pub_name).single())
            if result:
                pub_node_uuid = result['uuid']

        # If still not found, create a new Publication node
        if not pub_node_uuid:
            # Prepare properties and identifier map for the new Publication
            pub_properties = {"name": pub_name} # Add other properties from review_data if applicable
            identifier_props = {}
            for id_obj in pub_identifiers:
                idtype = id_obj.get('idtype')
                value = id_obj.get('value')
                if idtype and value:
                    identifier_props[f"identifier#{idtype}"] = value

            # Cypher to create Publication node
            # Use a primary identifier or name for the MERGE key
            primary_id_key = next((f"identifier#{id_obj['idtype']}" for id_obj in pub_identifiers if id_obj.get('idtype')), None)
            if primary_id_key:
                 primary_id_value = identifier_props[primary_id_key]
                 merge_condition = f"{{ {primary_id_key}: $primary_id_value }}"
            else:
                 primary_id_value = pub_name
                 merge_condition = "{ name: $primary_id_value }"

            create_pub_query = f"""
            MERGE (pub:Publication {merge_condition})
            ON CREATE SET
                pub.iroko_uuid = toString(randomUUID()),
                pub += $properties
            ON MATCH SET
                pub += $properties
            RETURN pub.iroko_uuid AS uuid
            """

            result = await session.execute_write(
                lambda tx: tx.run(create_pub_query, primary_id_value=primary_id_value, properties=pub_properties).single()
            )
            pub_node_uuid = result['uuid'] if result else None


        # Create the REVIEWER_IN relationship
        if pub_node_uuid:
            roles = review_data.get('roles', [])
            start_date = review_data.get('start_date')
            end_date = review_data.get('end_date')
            # affiliation_type seems misplaced in peer review schema, ignore for relationship props

            # Cypher to merge the relationship
            merge_rel_query = """
            MATCH (p:Person {identifier#orcid: $person_orcid})
            MATCH (pub:Publication {iroko_uuid: $pub_uuid})
            MERGE (p)-[r:REVIEWER_IN]->(pub)
            SET r.roles = $roles, r.start_date = $start_date, r.end_date = $end_date
            """

            await session.execute_write(
                lambda tx: tx.run(
                    merge_rel_query,
                    person_orcid=person_orcid,
                    pub_uuid=pub_node_uuid,
                    roles=roles,
                    start_date=start_date,
                    end_date=end_date
                )
            )
        else:
            self.logger.warning(f"Could not establish peer review link for ORCID {person_orcid} and pub '{pub_name}', no pub node found or created.")


    async def _save_created_orgs_json(self):
        """Saves the list of organizations created during the process to a JSON file."""
        if self._created_orgs_json:
            output_path = os.path.join(self.output_folder, "created_organizations.json")
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self._created_orgs_json, f, ensure_ascii=False, indent=2)
            self.logger.info(f"Saved {len(self._created_orgs_json)} created organizations to {output_path}.")
        else:
            self.logger.info("No organizations were created during the process.")




class OrcidMappingTaskDepr(CrawlerTask):
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
        'keyword': 'http://www.orcid.org/ns/keyword',
        'other-name': 'http://www.orcid.org/ns/other-name'
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
            orcid, person_data = await self._map_orcid_to_schema(root, xml_file)
            
            if orcid != '' and person_data:
                # Save as JSON file
                output_filename = f"{orcid}.json"
                output_path = Path(self.output_dir) / output_filename
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(person_data, f, indent=2, ensure_ascii=False)
                
                # Store mapping in Neo4j
                # await self._store_mapping_in_neo4j(session, person_data, str(xml_file))
                
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
            orcid, identifiers = self._extract_identifiers(root)
            person_data = {
                "iroko_id": str(uuid.uuid4()),  # Generate Iroko UUID
                "identifiers": identifiers,
                "name": self._extract_full_name(root),
                "given_name": self._extract_given_name(root),
                "family_name": self._extract_family_name(root),
                "public": self._extract_visibility_status(root),
                "gender": self._extract_gender(root),
                "country": self._extract_country(root),
                "email_addresses": self._extract_emails(root),
                "aliases": self._extract_aliases(root),
                "academic_titles": self._extract_academic_titles(root),
                "affiliations": self._extract_affiliations(root)
            }
            
            # Validate required fields are present
            if not all([person_data["iroko_id"], person_data["identifiers"], person_data["name"]]):
                self.logger.warning(f"Missing required fields in ORCID record from {xml_file}")
                return None
                
            return orcid, person_data
            
        except Exception as e:
            self.logger.error(f"Error mapping ORCID to schema for {xml_file}: {str(e)}")
            return None
    
    def _extract_identifiers(self, root) -> List[Dict[str, str]]:
        """
        Extract person identifiers from ORCID record[citation:1][citation:7].
        """
        identifiers = []
        orcid = ''
        # ORCID iD itself[citation:1]
        orcid_element = root.find('.//common:orcid-identifier', self.NAMESPACES)
        if orcid_element is not None:
            path_element = orcid_element.find('common:path', self.NAMESPACES)
            if path_element is not None and path_element.text:
                identifiers.append({
                    "idtype": "orcid",
                    "value": path_element.text
                })
                orcid = path_element.text
        
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
        
        return orcid, identifiers
    
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

    def _extract_given_name(self, root) -> str:
        """
        Extract family name from ORCID record.
        """
        given_names_elem = root.find('.//personal-details:given-names', self.NAMESPACES)
        return given_names_elem.text if given_names_elem is not None else ""

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
        # try:

        other_names = root.findall('.//other-name:other-names', self.NAMESPACES)
        
        if other_names:
            for name_elem in other_names:
                if name_elem.text:
                    aliases.append(name_elem.text)
        # except:
        #     return aliases
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
                "iroko_id": str(uuid.uuid4()),  # Generate organization relationship UUID
                "affiliation_type": affiliation_type,
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
            "iroko_id": person_data["iroko_id"],
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
        return [] 