# Descripcion general del sistema. 

Es un CRIS que usa neo4j como base de datos principal. 


## Componentes de iroko-cris

- Base de datos neo4j para todos los metadatos
- Base de datos en typesense para para los textos completos
- Base de datos redis, auxiliar.(opcional, valorar si es necesario)
- iroko: modulos de python con las funcionalidades principales. 
- ui: app en Flet que implementa la interfaz de usuario


## Entidades

Los principales tipos de datos son:
- Sources
- Organizations
- Persons
- Projects
- Outputs
- Terms (Vocabularios y terminos, un mapeo de skos)

Estas entidades estan basadas en sceiba-ontology

El grafo puede tener otros tipos de nodos, es decir otros tipos de entidades, pero las principales son las que se toman como referencia, son las mas importantes. 

## iroko

- api: implementacion del api-rest
- crawler: recoleccion de datos, interfaz de consola
- evals: evaluacion de las entidades principales utilizando alguna metodologia establecda
- stats: implementacion de estadisticas basicas
- nlputils: usando metodos procesamiento de lenguaje (clasicos o mas actuales), debe permitir operaciones de clasificacion, descubrimiento de entidades, desambiguacion de nombres, entre otras. 
- agent: implementa un agente usando GraphRAG para responder preguntas en lenguaje natural, recibe como entrada un acceso a un LLM

### api

Usando FastAPI se deben habilitar los siguientes endpoints: 

 - /pid/<id>: acceso a las entidades usando identificadores persistentes
 - /sources: listas de fuentes
 - /organizations: lista de organizaciones
 - /persons: lista de personas
 - /projects: lista de proyectos
 - /outputs: lista de resultados de investigacion
 - /vocabs: lista de vocabularios
 - /terms/[voc-id]: lista de los terminos dado un id de vocabulario 

 - /graph: queries cypher de solo lectura a neo4j

 - /search: busquedas por typesense

 - /evals: evaluaciones

 - /stats: estadisticas

 - /nlputils: acceso a las funcionalidades de clasificacion y desambiguacion de nombres

 - /agent: acceso al agente graphRAG


### crawler

Debe implementar la recoleccion de datos a partir de las fuentes. 
Aqui deben ir otras recolecciones ad-hoc para otras entidades
- organizaciones de la ONEI, ROR
- personas de ORCID, sistemas de recursos humanos
- debe permirir importar datos desde csv, json, yaml.

- en iteraciones sucesivas el crawler va enriqueciendo el grafo

- maneja los textos completos que luego son incorporados en typesense

### evals

- Todas las entidades son suceptibles de ser evaluadas

- una evaluacion siempre es una funcion que recibe un nodo como entrada y realiza un conjunto de operaciones en los nodos adyacentes al grafo, por ejemplo: la evaluacion de una revista depende de sus propios metadatos, pero tambien puede depender calculos que toman en cuenta de los autores de la revista 
- las evaluaciones se especifican en un formato YAML, pero hay funciones que inevitablemente son funciones de python a las que hay que hacer referencia 
- una evaluacion es especifica para un tipo de entidad
- en el modulo deben estar implementadas una serie de operaciones de "alto nivel" que se pueden especificar en el formato YAML de la evaliuacion

### stats

- Este es un modulo que implementa una serie de estadisticas basicas generales "ad-hoc"
- Por cada una de las entidades es posible implementar estas estadisticas, en principio sumatorias, ejemplo: cantidad de autores que publica en una revista, etc.
- En principio, se recibe como entrada un id de un nodo y en dependencia del tipo de nodo, las estadisticas calculadas son distintas. 
- valorar la utilizacion de redis como cache de estadisticas...

- implementa ademas otras estadisticas especiales que se necesiten calcular, por ejemplo para la pagina de inicio. 


### nlputils

El objetivo de este modulo es la implementacion de funcionalidades basicas de procesamiento de lenguaje natural para resolver tareas basicas que pueden ser usadas por los otros modulos o brindadas como servicios, algunas son:
- clasificacion de textos, usando los vocabularios de iroko
- desambiguacion de nombres, para sugerir nuevas relaciones en el grafo, por ejemplo, saber si un nombre que se encuentra en un texto o se recibe como metadato se corresponde con el nombre de una instancia de la entidad persona. 


### agent 

- Este modulo implementa un agente graphRAG para responder preguntas en lenguaje natural 
- Utiliza el grafo y typesense como entradas,
- Recibe como entrada el acceso al api de un modelo, en principo iroko no tiene un llm incorporado


## ui

App en Flet que implementa la interfaz de usuario. 
Hace uso del API. 

Principales comoponentes: 

- inicio: muestra resumen de las estadisticas generales

- listas: se utiliza para mostrar las listas de las entidades principales. Cada lista es posible filtrarla por los metadatos del nodo. 

- node-viewer: muestra un nodo, con sus metadatos correspondientes y ademas las estadisticas de ese nodo. Por cada tipo de relacion que tiene un nodo existe un tab donde se muesta la lista de nodos que estan relacionados con el nodo que se esta visitando. Si se tienen los permisos adecuados, es posible editar los metadatos de un nodo y tambien sus relaciones. 

- search: interfaz de busqueda a texto completo de typesense

- agent: interfaz para interactuar con el agente, en la respuesta del agente, ademas del texto de respuesta, se debe mostrar una lista de las entidades principales involucradas en la respuesta. 

