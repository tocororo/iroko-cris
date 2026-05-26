from abc import ABC, abstractmethod
import json
import string
from typing import Dict, Any, List, Optional, Tuple
import logging
import os
from pathlib import Path
from lxml import etree
import shutil

from uuid import UUID
import uuid
import xml.etree.ElementTree as ET

import unicodedata

import pycountry
from iroko.tasks.schemas import TaskExecution
from iroko.tasks.task import CrawlerTask
from iroko.storage import neo4j_db
from iroko.database import AsyncSessionLocal
from iroko.nodes.service import NodeService


import asyncio
import json
import re
import pandas as pd
import xmltodict

from iroko.tasks.tasks import organizations


logger = logging.getLogger('iroko-cris.tasks')


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
            session = neo4j_db.get_session()
            async with AsyncSessionLocal() as pg_session:
                service = NodeService(pg_session, session)
                results = await self._process_orcid_dump(service)

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
    
    async def _process_orcid_dump(self, service: NodeService) -> Dict[str, Any]:
        base_path = Path(self.base_path)
        results = {"total_files_processed": 0, "cuban_researchers": [], "saved_files": [], "errors": []}
        
        for folder_name in os.listdir(base_path):
            folder_path = base_path / folder_name
            if not folder_path.exists():
                continue
                
            self.logger.debug(f"Processing folder: {folder_name}")
            
            for xml_file in folder_path.glob("*.xml"):
                try:
                    await self._process_orcid_file(xml_file, service, results)
                except Exception as e:
                    error_msg = f"Error processing file {xml_file}: {str(e)}"
                    self.logger.error(error_msg)
                    results["errors"].append(error_msg)
        
        return results
    
    async def _process_orcid_file(self, xml_file: Path, service: NodeService, results: Dict[str, Any]):
        self.logger.debug(f"Processing ORCID file: {xml_file}")
        
        try:
            tree = etree.parse(str(xml_file))
            root = tree.getroot()

            orcid_element = root.find(".//{http://www.orcid.org/ns/common}orcid-identifier")
            orcid_id = None
            
            if orcid_element is not None:
                path_element = orcid_element.find("{http://www.orcid.org/ns/common}path")
                if path_element is not None:
                    orcid_id = path_element.text
            
            if not orcid_id:
                orcid_id = xml_file.stem
            
            is_cuban_researcher = await self._is_cuban_researcher(root, orcid_id, service.mg)
            
            self.processed_count += 1
            results["total_files_processed"] += 1
            
            if is_cuban_researcher:
                self.cuban_researchers_count += 1
                
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
                
                await self._store_researcher_in_neo4j(service, orcid_id, researcher_data, is_cuban_researcher)
                
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
    
    async def _store_researcher_in_neo4j(self, service: NodeService, orcid_id: str, 
                                       researcher_data: Dict[str, Any], 
                                       cuban_indicator: Dict[str, Any]):
        # Lookup existing researcher by orcid_id
        result = await service.mg.run(
            "MATCH (r:Researcher {orcid_id: $id}) RETURN r.iroko_uuid as uuid",
            id=orcid_id)
        rec = await result.single()
        existing_uuid = UUID(rec["uuid"]) if rec else None

        r_node = await service.merge_node(
            iroko_uuid=existing_uuid,
            name=orcid_id,
            labels=['Researcher'],
            data={
                'orcid_id': orcid_id,
                'identification_method': cuban_indicator["method"],
                'confidence': cuban_indicator.get("confidence", "medium"),
                'file_path': researcher_data["file_path"],
                'saved_file_path': researcher_data["saved_file_path"],
            })

        indicator = cuban_indicator
        result = await service.mg.run(
            "MATCH (ci:CubanIndicator {type: $t}) RETURN ci.iroko_uuid as uuid",
            t=indicator["method"])
        rec = await result.single()
        ci_uuid = UUID(rec["uuid"]) if rec else None

        ci_node = await service.merge_node(
            iroko_uuid=ci_uuid,
            name=indicator["method"],
            labels=['CubanIndicator'],
            data={'type': indicator["method"]})

        await service.merge_relationship(
            r_node.iroko_uuid, ci_node.iroko_uuid, "HAS_INDICATOR",
            {'details': indicator.get("details"), 'confidence': indicator.get("confidence")})
    
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


class OrcidToIrokoMapper:
    # ORCID activity types
    AFFILIATION_ENUMS = {
        "employments": "employments",
        "educations": "educations",
        "qualifications": "qualifications",
        "invited-positions": "invited-positions",
        "distinctions": "distinctions",
        "memberships": "memberships",
        "services": "services",
        "fundings": "fundings",
    }

    def map(self, input_path: str, country_code: str = 'CU') -> Dict[str, Any]:
        tree = etree.parse(input_path)
        root = tree.getroot()

        result: Dict[str, Any] = {}

        orcid_id = self._extract_orcid_id(root)
        

        identifiers = []
        # add orcid id as an identifier
        if orcid_id:
            identifiers.append({"idtype": "orcid", "value": orcid_id, "relationship": "self"})

        identifiers.extend(self._extract_external_identifiers(root))
        identifiers.extend(self._extract_researcher_urls_as_identifiers(root))

        # ensure identifiers present (schema requires it)
        result["identifiers"] = identifiers or []

        # names
        name_full = self._extract_credit_name(root) or self._combine_name(root)
        if name_full:
            result["name"] = name_full
        given = self._extract_text(root, "given-names")
        family = self._extract_text(root, "family-name")
        if given:
            result["given_name"] = given
        if family:
            result["family_name"] = family

        # biography
        bio = self._extract_text(root, "biography")
        if bio:
            result["biography"] = bio

        # public boolean heuristic
        result["public"] = self._is_public_profile(root)

        # gender
        gender = self._extract_text(root, "gender")
        if gender:
            result["gender"] = gender

        # country top-level (primary)
        country = self._extract_country(root, country_code)
        if country:
            result["country"] = country

        # addresses
        addresses = self._extract_addresses(root)
        if addresses:
            result["addresses"] = addresses

        # emails
        emails = self._extract_emails(root)
        if emails:
            result["email_addresses"] = emails

        # aliases
        aliases = self._extract_other_names(root)
        if aliases:
            result["aliases"] = aliases

        # keywords
        keywords = self._extract_keywords(root)
        if keywords:
            result["keywords"] = keywords

        # affiliations (collect all ORCID affiliation types)
        affiliations = []
        # check grouped summaries (e.g., employment-summary under employments)
        for api_type, enum_val in [
            ("employment-summary", "employments"),
            ("education-summary", "educations"),
            ("qualification-summary", "qualifications"),
            ("invited-position-summary", "invited-positions"),
            ("distinction-summary", "distinctions"),
            ("membership-summary", "memberships"),
            ("service-summary", "services"),
            ("funding-summary", "fundings"),
        ]:
            nodes = root.xpath('.//*[local-name()="%s"]' % api_type)
            for n in nodes:
                mapped = self._map_affiliation_node(n, affiliation_type=enum_val)
                if mapped:
                    affiliations.append(mapped)
        # also check singular tags (employment, education, etc.)
        for singular, enum_val in [
            ("employment", "employments"),
            ("education", "educations"),
            ("qualification", "qualifications"),
            ("invited-position", "invited-positions"),
            ("distinction", "distinctions"),
            ("membership", "memberships"),
            ("service", "services"),
            ("funding", "fundings"),
        ]:
            nodes = root.xpath('.//*[local-name()="%s"]' % singular)
            for n in nodes:
                mapped = self._map_affiliation_node(n, affiliation_type=enum_val)
                if mapped:
                    affiliations.append(mapped)

        if affiliations:
            result["affiliations"] = self._dedupe_affiliations(affiliations)
        else:
            result["affiliations"] = []

        # peer-review mapping
        peer_reviews = self._extract_peer_reviews(root)
        result["peer-review"] = peer_reviews or []

        return result

    # ---------- Helper extraction methods ----------
    def _extract_orcid_id(self, root) -> Optional[str]:
        p = root.xpath('.//*[local-name()="orcid-identifier"]/*[local-name()="path"]/text()')
        if p:
            return p[0].strip()
        uri = root.xpath('.//*[local-name()="orcid-identifier"]/*[local-name()="uri"]/text()')
        if uri:
            u = uri[0].strip()
            return u.rstrip('/').split('/')[-1]
        alt = root.xpath('.//*[local-name()="orcid"]/text()')
        if alt:
            return alt[0].strip()
        return None

    def _extract_text(self, root, tag: str) -> Optional[str]:
        """
        Extract text for person-level fields like biography, respecting ORCID XML structure.
        Handles both:
        <biography><content>...</content></biography>
        and variants.
        """

        # 1. Find the element under PERSON only
        nodes = root.xpath(
            './/*[local-name()="person"]//*[local-name()="%s"]' % tag
        )

        if not nodes:
            return None

        node = nodes[0]

        # 2. ORCID biography rarely has direct text; try text() first anyway
        direct_text = node.xpath('text()')
        if direct_text and direct_text[0].strip():
            return direct_text[0].strip()

        # 3. ORCID biography uses <common:content>
        content_text = node.xpath('./*[local-name()="content"]/text()')
        if content_text:
            return content_text[0].strip()

        return None

    def _extract_credit_name(self, root) -> Optional[str]:
        n = root.xpath('.//*[local-name()="credit-name"]/text()')
        if n:
            return n[0].strip()
        n2 = root.xpath('.//*[local-name()="credit-name"]/*[local-name()="content"]/text()')
        if n2:
            return n2[0].strip()
        return None

    def _combine_name(self, root) -> Optional[str]:
        given = self._extract_text(root, "given-names")
        family = self._extract_text(root, "family-name")
        if given and family:
            return f"{given} {family}"
        if given:
            return given
        if family:
            return family
        return None

    def _is_public_profile(self, root) -> bool:
        nodes = root.xpath('.//*[local-name()="visibility"]/text()')
        for n in nodes:
            if n and n.strip().lower() == "public":
                return True
        return False

    def _extract_external_identifiers(self, root) -> List[Dict[str, str]]:
        """
        Extract only *person-level* external identifiers from ORCID XML.
        Avoids identifiers found inside activities, works, fundings, etc.
        """

        out: List[Dict[str, str]] = []

        # ORCID always uses namespaces, so we select by local-name
        # Path: record → person → external-identifiers → external-identifier
        nodes = root.xpath(
            './/*[local-name()="person"]/*[local-name()="external-identifiers"]/*[local-name()="external-identifier"]'
        )

        for n in nodes:
            idtype_nodes = (
                n.xpath('./*[local-name()="external-id-type"]/text()')
                or n.xpath('./*[local-name()="external-identifier-type"]/text()')
            )
            value_nodes = (
                n.xpath('./*[local-name()="external-id-value"]/text()')
                or n.xpath('./*[local-name()="external-identifier-value"]/text()')
            )
            url_nodes = (
                n.xpath('./*[local-name()="external-id-url"]/text()')
                or n.xpath('./*[local-name()="external-identifier-url"]/text()')
            )
            rel_nodes = (
                n.xpath('./*[local-name()="external-id-relationship"]/text()')
                or n.xpath('./*[local-name()="external-identifier-relationship"]/text()')
            )

            if not (idtype_nodes and value_nodes):
                continue

            idtype = idtype_nodes[0].strip()
            value = value_nodes[0].strip()
            rel = rel_nodes[0].strip() if rel_nodes else "self"
            if url_nodes and len(url_nodes) > 0:
                url = url_nodes[0].strip()
                out.append({
                    "idtype": idtype,
                    "value": value,
                    "relationship": rel,
                    "url": url
                })
            else:
                out.append({
                    "idtype": idtype,
                    "value": value,
                    "relationship": rel
                })

        return out

    def _extract_researcher_urls_as_identifiers(self, root) -> List[Dict[str, str]]:
        out = []
        nodes = root.xpath('.//*[local-name()="researcher-url"]') or root.xpath('.//*[local-name()="researcher-urls"]/*[local-name()="researcher-url"]')
        for r in nodes:
            # researcher-url may have 'url' -> 'value', or plain text
            v = r.xpath('.//*[local-name()="url"]/*[local-name()="value"]/text()') or r.xpath('.//*[local-name()="url"]/text()')
            name = r.xpath('.//*[local-name()="url-name"]/*[local-name()="value"]/text()') or r.xpath('.//*[local-name()="url-name"]/text()')
            if not v:
                # check researcher-url/text()
                txt = (r.text or "").strip()
                if txt:
                    v = [txt]
            if not name: 
                txt = (r.text or "").strip()
                if txt:
                    name = [txt]
            nname = name[0] if len(name) > 1 else ""
            out.append({"idtype": "profile-url", "value": v[0].strip(), "name": nname.strip()})
        return out

    def _extract_emails(self, root) -> List[str]:
        out = []
        nodes = root.xpath('.//*[local-name()="email"]')
        for e in nodes:
            if e.get("email"):
                out.append(e.get("email").strip())
            else:
                t = (e.text or "").strip()
                if t:
                    out.append(t)
        # unique preserve order
        seen = set()
        uniq = []
        for s in out:
            if s not in seen:
                seen.add(s)
                uniq.append(s)
        return uniq

    def _extract_other_names(self, root) -> List[str]:
        out = []
        nodes = root.xpath('.//*[local-name()="other-name"]') or root.xpath('.//*[local-name()="other-names"]/*[local-name()="other-name"]')
        for n in nodes:
            # content child or text
            c = n.xpath('./*[local-name()="content"]/text()') or n.xpath('./text()')
            if c:
                val = c[0].strip()
                if val:
                    out.append(val)
        # dedupe
        return list(dict.fromkeys(out))

    def _extract_keywords(self, root) -> List[str]:
        out = []
        nodes = root.xpath('.//*[local-name()="keyword"]')
        for n in nodes:
            c = n.xpath('./*[local-name()="content"]/text()') or n.xpath('./text()')
            if c:
                v = c[0].strip()
                if v:
                    out.append(v)
        return list(dict.fromkeys(out))
    
    def _extract_country(self, root, country_code: str) -> Optional[Dict[str, str]]:
        """
        Extract country for the person using rules:
        1. Check if country_code exists in employment affiliations
        2. Check if country_code exists in addresses
        
        Returns the country dict if found, otherwise None.
        """
        
        # Rule 1: Check employment affiliations
        if self._country_in_employments(root, country_code):
            return {"code": country_code, "name": ""}
        
        # Rule 2: Check addresses
        if self._country_in_addresses(root, country_code):
            return {"code": country_code, "name": ""}
        
        return None

    def _country_in_employments(self, root, country_code: str) -> bool:
        """
        Check if the given country_code exists in any employment affiliation.
        """
        # Find all employment affiliations
        employment_nodes = root.xpath('.//*[local-name()="employment-summary"]') + root.xpath('.//*[local-name()="employment"]')
        
        for employment in employment_nodes:
            # Extract organization country
            employment_country_nodes = employment.xpath('.//*[local-name()="organization"]//*[local-name()="address"]/*[local-name()="country"]/text()')
            if not employment_country_nodes:
                employment_country_nodes = employment.xpath('.//*[local-name()="organization"]//*[local-name()="country"]/text()')
            
            for emp_country in employment_country_nodes:
                if emp_country.strip().lower() == country_code.lower():
                    return True
        
        return False

    def _country_in_addresses(self, root, country_code: str) -> bool:
        """
        Check if the given country_code exists in any address.
        """
        # Check personal-details addresses
        personal_country_nodes = root.xpath('.//*[local-name()="personal-details"]//*[local-name()="country"]/*[local-name()="value"]/text()')
        if not personal_country_nodes:
            personal_country_nodes = root.xpath('.//*[local-name()="personal-details"]//*[local-name()="country"]/text()')
        
        for personal_country in personal_country_nodes:
            if personal_country.strip().lower() == country_code.lower():
                return True
        
        # Check general addresses
        address_country_nodes = root.xpath('.//*[local-name()="person"]//*[local-name()="address"]//*[local-name()="country"]/text()')
        for address_country in address_country_nodes:
            if address_country.strip().lower() == country_code.lower():
                return True
        
        return False

    def _extract_addresses(self, root) -> List[Dict[str, Any]]:
        out = []
        # Only extract addresses within the person tag
        nodes = root.xpath('.//*[local-name()="person"]//*[local-name()="address"]')
        for a in nodes:
            city = a.xpath('./*[local-name()="city"]/text()')
            region = a.xpath('./*[local-name()="region"]/text()')
            country = a.xpath('./*[local-name()="country"]/*[local-name()="value"]/text()') or a.xpath('./*[local-name()="country"]/text()')
            addr = {}
            if city and city[0].strip():
                addr["city"] = city[0].strip()
            if region and region[0].strip():
                addr["region"] = region[0].strip()
            if country and country[0].strip():
                addr["country"] = {"code": country[0].strip(), "name": ""}
            if addr:
                out.append(addr)
        return out

    def _map_affiliation_node(self, node, affiliation_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        try:
            affiliation: Dict[str, Any] = {}

            # organization name
            org_name_nodes = (
                node.xpath('.//*[local-name()="organization"]/*[local-name()="name"]/text()')
                or node.xpath('.//*[local-name()="organization-name"]/text()')
            )
            if org_name_nodes:
                affiliation["name"] = org_name_nodes[0].strip()

            # identifiers inside organization
            org_identifiers = []
            org_nodes = node.xpath('.//*[local-name()="organization"]')
            if org_nodes:
                org0 = org_nodes[0]

                # disambiguated-organization-identifier + source
                disamb_val = org0.xpath('.//*[local-name()="disambiguated-organization-identifier"]/text()')
                disamb_src = org0.xpath('.//*[local-name()="disambiguation-source"]/text()')
                if disamb_val:
                    idv = disamb_val[0].strip()
                    src = disamb_src[0].strip() if disamb_src else "disambiguated"
                    org_identifiers.append({"idtype": src, "value": idv, "relationship": "self"})

                # organization-id elements
                org_ids = org0.xpath('.//*[local-name()="organization-id"]')
                for oid in org_ids:
                    val = (oid.text or "").strip()
                    typ = oid.get("type") or oid.get("organization-id-type") or "org-id"
                    if val:
                        org_identifiers.append({"idtype": typ, "value": val, "relationship": "self"})

                # address country
                c_nodes = org0.xpath('.//*[local-name()="address"]/*[local-name()="country"]/text()')
                if c_nodes:
                    affiliation["country"] = {"code": c_nodes[0].strip(), "name": ""}

            if org_identifiers:
                affiliation["identifiers"] = org_identifiers

            # start and end dates
            start_date = self._parse_iso_date_from_node(
                node.xpath('./*[local-name()="start-date"]') or node.xpath('.//*[local-name()="start-date"]')
            )
            end_date = self._parse_iso_date_from_node(
                node.xpath('./*[local-name()="end-date"]') or node.xpath('.//*[local-name()="end-date"]')
            )
            if start_date:
                affiliation["start_date"] = start_date
            if end_date:
                affiliation["end_date"] = end_date

            # roles
            roles = []
            role_nodes = (
                node.xpath('.//*[local-name()="role-title"]/text()')
                or node.xpath('.//*[local-name()="role"]/text()')
            )
            for r in role_nodes:
                if r and r.strip():
                    roles.append(r.strip())

            if roles:
                affiliation["roles"] = list(dict.fromkeys(roles))

            # department-name — now ONLY here
            dept = node.xpath('.//*[local-name()="department-name"]/text()')
            if dept and dept[0].strip():
                affiliation["department_name"] = dept[0].strip()

            # affiliation type normalized
            if affiliation_type and affiliation_type in self.AFFILIATION_ENUMS:
                affiliation["affiliation_type"] = self.AFFILIATION_ENUMS[affiliation_type]

            # meaningful?
            if affiliation.get("name") or affiliation.get("identifiers") or affiliation.get("roles") or affiliation.get("department_name"):
                return affiliation

        except Exception as e:
            logger.debug("affiliation mapping error: %s", e)
            return None

        return None

    def _parse_iso_date_from_node(self, nodes) -> Optional[str]:
        """
        Accept a list of nodes (possibly empty). Return ISO date string 'YYYY-MM-DD', 'YYYY-MM', or 'YYYY'.
        ORCID typically uses nested year/month/day elements.
        """
        if not nodes:
            return None
        node = nodes[0]
        if isinstance(node, list):
            node = node[0]
        # look for year/month/day child nodes
        year = node.xpath('./*[local-name()="year"]/text()')
        month = node.xpath('./*[local-name()="month"]/text()')
        day = node.xpath('./*[local-name()="day"]/text()')
        if year:
            y = year[0].strip()
            if month:
                m = month[0].strip().zfill(2)
                if day:
                    d = day[0].strip().zfill(2)
                    return f"{y}-{m}-{d}"
                return f"{y}-{m}"
            return y
        # fallback: node text
        txt = (node.text or "").strip()
        if txt:
            return txt
        return None

    def _dedupe_affiliations(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        out = []
        for it in items:
            key = (
                it.get("name", ""),
                it.get("start_date", ""),
                it.get("end_date", ""),
                tuple(sorted([(i.get("idtype",""), i.get("value","")) for i in it.get("identifiers", [])]))
            )
            if key not in seen:
                seen.add(key)
                out.append(it)
        return out

    def _extract_peer_reviews(self, root) -> List[Dict[str, Any]]:
        """
        Extract journals where the person acts as a reviewer.
        Focuses on review-group-id (ISSN) for identifiers and convening-organization for organization details.
        """
        out = []

        # Find peer review groups and summaries
        nodes = root.xpath(
            './/*[local-name()="activities-summary"]//*[local-name()="peer-review"]'
        ) + root.xpath(
            './/*[local-name()="activities-summary"]//*[local-name()="peer-review-summary"]'
        ) + root.xpath(
            './/*[local-name()="peer-review-group"]'
        )

        # We'll track journals by their review-group-id to avoid duplicates
        journal_map = {}

        for n in nodes:
            try:
                # Extract the journal/convening organization information
                convening_org = n.xpath('.//*[local-name()="convening-organization"]')
                if not convening_org:
                    continue

                convening_org = convening_org[0]

                # Get the journal/organization name
                org_name_nodes = convening_org.xpath('.//*[local-name()="name"]/text()')
                if not org_name_nodes:
                    continue

                org_name = org_name_nodes[0].strip()

                # Get the review-group-id (typically ISSN for journals)
                review_group_id_nodes = n.xpath('.//*[local-name()="review-group-id"]/text()')
                if not review_group_id_nodes:
                    continue

                review_group_id = review_group_id_nodes[0].strip()

                # Use review-group-id as the key to group by journal
                journal_key = review_group_id

                if journal_key not in journal_map:
                    # Create new journal entry
                    journal_entry: Dict[str, Any] = {
                        "identifiers": []
                    }

                    # Extract ISSN from review-group-id and add to identifiers
                    if ':' in review_group_id:
                        # Handle formats like "issn:1050-4648"
                        id_type, id_value = review_group_id.split(':', 1)
                        journal_entry["identifiers"].append({
                            "idtype": id_type,
                            "value": id_value,
                            "relationship": "self"
                        })
                    else:
                        journal_entry["identifiers"].append({
                            "idtype": "issn",
                            "value": review_group_id,
                            "relationship": "self"
                        })

                    # Build organization object
                    organization: Dict[str, Any] = {
                        "name": org_name,
                        "identifiers": []
                    }

                    # Extract organization identifiers from convening-organization
                    # disambiguated-organization-identifier + source
                    disamb_val = convening_org.xpath('.//*[local-name()="disambiguated-organization-identifier"]/text()')
                    disamb_src = convening_org.xpath('.//*[local-name()="disambiguation-source"]/text()')
                    if disamb_val:
                        idv = disamb_val[0].strip()
                        src = disamb_src[0].strip() if disamb_src else "disambiguated"
                        organization["identifiers"].append({"idtype": src, "value": idv, "relationship": "self"})

                    # organization-id elements
                    org_ids = convening_org.xpath('.//*[local-name()="organization-id"]')
                    for oid in org_ids:
                        val = (oid.text or "").strip()
                        typ = oid.get("type") or oid.get("organization-id-type") or "org-id"
                        if val:
                            organization["identifiers"].append({"idtype": typ, "value": val, "relationship": "self"})

                    # Add organization to journal entry
                    journal_entry["organization"] = organization

                    # Extract roles from this peer review
                    roles = set()
                    rnodes = n.xpath('.//*[local-name()="reviewer-role"]/text()') + \
                            n.xpath('.//*[local-name()="review-role"]/text()')
                    for r in rnodes:
                        if r.strip():
                            roles.add(r.strip())

                    if roles:
                        journal_entry["roles"] = list(roles)

                    # Extract review dates
                    completion_date = n.xpath('.//*[local-name()="completion-date"]') or \
                                    n.xpath('.//*[local-name()="review-completion-date"]')
                    if completion_date:
                        cd = self._parse_iso_date_from_node(completion_date)
                        if cd:
                            journal_entry["start_date"] = cd

                    journal_map[journal_key] = journal_entry

                else:
                    # Update existing journal entry with additional roles
                    existing_entry = journal_map[journal_key]
                    
                    # Add any new roles
                    rnodes = n.xpath('.//*[local-name()="reviewer-role"]/text()') + \
                            n.xpath('.//*[local-name()="review-role"]/text()')
                    for r in rnodes:
                        if r.strip():
                            if "roles" not in existing_entry:
                                existing_entry["roles"] = set()
                            elif isinstance(existing_entry["roles"], list):
                                existing_entry["roles"] = set(existing_entry["roles"])
                            existing_entry["roles"].add(r.strip())

            except Exception as e:
                logger.debug("peer-review journal mapping error: %s", e)
                continue

        # Convert sets to lists and prepare final output
        for journal in journal_map.values():
            if "roles" in journal and isinstance(journal["roles"], set):
                journal["roles"] = list(journal["roles"])
            
            # Ensure we have at least the organization and identifiers
            if journal.get("organization") and journal.get("identifiers"):
                out.append(journal)

        return out


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

            # self.logger.info("Loading Person JSON Schema...")
            # with open(self.person_schema_path, 'r', encoding='utf-8') as f:
            #      self.person_json_schema = json.load(f)

            # )

            self.logger.info("Starting ORCID mapping step...")
            # await self._step1_mapping()

            self.logger.info("Starting Neo4j ingestion step...")
            await self._step2_ingest()

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

        mapper = OrcidToIrokoMapper()
        
        
        for idx, filename in enumerate(xml_files):
            self.logger.info(f"Processing file {idx + 1}/{total_files}: {filename}")
            input_path = os.path.join(self.input_folder, filename)

            try:
                orcid_value = os.path.splitext(filename)[0]


                output_filename = f"{orcid_value}.json"
                output_path = os.path.join(self.output_folder, output_filename)
                person = mapper.map(input_path)
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(person, f, ensure_ascii=False, indent=2)
 
            except ET.ParseError as pe:
                self.logger.error(f"XML parsing error for {filename}: {pe}")
                # Optionally, continue processing other files or raise
                # raise
            except Exception as e:
                self.logger.error(f"Unexpected error processing {filename}: {e}", exc_info=True)
                # Optionally, continue processing other files or raise
                # raise

    async def _step2_ingest(self):
        """Ingests the mapped JSON files into Neo4j."""
        
        self.failed_folder = f"{self.output_folder}_failed"
        os.makedirs(self.failed_folder, exist_ok=True)
        self.logger.info(f"Failed ingestion files will be moved to: {self.failed_folder}")
        
        self.no_country_folder = f"{self.output_folder}_no_country"
        os.makedirs(self.no_country_folder, exist_ok=True)
        self.logger.info(f"no_country ingestion files will be moved to: {self.no_country_folder}")


        json_files = [f for f in os.listdir(self.output_folder) if f.endswith('.json')]
        total_files = len(json_files)

        self.logger.info("Loading DIUNE data...")
        self.diune_df = pd.read_excel(self.diune_path, dtype=str)
        # Use unicodedata for normalization instead of unidecode
        self.diune_df['descripcion_lower'] = self.diune_df['descripcion'].apply(
        lambda x: unicodedata.normalize('NFKD', x.lower())
            .encode('ascii', 'ignore')
            .decode('ascii')
            .translate(str.maketrans('', '', string.punctuation + ' ')) 
            if pd.notna(x) else x
        )
        
        # Files to track created organizations
        self.diune_organizations_file = os.path.join(f'{self.output_folder}_nodes', "diune_organizations.json")
        self.new_organizations_file = os.path.join(f'{self.output_folder}_nodes', "new_organizations.json")
        self.created_diune_orgs = []
        self.created_new_orgs = []

        self.new_publications_file = os.path.join(f'{self.output_folder}_nodes', "new_publications.json")
        self.created_new_publications = []

        self.no_orcid_file = os.path.join(f'{self.output_folder}_nodes', "no_orcid.json")
        self.no_orcid = []
        
        try:
            session = neo4j_db.get_session()
            async with AsyncSessionLocal() as pg_session:
                service = NodeService(pg_session, session)
                for idx, filename in enumerate(json_files):
                    self.logger.info(f"Ingesting file {idx + 1}/{total_files}: {filename}")
                    input_path = os.path.join(self.output_folder, filename)

                    with open(input_path, 'r', encoding='utf-8') as f:
                        person_data = json.load(f)

                    person_identifiers = person_data.get('identifiers', [])
                    orcid_id = next((id_obj['value'] for id_obj in person_identifiers if id_obj.get('idtype') == 'orcid'), None)

                    if not orcid_id:
                        self.logger.warning(f"No ORCID found in {filename}, skipping ingestion.")
                        self.no_orcid.append({"file": filename, "orcid": orcid_id})
                        continue

                    try:
                        await self._ingest_person_unit_of_work(service, person_data, orcid_id)
                    except Exception as e:
                        self.logger.error(f"Failed to ingest {filename}. Error: {e}", exc_info=True)
                        await self._copy_failed_file(input_path, filename, self.failed_folder)

            # Save created organizations to files
            self._save_new_nodes_to_file()

        except Exception as e:
            self.logger.error(f"Failed to start ingest ", exc_info=True)

    async def _ingest_person_unit_of_work(self, service: NodeService, person_data, orcid_id):
        country = person_data.get('country')
        if country and country.get('code'):
            await self._process_person_properties(service, person_data, orcid_id)
            await self._process_identifiers(service, person_data, orcid_id)
            await self._process_keywords(service, person_data, orcid_id)

            affiliations = person_data.get('affiliations', [])
            for affiliation in affiliations:
                await self._create_or_link_affiliation(service, person_data, affiliation, orcid_id)

            peer_reviews = person_data.get('peer-review', [])
            for review in peer_reviews:
                await self._create_or_link_peer_review(service, person_data, review, orcid_id)
        else:
            input_path = os.path.join(self.input_folder, f'{orcid_id}.xml')
            await self._copy_failed_file(input_path, f'{orcid_id}.xml', self.no_country_folder)
        

    async def _copy_failed_file(self, source_path: str, filename: str, destination_folder: str):
        """Moves a file that failed ingestion to the designated 'failed' directory."""
        if not self.failed_folder:
            self.logger.error("The 'failed_folder' path is not configured. Cannot move the file.")
            return

        destination_path = os.path.join(destination_folder, filename)
        try:
            # shutil.move is a synchronous (blocking) operation, but it's typically
            # very fast and acceptable to call within an async method for local file operations.
            shutil.copy(source_path, destination_path)
            self.logger.info(f"Successfully moved failed file '{filename}' to '{destination_path}'")
        except FileNotFoundError:
            self.logger.error(f"Could not move file. Source file not found: {source_path}")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred while moving file '{filename}'. Error: {e}", exc_info=True)

    async def _process_identifiers(self, service: NodeService, person_data, orcid_id):
        person_identifiers = person_data.get('identifiers', [])
        
        # Get Person node uuid
        result = await service.mg.run(
            "MATCH (p:Person {orcid: $id}) RETURN p.iroko_uuid as uuid", id=orcid_id)
        rec = await result.single()
        person_uuid = UUID(rec["uuid"]) if rec else None
        if not person_uuid:
            return

        for identifier in person_identifiers:
            idtype = identifier.get('idtype')
            value = identifier.get('value')
            name = identifier.get('name', '')
            url = identifier.get('url', '')
            relationship = identifier.get('relationship', 'self')
            
            if not idtype or not value:
                continue

            # Lookup existing Identifier node
            result = await service.mg.run(
                "MATCH (i:Identifier {idtype: $t, value: $v}) RETURN i.iroko_uuid as uuid",
                t=idtype, v=value)
            rec = await result.single()
            ident_uuid = UUID(rec["uuid"]) if rec else None

            data = {'idtype': idtype, 'value': value}
            if name: data['name'] = name
            if url: data['url'] = url

            ident_node = await service.merge_node(
                iroko_uuid=ident_uuid, name=value, labels=['Identifier'], data=data)

            await service.merge_relationship(
                person_uuid, ident_node.iroko_uuid, "HAS_IDENTIFIER",
                {"relationship": relationship})

    async def _process_person_properties(self, service: NodeService, person_data, orcid_id):
        # Lookup existing Person by orcid
        result = await service.mg.run(
            "MATCH (p:Person {orcid: $id}) RETURN p.iroko_uuid as uuid", id=orcid_id)
        rec = await result.single()
        existing_uuid = UUID(rec["uuid"]) if rec else None

        data = {
            'orcid': orcid_id,
            'name': person_data.get('name'),
            'given_name': person_data.get('given_name'),
            'family_name': person_data.get('family_name'),
            'biography': person_data.get('biography'),
            'public': person_data.get('public', False),
        }
        person_node = await service.merge_node(
            iroko_uuid=existing_uuid, name=person_data.get('name') or orcid_id,
            labels=['Person'], data=data)

        country = person_data.get('country')
        if country and country.get('code'):
            await self._link_country_to_person(service, str(person_node.iroko_uuid), country)
        
        # Process addresses
        # addresses = person_data.get('addresses', [])
        # for address in addresses:
        #     if address.get('country') and address['country'].get('code'):
        #         await self._link_country_to_person(session, orcid_id, address['country'])

    async def _process_keywords(self, session, person_data, orcid_id):
        """Process keywords and create Term/Keyword nodes."""
        keywords = person_data.get('keywords', [])

        DELIMITERS = r'[,;\n\r]+'

        # Get Person node uuid
        result = await service.mg.run(
            "MATCH (p:Person {orcid: $id}) RETURN p.iroko_uuid as uuid", id=orcid_id)
        rec = await result.single()
        person_uuid = UUID(rec["uuid"]) if rec else None
        if not person_uuid:
            return

        for keyword in keywords:
            if not keyword:
                continue
            sub_keywords = [kw.strip() for kw in re.split(DELIMITERS, keyword) if kw.strip()]
            for sub_keyword in sub_keywords:
                result = await service.mg.run(
                    "MATCH (t:Term:Keyword {name: $n}) RETURN t.iroko_uuid as uuid", n=sub_keyword)
                rec = await result.single()
                kw_uuid = UUID(rec["uuid"]) if rec else None

                kw_node = await service.merge_node(
                    iroko_uuid=kw_uuid, name=sub_keyword,
                    labels=['Term', 'Keyword'],
                    data={'vocabulary': 'keyword'})

                await service.merge_relationship(person_uuid, kw_node.iroko_uuid, "HAS_KEYWORD")

    async def _create_or_link_affiliation(self, service: NodeService, person_data, affiliation, orcid_id):
        org_name = affiliation.get('name')
        if not org_name:
            return

        organization_node = await self._find_or_create_organization(service, affiliation)
        if not organization_node or orcid_id is None:
            return

        result = await service.mg.run(
            "MATCH (p:Person {orcid: $id}) RETURN p.iroko_uuid as uuid", id=orcid_id)
        rec = await result.single()
        person_uuid = UUID(rec["uuid"]) if rec else None
        if not person_uuid:
            return

        rel_type = affiliation.get('affiliation_type', '').replace('-', '_').upper() + '_IN'
        props = {
            'roles': affiliation.get('roles'),
            'start_date': affiliation.get('start_date'),
            'end_date': affiliation.get('end_date'),
            'department_name': affiliation.get('department_name'),
        }
        props = {k: v for k, v in props.items() if v is not None}

        await service.merge_relationship(person_uuid, UUID(organization_node['iroko_uuid']), rel_type, props)

    async def _find_or_create_organization(self, service: NodeService, affiliation):
        org_name = affiliation.get('name')
        if not org_name:
            return

        normalized_name = (unicodedata.normalize('NFKD', org_name.lower())
                   .encode('ascii', 'ignore')
                   .decode('ascii')
                   .translate(str.maketrans('', '', string.punctuation + ' ')))
        
        organization_node = await self._find_organization_by_identifiers(service.mg, affiliation.get('identifiers', []))
        
        if not organization_node:
            organization_node = await self._find_organization_by_name(service.mg, org_name, normalized_name)
            
        if not organization_node:
            organization_node = await self._find_organization_in_diune(service, org_name, normalized_name)
            
        if not organization_node:
            organization_node = await self._create_new_organization(service, org_name, affiliation)
        
        country = affiliation.get('country')
        if country and country.get('code'):
            await self._link_country_to_organization(service, organization_node['iroko_uuid'], country)
        
        return organization_node
    
    async def _find_organization_by_identifiers(self, session, identifiers):
        """Find organization by its identifiers."""
        for identifier in identifiers:
            if not identifier.get('idtype') or not identifier.get('value'):
                continue
                
            query = """
            MATCH (o:Organization)-[:HAS_IDENTIFIER]->(i:Identifier {idtype: $idtype, value: $value})
            RETURN o.iroko_uuid as iroko_uuid, o.name as name
            LIMIT 1
            """
            result = await session.run(query, idtype=identifier['idtype'], value=identifier['value'])
            record = await result.single()
            
            if record:
                return dict(record)
        return None

    async def _find_organization_by_name(self, session, org_name, normalized_name):
        """Find organization by name in Neo4j."""
        # OR apoc.text.clean(o.name) = $normalized_name
        query = """
        MATCH (o:Organization)
        WHERE o.name = $org_name 
        RETURN o.iroko_uuid as iroko_uuid, o.name as name
        LIMIT 1
        """
        result = await session.run(query, org_name=org_name, normalized_name=normalized_name)
        record = await result.single()
        return dict(record) if record else None

    async def _find_organization_in_diune(self, service: NodeService, org_name, normalized_name):
        diune_match = self.diune_df[self.diune_df['descripcion_lower'] == normalized_name]
        
        if not diune_match.empty:
            diune_row = diune_match.iloc[0]
            data = {
                'descripcion': diune_row['descripcion'],
                'descripcion_nae': diune_row.get('descripcion_nae'),
                'descripcion_cnae': diune_row.get('descripcion_cnae'),
                'forma_organizativa': diune_row.get('desfo'),
            }
            node = await service.merge_node(
                name=diune_row['descripcion'],
                labels=['Organization'],
                data=data)

            await self._link_country_to_organization(
                service, str(node.iroko_uuid), {"code": "cu", "name": "Cuba"})

            # Create ONEI identifier
            onei_value = f"onei.diune.{diune_row['codigo']}"
            result = await service.mg.run(
                "MATCH (i:Identifier {idtype: 'onei', value: $v}) RETURN i.iroko_uuid as uuid",
                v=onei_value)
            rec = await result.single()
            ident_uuid = UUID(rec["uuid"]) if rec else None

            ident_node = await service.merge_node(
                iroko_uuid=ident_uuid, name=onei_value,
                labels=['Identifier'],
                data={'idtype': 'onei', 'value': onei_value})

            await service.merge_relationship(
                node.iroko_uuid, ident_node.iroko_uuid, "HAS_IDENTIFIER")

            self.created_diune_orgs.append({
                'iroko_uuid': str(node.iroko_uuid),
                'name': diune_row['descripcion'],
                'descripcion': diune_row['descripcion'],
                'descripcion_nae': diune_row.get('descripcion_nae'),
                'descripcion_cnae': diune_row.get('descripcion_cnae'),
                'forma_organizativa': diune_row.get('desfo'),
                'onei_identifier': onei_value
            })

            return {'iroko_uuid': str(node.iroko_uuid), 'name': diune_row['descripcion']}
            
        return None

    async def _create_new_organization(self, service: NodeService, org_name, affiliation):
        node = await service.merge_node(
            name=org_name,
            labels=['Organization'],
            data={'name': org_name})

        country = affiliation.get('country')
        if country and country.get('code'):
            await self._link_country_to_organization(service, str(node.iroko_uuid), country)

        identifiers = affiliation.get('identifiers', [])
        for identifier in identifiers:
            if identifier.get('idtype') and identifier.get('value'):
                result = await service.mg.run(
                    "MATCH (i:Identifier {idtype: $t, value: $v}) RETURN i.iroko_uuid as uuid",
                    t=identifier['idtype'], v=identifier['value'])
                rec = await result.single()
                ident_uuid = UUID(rec["uuid"]) if rec else None

                ident_node = await service.merge_node(
                    iroko_uuid=ident_uuid, name=identifier['value'],
                    labels=['Identifier'],
                    data={'idtype': identifier['idtype'], 'value': identifier['value']})

                await service.merge_relationship(
                    node.iroko_uuid, ident_node.iroko_uuid, "HAS_IDENTIFIER")

        org_data = {
            'iroko_uuid': str(node.iroko_uuid),
            'name': org_name,
            'country': country,
            'identifiers': identifiers
        }
        self.created_new_orgs.append(org_data)
        
        return {'iroko_uuid': str(node.iroko_uuid), 'name': org_name}

    async def _create_or_link_peer_review(self, service: NodeService, person_data, review, orcid_id):
        organization = review.get('organization')
        org_node = None
        if organization:
            org_name = organization.get('name')
            if org_name:
                temp_affiliation = {
                    'name': org_name,
                    'identifiers': organization.get('identifiers', []),
                    "affiliation_type": "reviewer"
                }
                org_node = await self._find_or_create_organization(service, temp_affiliation)
        
        publication_node = await self._find_or_create_publication(service, review, org_node)
        if not publication_node:
            return

        result = await service.mg.run(
            "MATCH (p:Person {orcid: $id}) RETURN p.iroko_uuid as uuid", id=orcid_id)
        rec = await result.single()
        person_uuid = UUID(rec["uuid"]) if rec else None
        if not person_uuid:
            return

        roles = review.get('roles', [])
        if not roles:
            return
        for role in roles:
            rel_type = role.upper() + '_IN'
            await service.merge_relationship(
                person_uuid, UUID(publication_node['iroko_uuid']), rel_type,
                {'roles': roles, 'start_date': review.get('start_date'), 'end_date': review.get('end_date')})

    async def _find_or_create_publication(self, service: NodeService, review, org_node):
        identifiers = review.get('identifiers', [])
        publication_node = await self._find_publication_by_identifiers(service.mg, identifiers)
        if publication_node:
            return publication_node

        issn_identifier = next((id_obj for id_obj in identifiers if id_obj.get('idtype') == 'issn'), None)
        if issn_identifier:
            publication_data = await self._fetch_publication_from_issn(issn_identifier['value'])
            if publication_data:
                return await self._create_publication_from_issn_data(service, publication_data, identifiers, review, org_node)

        return await self._create_publication_from_review(service, review, org_node)

    async def _find_publication_by_identifiers(self, session, identifiers):
        for identifier in identifiers:
            if not identifier.get('idtype') or not identifier.get('value'):
                continue
            query = """
            MATCH (pub:Publication)-[:HAS_IDENTIFIER]->(i:Identifier {idtype: $idtype, value: $value})
            RETURN pub.iroko_uuid as iroko_uuid, pub.name as name
            LIMIT 1
            """
            result = await session.run(query, idtype=identifier['idtype'], value=identifier['value'])
            record = await result.single()
            if record:
                return dict(record)
        return None

    async def _fetch_publication_from_issn(self, issn):
        import httpx
        url = f"https://portal.issn.org/resource/ISSN/{issn}?format=json"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=30.0)
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            self.logger.warning(f"Failed to fetch data from ISSN API for ISSN {issn}: {e}")
        return None

    async def _create_publication_from_issn_data(self, service, issn_data, original_identifiers, review, org_node):
        main_title = None
        graph_data = issn_data.get('@graph', [])
        for item in graph_data:
            if 'mainTitle' in item:
                main_title = item['mainTitle']
                break
        if not main_title:
            return None

        if isinstance(main_title, list):
            main_title = " | ".join(str(t) for t in main_title if t is not None)
        elif not isinstance(main_title, str):
            main_title = str(main_title)

        pub_node = await service.merge_node(
            name=main_title, labels=['Publication'], data={})

        all_identifiers = original_identifiers.copy()
        if not any(id_obj.get('idtype') == 'issn' for id_obj in all_identifiers):
            all_identifiers.append({'idtype': 'issn', 'value': issn_data.get('@id', '').split('/')[-1]})

        for identifier in all_identifiers:
            if identifier.get('idtype') and identifier.get('value'):
                result = await service.mg.run(
                    "MATCH (i:Identifier {idtype: $t, value: $v}) RETURN i.iroko_uuid as uuid",
                    t=identifier['idtype'], v=identifier['value'])
                rec = await result.single()
                ident_uuid = UUID(rec["uuid"]) if rec else None
                ident_node = await service.merge_node(
                    iroko_uuid=ident_uuid, name=identifier['value'],
                    labels=['Identifier'],
                    data={'idtype': identifier['idtype'], 'value': identifier['value']})
                await service.merge_relationship(
                    pub_node.iroko_uuid, ident_node.iroko_uuid, "HAS_IDENTIFIER")

        
        # Link to country if found
        country_code = None
        country_name = None
        for item in graph_data:
            if '@id' in item and 'http://id.loc.gov/vocabulary/countries/' in item['@id']:
                potential_code = item['@id'].split('/')[-1]
                potential_name = item.get('label', '')
                
                # Let _ensure_country_exists handle the normalization
                country_code = await self._ensure_country_exists(session, potential_code, potential_name)
                if country_code:
                    break
        if country_code:
            await self._link_country_to_publication(session, pub_uuid, country_code, country_name)
        
        # Link publication to organization 
        if org_node:
            org_uuid = org_node.get('iroko_uuid')
            if org_uuid:
                query = """
                    MATCH (pub:Publication {iroko_uuid: $pub_uuid})
                    MATCH (o:Organization {iroko_uuid: $org_uuid})
                    MERGE (pub)-[:SOURCE_CREATED_IN]->(o)
                    """
                result = await session.run(query, pub_uuid=pub_uuid, org_uuid=org_uuid)
                await result.consume()

        
        pub = dict(record) if record else None
        self.created_new_publications.append({'pub': pub_node, 'identifiers': all_identifiers})
        
        # Link country
        country_code = None
        country_name = None
        for item in graph_data:
            if '@id' in item and 'http://id.loc.gov/vocabulary/countries/' in item['@id']:
                potential_code = item['@id'].split('/')[-1]
                potential_name = item.get('label', '')
                country_code = await self._ensure_country_exists(service, potential_code, potential_name)
                if country_code:
                    break
        if country_code:
            await self._link_country_to_publication(service, str(pub_node.iroko_uuid), potential_code, potential_name)

        if org_node:
            org_uuid = org_node.get('iroko_uuid')
            if org_uuid:
                await self._link_country_to_organization(service, org_uuid, {"code": "cu", "name": "Cuba"})
                await service.merge_relationship(pub_node.iroko_uuid, UUID(org_uuid), "SOURCE_CREATED_IN")

        return {'iroko_uuid': str(pub_node.iroko_uuid), 'name': main_title}

    async def _create_publication_from_review(self, service: NodeService, review, org_node):
        identifiers = review.get('identifiers', [])
        name = "Unknown Publication"
        if identifiers:
            name = f"Publication ({identifiers[0].get('value', 'Unknown')})"

        pub_node = await service.merge_node(name=name, labels=['Publication'], data={})

        for identifier in identifiers:
            if identifier.get('idtype') and identifier.get('value'):
                result = await service.mg.run(
                    "MATCH (i:Identifier {idtype: $t, value: $v}) RETURN i.iroko_uuid as uuid",
                    t=identifier['idtype'], v=identifier['value'])
                rec = await result.single()
                ident_uuid = UUID(rec["uuid"]) if rec else None
                ident_node = await service.merge_node(
                    iroko_uuid=ident_uuid, name=identifier['value'],
                    labels=['Identifier'],
                    data={'idtype': identifier['idtype'], 'value': identifier['value']})
                await service.merge_relationship(
                    pub_node.iroko_uuid, ident_node.iroko_uuid, "HAS_IDENTIFIER")

        if org_node:
            org_uuid = org_node.get('iroko_uuid')
            if org_uuid:
                await service.merge_relationship(pub_node.iroko_uuid, UUID(org_uuid), "SOURCE_CREATED_IN")

        pub = {'iroko_uuid': str(pub_node.iroko_uuid), 'name': name}
        self.created_new_publications.append({'pub': pub, 'identifiers': identifiers})
        return pub

    async def _link_country_to_person(self, service: NodeService, person_uuid: str, country):
        country_code = country.get('code')
        country_name = country.get('name')
        if not country_code:
            return
        normalized_code = await self._ensure_country_exists(service, country_code, country_name)
        if normalized_code:
            await service.merge_relationship(
                UUID(person_uuid), UUID(normalized_code), "IN_COUNTRY")

    async def _link_country_to_publication(self, service: NodeService, pub_uuid: str, country_code, country_name):
        if not country_code:
            return
        normalized_code = await self._ensure_country_exists(service, country_code, country_name)
        if normalized_code:
            await service.merge_relationship(
                UUID(pub_uuid), UUID(normalized_code), "IN_COUNTRY")

    async def _link_country_to_organization(self, service: NodeService, org_uuid: str, country):
        country_code = country.get('code')
        country_name = country.get('name')
        if not country_code:
            return
        normalized_code = await self._ensure_country_exists(service, country_code, country_name)
        if normalized_code:
            await service.merge_relationship(
                UUID(org_uuid), UUID(normalized_code), "IN_COUNTRY")

    async def _ensure_country_exists(self, service: NodeService, country_code, country_name):
        if not country_code:
            return None
        
        original_code = country_code
        original_name = country_name
        normalized_code, normalized_name = self._normalize_country_code_and_name(country_code, country_name)
        country_code = normalized_code or original_code
        country_name = normalized_name or original_name
        if not country_name:
            country_name = country_code

        # Lookup existing country
        result = await service.mg.run(
            "MATCH (c:Country {code: $code}) RETURN c.iroko_uuid as uuid", code=country_code)
        rec = await result.single()
        existing_uuid = UUID(rec["uuid"]) if rec else None

        node = await service.merge_node(
            iroko_uuid=existing_uuid, name=country_name,
            labels=['Country'],
            data={'code': country_code, 'name': country_name})

        return str(node.iroko_uuid)

    def _normalize_country_code_and_name(self, country_code, country_name):
        """Comprehensive country normalization returning 2-letter code and name."""
        if not country_code:
            return None, country_name
        
        # Method 1: Check current countries by code
        country = pycountry.countries.get(alpha_2=country_code.upper())
        if country:
            return country.alpha_2, country.name
        
        # Method 2: Check historic countries by code
        historic_country = pycountry.historic_countries.get(alpha_2=country_code.upper())
        if historic_country:
            return historic_country.alpha_2, historic_country.name
        
        # Method 3: Check subdivisions (regions/states) by code
        subdivision = pycountry.subdivisions.get(code=country_code.upper())
        if subdivision:
            parent_country = pycountry.countries.get(alpha_2=subdivision.country_code)
            if parent_country:
                return parent_country.alpha_2, parent_country.name
        
        # Method 4: If we have a name but not a valid code, try fuzzy search by name
        if country_name:
            # Try current countries
            try:
                fuzzy_results = pycountry.countries.search_fuzzy(country_name)
                if fuzzy_results:
                    return fuzzy_results[0].alpha_2, fuzzy_results[0].name
            except LookupError:
                pass
            
            # Try historic countries
            try:
                historic_fuzzy = pycountry.historic_countries.search_fuzzy(country_name)
                if historic_fuzzy:
                    return historic_fuzzy[0].alpha_2, historic_fuzzy[0].name
            except LookupError:
                pass
            
            # Try subdivisions
            try:
                subdivision_fuzzy = pycountry.subdivisions.search_fuzzy(country_name)
                if subdivision_fuzzy:
                    parent_country = pycountry.countries.get(alpha_2=subdivision_fuzzy[0].country_code)
                    if parent_country:
                        return parent_country.alpha_2, parent_country.name
            except LookupError:
                pass
        
        # Method 5: Try fuzzy search with the code as name (for cases where code is actually a name)
        try:
            fuzzy_results = pycountry.countries.search_fuzzy(country_code)
            if fuzzy_results:
                return fuzzy_results[0].alpha_2, fuzzy_results[0].name
        except LookupError:
            pass
        
        # Final fallback: return original values
        return country_code, country_name

    def _normalize_country_code(self, country_code):
        """Normalize country code to 2-letter format."""
        if not country_code or len(country_code) == 2:
            return country_code
        
        try:
            # Try to convert 3-letter code to 2-letter code
            if len(country_code) == 3:
                country = pycountry.countries.get(alpha_3=country_code.upper())
                if country:
                    return country.alpha_2
            
            # Try to find by name
            country = pycountry.countries.get(name=country_code)
            if country:
                return country.alpha_2
            
            # Try case-insensitive search
            for country in pycountry.countries:
                if country_code.upper() in [country.alpha_2, country.alpha_3, country.name.upper()]:
                    return country.alpha_2
                    
        except Exception as e:
            print(f"Error normalizing country code {country_code}: {e}")
        
        # Return original if normalization fails
        return country_code

    def _save_new_nodes_to_file(self):
        """Save created organizations to JSON files."""
        if self.created_diune_orgs:
            with open(self.diune_organizations_file, 'w', encoding='utf-8') as f:
                json.dump(self.created_diune_orgs, f, ensure_ascii=False, indent=2)
            self.logger.info(f"Saved {len(self.created_diune_orgs)} DIUNE organizations to {self.diune_organizations_file}")
        
        if self.created_new_orgs:
            with open(self.new_organizations_file, 'w', encoding='utf-8') as f:
                json.dump(self.created_new_orgs, f, ensure_ascii=False, indent=2)
            self.logger.info(f"Saved {len(self.created_new_orgs)} new organizations to {self.new_organizations_file}")

        if self.created_new_publications:
            with open(self.new_publications_file, 'w', encoding='utf-8') as f:
                json.dump(self.created_new_publications, f, ensure_ascii=False, indent=2)
            self.logger.info(f"Saved {len(self.created_new_publications)} new publications to {self.new_publications_file}")

        if self.no_orcid:
            with open(self.no_orcid_file, 'w', encoding='utf-8') as f:
                json.dump(self.no_orcid, f, ensure_ascii=False, indent=2)
            self.logger.info(f"Saved {len(self.no_orcid)} new publications to {self.no_orcid_file}")

