import json
import unicodedata
import pandas as pd
from abc import ABC, abstractmethod
from typing import Dict, Any, List
import logging
import uuid

from sqlalchemy import desc
from iroko.tasks.schemas import TaskExecution
from iroko.tasks.task import CrawlerTask
from iroko.storage import neo4j_db

logger = logging.getLogger('iroko-cris')


def excel_dict(excel_file_path, output_json_path=None, sheet_name=0):
    # Read the Excel file
    df = pd.read_excel(excel_file_path, sheet_name=sheet_name, dtype=str)
    
    # Convert DataFrame to a list of dictionaries (each row becomes a dict)
    records = df.to_dict(orient='records')
    
    # Handle NaN values and ensure proper data types
    def clean_record(record):
        cleaned = {}
        for key, value in record.items():
            if pd.isna(value):
                cleaned[key] = None
            else:
                cleaned[key] = str(value)
        return cleaned
    
    clean_records = [clean_record(record) for record in records]
    return clean_records

class OrganizationsProcessingTask(CrawlerTask):
    """Task to process organizations data from various sources into Neo4j database"""

    async def execute(self, execution: TaskExecution) -> Dict[str, Any]:
        """
        Execute the organizations processing task
        
        Args:
            execution: Task execution record for tracking progress
            
        Returns:
            Dictionary with execution results
        """
        results = {
            "step1_codepa_processed": 0,
            "step2_organizations_cleaned": 0,
            "step3_diune_processed": 0,
            "step4_ror_processed": 0,
            "ror_not_found": []
        }
        
        session = neo4j_db.get_session()
        
        try:
            # STEP 1: Process codepa
            if "codepa" in self.config:
                codepa_path = self.config["codepa"]
                results["step1_codepa_processed"] = await self._process_codepa(session, codepa_path)
            
            # # STEP 2: Clean organization relationships
            results["step2_organizations_cleaned"] = await self._clean_organization_relationships(session)
            
            # STEP 3: Process diune
            if "diune" in self.config:
                diune_path = self.config["diune"]
                results["step3_diune_processed"] = await self._process_diune(session, diune_path)
            
            # STEP 4: Process ror
            if "ror" in self.config:
                ror_path = self.config["ror"]
                results.update(await self._process_ror(session, ror_path))
            
            self.logger.info(f"Organizations processing completed: {results}")

        
            # --- Save data dict to output file ---
            try:
                with open(self.config["output"], 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
                self.logger.info(f"Output results written to {self.config["output"]}")
            except Exception as e:
                self.logger.error(f"Failed to write output file {self.config["output"]}: {e}")
                raise
            return results
            
        except Exception as e:
            self.logger.error(f"Error during organizations processing: {str(e)}")
            raise
        finally:
            await session.close()

    def validate_config(self) -> bool:
        """
        Validate task configuration
        
        Returns:
            True if configuration is valid
        """
        required_keys = ["codepa", "diune", "ror", "output"]
        for key in required_keys:
            if key not in self.config or not self.config[key]:
                self.logger.error(f"Missing required configuration key: {key}")
                return False
        return True

    async def _process_codepa(self, session, codepa_path: str) -> int:
        """Process codepa excel file to create DPA nodes in Neo4j"""
        records = excel_dict(codepa_path)
        processed_count = 0
        
        for record in records:
            cod = record.get("COD")
            descripcion = record.get("DESCRIPCION")
            
            if not cod or not descripcion:
                continue
                
            # Determine if it's a province or municipality based on length
            is_province = len(cod) == 2
            tipo = "Provincia" if is_province else "Municipio"
            
            identifier = f"onei.dpa.{cod}"
            
            # Create the node
            query = """
            MERGE (n:Term:DPA {`identifier#onei`: $identifier})
            SET n.name = $descripcion,
                n.tipo = $tipo
            """
            
            await session.run(query, identifier=identifier, descripcion=descripcion, tipo=tipo)
            processed_count += 1
        
        # Now create relationships between municipalities and provinces
        for record in records:
            cod = record.get("COD")
            descripcion = record.get("DESCRIPCION")
            
            if not cod or not descripcion:
                continue
                
            # Only municipalities have parent relationships
            if len(cod) > 2:
                province_code = cod[:2]
                
                query = """
                MATCH (municipality:DPA {`identifier#onei`: $municipality_id})
                MATCH (province:DPA {`identifier#onei`: $province_id})
                MERGE (municipality)-[:PARENT]->(province)
                """
                
                municipality_id = f"onei.dpa.{cod}"
                province_id = f"onei.dpa.{province_code}"
                
                await session.run(query, municipality_id=municipality_id, province_id=province_id)
        
        self.logger.info(f"Processed {processed_count} DPA records from codepa")
        return processed_count

    async def _clean_organization_relationships(self, session) -> int:
        """Delete organizations that don't have at least one SOURCE_CREATED_IN relationship"""
        # Find organizations without SOURCE_CREATED_IN relationship
        query = """
        MATCH (org:Organization)
        WHERE NOT (org)<-[:SOURCE_CREATED_IN]-(:Publication)
        DETACH DELETE org
        RETURN count(org) as deleted_count
        """
        
        result = await session.run(query)
        record = await result.single()
        deleted_count = record["deleted_count"] if record else 0
        
        self.logger.info(f"Deleted {deleted_count} organizations without SOURCE_CREATED_IN relationships")
        return deleted_count

    async def _process_diune(self, session, diune_path: str) -> int:
        """Process diune excel file to update organization nodes in Neo4j"""
        records = excel_dict(diune_path)
        processed_count = 0
        created_nodes = []
        
        for record in records:
            codigo = record.get("codigo")
            
            if not codigo:
                continue
                
            # Handle the codigo formatting issue: remove leading zeros for matching with reup identifiers
            codigo_normalized = codigo.lstrip('0')  # Remove leading zeros
            if not codigo_normalized:  # If codigo was all zeros, keep at least one zero
                codigo_normalized = "0"
                
            old_identifier = f"reup.{codigo_normalized}"
            new_identifier = f"onei.diune.{codigo}"
                        
            # First, try to find node by the new identifier (in case this is a subsequent run)
            query_check_new = """
            MATCH (org:Organization {`identifier#onei`: $new_identifier})
            RETURN org
            """

            result_new = await session.run(query_check_new, new_identifier=new_identifier)
            existing_with_new = await result_new.single()

            if existing_with_new:
                
                # check if there is also a node with the older identifier
                q_check_old = """
                MATCH (org:Organization {`identifier#reup`: $old_identifier})
                RETURN org
                """
                result_old = await session.run(q_check_old, old_identifier=old_identifier)
                existing_with_old = await result_old.single()
                
                if existing_with_old:
                    # Keep the old node and update it with new identifier and properties, then delete the new duplicate
                    merge_query = """
                    MATCH (new_org:Organization {`identifier#onei`: $new_identifier})
                    MATCH (old_org:Organization {`identifier#reup`: $old_identifier})
                    
                    // Update the old node with new identifier and properties
                    WITH old_org, new_org
                    SET old_org.`identifier#onei` = $new_identifier,
                        old_org.descripcion = $descripcion,
                        old_org.descripcion_nae = $descripcion_nae,
                        old_org.descripcion_cnae = $descripcion_cnae,
                        old_org.forma_organizativa = $forma_organizativa,
                        old_org.name = coalesce(old_org.name, new_org.name, $descripcion)
                    REMOVE old_org.`identifier#reup`
                    
                    // Finally, delete the new duplicate node
                    WITH new_org
                    DETACH DELETE new_org
                    
                    RETURN count(*) as merged_count
                    """
                    
                    result = await session.run(
                        merge_query,
                        new_identifier=new_identifier,
                        old_identifier=old_identifier,
                        descripcion=record.get("descripcion"),
                        descripcion_nae=record.get("descripcion_nae"),
                        descripcion_cnae=record.get("descripcion_cnae"),
                        forma_organizativa=record.get("desfo")
                    )
                    
                    summary = await result.consume()
                    processed_count += 1
                    
                    self.logger.info(f"Merged duplicate nodes: kept {old_identifier} with new identifier {new_identifier}")
                    
                else:
                    # Node already exists with the new identifier, just update it
                    update_query = """
                    MATCH (org:Organization {`identifier#onei`: $new_identifier})
                    SET org.descripcion = $descripcion,
                        org.descripcion_nae = $descripcion_nae,
                        org.descripcion_cnae = $descripcion_cnae,
                        org.forma_organizativa = $forma_organizativa
                    """
                    
                    result = await session.run(
                        update_query,
                        new_identifier=new_identifier,
                        descripcion=record.get("descripcion"),
                        descripcion_nae=record.get("descripcion_nae"),
                        descripcion_cnae=record.get("descripcion_cnae"),
                        forma_organizativa=record.get("desfo")
                    )
                    
                    summary = await result.consume()
                    if summary.counters.properties_set > 0:
                        processed_count += 1
                
                # Update DPA relationship if needed (for both cases)
                dpa_code = record.get("dpa")
                if dpa_code:
                    dpa_identifier = f"onei.dpa.{dpa_code}"
                    
                    query = """
                    MATCH (org:Organization {`identifier#onei`: $org_identifier})
                    MATCH (dpa:DPA {`identifier#onei`: $dpa_identifier})
                    MERGE (org)-[:IN_DPA]->(dpa)
                    """
                    
                    await session.run(
                        query,
                        org_identifier=new_identifier,
                        dpa_identifier=dpa_identifier
                    )
                
                continue
            
            # If not found with new identifier, try to find with old reup identifier
            q_check_old = """
            MATCH (org:Organization {`identifier#reup`: $old_identifier})
            RETURN org
            """
            
            result_old = await session.run(q_check_old, old_identifier=old_identifier)
            existing_with_old = await result_old.single()
            
            if existing_with_old:
                # Update existing node from reup to onei identifier
                query = """
                MATCH (org:Organization {`identifier#reup`: $old_identifier})
                SET org.`identifier#onei` = $new_identifier,
                    org.descripcion = $descripcion,
                    org.descripcion_nae = $descripcion_nae,
                    org.descripcion_cnae = $descripcion_cnae,
                    org.forma_organizativa = $forma_organizativa
                REMOVE org.`identifier#reup`
                """
                
                result = await session.run(
                    query,
                    old_identifier=old_identifier,
                    new_identifier=new_identifier,
                    descripcion=record.get("descripcion"),
                    descripcion_nae=record.get("descripcion_nae"),
                    descripcion_cnae=record.get("descripcion_cnae"),
                    forma_organizativa=record.get("desfo")
                )
                
                summary = await result.consume()
                if summary.counters.properties_set > 0:
                    dpa_code = record.get("dpa")
                    if dpa_code:
                        dpa_identifier = f"onei.dpa.{dpa_code}"
                        
                        # Create relationship with DPA node
                        query = """
                        MATCH (org:Organization {`identifier#onei`: $org_identifier})
                        MATCH (dpa:DPA {`identifier#onei`: $dpa_identifier})
                        MERGE (org)-[:IN_DPA]->(dpa)
                        """
                        
                        await session.run(
                            query,
                            org_identifier=new_identifier,
                            dpa_identifier=dpa_identifier
                        )
                    
                    processed_count += 1
            else:
                # Node was not found with either identifier, check if we should create it based on keywords
                descripcion = record.get("descripcion")
                descripcion_cnae = record.get("descripcion_cnae", "")
                descripcion_nae = record.get("descripcion_nae", "")
                
                # Define keywords that indicate we should create the node
                keywords = ["ciencia", "investigacion", "INVESTIGACIONES", "ciencias", 
                        "universidad", "laboratorio", "instituto","cientifica", "cientificas"]
                
                # Check if any keyword appears in either field
                should_create = any(keyword.lower() in descripcion_cnae.lower() or 
                                keyword.lower() in descripcion_nae.lower() or 
                                keyword.lower() in descripcion.lower() 
                                for keyword in keywords)
                
                if should_create:
                    # Create the new organization node
                    create_query = """
                    CREATE (org:Organization {
                        id: $uuid,
                        `identifier#onei`: $new_identifier,
                        name: $descripcion,
                        descripcion: $descripcion,
                        descripcion_nae: $descripcion_nae,
                        descripcion_cnae: $descripcion_cnae,
                        forma_organizativa: $forma_organizativa
                    })
                    """
                    
                    uuid_val = str(uuid.uuid4())
                    
                    await session.run(
                        create_query,
                        uuid=uuid_val,
                        new_identifier=new_identifier,
                        descripcion=record.get("descripcion"),
                        descripcion_nae=record.get("descripcion_nae"),
                        descripcion_cnae=record.get("descripcion_cnae"),
                        forma_organizativa=record.get("desfo")
                    )
                    
                    # Create relationship with DPA if dpa field exists
                    dpa_code = record.get("dpa")
                    if dpa_code:
                        dpa_identifier = f"onei.dpa.{dpa_code}"
                        
                        # Create relationship with DPA node
                        query = """
                        MATCH (org:Organization {`identifier#onei`: $org_identifier})
                        MATCH (dpa:DPA {`identifier#onei`: $dpa_identifier})
                        MERGE (org)-[:IN_DPA]->(dpa)
                        """
                        
                        await session.run(
                            query,
                            org_identifier=new_identifier,
                            dpa_identifier=dpa_identifier
                        )
                    
                    # Record the created node
                    created_nodes.append({
                        "codigo": codigo,
                        "descripcion": record.get("descripcion"),
                        "descripcion_nae": record.get("descripcion_nae"),
                        "descripcion_cnae": record.get("descripcion_cnae"),
                        "uuid": uuid_val
                    })
                    
                    processed_count += 1
        
        self.logger.info(f"Processed {processed_count} organizations from diune, {len(created_nodes)} created")
        return processed_count

    async def _process_ror(self, session, ror_path: str) -> Dict[str, Any]:
        """Process ROR JSON file to update organization nodes in Neo4j"""
        with open(ror_path, 'r', encoding='utf-8') as f:
            ror_data = json.load(f)
        
        processed_count = 0
        not_found = []
        found_in_neo4j = []
        found_in_diune = []
            # Load diune data once at the beginning for optimization
        diune_df = None
        if "diune" in self.config:
            diune_path = self.config["diune"]
            # Read the Excel file directly with pandas for better performance
            diune_df = pd.read_excel(diune_path, dtype=str)
            # Convert descripcion to lowercase for case-insensitive matching
            diune_df['descripcion_lower'] = diune_df['descripcion'].str.lower()
        
        
        for ror_entry in ror_data:
            ror_id = ror_entry.get("id")
            
            if not ror_id:
                continue
            
            # Check if organization exists with this ROR ID
            query = """
            MATCH (org:Organization {`identifier#ror`: $ror_id})
            RETURN org
            """
            
            result = await session.run(query, ror_id=ror_id)
            record = await result.single()
            
            if record:
                # Update existing organization with ROR ID
                await self._update_organization_with_ror_data(session, ror_entry, ror_id)
                processed_count += 1
            else:
                # Search by names in the organization nodes
                names_data = ror_entry.get("names", [])
                found_org = False
                
                for name_entry in names_data:
                    name_value = name_entry.get("value")
                    if name_value:
                        # Search by name (case-insensitive)
                        search_query = """
                        MATCH (org:Organization)
                        WHERE toLower(org.name) = toLower($name_value)
                        RETURN org
                        LIMIT 1
                        """
                        
                        search_result = await session.run(search_query, name_value=name_value)
                        search_record = await search_result.single()
                        
                        if search_record:
                            # Update existing organization with ROR ID
                            await self._update_organization_with_ror_data(session, ror_entry, ror_id)
                            processed_count += 1
                            found_org = True
                            found_in_neo4j.append(name_value)
                            break
                
                if not found_org:
                    # Search in diune dataframe by descripcion if it exists
                    if diune_df is not None:
                        for name_entry in names_data:
                            name_value = name_entry.get("value")
                            if name_value:
                                normalized_name = unicodedata.normalize('NFD', name_value).encode('ascii', errors='ignore').decode('utf-8')
                                escaped_name_value = normalized_name.replace('"', '\\"')
                                escaped_name_value = escaped_name_value.replace(',', '\\,')
                                escaped_name_value = escaped_name_value.replace('.', '\\.')
                                escaped_name_value = escaped_name_value.replace(';', '\\;')
                                escaped_name_value = escaped_name_value.replace(':', '\\:')
                                escaped_name_value = escaped_name_value.replace("'", "\\'")
                                # Use pandas to find matching rows efficiently
                                matching_rows = diune_df[diune_df['descripcion_lower'] == escaped_name_value.lower()]
                                
                                if not matching_rows.empty:
                                    # Get the first matching row
                                    matched_row = matching_rows.iloc[0]
                                    
                                    # Create new organization from diune record
                                    codigo = matched_row['codigo']
                                    if codigo:
                                        new_identifier = f"onei.diune.{codigo}"
                                        
                                        # Create the organization node
                                        create_query = """
                                        CREATE (org:Organization {
                                            id: $uuid,
                                            `identifier#onei`: $new_identifier,
                                            `identifier#ror`: $ror_id,
                                            name: $name,
                                            descripcion: $descripcion,
                                            descripcion_nae: $descripcion_nae,
                                            descripcion_cnae: $descripcion_cnae,
                                            forma_organizativa: $forma_organizativa
                                        })
                                        """
                                        
                                        await session.run(
                                            create_query,
                                            uuid=str(uuid.uuid4()), 
                                            new_identifier=new_identifier,
                                            ror_id=ror_id,
                                            name=name_value,  # Using the name from ROR as the organization name
                                            descripcion=matched_row['descripcion'],
                                            descripcion_nae=matched_row.get('descripcion_nae'),
                                            descripcion_cnae=matched_row.get('descripcion_cnae'),
                                            forma_organizativa=matched_row.get('desfo')
                                        )
                                        
                                        # Now update with ROR data
                                        await self._update_organization_with_ror_data(session, ror_entry, ror_id, skip_ror_id=True)
                                        
                                        processed_count += 1
                                        found_org = True
                                        found_in_diune.append(name_value)
                                        break
                    
                    if not found_org:
                        # Add to not found list if no organization was found or created
                        not_found.append(ror_entry)
        
        self.logger.info(f"Processed {processed_count} organizations from ROR, {len(not_found)} not found")
        
        return {
            "step4_ror_processed": processed_count,
            "ror_not_found": not_found,
            "found_in_neo4j": found_in_neo4j,
            "found_in_diune": found_in_diune
        }

    async def _update_organization_with_ror_data(self, session, ror_entry, ror_id, skip_ror_id=False):
        """Helper method to update organization with ROR data"""
        # Process external IDs
        external_ids = ror_entry.get("external_ids", [])
        identifier_updates = {}
        for ext_id in external_ids:
            ext_type = ext_id.get("type")
            identifier_type = f"{ext_type}"
            preferred = ext_id.get("preferred")
            all_values = ext_id.get("all", [])
            
            if preferred is not None:
                identifier_value = preferred
            elif all_values:
                identifier_value = all_values[0] if all_values else None
            else:
                identifier_value = None
            
            if identifier_value is not None:
                identifier_updates[identifier_type] = identifier_value
        
        # Process names field to separate acronyms and aliases
        names_data = ror_entry.get("names", [])
        acronyms = []
        aliases = []
        
        for name_entry in names_data:
            value = name_entry.get("value")
            types = name_entry.get("types", [])
            
            if "acronym" in types:
                acronyms.append(value)
            if "label" in types:  # or "labels" depending on the actual field name
                aliases.append(value)
        
        # Process links field to only include website links
        links_data = ror_entry.get("links", [])
        websites = []
        
        for link_entry in links_data:
            link_type = link_entry.get("type")
            link_value = link_entry.get("value")
            
            if link_type == "website":
                websites.append(link_value)
        
        # Build the SET clause dynamically
        set_clauses = [
            "org.acronyms = $acronyms",
            "org.aliases = $aliases",
            "org.links = $websites",
            "org.organizationType = $types",
            "org.status = $status"
        ]
        
        # Add identifier#ror if not skipping
        if not skip_ror_id:
            set_clauses.append("org.`identifier#ror` = $ror_id")
        
        # Add id if the node doesn't have one
        set_clauses.append("org.id = coalesce(org.id, $uuid)")

        # Add identifier updates to the SET clause
        for identifier_type, identifier_value in identifier_updates.items():
            set_clauses.append(f"org.`identifier#{identifier_type}` = ${identifier_type}")
        
        # Join all SET clauses
        set_clause = ", ".join(set_clauses)
        
        # Create the final query
        update_query = f"""
        MATCH (org:Organization {{`identifier#ror`: $ror_id}})
        SET {set_clause}
        """
        
        # Prepare parameters
        params = {
            "ror_id": ror_id,
            "acronyms": acronyms,
            "aliases": aliases,
            "websites": websites,
            "types": ror_entry.get("types"),
            "status": ror_entry.get("status"),
            "uuid": str(uuid.uuid4()) 
        }
        
        # Add identifier parameters
        params.update(identifier_updates)
        
        await session.run(update_query, **params)