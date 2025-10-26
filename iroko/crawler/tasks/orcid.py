from abc import ABC, abstractmethod
import json
from typing import Dict, Any, List
import logging
import os
from pathlib import Path
from lxml import etree
import shutil

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