# iroko/evals/rules/m_001.py
"""
Rules for methodology m_001 (sceiba-journal evaluation)
"""
from typing import Dict, Any, Union
from neo4j import AsyncSession
from numpy import number

from iroko.evals.context import EvaluationContext
from iroko.evals.schemas import Answer
from ..rules_registry import rules_registry

import logging

logger = logging.getLogger('iroko-cris')

# =============================================================================
# QUESTION RULES for m_001
# =============================================================================

@rules_registry.register_question_rule('c_001_q_001')
async def c_001_q_001(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
    """Está incluida en DOAJ"""
    e: Answer = {'result': True, 'recommendation':None}
    return None
    # query = """
    # MATCH (s:Source {id: $node_id})-[:HAS_IDENTIFIER]->(id:Identifier)
    # WHERE id.idtype = 'doaj' AND id.value IS NOT NULL
    # RETURN COUNT(id) > 0 as in_doaj
    # """
    # result = await neo4j_session.run(query, node_id=node_data.get('id'))
    # record = await result.single()
    # return record['in_doaj'] if record else False

@rules_registry.register_question_rule('c_001_q_002')
async def c_001_q_002(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
    """Está en Scopus y/o JCR de la Web de la Ciencia"""
    e: Answer = {'result': True, 'recommendation':''}
    return None
    # query = """
    # MATCH (s:Source {id: $node_id})-[:HAS_IDENTIFIER]->(id:Identifier)
    # WHERE id.idtype IN ['scopus', 'wos'] AND id.value IS NOT NULL
    # RETURN COUNT(id) > 0 as in_index
    # """
    # result = await neo4j_session.run(query, node_id=node_data.get('id'))
    # record = await result.single()
    # return record['in_index'] if record else False

@rules_registry.register_question_rule('c_001_q_003')
async def c_001_q_003(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
    """Está incluida en base de datos de indización y resumen especializada"""
    e: Answer = {'result': 3, 'recommendation':'necesitas mas...'}
    return None

@rules_registry.register_question_rule('c_001_q_004')
async def c_001_q_004(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
    """Está incluida en base de datos de indización y resumen multidisciplinar"""
    return None

@rules_registry.register_question_rule('c_002_q_001')
async def c_002_q_001(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
    """Existe un sitio web propio de la revista"""
    return None

@rules_registry.register_question_rule('c_002_q_004')
async def c_002_q_004(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
    """Existen artículos de la revista en repositorios nacional y/o institucional de acceso abierto"""
    return None

@rules_registry.register_question_rule('c_002_q_005')
async def c_002_q_005(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
    """Existen artículos de la revista en repositorios de acceso abierto internacionales generales y/o temáticos"""
    return None

@rules_registry.register_question_rule('c_003_q_001')
async def c_003_q_001(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
    """Emplea algún formato de metadatos"""
    return None

@rules_registry.register_question_rule('c_003_q_003')
async def c_003_q_003(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
    """Metadatos obligatorios OpenAIRE presentes"""
    return None

@rules_registry.register_question_rule('c_003_q_004')
async def c_003_q_004(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
    """Metadatos recomendables OpenAIRE presentes"""
    return None

@rules_registry.register_question_rule('c_003_q_005')
async def c_003_q_005(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
    """Incluye ISSN y/o ISSN-E"""
    return None

@rules_registry.register_question_rule('c_003_q_006')
async def c_003_q_006(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
    """Incluye identificadores persistentes de objetos digitales"""
    return None

@rules_registry.register_question_rule('c_003_q_007')
async def c_003_q_007(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
    """Incluye identificadores persistentes para personas"""
    return None

@rules_registry.register_question_rule('c_003_q_008')
async def c_003_q_008(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
    """Incluye identificadores persistentes para organizaciones"""
    return None

@rules_registry.register_question_rule('c_004_q_002')
async def c_004_q_002(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
    """Declara que no tiene costo por procesamiento de artículos (APC)"""
    return None

@rules_registry.register_question_rule('c_004_q_003')
async def c_004_q_003(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
    """Es una revista de acceso abierto y declara política de acceso abierto"""
    return None

@rules_registry.register_question_rule('c_004_q_004')
async def c_004_q_004(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
    """Promueve depósito de datos de investigación"""
    return None

@rules_registry.register_question_rule('c_004_q_005')
async def c_004_q_005(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
    """Ofrece contenidos bajo licencia Creative Commons"""
    return None

@rules_registry.register_question_rule('c_005_q_001')
async def c_005_q_001(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
    return None

@rules_registry.register_question_rule('c_006_q_001')
async def c_006_q_001(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
    return None

@rules_registry.register_question_rule('c_007_q_001')
async def c_007_q_001(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
    """Tiene citas registradas"""
    return None

# Placeholder rules for questions that need user input
@rules_registry.register_question_rule('c_002_q_002')
async def c_002_q_002(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
    """Están disponibles los últimos números en el sitio web de la revista"""
    return None

@rules_registry.register_question_rule('c_002_q_003')
async def c_002_q_003(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
    """Están disponibles los artículos de manera individual en el sitio web de la revista"""
    return None

@rules_registry.register_question_rule('c_003_q_002')
async def c_003_q_002(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
    """Uso de OAI-PMH"""
    return None

@rules_registry.register_question_rule('c_004_q_001')
async def c_004_q_001(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
    """Permite depósito en plataformas no comerciales o comerciales"""
    return None

@rules_registry.register_question_rule('c_005_q_002')
async def c_005_q_002(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
    """Porcentaje de artículos en Inglés supera el 15%"""
    return None

@rules_registry.register_question_rule('c_005_q_003')
async def c_005_q_003(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
    """Miembros del comité editorial de instituciones extranjeras"""
    return None

@rules_registry.register_question_rule('c_005_q_004')
async def c_005_q_004(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
    """Miembros externos a la institución editora"""
    return None

@rules_registry.register_question_rule('c_005_q_005')
async def c_005_q_005(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
    """Artículos firmados por miembros del consejo editorial"""
    return None

@rules_registry.register_question_rule('c_005_q_006')
async def c_005_q_006(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
    """Firma de autores afiliados a instituciones extranjeras"""
    return None

@rules_registry.register_question_rule('c_006_q_002')
async def c_006_q_002(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
    """Posee perfiles en redes sociales"""
    return None

@rules_registry.register_question_rule('c_006_q_003')
async def c_006_q_003(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
    """Difunde artículos a través de redes sociales"""
    return None

@rules_registry.register_question_rule('c_007_q_002')
async def c_007_q_002(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
    """Citas recibidas"""
    return None

@rules_registry.register_question_rule('c_007_q_003')
async def c_007_q_003(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
    """Índice H5 de la revista"""
    return None

@rules_registry.register_question_rule('c_008_q_001')
async def c_008_q_001(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
    """Está en rankings de revistas"""
    return None

# =============================================================================
# CATEGORY RULES for m_001
# =============================================================================

@rules_registry.register_category_rule('m_001_indizacion', [
    'c_001_q_001', 'c_004_q_003', 'c_007_q_001', 'c_007_q_002', 'c_007_q_003', 'c_001_q_002', 'c_001_q_003', 'c_001_q_004'
])
async def m_001_indizacion(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
    """Calculate results and recommendations for Indización category"""

    recoms = []
    c_001_q_001 = context.get_answer('c_001_q_001').result
    c_004_q_003 = context.get_answer('c_004_q_003').result
    c_007_q_001 = context.get_answer('c_007_q_001').result
    c_007_q_002 = context.get_answer('c_007_q_002').result
    c_007_q_003 = context.get_answer('c_007_q_003').result
    c_001_q_002 = context.get_answer('c_001_q_002').result
    c_001_q_003 = context.get_answer('c_001_q_003').result
    c_001_q_004 = context.get_answer('c_001_q_004').result

    if (c_001_q_001 == False and c_004_q_003 ==True):
        recoms.append('Postular revista a DOAJ')

    if (c_007_q_001 == True and
        (c_007_q_002 == 'MAS_DEL_50_ART_ULT_3_AÑOS_REC_ALGUNA_CITA') and
        (c_007_q_003 == 'MAYOR_IND_H5_REV_PER_ANT') and
        (c_001_q_002 == False)):

        recoms.append('Considerar la posibilidad de postular la revista a SCOPUS/Web de la Ciencia')

    if (float(c_001_q_003) <= 1):
        recoms.append('Postular revista a otras bases de datos de indización y resumen especializadas')

    if (float(c_001_q_004) <= 1):
        recoms.append('Postular revista a otras bases de datos de indización y resumen multidisciplinares')

    var1 = (c_004_q_003 == c_001_q_001)

    var2 = ((var1) and
            c_001_q_002 == True and
            (int(c_001_q_003) + int(c_001_q_004) >= 1))

    var3 = (c_001_q_001 == False  and
            (c_001_q_002 == False) and
            (int(c_001_q_003) + int(c_001_q_004) == 0))

    var4 = (not var2) and (not var3)

    result = 'ERROR'
    if var2:
        result = "ALTO"

    if var4:
        result = "MEDIO"

    if var3:
        result = "BAJO"
    a = Answer(result=result, recommendation=recoms)
    logger.debug(a)
    return a


@rules_registry.register_category_rule('m_001_acceso', [
    'c_002_q_001', 'c_002_q_002', 'c_002_q_003', 'c_002_q_004', 'c_002_q_005'
])
async def m_001_acceso(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
    recoms = []

    c_002_q_001 = context.get_answer('c_002_q_001').result
    c_002_q_002 = context.get_answer('c_002_q_002').result
    c_002_q_003 = context.get_answer('c_002_q_003').result
    c_002_q_004 = context.get_answer('c_002_q_004').result
    c_002_q_005 = context.get_answer('c_002_q_005').result

    if c_002_q_001 == False:
        recoms.append('Crear el sitio web propio de la revista y solicitar el E-ISSN')

    if (c_002_q_002 == 'NO_DISPONIBLE_ULTIMO_NUM') or (c_002_q_002 == 'SOLAMENTE_DISPONIBLE_ULTIMO_NUM'):
        recoms.append('Actualizar el sitio web propio de la revista con todos los números publicados en los últimos dos años')

    if c_002_q_002 == 'NO_APLICA':
        recoms.append('Si crea un sitio web para la revista asegúrese de actualizarlo con todos los números publicados en los últimos dos años')

    if c_002_q_003 != 'SI_DISPONIBLE_IND_SI_DESC_NUM':
        recoms.append('Evaluar cómo alinear las buenas prácticas de acceso abierto con las políticas editoriales')

    var1 = (c_002_q_004 == True) or (c_002_q_005 == True)
    if var1:
        recoms.append('Promover el depósito de los artículos en repositorios internacionales, nacional, institucional, multidisciplinarios y temáticos')

    var2 = (
        (c_002_q_001 == True) and
        (c_002_q_002 == 'TODOS_NUM_PUBLICADOS_ULTIMOS_DOS_AÑOS') and
        (c_002_q_003 == 'SI_DISPONIBLE_IND_SI_DESC_NUM') and
        (c_002_q_005 == True)
    )

    var3 = (
        (c_002_q_001 == False) or
        (c_002_q_003 == 'SI_DISPONIBLE_IND_NO_DESC_NUM') or
        (c_002_q_003 == 'NO_DISPONIBLE_IND_NO_DESC_NUM') or
        (c_002_q_002 == 'NO_DISPONIBLE_ULTIMO_NUM') or
        (c_002_q_002 == 'NO_APLICA') or
        (c_002_q_004 == False and c_002_q_005 == False)
    )

    var4 = (not var2) and (not var3)

    if var2:
        result = "ALTO"
    elif var4:
        result = "MEDIO"
    elif var3:
        result = "BAJO"
    else:
        result = "ERROR"

    return Answer(result=result, recommendation=recoms)

@rules_registry.register_category_rule('m_001_interoperabilidad', [
    'c_003_q_001', 'c_003_q_002', 'c_003_q_003', 'c_003_q_004',
    'c_003_q_005', 'c_003_q_006', 'c_003_q_008'
])
async def m_001_interoperabilidad(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
    """Calculate results and recommendations for Interoperabilidad category"""
    recoms = []

    c_003_q_001 = context.get_answer('c_003_q_001').result
    c_003_q_002 = context.get_answer('c_003_q_002').result
    c_003_q_003 = context.get_answer('c_003_q_003').result
    c_003_q_004 = context.get_answer('c_003_q_004').result
    c_003_q_005 = context.get_answer('c_003_q_005').result
    c_003_q_006 = context.get_answer('c_003_q_006').result
    c_003_q_008 = context.get_answer('c_003_q_008').result

    if c_003_q_001 == False:
        recoms.append('Emplear algún formato de metadatos (ej. Uso de OAI-DC , DC, Cerif, Mods, METS, etc.) para la descripción de sus publicaciones')

    if c_003_q_002 == False:
        recoms.append('Implementar el protocolo OAI-PMH que permita la recopilación de metadatos por otros sistemas')

    if c_003_q_003 == False:
        recoms.append('Completar en todos los artículos los metadatos definidos como obligatorios en el OpenAIRE Guidelines for Literature Repositories v3')

    if c_003_q_004 == False:
        recoms.append('Revisar que en todos los artículos estén los metadatos Field Language(Idioma), Field License Condition, Field Source, definidos como recomendables en el OpenAIRE Guidelines for Literature Repositories v3')

    if c_003_q_005 == False:
        recoms.append('Incluir entre sus metadatos Identificadores Persistentes de la publicación o relacionados a ella ( ej. ISSN-EISSN, DOI-Handle-URI-URN-Scopus ID-Wos ID-Scielo ID) en los campos Resource Identifier o Alternative Identifier según corresponda')

    if c_003_q_006 == False:
        recoms.append('Incluir como parte de su práctica editorial la solicitud del ORCID asociado al nombre de los autores y registrarlo como parte de sus metadatos')

    if c_003_q_008 == False:
        recoms.append('Explorar la posibilidad de incluir entre sus metadatos Identificador(es) Persistente(s) para organizaciones (ej.: GRID, ROR)')

    var1 = (
        c_003_q_001 == True and
        c_003_q_002 == True and
        c_003_q_003 == True and
        c_003_q_005 == True
    )

    var2 = var1 and (c_003_q_006 == True)
    var3 = var1 and (c_003_q_006 == False)
    var4 = (
        c_003_q_001 == False or
        c_003_q_002 == False or
        c_003_q_003 == False or
        c_003_q_005 == False
    )

    if var2:
        result = "ALTO"
    elif var3:
        result = "MEDIO"
    elif var4:
        result = "BAJO"
    else:
        result = "ERROR"

    return Answer(result=result, recommendation=recoms)

@rules_registry.register_category_rule('m_001_apertura', [
        'c_004_q_001', 'c_004_q_002', 'c_004_q_003', 'c_004_q_004',
    'c_004_q_005', 'c_002_q_003'
])
async def m_001_apertura(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
    recoms = []

    c_004_q_001 = context.get_answer('c_004_q_001').result
    c_004_q_002 = context.get_answer('c_004_q_002').result
    c_004_q_003 = context.get_answer('c_004_q_003').result
    c_004_q_004 = context.get_answer('c_004_q_004').result
    c_004_q_005 = context.get_answer('c_004_q_005').result
    c_002_q_003 = context.get_answer('c_002_q_003').result

    if c_004_q_001 == 'NO_PERMITE_AUTOARCHIVADO_VER':
        recoms.append('Evaluar cómo alinear las buenas prácticas de acceso abierto con las políticas editoriales')

    if c_004_q_002 == False:
        recoms.append('En caso de no cobrar costo por procesamiento de artículos (APC), declararlo explícitamente en las políticas editoriales')

    if c_004_q_003 == False:
        recoms.append('Declarar explícitamente cuál es la política de acceso abierto de la revista')

    if c_004_q_004 == False:
        recoms.append('Promover el depósito de los datos de investigación en repositorios de acceso abierto como parte de su política editorial')

    if c_004_q_005 == False:
        recoms.append('Ofrecer sus contenidos bajo algún tipo de licencia Creative Common')

    var1 = (
        c_004_q_001 != 'NO_PERMITE_AUTOARCHIVADO_VER' and
        c_004_q_002 == True and
        c_004_q_003 == True and
        c_004_q_005 == True and
        c_002_q_003 == 'SI_DISPONIBLE_IND_SI_DESC_NUM'
    )

    var2 = (
        c_004_q_001 == 'NO_PERMITE_AUTOARCHIVADO_VER' or
        c_004_q_002 == False or
        c_004_q_003 == False or
        c_004_q_005 == False
    )

    var3 = (not var1) and (not var2)

    if var1:
        result = "ALTO"
    elif var3:
        result = "MEDIO"
    elif var2:
        result = "BAJO"
    else:
        result = "ERROR"

    return Answer(result=result, recommendation=recoms)

@rules_registry.register_category_rule('m_001_internacionalizacion', [
    'c_005_q_001', 'c_005_q_002', 'c_005_q_003', 'c_005_q_004',
    'c_005_q_005', 'c_005_q_006'
])
async def m_001_internacionalizacion(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
    """Calculate results and recommendations for Internacionalización category"""
    recoms = []

    c_005_q_001 = context.get_answer('c_005_q_001').result
    c_005_q_002 = context.get_answer('c_005_q_002').result
    c_005_q_003 = context.get_answer('c_005_q_003').result
    c_005_q_004 = context.get_answer('c_005_q_004').result
    c_005_q_005 = context.get_answer('c_005_q_005').result
    c_005_q_006 = context.get_answer('c_005_q_006').result

    if (c_005_q_004 != 'MAS_DEL_70') or (c_005_q_003 != 'MAS_DEL_50'):
        recoms.append('Aumentar la representación de expertos y especialistas externos a la institución editora, considerando mayor presencia de afiliados a instituciones extranjeras')

    if c_005_q_005 != 'MENOS_DEL_20_TOTAL_PUBLICADO_PERIODO':
        recoms.append('Desarrollar mecanismos rigurosos que garanticen la conducta ética, la integridad académica, la resolución de conflictos de intereses y la transparencia en el proceso editorial según las buenas prácticas internacionales de publicación (ej. COPE guidelines, ICMJE Recommendations)')

    if c_005_q_006 == 'MAS_DEL_25_TOTAL_ART_ULT_DOS_AÑOS':
        recoms.append('Evaluar posibilidades para potenciar la revista como una vía para fortalecer la colaboración interinstitucional a nivel nacional e internacional')

    var1 = (
        c_005_q_001 == 'EN_MAS_DE_UN_IDIOMA' and
        c_005_q_002 == True and
        c_005_q_003 == 'MAS_DEL_50' and
        c_005_q_004 == 'MAS_DEL_70' and
        c_005_q_005 == 'MENOS_DEL_20_TOTAL_PUBLICADO_PERIODO' and
        c_005_q_006 == 'MAS_DEL_25_TOTAL_ART_ULT_DOS_AÑOS'
    )

    var2 = (
        c_005_q_001 != 'EN_MAS_DE_UN_IDIOMA' or
        c_005_q_003 == 'MENOS_DEL_20' or
        c_005_q_004 == 'MENOS_DEL_20' or
        c_005_q_005 == 'MAS_DEL_50_TOTAL_PUBLICADO_PERIODO' or
        c_005_q_006 == 'MENOS_DEL_5_TOTAL_ART_ULT_DOS_AÑOS'
    )

    var3 = (not var1) and (not var2)

    if var1:
        result = "ALTO"
    elif var3:
        result = "MEDIO"
    elif var2:
        result = "BAJO"
    else:
        result = "ERROR"

    return Answer(result=result, recommendation=recoms)

@rules_registry.register_category_rule('m_001_redes_sociales', [
    'c_006_q_001', 'c_006_q_002', 'c_006_q_003', 'c_007_q_001'
])
async def m_001_redes_sociales(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
    """Calculate results and recommendations for Redes sociales category"""
    recoms = []

    c_006_q_001 = context.get_answer('c_006_q_001').result
    c_006_q_002 = context.get_answer('c_006_q_002').result
    c_006_q_003 = context.get_answer('c_006_q_003').result
    c_007_q_001 = context.get_answer('c_007_q_001').result

    if c_006_q_001 == False:
        recoms.append('Implementar funcionalidad de compartir contenidos en redes sociales')

    if c_006_q_002 == 'PERFIL_RED_SOC_SI_MENDELEY_RESEARCHGATE':
        recoms.append('Crear y mantener activos perfiles tanto en redes sociales generales como en Mendeley y Researchgate para aumentar la difusión de sus publicaciones')

    var1 = (
        c_007_q_001 == True and
        c_006_q_002 == 'PERFIL_RED_SOC_SI_MENDELEY_RESEARCHGATE' and
        c_006_q_003 == 'TWITTER_FACEBOOK_INSTAGRAM_MENDELEY_RESEARCHGATE'
    )

    var2 = (
        c_007_q_001 == False or
        c_006_q_002 == 'NO' or
        c_006_q_003 == 'NO'
    )

    var3 = (not var1) and (not var2)

    if var1:
        result = "ALTO"
    elif var3:
        result = "MEDIO"
    elif var2:
        result = "BAJO"
    else:
        result = "ERROR"

    return Answer(result=result, recommendation=recoms)

@rules_registry.register_category_rule('m_001_impacto_academico', [
    'c_007_q_001', 'c_007_q_002', 'c_007_q_003', 'c_008_q_001', 'c_001_q_002'
])
async def m_001_impacto_academico(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
    """Calculate results and recommendations for Impacto académico category"""
    c_007_q_001 = context.get_answer('c_007_q_001').result
    c_007_q_002 = context.get_answer('c_007_q_002').result
    c_007_q_003 = context.get_answer('c_007_q_003').result
    c_008_q_001 = context.get_answer('c_008_q_001').result
    c_001_q_002 = context.get_answer('c_001_q_002').result

    var1 = (
        c_007_q_001 == True and
        c_007_q_002 == 'MAS_DEL_50_ART_ULT_3_AÑOS_REC_ALGUNA_CITA' and
        c_007_q_003 == 'MAYOR_IND_H5_REV_PER_ANT' and
        c_008_q_001 == 'Q1_Q2_JOURNAL_CITATION' and
        c_001_q_002 == True
    )

    var2 = (
        c_007_q_003 == 'NO_APLICA' or
        c_007_q_002 == 'MENOS_DEL_20_ART_ULT_3_AÑOS_REC_ALGUNA_CITA' or
        c_007_q_001 == False
    )

    var3 = (not var1) and (not var2)

    common_recom = [
            "a) Orientar a los profesores que forman parte del consejo/comité editorial para el direccionamiento estratégico de la calidad de la revista, ", 
            
            "b) ofrecer pautas a los autores que les permitan mejorar el rigor y originalidad de los trabajos que envían a la revista indicándolas explícitamente en las instrucciones a los autores y la política editorial así como en Editoriales, Cartas al editor o "
            "otros tipos de artículos publicados en la misma revista, ",

            "c) mejorar la calidad de las revisiones a través de la mejora de los formularios de revisión, la elección de los revisores más adecuados para cada manuscrito, compartir las buenas prácticas de revisión, desarrollar competencias en los revisores novatos que les permitan reconocer las contribuciones potenciales de los manuscritos y cómo facilitar el desarrollo de ese potencial para elevar la calidad de los manuscritos aceptados y publicados"
       ]

    if var1:
        return Answer(result="ALTO", recommendation=[])
    elif var3:
        return Answer(result="MEDIO", recommendation=common_recom)
    elif var2:
        return Answer(result="BAJO", recommendation=common_recom)
    else:
        return Answer(result="ERROR", recommendation=[])

@rules_registry.register_category_rule('m_001_posicion_rankings', ['c_008_q_001'])
async def m_001_posicion_rankings(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
    """Calculate results and recommendations for Posición en rankings category"""
    c_008_q_001 = context.get_answer('c_008_q_001').result

    if c_008_q_001 == 'Q1_Q2_JOURNAL_CITATION':
        return Answer(result="ALTO", recommendation=[])
    elif c_008_q_001 != 'Q1_Q2_JOURNAL_CITATION' and c_008_q_001 != 'NO':
        return Answer(result="MEDIO", recommendation=[])
    elif c_008_q_001 == 'NO':
        return Answer(result="BAJO", recommendation=[])
    else:
        return Answer(result="ERROR", recommendation=[])

# =============================================================================
# SECTION RULES for m_001
# =============================================================================

@rules_registry.register_section_rule('m_001_01', ['m_001_01_01', 'm_001_01_02', 'm_001_01_03', 'm_001_01_04', 'm_001_01_05', 'm_001_01_06'])
async def m_001_01(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
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
async def m_001_02(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
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
async def m_001(context: EvaluationContext, neo4j_session: AsyncSession) -> Answer:
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