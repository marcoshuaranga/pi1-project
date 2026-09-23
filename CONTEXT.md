# Plataforma RAG + KEDB (OITSI-MTC)

Plataforma de asistencia inteligente para la Mesa de Ayuda de OITSI-MTC: clasifica y prioriza tickets, recupera soluciones similares (RAG) y, a partir de tickets resueltos, genera artículos de una base de errores conocidos (KEDB) con trazabilidad N:1, validados por un experto humano.

> Nota: el código usa nombres de clase en inglés (`Orchestrator`, `ClassifierAgent`, `PrioritizerAgent`, `RAGAgent`, `KedbGeneratorAgent`). Este glosario usa los términos en español del producto como canónicos, porque son los que aparecen en el PRD, la UI y de cara al patrocinador.

## Language

### Entidades del dominio

**Ticket**:
Una incidencia o solicitud de la Mesa de Ayuda, importada del histórico GLPI. Tiene un estado (`abierto`, `en_proceso`, `cerrado`), una categoría y, si está cerrado, una solución.
_Avoid_: Caso, Incidencia, Solicitud

**Sesión de ticket** (`TicketSessionStatus`: `procesando` / `completado` / `error`):
No confundir con el estado GLPI del Ticket de arriba. Es el estado de la ejecución del pipeline (Orquestador) sobre un ticket nuevo que el Operador acaba de enviar — permite que la interfaz consulte `GET /tickets/{id}` y distinga "todavía procesando" de "ya terminó" o "falló", incluso si se reconecta a medio camino (p. ej. tras perder el WebSocket).

**Artículo KEDB** (`KedbArticulo`):
Un artículo de la base de errores conocidos, generado a partir de uno o más tickets resueltos similares. Tiene síntoma, causa, solución y una lista de `tickets_fuente`. Pasa por un ciclo de vida: `borrador` → `validado` → `obsoleto` / `archivado`.
_Avoid_: Nota de solución, KB article

**Trazabilidad N:1**:
La relación entre un artículo KEDB y los múltiples tickets fuente (`tickets_fuente`) que lo originaron. Es la evidencia de que el artículo "se escribe solo" a partir del histórico real, no de un resumen inventado.

**Ciclo cerrado asistencia ↔ KEDB**:
El flujo por el cual la asistencia a un ticket nuevo (clasificación + RAG) y la generación de conocimiento se retroalimentan mutuamente: tickets resueltos generan artículos KEDB, y los artículos KEDB validados vuelven a aparecer como soluciones sugeridas en tickets futuros. Es el diferenciador del producto.

**Solución sugerida** (`SolucionSugerida`):
Un resultado devuelto por el Agente RAG. Puede provenir de un ticket histórico (`tipo: ticket`) o de un artículo KEDB validado (`tipo: kedb`), con un score de similitud.

**Golden Set**:
Conjunto de tickets etiquetados manualmente (doble etiquetado por dos expertos, más la categoría predicha por el sistema) usado como verdad de referencia para medir la precisión del Clasificador. Particionado en splits `train` / `eval` / `holdout`.
_Avoid_: Ground truth, dataset de evaluación

**Anonimización**:
El proceso que reemplaza datos personales (nombres, correos, DNI, teléfonos, IPs) en el histórico de tickets crudo por tokens (`[NOMBRE]`, `[CORREO]`, etc.) antes de que cualquier dato entre al pipeline. Requisito de cumplimiento (Ley 29733). Ver [ADR-0008](docs/adr/0008-regex-plus-spacy-ner-anonymization.md).

### Agentes

**Agente**:
Cada uno de los cinco componentes de software (`AgenteTipo`) que participan en el pipeline de un ticket: Clasificador, Priorizador, Agente RAG, GeneradorKEDB y Orquestador.

**Clasificador**:
Agente que asigna una categoría y un nivel de confianza a un ticket nuevo, por similitud de embeddings (kNN) contra el split `train`.

**Priorizador**:
Agente que calcula la prioridad de un ticket mediante una fórmula de negocio fija y ponderada — no delega el scoring a un LLM, para mantenerlo auditable. Ver [ADR-0007](docs/adr/0007-fixed-business-formula-for-priority-scoring.md).

**Agente RAG**:
Agente que recupera las Top-5 soluciones más similares a un ticket nuevo, buscando tanto en tickets históricos como en artículos KEDB validados.
_Avoid_: Buscador semántico, retriever

**GeneradorKEDB**:
Agente que agrupa tickets resueltos similares (clustering) y sintetiza artículos KEDB en estado `borrador` a partir de cada grupo. Ver [ADR-0005](docs/adr/0005-hdbscan-for-kedb-clustering.md).
_Avoid_: KEDB generator, agente de síntesis

**Orquestador**:
El agente coordinador: ejecuta el grafo de estado que encadena Clasificador, Priorizador y Agente RAG (y dispara GeneradorKEDB sobre tickets resueltos), emitiendo un evento de pipeline por cada paso. Ver [ADR-0001](docs/adr/0001-langgraph-for-agent-orchestration.md) y [ADR-0006](docs/adr/0006-conditional-routing-in-orchestrator-graph.md).

**Evento de pipeline** (`PipelineEvento`):
Un mensaje emitido por el Orquestador por cada nodo del grafo que se ejecuta (`inicio`, `fin`, `error`), transmitido por WebSocket para que la interfaz resalte el agente activo en tiempo real.

### Interfaz y personas

**Operador**:
La persona que atiende tickets en la pantalla principal (`/`): envía el texto del ticket y ve categoría, prioridad y soluciones sugeridas. Puede recibir un ticket ya redactado desde la simulación de WhatsApp (`/whatsapp`) como punto de entrada alternativo al mismo flujo.

**Experto KEDB**:
La persona que revisa los artículos KEDB en `borrador` (`/experto`) y decide aprobarlos (→ `validado`), editarlos o rechazarlos. Es el punto de control humano del ciclo cerrado — sin su aprobación, un artículo nunca llega a alimentar el Agente RAG.

**Coordinador**:
La persona que consulta el tablero de métricas (`/dashboard`): datos reales de uso y evaluación (`/metrics/dashboard`, `/metrics/evaluacion`), no un mockup. Documentado en el PRD como "Fase 2, esqueleto" — esa descripción está desactualizada frente al código; el tablero ya consume datos en vivo.

**Live Docs**:
La proyección en Markdown de los artículos KEDB en estado `validado`, disponible en `/docs` como documentación de consulta de solo lectura.
