# iroko/evals/rules/m_001.py
"""
Rules for methodology m_001 (sceiba-journal evaluation)
"""
from typing import Dict, Any, Union
from neo4j import AsyncSession

from iroko.evals.schemas import Answer
from ..rules_registry import rules_registry

# =============================================================================
# QUESTION RULES for m_001
# =============================================================================

@rules_registry.register_question_rule('c_001_q_001')
async def c_001_q_001(node_data: dict, neo4j_session: AsyncSession) -> Answer:
    """Está incluida en DOAJ"""
    e: Answer = {'result': True, 'recommendation':''}
    return e
    # query = """
    # MATCH (s:Source {id: $node_id})-[:HAS_IDENTIFIER]->(id:Identifier)
    # WHERE id.idtype = 'doaj' AND id.value IS NOT NULL
    # RETURN COUNT(id) > 0 as in_doaj
    # """
    # result = await neo4j_session.run(query, node_id=node_data.get('id'))
    # record = await result.single()
    # return record['in_doaj'] if record else False

@rules_registry.register_question_rule('c_001_q_002')
async def c_001_q_002(node_data: dict, neo4j_session: AsyncSession) -> Answer:
    """Está en Scopus y/o JCR de la Web de la Ciencia"""
    e: Answer = {'result': True, 'recommendation':''}
    return e
    # query = """
    # MATCH (s:Source {id: $node_id})-[:HAS_IDENTIFIER]->(id:Identifier)
    # WHERE id.idtype IN ['scopus', 'wos'] AND id.value IS NOT NULL
    # RETURN COUNT(id) > 0 as in_index
    # """
    # result = await neo4j_session.run(query, node_id=node_data.get('id'))
    # record = await result.single()
    # return record['in_index'] if record else False

@rules_registry.register_question_rule('c_001_q_003')
async def c_001_q_003(node_data: dict, neo4j_session: AsyncSession) -> Answer:
    """Está incluida en base de datos de indización y resumen especializada"""
    e: Answer = {'result': 3, 'recommendation':'necesitas mas...'}
    return e

@rules_registry.register_question_rule('c_001_q_004')
async def c_001_q_004(node_data: dict, neo4j_session: AsyncSession) -> Answer:
    """Está incluida en base de datos de indización y resumen multidisciplinar"""
    return None

@rules_registry.register_question_rule('c_002_q_001')
async def c_002_q_001(node_data: dict, neo4j_session: AsyncSession) -> Answer:
    """Existe un sitio web propio de la revista"""
    return None

@rules_registry.register_question_rule('c_002_q_004')
async def c_002_q_004(node_data: dict, neo4j_session: AsyncSession) -> Answer:
    """Existen artículos de la revista en repositorios nacional y/o institucional de acceso abierto"""
    return None

@rules_registry.register_question_rule('c_002_q_005')
async def c_002_q_005(node_data: dict, neo4j_session: AsyncSession) -> Answer:
    """Existen artículos de la revista en repositorios de acceso abierto internacionales generales y/o temáticos"""
    return None

@rules_registry.register_question_rule('c_003_q_001')
async def c_003_q_001(node_data: dict, neo4j_session: AsyncSession) -> Answer:
    """Emplea algún formato de metadatos"""
    return None

@rules_registry.register_question_rule('c_003_q_003')
async def c_003_q_003(node_data: dict, neo4j_session: AsyncSession) -> Answer:
    """Metadatos obligatorios OpenAIRE presentes"""
    return None

@rules_registry.register_question_rule('c_003_q_004')
async def c_003_q_004(node_data: dict, neo4j_session: AsyncSession) -> Answer:
    """Metadatos recomendables OpenAIRE presentes"""
    return None

@rules_registry.register_question_rule('c_003_q_005')
async def c_003_q_005(node_data: dict, neo4j_session: AsyncSession) -> Answer:
    """Incluye ISSN y/o ISSN-E"""
    return None

@rules_registry.register_question_rule('c_003_q_006')
async def c_003_q_006(node_data: dict, neo4j_session: AsyncSession) -> Answer:
    """Incluye identificadores persistentes de objetos digitales"""
    return None

@rules_registry.register_question_rule('c_003_q_007')
async def c_003_q_007(node_data: dict, neo4j_session: AsyncSession) -> Answer:
    """Incluye identificadores persistentes para personas"""
    return None

@rules_registry.register_question_rule('c_003_q_008')
async def c_003_q_008(node_data: dict, neo4j_session: AsyncSession) -> Answer:
    """Incluye identificadores persistentes para organizaciones"""
    return None

@rules_registry.register_question_rule('c_004_q_002')
async def c_004_q_002(node_data: dict, neo4j_session: AsyncSession) -> Answer:
    """Declara que no tiene costo por procesamiento de artículos (APC)"""
    return None

@rules_registry.register_question_rule('c_004_q_003')
async def c_004_q_003(node_data: dict, neo4j_session: AsyncSession) -> Answer:
    """Es una revista de acceso abierto y declara política de acceso abierto"""
    return None

@rules_registry.register_question_rule('c_004_q_004')
async def c_004_q_004(node_data: dict, neo4j_session: AsyncSession) -> Answer:
    """Promueve depósito de datos de investigación"""
    return None

@rules_registry.register_question_rule('c_004_q_005')
async def c_004_q_005(node_data: dict, neo4j_session: AsyncSession) -> Answer:
    """Ofrece contenidos bajo licencia Creative Commons"""
    return None

@rules_registry.register_question_rule('c_005_q_001')
async def c_005_q_001(node_data: dict, neo4j_session: AsyncSession) -> Answer:
    return None

@rules_registry.register_question_rule('c_006_q_001')
async def c_006_q_001(node_data: dict, neo4j_session: AsyncSession) -> Answer:
    return None

@rules_registry.register_question_rule('c_007_q_001')
async def c_007_q_001(node_data: dict, neo4j_session: AsyncSession) -> Answer:
    """Tiene citas registradas"""
    return None

# Placeholder rules for questions that need user input
@rules_registry.register_question_rule('c_002_q_002')
async def c_002_q_002(node_data: dict, neo4j_session: AsyncSession) -> Answer:
    """Están disponibles los últimos números en el sitio web de la revista"""
    return None

@rules_registry.register_question_rule('c_002_q_003')
async def c_002_q_003(node_data: dict, neo4j_session: AsyncSession) -> Answer:
    """Están disponibles los artículos de manera individual en el sitio web de la revista"""
    return None

@rules_registry.register_question_rule('c_003_q_002')
async def c_003_q_002(node_data: dict, neo4j_session: AsyncSession) -> Answer:
    """Uso de OAI-PMH"""
    return None

@rules_registry.register_question_rule('c_004_q_001')
async def c_004_q_001(node_data: dict, neo4j_session: AsyncSession) -> Answer:
    """Permite depósito en plataformas no comerciales o comerciales"""
    return None

@rules_registry.register_question_rule('c_005_q_002')
async def c_005_q_002(node_data: dict, neo4j_session: AsyncSession) -> Answer:
    """Porcentaje de artículos en Inglés supera el 15%"""
    return None

@rules_registry.register_question_rule('c_005_q_003')
async def c_005_q_003(node_data: dict, neo4j_session: AsyncSession) -> Answer:
    """Miembros del comité editorial de instituciones extranjeras"""
    return None

@rules_registry.register_question_rule('c_005_q_004')
async def c_005_q_004(node_data: dict, neo4j_session: AsyncSession) -> Answer:
    """Miembros externos a la institución editora"""
    return None

@rules_registry.register_question_rule('c_005_q_005')
async def c_005_q_005(node_data: dict, neo4j_session: AsyncSession) -> Answer:
    """Artículos firmados por miembros del consejo editorial"""
    return None

@rules_registry.register_question_rule('c_005_q_006')
async def c_005_q_006(node_data: dict, neo4j_session: AsyncSession) -> Answer:
    """Firma de autores afiliados a instituciones extranjeras"""
    return None

@rules_registry.register_question_rule('c_006_q_002')
async def c_006_q_002(node_data: dict, neo4j_session: AsyncSession) -> Answer:
    """Posee perfiles en redes sociales"""
    return None

@rules_registry.register_question_rule('c_006_q_003')
async def c_006_q_003(node_data: dict, neo4j_session: AsyncSession) -> Answer:
    """Difunde artículos a través de redes sociales"""
    return None

@rules_registry.register_question_rule('c_007_q_002')
async def c_007_q_002(node_data: dict, neo4j_session: AsyncSession) -> Answer:
    """Citas recibidas"""
    return None

@rules_registry.register_question_rule('c_007_q_003')
async def c_007_q_003(node_data: dict, neo4j_session: AsyncSession) -> Answer:
    """Índice H5 de la revista"""
    return None

@rules_registry.register_question_rule('c_008_q_001')
async def c_008_q_001(node_data: dict, neo4j_session: AsyncSession) -> Answer:
    """Está en rankings de revistas"""
    return None

# =============================================================================
# CATEGORY RULES for m_001
# =============================================================================

@rules_registry.register_category_rule('m_001_01_01', ['c_001_q_001', 'c_001_q_002', 'c_001_q_003', 'c_001_q_004'])
async def m_001_01_01(category_data: Dict, answers: Dict) -> Answer:
    """Calculate results and recommendations for Indización category"""
    return None    
    # score = 0
    # max_score = 4
    # recommendations = []
    
    # if answers.get('c_001_q_001'):
    #     score += 1
    # else:
    #     recommendations.append("Considerar inclusión en DOAJ")
    
    # if answers.get('c_001_q_002'):
    #     score += 1
    # else:
    #     recommendations.append("Buscar inclusión en Scopus o Web of Science")
    
    # specialized_count = answers.get('c_001_q_003', 0)
    # if specialized_count > 0:
    #     score += min(1, specialized_count / 2)
    # else:
    #     recommendations.append("Incrementar presencia en bases de datos especializadas")
    
    # multidisciplinary_count = answers.get('c_001_q_004', 0)
    # if multidisciplinary_count > 0:
    #     score += min(1, multidisciplinary_count / 2)
    # else:
    #     recommendations.append("Incrementar presencia en bases de datos multidisciplinarias")
    
    # final_score = score / max_score
    
    # return {
    #     'result': final_score,
    #     'recommendation': ' | '.join(recommendations) if recommendations else "Buena cobertura de indización"
    # }

@rules_registry.register_category_rule('m_001_01_02', ['c_002_q_001', 'c_002_q_002', 'c_002_q_003', 'c_002_q_004', 'c_002_q_005'])
async def m_001_01_02(category_data: Dict, answers: Dict) -> Answer:
    """Calculate results and recommendations for Acceso category"""
    return None

@rules_registry.register_category_rule('m_001_01_03', [
    'c_003_q_001', 'c_003_q_002', 'c_003_q_003', 'c_003_q_004', 
    'c_003_q_005', 'c_003_q_006', 'c_003_q_007', 'c_003_q_008'
])
async def m_001_01_03(category_data: Dict, answers: Dict) -> Answer:
    """Calculate results and recommendations for Interoperabilidad category"""
    return None

@rules_registry.register_category_rule('m_001_01_04', ['c_004_q_001', 'c_004_q_002', 'c_004_q_003', 'c_004_q_004', 'c_004_q_005'])
async def m_001_01_04(category_data: Dict, answers: Dict) -> Answer:
    """Calculate results and recommendations for Apertura category"""
    return None

@rules_registry.register_category_rule('m_001_01_05', ['c_005_q_001', 'c_005_q_002', 'c_005_q_003', 'c_005_q_004', 'c_005_q_005', 'c_005_q_006'])
async def m_001_01_05(category_data: Dict, answers: Dict) -> Answer:
    """Calculate results and recommendations for Internacionalización category"""
    return None

@rules_registry.register_category_rule('m_001_01_06', ['c_006_q_001', 'c_006_q_002', 'c_006_q_003'])
async def m_001_01_06(category_data: Dict, answers: Dict) -> Answer:
    """Calculate results and recommendations for Redes sociales category"""
    return None

@rules_registry.register_category_rule('m_001_02_01', ['c_007_q_001', 'c_007_q_002', 'c_007_q_003'])
async def m_001_02_01(category_data: Dict, answers: Dict) -> Answer:
    """Calculate results and recommendations for Impacto académico category"""
    return None

@rules_registry.register_category_rule('m_001_02_02', ['c_008_q_001'])
async def m_001_02_02(category_data: Dict, answers: Dict) -> Answer:
    """Calculate results and recommendations for Posición en rankings category"""
    return None

# =============================================================================
# SECTION RULES for m_001
# =============================================================================

@rules_registry.register_section_rule('m_001_01', ['m_001_01_01', 'm_001_01_02', 'm_001_01_03', 'm_001_01_04', 'm_001_01_05', 'm_001_01_06'])
async def m_001_01(section_data: Dict, category_results: Dict) -> Answer:
    """Calculate overall Visibilidad section results"""
    return None
    # visibility_categories = ['m_001_01_01', 'm_001_01_02', 'm_001_01_03', 'm_001_01_04', 'm_001_01_05', 'm_001_01_06']
    
    # total_score = 0
    # valid_categories = 0
    # recommendations = []
    
    # for category_id in visibility_categories:
    #     category_result = category_results.get(category_id, {})
    #     if category_result and 'result' in category_result and category_result['result'] is not None:
    #         total_score += category_result['result']
    #         valid_categories += 1
    #         if category_result.get('recommendation'):
    #             recommendations.append(category_result['recommendation'])
    
    # final_score = total_score / valid_categories if valid_categories > 0 else 0
    
    # # Overall recommendation based on score
    # if final_score >= 0.8:
    #     overall_rec = "Excelente visibilidad"
    # elif final_score >= 0.6:
    #     overall_rec = "Buena visibilidad"
    # else:
    #     overall_rec = "Visibilidad necesita mejora"
    
    # if recommendations:
    #     overall_rec += f". Recomendaciones: {'; '.join(recommendations)}"
    
    # return {
    #     'result': final_score,
    #     'recommendation': overall_rec
    # }

@rules_registry.register_section_rule('m_001_02', ['m_001_02_01', 'm_001_02_02'])
async def m_001_02(section_data: Dict, category_results: Dict) -> Answer:
    """Calculate overall Impacto section results"""
    return None
    # impact_categories = ['m_001_02_01', 'm_001_02_02']
    
    # total_score = 0
    # valid_categories = 0
    # recommendations = []
    
    # for category_id in impact_categories:
    #     category_result = category_results.get(category_id, {})
    #     if category_result and 'result' in category_result and category_result['result'] is not None:
    #         total_score += category_result['result']
    #         valid_categories += 1
    #         if category_result.get('recommendation'):
    #             recommendations.append(category_result['recommendation'])
    
    # final_score = total_score / valid_categories if valid_categories > 0 else 0
    
    # # Overall recommendation based on score
    # if final_score >= 0.8:
    #     overall_rec = "Excelente impacto"
    # elif final_score >= 0.6:
    #     overall_rec = "Buen impacto"
    # else:
    #     overall_rec = "Impacto necesita mejora"
    
    # if recommendations:
    #     overall_rec += f". Recomendaciones: {'; '.join(recommendations)}"
    
    # return {
    #     'result': final_score,
    #     'recommendation': overall_rec
    # }

# =============================================================================
# METHODOLOGY RULES for m_001
# =============================================================================

@rules_registry.register_methodology_rule('m_001', ['m_001_01', 'm_001_02'])
async def m_001(evaluation_result: Dict, section_results: Dict) -> Answer:
    """Calculate final methodology results and overall recommendations"""
    return None
    # visibility_score = section_results.get('m_001_01', {}).get('result', 0)
    # impact_score = section_results.get('m_001_02', {}).get('result', 0)
    
    # # Weighted final score (60% visibility, 40% impact)
    # final_score = (visibility_score * 0.6) + (impact_score * 0.4)
    
    # recommendations = []
    
    # visibility_rec = section_results.get('m_001_01', {}).get('recommendation')
    # impact_rec = section_results.get('m_001_02', {}).get('recommendation')
    
    # if visibility_rec:
    #     recommendations.append(f"Visibilidad: {visibility_rec}")
    # if impact_rec:
    #     recommendations.append(f"Impacto: {impact_rec}")
    
    # # Overall assessment
    # if final_score >= 0.8:
    #     overall_assessment = "Revista de excelente calidad"
    # elif final_score >= 0.6:
    #     overall_assessment = "Revista de buena calidad"
    # elif final_score >= 0.4:
    #     overall_assessment = "Revista que necesita mejoras"
    # else:
    #     overall_assessment = "Revista que requiere mejoras significativas"
    
    # return {
    #     'final_score': final_score,
    #     'overall_assessment': overall_assessment,
    #     'recommendations': recommendations
    # }