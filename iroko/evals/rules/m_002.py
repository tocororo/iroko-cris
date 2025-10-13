# iroko/evals/rules/m_001.py
"""
Rules for methodology m_001 (sceiba-journal evaluation)
"""
from typing import Dict, Any, Union
from neo4j import AsyncSession
from ..rules_registry import rules_registry

# =============================================================================
# QUESTION RULES for m_001
# =============================================================================

@rules_registry.register_question_rule('c_001_q_001')
async def c_001_q_001(node_data: dict, neo4j_session: AsyncSession) -> bool:
    """Está incluida en DOAJ"""
    query = """
    MATCH (s:Source {id: $node_id})-[:HAS_IDENTIFIER]->(id:Identifier)
    WHERE id.idtype = 'doaj' AND id.value IS NOT NULL
    RETURN COUNT(id) > 0 as in_doaj
    """
    result = await neo4j_session.run(query, node_id=node_data.get('id'))
    record = await result.single()
    return record['in_doaj'] if record else False

@rules_registry.register_question_rule('c_001_q_002')
async def c_001_q_002(node_data: dict, neo4j_session: AsyncSession) -> bool:
    """Está en Scopus y/o JCR de la Web de la Ciencia"""
    query = """
    MATCH (s:Source {id: $node_id})-[:HAS_IDENTIFIER]->(id:Identifier)
    WHERE id.idtype IN ['scopus', 'wos'] AND id.value IS NOT NULL
    RETURN COUNT(id) > 0 as in_index
    """
    result = await neo4j_session.run(query, node_id=node_data.get('id'))
    record = await result.single()
    return record['in_index'] if record else False

@rules_registry.register_question_rule('c_001_q_003')
async def c_001_q_003(node_data: dict, neo4j_session: AsyncSession) -> int:
    """Está incluida en base de datos de indización y resumen especializada"""
    query = """
    MATCH (s:Source {id: $node_id})-[:CLASSIFIED_BY]->(t:Term)
    WHERE t.vocabulary CONTAINS 'specialized'
    RETURN COUNT(t) as count_specialized
    """
    result = await neo4j_session.run(query, node_id=node_data.get('id'))
    record = await result.single()
    return record['count_specialized'] if record else 0

@rules_registry.register_question_rule('c_001_q_004')
async def c_001_q_004(node_data: dict, neo4j_session: AsyncSession) -> int:
    """Está incluida en base de datos de indización y resumen multidisciplinar"""
    query = """
    MATCH (s:Source {id: $node_id})-[:CLASSIFIED_BY]->(t:Term)
    WHERE t.vocabulary CONTAINS 'multidisciplinary'
    RETURN COUNT(t) as count_multidisciplinary
    """
    result = await neo4j_session.run(query, node_id=node_data.get('id'))
    record = await result.single()
    return record['count_multidisciplinary'] if record else 0

@rules_registry.register_question_rule('c_002_q_001')
async def c_002_q_001(node_data: dict, neo4j_session: AsyncSession) -> bool:
    """Existe un sitio web propio de la revista"""
    return bool(node_data.get('url'))

@rules_registry.register_question_rule('c_002_q_004')
async def c_002_q_004(node_data: dict, neo4j_session: AsyncSession) -> bool:
    """Existen artículos de la revista en repositorios nacional y/o institucional de acceso abierto"""
    query = """
    MATCH (s:Source {id: $node_id})<-[:COLLECTED_FROM]-(o:Output)
    WHERE o.source_repo CONTAINS 'institutional'
    RETURN COUNT(o) > 0 as has_institutional_outputs
    """
    result = await neo4j_session.run(query, node_id=node_data.get('id'))
    record = await result.single()
    return record['has_institutional_outputs'] if record else False

@rules_registry.register_question_rule('c_002_q_005')
async def c_002_q_005(node_data: dict, neo4j_session: AsyncSession) -> bool:
    """Existen artículos de la revista en repositorios de acceso abierto internacionales generales y/o temáticos"""
    query = """
    MATCH (s:Source {id: $node_id})<-[:COLLECTED_FROM]-(o:Output)
    WHERE o.source_repo CONTAINS 'international' OR o.source_repo CONTAINS 'zenodo'
    RETURN COUNT(o) > 0 as has_international_outputs
    """
    result = await neo4j_session.run(query, node_id=node_data.get('id'))
    record = await result.single()
    return record['has_international_outputs'] if record else False

@rules_registry.register_question_rule('c_003_q_001')
async def c_003_q_001(node_data: dict, neo4j_session: AsyncSession) -> bool:
    """Emplea algún formato de metadatos"""
    return bool(node_data.get('identifiers') and len(node_data.get('identifiers', [])) > 0)

@rules_registry.register_question_rule('c_003_q_003')
async def c_003_q_003(node_data: dict, neo4j_session: AsyncSession) -> bool:
    """Metadatos obligatorios OpenAIRE presentes"""
    required_fields = ['title', 'creators', 'publication_date']
    return all(field in node_data and node_data[field] for field in required_fields)

@rules_registry.register_question_rule('c_003_q_004')
async def c_003_q_004(node_data: dict, neo4j_session: AsyncSession) -> bool:
    """Metadatos recomendables OpenAIRE presentes"""
    recommended_fields = ['language', 'rights', 'publisher']
    present_fields = sum(1 for field in recommended_fields if field in node_data and node_data[field])
    return present_fields >= 2

@rules_registry.register_question_rule('c_003_q_005')
async def c_003_q_005(node_data: dict, neo4j_session: AsyncSession) -> bool:
    """Incluye ISSN y/o ISSN-E"""
    query = """
    MATCH (s:Source {id: $node_id})-[:HAS_IDENTIFIER]->(id:Identifier)
    WHERE id.idtype IN ['issn', 'eissn'] AND id.value IS NOT NULL
    RETURN COUNT(id) > 0 as has_issn
    """
    result = await neo4j_session.run(query, node_id=node_data.get('id'))
    record = await result.single()
    return record['has_issn'] if record else False

@rules_registry.register_question_rule('c_003_q_006')
async def c_003_q_006(node_data: dict, neo4j_session: AsyncSession) -> bool:
    """Incluye identificadores persistentes de objetos digitales"""
    digital_object_ids = ['doi', 'handle', 'purl', 'arxiv']
    query = """
    MATCH (s:Source {id: $node_id})-[:HAS_IDENTIFIER]->(id:Identifier)
    WHERE id.idtype IN $digital_object_ids AND id.value IS NOT NULL
    RETURN COUNT(id) > 0 as has_digital_id
    """
    result = await neo4j_session.run(query, node_id=node_data.get('id'), digital_object_ids=digital_object_ids)
    record = await result.single()
    return record['has_digital_id'] if record else False

@rules_registry.register_question_rule('c_003_q_007')
async def c_003_q_007(node_data: dict, neo4j_session: AsyncSession) -> bool:
    """Incluye identificadores persistentes para personas"""
    query = """
    MATCH (s:Source {id: $node_id})<-[:COLLECTED_FROM]-(o:Output)-[:CREATED_BY]->(a:Author)
    WHERE a.identifiers IS NOT NULL AND ANY(id IN a.identifiers WHERE id.idtype = 'orcid')
    RETURN COUNT(a) > 0 as has_orcid
    """
    result = await neo4j_session.run(query, node_id=node_data.get('id'))
    record = await result.single()
    return record['has_orcid'] if record else False

@rules_registry.register_question_rule('c_003_q_008')
async def c_003_q_008(node_data: dict, neo4j_session: AsyncSession) -> bool:
    """Incluye identificadores persistentes para organizaciones"""
    org_ids = ['grid', 'ror', 'isni']
    query = """
    MATCH (s:Source {id: $node_id})-[:SOURCE_CREATED_IN]->(o:Organization)
    WHERE o.identifiers IS NOT NULL AND ANY(id IN o.identifiers WHERE id.idtype IN $org_ids)
    RETURN COUNT(o) > 0 as has_org_ids
    """
    result = await neo4j_session.run(query, node_id=node_data.get('id'), org_ids=org_ids)
    record = await result.single()
    return record['has_org_ids'] if record else False

@rules_registry.register_question_rule('c_004_q_002')
async def c_004_q_002(node_data: dict, neo4j_session: AsyncSession) -> bool:
    """Declara que no tiene costo por procesamiento de artículos (APC)"""
    description = node_data.get('description', '').lower()
    apc_indicators = ['sin costo', 'no charge', 'free', 'gratuito', 'no apc']
    return any(indicator in description for indicator in apc_indicators)

@rules_registry.register_question_rule('c_004_q_003')
async def c_004_q_003(node_data: dict, neo4j_session: AsyncSession) -> bool:
    """Es una revista de acceso abierto y declara política de acceso abierto"""
    description = node_data.get('description', '').lower()
    oa_indicators = ['acceso abierto', 'open access', 'oa journal']
    return any(indicator in description for indicator in oa_indicators)

@rules_registry.register_question_rule('c_004_q_004')
async def c_004_q_004(node_data: dict, neo4j_session: AsyncSession) -> bool:
    """Promueve depósito de datos de investigación"""
    description = node_data.get('description', '').lower()
    data_deposit_indicators = ['datos de investigación', 'research data', 'data repository']
    return any(indicator in description for indicator in data_deposit_indicators)

@rules_registry.register_question_rule('c_004_q_005')
async def c_004_q_005(node_data: dict, neo4j_session: AsyncSession) -> bool:
    """Ofrece contenidos bajo licencia Creative Commons"""
    rights = node_data.get('rights', [])
    if isinstance(rights, list):
        rights = ' '.join(rights).lower()
    else:
        rights = str(rights).lower()
    cc_indicators = ['creative commons', 'cc by', 'cc-by']
    return any(indicator in rights for indicator in cc_indicators)

@rules_registry.register_question_rule('c_005_q_001')
async def c_005_q_001(node_data: dict, neo4j_session: AsyncSession) -> str:
    """Declara que acepta artículos en idioma"""
    languages = node_data.get('language')
    if not languages:
        return 'SOLAMENTE_ESPAÑOL'
    
    if isinstance(languages, list) and len(languages) > 1:
        return 'EN_MAS_DE_UN_IDIOMA'
    elif languages and 'es' not in str(languages).lower():
        return 'SOLAMENTE_UN_IDIOMA'
    else:
        return 'SOLAMENTE_ESPAÑOL'

@rules_registry.register_question_rule('c_006_q_001')
async def c_006_q_001(node_data: dict, neo4j_session: AsyncSession) -> bool:
    """Posee funcionalidad de compartir contenidos en redes sociales"""
    links = node_data.get('links', [])
    social_indicators = ['twitter', 'facebook', 'linkedin', 'share', 'social']
    return any(any(indicator in str(link).lower() for indicator in social_indicators) for link in links)

@rules_registry.register_question_rule('c_007_q_001')
async def c_007_q_001(node_data: dict, neo4j_session: AsyncSession) -> bool:
    """Tiene citas registradas"""
    query = """
    MATCH (s:Source {id: $node_id})<-[:COLLECTED_FROM]-(o:Output)
    WHERE o.citation_count IS NOT NULL AND o.citation_count > 0
    RETURN COUNT(o) > 0 as has_citations
    """
    result = await neo4j_session.run(query, node_id=node_data.get('id'))
    record = await result.single()
    return record['has_citations'] if record else False

# Placeholder rules for questions that need user input
@rules_registry.register_question_rule('c_002_q_002')
async def c_002_q_002(node_data: dict, neo4j_session: AsyncSession) -> str:
    """Están disponibles los últimos números en el sitio web de la revista"""
    return None

@rules_registry.register_question_rule('c_002_q_003')
async def c_002_q_003(node_data: dict, neo4j_session: AsyncSession) -> str:
    """Están disponibles los artículos de manera individual en el sitio web de la revista"""
    return None

@rules_registry.register_question_rule('c_003_q_002')
async def c_003_q_002(node_data: dict, neo4j_session: AsyncSession) -> bool:
    """Uso de OAI-PMH"""
    return None

@rules_registry.register_question_rule('c_004_q_001')
async def c_004_q_001(node_data: dict, neo4j_session: AsyncSession) -> str:
    """Permite depósito en plataformas no comerciales o comerciales"""
    return None

@rules_registry.register_question_rule('c_005_q_002')
async def c_005_q_002(node_data: dict, neo4j_session: AsyncSession) -> bool:
    """Porcentaje de artículos en Inglés supera el 15%"""
    return None

@rules_registry.register_question_rule('c_005_q_003')
async def c_005_q_003(node_data: dict, neo4j_session: AsyncSession) -> str:
    """Miembros del comité editorial de instituciones extranjeras"""
    return None

@rules_registry.register_question_rule('c_005_q_004')
async def c_005_q_004(node_data: dict, neo4j_session: AsyncSession) -> str:
    """Miembros externos a la institución editora"""
    return None

@rules_registry.register_question_rule('c_005_q_005')
async def c_005_q_005(node_data: dict, neo4j_session: AsyncSession) -> str:
    """Artículos firmados por miembros del consejo editorial"""
    return None

@rules_registry.register_question_rule('c_005_q_006')
async def c_005_q_006(node_data: dict, neo4j_session: AsyncSession) -> str:
    """Firma de autores afiliados a instituciones extranjeras"""
    return None

@rules_registry.register_question_rule('c_006_q_002')
async def c_006_q_002(node_data: dict, neo4j_session: AsyncSession) -> str:
    """Posee perfiles en redes sociales"""
    return None

@rules_registry.register_question_rule('c_006_q_003')
async def c_006_q_003(node_data: dict, neo4j_session: AsyncSession) -> str:
    """Difunde artículos a través de redes sociales"""
    return None

@rules_registry.register_question_rule('c_007_q_002')
async def c_007_q_002(node_data: dict, neo4j_session: AsyncSession) -> str:
    """Citas recibidas"""
    return None

@rules_registry.register_question_rule('c_007_q_003')
async def c_007_q_003(node_data: dict, neo4j_session: AsyncSession) -> str:
    """Índice H5 de la revista"""
    return None

@rules_registry.register_question_rule('c_008_q_001')
async def c_008_q_001(node_data: dict, neo4j_session: AsyncSession) -> str:
    """Está en rankings de revistas"""
    return None

# =============================================================================
# CATEGORY RULES for m_001
# =============================================================================

@rules_registry.register_category_rule('m_001_01_01', ['c_001_q_001', 'c_001_q_002', 'c_001_q_003', 'c_001_q_004'])
async def m_001_01_01(category_data: Dict, answers: Dict) -> Dict[str, Any]:
    """Calculate results and recommendations for Indización category"""
    score = 0
    max_score = 4
    recommendations = []
    
    if answers.get('c_001_q_001'):
        score += 1
    else:
        recommendations.append("Considerar inclusión en DOAJ")
    
    if answers.get('c_001_q_002'):
        score += 1
    else:
        recommendations.append("Buscar inclusión en Scopus o Web of Science")
    
    specialized_count = answers.get('c_001_q_003', 0)
    if specialized_count > 0:
        score += min(1, specialized_count / 2)
    else:
        recommendations.append("Incrementar presencia en bases de datos especializadas")
    
    multidisciplinary_count = answers.get('c_001_q_004', 0)
    if multidisciplinary_count > 0:
        score += min(1, multidisciplinary_count / 2)
    else:
        recommendations.append("Incrementar presencia en bases de datos multidisciplinarias")
    
    final_score = score / max_score
    
    return {
        'result': final_score,
        'recommendation': ' | '.join(recommendations) if recommendations else "Buena cobertura de indización"
    }

@rules_registry.register_category_rule('m_001_01_02', ['c_002_q_001', 'c_002_q_002', 'c_002_q_003', 'c_002_q_004', 'c_002_q_005'])
async def m_001_01_02(category_data: Dict, answers: Dict) -> Dict[str, Any]:
    """Calculate results and recommendations for Acceso category"""
    score = 0
    max_score = 5
    recommendations = []
    
    if answers.get('c_002_q_001'):
        score += 1
    else:
        recommendations.append("Desarrollar sitio web propio de la revista")
    
    # For select questions, we need specific logic based on the answer value
    access_availability = answers.get('c_002_q_002')
    individual_access = answers.get('c_002_q_003')
    
    if access_availability and individual_access:
        # Add scoring logic based on the specific values
        if 'SOLAMENTE_DISPONIBLE_ULTIMO_NUM' in str(access_availability):
            score += 0.5
        elif 'TODOS_NUM_PUBLICADOS_ULTIMOS_DOS_AÑOS' in str(access_availability):
            score += 1
        
        if 'SI_DISPONIBLE_IND_SI_DESC_NUM' in str(individual_access):
            score += 1
        elif 'SI_DISPONIBLE_IND_NO_DESC_NUM' in str(individual_access):
            score += 0.5
    
    if answers.get('c_002_q_004'):
        score += 1
    else:
        recommendations.append("Fomentar depósito en repositorios institucionales")
    
    if answers.get('c_002_q_005'):
        score += 1
    else:
        recommendations.append("Fomentar depósito en repositorios internacionales")
    
    final_score = score / max_score
    
    return {
        'result': final_score,
        'recommendation': ' | '.join(recommendations) if recommendations else "Acceso adecuado a los contenidos"
    }

@rules_registry.register_category_rule('m_001_01_03', [
    'c_003_q_001', 'c_003_q_002', 'c_003_q_003', 'c_003_q_004', 
    'c_003_q_005', 'c_003_q_006', 'c_003_q_007', 'c_003_q_008'
])
async def m_001_01_03(category_data: Dict, answers: Dict) -> Dict[str, Any]:
    """Calculate results and recommendations for Interoperabilidad category"""
    score = 0
    max_score = 8
    recommendations = []
    
    if answers.get('c_003_q_001'):
        score += 1
    else:
        recommendations.append("Implementar formatos de metadatos estandarizados")
    
    if answers.get('c_003_q_002'):
        score += 1
    else:
        recommendations.append("Implementar protocolo OAI-PMH")
    
    if answers.get('c_003_q_003'):
        score += 1
    else:
        recommendations.append("Incluir metadatos obligatorios OpenAIRE")
    
    if answers.get('c_003_q_004'):
        score += 1
    else:
        recommendations.append("Incluir metadatos recomendados OpenAIRE")
    
    if answers.get('c_003_q_005'):
        score += 1
    else:
        recommendations.append("Incluir identificadores ISSN")
    
    if answers.get('c_003_q_006'):
        score += 1
    else:
        recommendations.append("Incluir identificadores persistentes para objetos digitales")
    
    if answers.get('c_003_q_007'):
        score += 1
    else:
        recommendations.append("Incluir identificadores persistentes para autores (ORCID)")
    
    if answers.get('c_003_q_008'):
        score += 1
    else:
        recommendations.append("Incluir identificadores persistentes para organizaciones")
    
    final_score = score / max_score
    
    return {
        'result': final_score,
        'recommendation': ' | '.join(recommendations) if recommendations else "Buena interoperabilidad"
    }

@rules_registry.register_category_rule('m_001_01_04', ['c_004_q_001', 'c_004_q_002', 'c_004_q_003', 'c_004_q_004', 'c_004_q_005'])
async def m_001_01_04(category_data: Dict, answers: Dict) -> Dict[str, Any]:
    """Calculate results and recommendations for Apertura category"""
    score = 0
    max_score = 5
    recommendations = []
    
    deposit_policy = answers.get('c_004_q_001')
    if deposit_policy:
        if 'VARIAS_VERSIONES_ART' in str(deposit_policy):
            score += 1
        elif 'SOLAMENTE_VER_POST_PRINT' in str(deposit_policy):
            score += 0.7
        elif 'SOLAMENTE_VER_PREPRINT' in str(deposit_policy):
            score += 0.3
    
    if answers.get('c_004_q_002'):
        score += 1
    else:
        recommendations.append("Declarar política de no cobro por APC")
    
    if answers.get('c_004_q_003'):
        score += 1
    else:
        recommendations.append("Declarar política de acceso abierto")
    
    if answers.get('c_004_q_004'):
        score += 1
    else:
        recommendations.append("Promover depósito de datos de investigación")
    
    if answers.get('c_004_q_005'):
        score += 1
    else:
        recommendations.append("Adoptar licencias Creative Commons")
    
    final_score = score / max_score
    
    return {
        'result': final_score,
        'recommendation': ' | '.join(recommendations) if recommendations else "Buen nivel de apertura"
    }

@rules_registry.register_category_rule('m_001_01_05', ['c_005_q_001', 'c_005_q_002', 'c_005_q_003', 'c_005_q_004', 'c_005_q_005', 'c_005_q_006'])
async def m_001_01_05(category_data: Dict, answers: Dict) -> Dict[str, Any]:
    """Calculate results and recommendations for Internacionalización category"""
    score = 0
    max_score = 6
    recommendations = []
    
    language_policy = answers.get('c_005_q_001')
    if language_policy == 'EN_MAS_DE_UN_IDIOMA':
        score += 1
    elif language_policy == 'SOLAMENTE_UN_IDIOMA':
        score += 0.5
    else:
        recommendations.append("Considerar aceptar artículos en inglés")
    
    if answers.get('c_005_q_002'):
        score += 1
    else:
        recommendations.append("Incrementar porcentaje de artículos en inglés")
    
    # Add scoring for other internationalization factors
    foreign_editorial = answers.get('c_005_q_003')
    external_members = answers.get('c_005_q_004')
    editorial_publications = answers.get('c_005_q_005')
    foreign_authors = answers.get('c_005_q_006')
    
    # Simplified scoring for now - these would need more complex logic
    if foreign_editorial and 'MAS_DEL_50' in str(foreign_editorial):
        score += 1
    elif foreign_editorial and 'ENTRE_EL_20_Y_50' in str(foreign_editorial):
        score += 0.5
    
    if external_members and 'MAS_DEL_70' in str(external_members):
        score += 1
    elif external_members and 'ENTRE_EL_20_Y_70' in str(external_members):
        score += 0.5
    
    if editorial_publications and 'MENOS_DEL_20' in str(editorial_publications):
        score += 1
    elif editorial_publications and 'ENTRE_EL_20_Y_50' in str(editorial_publications):
        score += 0.5
    
    if foreign_authors and 'MAS_DEL_25' in str(foreign_authors):
        score += 1
    elif foreign_authors and 'ENTRE_EL_5_Y_25' in str(foreign_authors):
        score += 0.5
    
    final_score = score / max_score
    
    return {
        'result': final_score,
        'recommendation': ' | '.join(recommendations) if recommendations else "Buena internacionalización"
    }

@rules_registry.register_category_rule('m_001_01_06', ['c_006_q_001', 'c_006_q_002', 'c_006_q_003'])
async def m_001_01_06(category_data: Dict, answers: Dict) -> Dict[str, Any]:
    """Calculate results and recommendations for Redes sociales category"""
    score = 0
    max_score = 3
    recommendations = []
    
    if answers.get('c_006_q_001'):
        score += 1
    else:
        recommendations.append("Implementar funcionalidades de compartir en redes sociales")
    
    social_profiles = answers.get('c_006_q_002')
    if social_profiles == 'PERFIL_RED_SOC_SI_MENDELEY_RESEARCHGATE':
        score += 1
    elif social_profiles == 'PERFIL_RED_SOC_NO_MENDELEY_RESEARCHGATE':
        score += 0.5
    else:
        recommendations.append("Crear perfiles en redes sociales académicas")
    
    social_dissemination = answers.get('c_006_q_003')
    if social_dissemination == 'TWITTER_FACEBOOK_INSTAGRAM_MENDELEY_RESEARCHGATE':
        score += 1
    elif social_dissemination == 'GENERALES_TWITTER_FACEBOOK_INSTAGRAM':
        score += 0.7
    elif social_dissemination == 'SOLAMENTE_MENDELEY_RESEARCHGATE':
        score += 0.5
    else:
        recommendations.append("Utilizar redes sociales para difundir contenidos")
    
    final_score = score / max_score
    
    return {
        'result': final_score,
        'recommendation': ' | '.join(recommendations) if recommendations else "Buena presencia en redes sociales"
    }

@rules_registry.register_category_rule('m_001_02_01', ['c_007_q_001', 'c_007_q_002', 'c_007_q_003'])
async def m_001_02_01(category_data: Dict, answers: Dict) -> Dict[str, Any]:
    """Calculate results and recommendations for Impacto académico category"""
    score = 0
    max_score = 3
    recommendations = []
    
    if answers.get('c_007_q_001'):
        score += 1
    else:
        recommendations.append("Incrementar visibilidad para obtener más citas")
    
    citation_rate = answers.get('c_007_q_002')
    if citation_rate == 'MAS_DEL_50_ART_ULT_3_AÑOS_REC_ALGUNA_CITA':
        score += 1
    elif citation_rate == 'ENTRE_EL_20_Y_50_ART_ULT_3_AÑOS_REC_ALGUNA_CITA':
        score += 0.5
    else:
        recommendations.append("Mejorar calidad e impacto de los artículos")
    
    h5_index = answers.get('c_007_q_003')
    if h5_index == 'MAYOR_IND_H5_REV_PER_ANT':
        score += 1
    elif h5_index == 'MENOR_IGUAL_IND_H5_REV_PER_ANT':
        score += 0.5
    # No penalty for N/A
    
    final_score = score / max_score
    
    return {
        'result': final_score,
        'recommendation': ' | '.join(recommendations) if recommendations else "Buen impacto académico"
    }

@rules_registry.register_category_rule('m_001_02_02', ['c_008_q_001'])
async def m_001_02_02(category_data: Dict, answers: Dict) -> Dict[str, Any]:
    """Calculate results and recommendations for Posición en rankings category"""
    ranking = answers.get('c_008_q_001')
    score = 0
    recommendations = []
    
    if ranking == 'Q1_Q2_JOURNAL_CITATION':
        score = 1.0
    elif ranking == 'Q3_Q4_JOURNAL_CITATION':
        score = 0.7
    elif ranking == 'SOLAMENTE_RANKINGS_REV_REG_TEMAT':
        score = 0.4
    else:
        recommendations.append("Buscar inclusión en rankings internacionales")
    
    return {
        'result': score,
        'recommendation': ' | '.join(recommendations) if recommendations else "Buena posición en rankings"
    }

# =============================================================================
# SECTION RULES for m_001
# =============================================================================

@rules_registry.register_section_rule('m_001_01', ['m_001_01_01', 'm_001_01_02', 'm_001_01_03', 'm_001_01_04', 'm_001_01_05', 'm_001_01_06'])
async def m_001_01(section_data: Dict, category_results: Dict) -> Dict[str, Any]:
    """Calculate overall Visibilidad section results"""
    visibility_categories = ['m_001_01_01', 'm_001_01_02', 'm_001_01_03', 'm_001_01_04', 'm_001_01_05', 'm_001_01_06']
    
    total_score = 0
    valid_categories = 0
    recommendations = []
    
    for category_id in visibility_categories:
        category_result = category_results.get(category_id, {})
        if category_result and 'result' in category_result and category_result['result'] is not None:
            total_score += category_result['result']
            valid_categories += 1
            if category_result.get('recommendation'):
                recommendations.append(category_result['recommendation'])
    
    final_score = total_score / valid_categories if valid_categories > 0 else 0
    
    # Overall recommendation based on score
    if final_score >= 0.8:
        overall_rec = "Excelente visibilidad"
    elif final_score >= 0.6:
        overall_rec = "Buena visibilidad"
    else:
        overall_rec = "Visibilidad necesita mejora"
    
    if recommendations:
        overall_rec += f". Recomendaciones: {'; '.join(recommendations)}"
    
    return {
        'result': final_score,
        'recommendation': overall_rec
    }

@rules_registry.register_section_rule('m_001_02', ['m_001_02_01', 'm_001_02_02'])
async def m_001_02(section_data: Dict, category_results: Dict) -> Dict[str, Any]:
    """Calculate overall Impacto section results"""
    impact_categories = ['m_001_02_01', 'm_001_02_02']
    
    total_score = 0
    valid_categories = 0
    recommendations = []
    
    for category_id in impact_categories:
        category_result = category_results.get(category_id, {})
        if category_result and 'result' in category_result and category_result['result'] is not None:
            total_score += category_result['result']
            valid_categories += 1
            if category_result.get('recommendation'):
                recommendations.append(category_result['recommendation'])
    
    final_score = total_score / valid_categories if valid_categories > 0 else 0
    
    # Overall recommendation based on score
    if final_score >= 0.8:
        overall_rec = "Excelente impacto"
    elif final_score >= 0.6:
        overall_rec = "Buen impacto"
    else:
        overall_rec = "Impacto necesita mejora"
    
    if recommendations:
        overall_rec += f". Recomendaciones: {'; '.join(recommendations)}"
    
    return {
        'result': final_score,
        'recommendation': overall_rec
    }

# =============================================================================
# METHODOLOGY RULES for m_001
# =============================================================================

@rules_registry.register_methodology_rule('m_002', ['m_001_01', 'm_001_02'])
async def m_002(evaluation_result: Dict, section_results: Dict) -> Dict[str, Any]:
    """Calculate final methodology results and overall recommendations"""
    visibility_score = section_results.get('m_001_01', {}).get('result', 0)
    impact_score = section_results.get('m_001_02', {}).get('result', 0)
    
    # Weighted final score (60% visibility, 40% impact)
    final_score = (visibility_score * 0.6) + (impact_score * 0.4)
    
    recommendations = []
    
    visibility_rec = section_results.get('m_001_01', {}).get('recommendation')
    impact_rec = section_results.get('m_001_02', {}).get('recommendation')
    
    if visibility_rec:
        recommendations.append(f"Visibilidad: {visibility_rec}")
    if impact_rec:
        recommendations.append(f"Impacto: {impact_rec}")
    
    # Overall assessment
    if final_score >= 0.8:
        overall_assessment = "Revista de excelente calidad"
    elif final_score >= 0.6:
        overall_assessment = "Revista de buena calidad"
    elif final_score >= 0.4:
        overall_assessment = "Revista que necesita mejoras"
    else:
        overall_assessment = "Revista que requiere mejoras significativas"
    
    return {
        'final_score': final_score,
        'overall_assessment': overall_assessment,
        'recommendations': recommendations
    }