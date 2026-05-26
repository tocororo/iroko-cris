from uuid import UUID
import json
import unicodedata
import pandas as pd
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import logging
import uuid

from sqlalchemy import desc
from iroko.tasks.schemas import TaskExecution
from iroko.tasks.task import CrawlerTask
from iroko.storage import neo4j_db
from iroko.database import AsyncSessionLocal
from iroko.nodes.service import NodeService

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
        results = {
            "step1_codepa_processed": 0,
            "step2_organizations_cleaned": 0,
            "step3_diune_processed": 0,
            "step4_ror_processed": 0,
            "ror_not_found": []
        }
        
        session = neo4j_db.get_session()
        async with AsyncSessionLocal() as pg_session:
            service = NodeService(pg_session, session)
            try:
                if "codepa" in self.config:
                    codepa_path = self.config["codepa"]
                    results["step1_codepa_processed"] = await self._process_codepa(service, codepa_path)
                
                results["step2_organizations_cleaned"] = await self._clean_organization_relationships(service)
                
                if "diune" in self.config:
                    diune_path = self.config["diune"]
                    results["step3_diune_processed"] = await self._process_diune(service, diune_path)
                
                if "ror" in self.config:
                    ror_path = self.config["ror"]
                    results.update(await self._process_ror(service, ror_path))
                
                self.logger.info(f"Organizations processing completed: {results}")

                try:
                    with open(self.config["output"], 'w', encoding='utf-8') as f:
                        json.dump(results, f, indent=2, ensure_ascii=False)
                    self.logger.info(f"Output results written to {self.config['output']}")
                except Exception as e:
                    self.logger.error(f"Failed to write output file {self.config['output']}: {e}")
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

    async def _process_codepa(self, service: NodeService, codepa_path: str) -> int:
        records = excel_dict(codepa_path)
        processed_count = 0
        
        for record in records:
            cod = record.get("COD")
            descripcion = record.get("DESCRIPCION")
            if not cod or not descripcion:
                continue
                
            tipo = "Provincia" if len(cod) == 2 else "Municipio"
            identifier = f"onei.dpa.{cod}"

            # Lookup existing
            result = await service.mg.run(
                "MATCH (n:Term:DPA {`identifier#onei`: $id}) RETURN n.iroko_uuid as uuid",
                id=identifier)
            rec = await result.single()
            existing_uuid = UUID(rec["uuid"]) if rec else None

            await service.merge_node(
                iroko_uuid=existing_uuid,
                name=descripcion,
                labels=['Term', 'DPA'],
                data={'identifier#onei': identifier, 'tipo': tipo})
            processed_count += 1
        
        for record in records:
            cod = record.get("COD")
            if not cod or len(cod) <= 2:
                continue
                
            province_code = cod[:2]
            municipality_id = f"onei.dpa.{cod}"
            province_id = f"onei.dpa.{province_code}"

            result = await service.mg.run(
                "MATCH (n:Term:DPA {`identifier#onei`: $id}) RETURN n.iroko_uuid as uuid",
                id=municipality_id)
            mun_rec = await result.single()
            result = await service.mg.run(
                "MATCH (n:Term:DPA {`identifier#onei`: $id}) RETURN n.iroko_uuid as uuid",
                id=province_id)
            prov_rec = await result.single()

            if mun_rec and prov_rec:
                await service.merge_relationship(
                    UUID(mun_rec["uuid"]), UUID(prov_rec["uuid"]), "PARENT")
        
        self.logger.info(f"Processed {processed_count} DPA records from codepa")
        return processed_count

    async def _clean_organization_relationships(self, service: NodeService) -> int:
        # Find orgs to delete and collect uuids
        find_query = """
        MATCH (org:Organization)
        WHERE NOT (org)<-[:SOURCE_CREATED_IN]-(:Publication)
        RETURN org.iroko_uuid as uuid
        """
        result = await service.mg.run(find_query)
        uuids = []
        async for rec in result:
            if rec.get("uuid"):
                uuids.append(UUID(rec["uuid"]))
        
        # Delete from MG
        delete_query = """
        MATCH (org:Organization)
        WHERE NOT (org)<-[:SOURCE_CREATED_IN]-(:Publication)
        DETACH DELETE org
        RETURN count(org) as deleted_count
        """
        mg_result = await service.mg.run(delete_query)
        mg_rec = await mg_result.single()
        deleted_count = mg_rec["deleted_count"] if mg_rec else 0

        # Delete from PG
        for uid in uuids:
            try:
                await service.delete_node(uid)
            except Exception as e:
                self.logger.warning(f"Failed to delete org {uid} from PG: {e}")
        
        self.logger.info(f"Deleted {deleted_count} organizations without SOURCE_CREATED_IN relationships")
        return deleted_count

    async def _process_diune(self, service: NodeService, diune_path: str) -> int:
        records = excel_dict(diune_path)
        processed_count = 0
        created_nodes = []

        async def _get_org_uuid_by_identifier(id_val: str) -> Optional[str]:
            for lookup_key in ['identifier#onei', 'identifier#reup']:
                q = f"MATCH (org:Organization {{`{lookup_key}`: $id}}) RETURN org.iroko_uuid as uuid"
                r = await service.mg.run(q, id=id_val)
                rec = await r.single()
                if rec and rec.get("uuid"):
                    return rec["uuid"]
            return None

        async def _link_dpa(org_uuid: str, dpa_code: str):
            dpa_id = f"onei.dpa.{dpa_code}"
            q = "MATCH (dpa:DPA {`identifier#onei`: $id}) RETURN dpa.iroko_uuid as uuid"
            r = await service.mg.run(q, id=dpa_id)
            rec = await r.single()
            if rec and rec.get("uuid"):
                await service.merge_relationship(UUID(org_uuid), UUID(rec["uuid"]), "IN_DPA")

        for record in records:
            codigo = record.get("codigo")
            if not codigo:
                continue

            codigo_normalized = codigo.lstrip('0') or "0"
            old_identifier = f"reup.{codigo_normalized}"
            new_identifier = f"onei.diune.{codigo}"

            new_uuid = await _get_org_uuid_by_identifier(new_identifier)
            old_uuid = await _get_org_uuid_by_identifier(old_identifier)

            descripcion = record.get("descripcion")
            data = {
                'identifier#onei': new_identifier,
                'descripcion': descripcion,
                'descripcion_nae': record.get("descripcion_nae"),
                'descripcion_cnae': record.get("descripcion_cnae"),
                'forma_organizativa': record.get("desfo"),
            }
            name = descripcion or new_identifier

            if new_uuid and old_uuid and new_uuid != old_uuid:
                # Merge old into new: update old, delete new
                await service.merge_node(iroko_uuid=UUID(old_uuid), name=name, labels=['Organization'], data=data)
                await service.mg.run(
                    "MATCH (n {iroko_uuid: $uuid}) REMOVE n.`identifier#reup`",
                    uuid=old_uuid)
                await service.delete_node(UUID(new_uuid))
                processed_count += 1
            elif new_uuid:
                node_uuid = new_uuid
                await service.merge_node(iroko_uuid=UUID(node_uuid), name=name, labels=['Organization'], data=data)
                await service.mg.run(
                    "MATCH (n {iroko_uuid: $uuid}) REMOVE n.`identifier#reup`",
                    uuid=node_uuid)
                processed_count += 1
            elif old_uuid:
                node_uuid = old_uuid
                await service.merge_node(iroko_uuid=UUID(node_uuid), name=name, labels=['Organization'], data=data)
                await service.mg.run(
                    "MATCH (n {iroko_uuid: $uuid}) REMOVE n.`identifier#reup`",
                    uuid=node_uuid)
                processed_count += 1
            else:
                keywords = ["ciencia", "investigacion", "INVESTIGACIONES", "ciencias",
                            "universidad", "laboratorio", "instituto", "cientifica", "cientificas"]
                descripcion_cnae = record.get("descripcion_cnae", "") or ""
                descripcion_nae = record.get("descripcion_nae", "") or ""
                descripcion_text = descripcion or ""
                should_create = any(k.lower() in descripcion_cnae.lower() or
                                    k.lower() in descripcion_nae.lower() or
                                    k.lower() in descripcion_text.lower()
                                    for k in keywords)
                if should_create:
                    node = await service.merge_node(name=name, labels=['Organization'], data=data)
                    created_nodes.append({
                        "codigo": codigo,
                        "uuid": str(node.iroko_uuid),
                        **data
                    })
                    processed_count += 1

            dpa_code = record.get("dpa")
            if dpa_code:
                # Find the org uuid that was just processed
                org_uuid = await _get_org_uuid_by_identifier(new_identifier)
                if org_uuid:
                    await _link_dpa(org_uuid, dpa_code)

        self.logger.info(f"Processed {processed_count} organizations from diune, {len(created_nodes)} created")
        return processed_count

    async def _process_ror(self, service: NodeService, ror_path: str) -> Dict[str, Any]:
        with open(ror_path, 'r', encoding='utf-8') as f:
            ror_data = json.load(f)

        processed_count = 0
        not_found = []
        found_in_neo4j = []
        found_in_diune = []
        diune_df = None
        if "diune" in self.config:
            diune_path = self.config["diune"]
            diune_df = pd.read_excel(diune_path, dtype=str)
            diune_df['descripcion_lower'] = diune_df['descripcion'].str.lower()

        for ror_entry in ror_data:
            ror_id = ror_entry.get("id")
            if not ror_id:
                continue

            q = "MATCH (org:Organization {`identifier#ror`: $id}) RETURN org.iroko_uuid as uuid"
            r = await service.mg.run(q, id=ror_id)
            rec = await r.single()
            org_uuid = UUID(rec["uuid"]) if rec else None

            if org_uuid:
                await self._update_organization_with_ror_data(service, org_uuid, ror_entry, ror_id)
                processed_count += 1
            else:
                names_data = ror_entry.get("names", [])
                found_org = False

                for name_entry in names_data:
                    name_value = name_entry.get("value")
                    if not name_value:
                        continue
                    sq = "MATCH (org:Organization) WHERE toLower(org.name) = toLower($name) RETURN org.iroko_uuid as uuid LIMIT 1"
                    sr = await service.mg.run(sq, name=name_value)
                    srec = await sr.single()
                    if srec and srec.get("uuid"):
                        org_uuid = UUID(srec["uuid"])
                        await self._update_organization_with_ror_data(service, org_uuid, ror_entry, ror_id)
                        processed_count += 1
                        found_org = True
                        found_in_neo4j.append(name_value)
                        break

                if not found_org and diune_df is not None:
                    for name_entry in names_data:
                        name_value = name_entry.get("value")
                        if not name_value:
                            continue
                        normalized = unicodedata.normalize('NFD', name_value).encode('ascii', errors='ignore').decode('utf-8')
                        matching_rows = diune_df[diune_df['descripcion_lower'] == normalized.lower()]
                        if not matching_rows.empty:
                            matched_row = matching_rows.iloc[0]
                            codigo = matched_row['codigo']
                            if codigo:
                                data = {
                                    'identifier#onei': f"onei.diune.{codigo}",
                                    'descripcion': matched_row['descripcion'],
                                    'descripcion_nae': matched_row.get('descripcion_nae'),
                                    'descripcion_cnae': matched_row.get('descripcion_cnae'),
                                    'forma_organizativa': matched_row.get('desfo'),
                                }
                                node = await service.merge_node(name=name_value, labels=['Organization'], data=data)
                                org_uuid = node.iroko_uuid
                                await self._update_organization_with_ror_data(service, org_uuid, ror_entry, ror_id, skip_ror_id=True)
                                processed_count += 1
                                found_org = True
                                found_in_diune.append(name_value)
                                break

                if not found_org:
                    not_found.append(ror_entry)

        self.logger.info(f"Processed {processed_count} organizations from ROR, {len(not_found)} not found")
        return {
            "step4_ror_processed": processed_count,
            "ror_not_found": not_found,
            "found_in_neo4j": found_in_neo4j,
            "found_in_diune": found_in_diune
        }

    async def _update_organization_with_ror_data(self, service: NodeService, org_uuid: UUID, ror_entry, ror_id, skip_ror_id=False):
        external_ids = ror_entry.get("external_ids", [])
        identifier_updates = {}
        for ext_id in external_ids:
            ext_type = ext_id.get("type")
            preferred = ext_id.get("preferred")
            all_values = ext_id.get("all", [])
            identifier_value = preferred if preferred is not None else (all_values[0] if all_values else None)
            if identifier_value is not None:
                identifier_updates[f"{ext_type}"] = identifier_value

        names_data = ror_entry.get("names", [])
        acronyms = [n["value"] for n in names_data if "acronym" in n.get("types", []) and n.get("value")]
        aliases = [n["value"] for n in names_data if "label" in n.get("types", []) and n.get("value")]

        links_data = ror_entry.get("links", [])
        websites = [l["value"] for l in links_data if l.get("type") == "website" and l.get("value")]

        data = {
            'identifier#ror': ror_id,
            'acronyms': acronyms,
            'aliases': aliases,
            'links': websites,
            'organizationType': ror_entry.get("types", []),
            'status': ror_entry.get("status"),
        }
        for ext_type, ext_value in identifier_updates.items():
            data[f"identifier#{ext_type.lower()}"] = ext_value

        await service.merge_node(iroko_uuid=org_uuid, labels=['Organization'], data=data)