# PRD — Plataforma Multi-Agente RAG + KEDB (Mesa de Ayuda OITSI-MTC)

> **Naturaleza de este documento.** Este PRD es un artefacto de **ingeniería de construcción**, complementario a la tesis (`resources/chapter-3.md`, `resources/chapter-4.md`) pero no forma parte de ella. Se basa en la incepción ágil y la arquitectura ya aprobadas (Product Vision Board, Product Canvas, Historias de Usuario, arquitectura de 9 componentes, stack tecnológico y ADR-01 a ADR-08 de `knowledge/06-arquitectura-y-diseno.md`). Donde se propone un detalle de implementación que **no está en el material fuente** (endpoints REST concretos, payloads, estructura de carpetas, prompts de agente), se marca explícitamente como **[PROPUESTA DE INGENIERÍA]** — es una decisión de construcción libre de ajustar, no un dato de tesis que requiera trazabilidad académica.
>
> **Objetivo del documento.** Servir de especificación ejecutable para que agentes de codificación (p. ej. Claude Code) construyan el producto historia por historia, con criterios de aceptación verificables, contratos de datos explícitos y dependencias declaradas, sin necesidad de releer la tesis completa en cada tarea.

---

## 1. Resumen ejecutivo

Construir una plataforma multi-agente con RAG que, ante un ticket de la Mesa de Ayuda OITSI-MTC, lo clasifique, lo priorice y recupere soluciones similares ya aplicadas; y que, a partir de tickets resueltos, genere automáticamente artículos de una base de errores conocidos (KEDB) con trazabilidad N:1, validados por un experto. El ciclo cerrado **asistencia ↔ KEDB** es el diferenciador del producto: cada resolución retroalimenta la base que acelera las siguientes.

**Definición de "funcional con valor" (MVP):** un operador puede enviar un ticket de texto libre y recibir, en menos de 30 segundos, categoría + prioridad + Top-5 soluciones similares; y un experto puede revisar y aprobar artículos KEDB generados automáticamente a partir de tickets resueltos, quedando esos artículos disponibles para la siguiente búsqueda. Ese ciclo completo, de punta a punta, es el criterio de "listo" del MVP — no una demo parcial de un solo agente.

---

## 2. Alcance

### 2.1 Dentro de alcance (MVP funcional — Fase Core)

Corresponde al ciclo cerrado completo, ya validado en la incepción ágil y construido en Sprint 1 + Sprint 2 de la tesis (`chapter-4.md`):

| Bloque | Componentes | Historias de usuario |
| :--- | :--- | :--- |
| Datos | C1 Anonimización, C2 Ingesta/Normalización | HU13 (tarea técnica) |
| Asistencia | C3 Clasificador, C4 Priorizador, C5 Agente RAG | HU01, HU02 ✅, HU04, HU06, HU07 ✅ |
| Conocimiento | C6 Generador KEDB (agrupación + síntesis) | HU08a, HU08b, HU09 ✅, HU10, HU14 |
| Orquestación | C7 Orquestador (LangGraph, conditional routing) | tarea técnica (sustenta HU01/04/06/14) |
| Interfaz | C8 Interfaz del Operador (mínima) | soporte de HU01, HU04, HU06, HU10, HU14 |
| Evaluación | C9 Framework de evaluación (métricas de respaldo, no en vivo) | soporte de F1/Recall@5 |

> **Nota de construcción:** HU02, HU07 y HU09 se adelantaron al MVP (ya estaban en API/UI del camino dorado). Siguen listadas en §2.2 por trazabilidad del backlog original, marcadas como ✅ hechas.

### 2.2 Dentro de alcance (backlog completo — Fase 2, post-MVP)

Historias ya priorizadas en el Product Backlog (`chapter-3.md`, Tabla 27) que enriquecen el producto pero no son bloqueantes para que el ciclo cerrado funcione:

| ID | Título | Depende de | Notas |
| :--- | :--- | :--- | :--- |
| HU02 ✅ | Confianza de clasificación | HU01 | Adelantada a MVP — hecha |
| HU03 | Corrección de categoría | HU01 | |
| HU05 | Justificación de prioridad | HU04 | |
| HU07 ✅ | Indicador de similitud | HU06 | Adelantada a MVP — hecha |
| HU09 ✅ | Trazabilidad del artículo | HU08b | Adelantada a MVP — hecha (Escena 2) |
| HU11 | Utilidad del artículo | HU06 | |
| HU12 | Registro de nueva solución | HU06 | |
| HU15 | Tablero del coordinador | HU01, HU08b | |
| HU16 | Búsqueda directa en la KEDB | HU06 | |
| HU17 | Gestión del ciclo de vida | HU10 | |

### 2.3 Fuera de alcance (todo el producto, MVP y Fase 2)

Según `chapter-3.md` §3.1.9: cobertura limitada a las 9 categorías de mayor volumen (50% del total); sin gestión de accesos/gobernanza de usuarios; sin integración con Active Directory, correo o sistemas administrativos externos; sin interfaz móvil; sin analítica avanzada más allá del tablero del coordinador; sin conexión activa a una instancia GLPI en producción (el histórico se consume como export estático); sin soporte productivo post-entrega.

### 2.4 Ruta de demo (valor visible al cliente) **[PROPUESTA DE INGENIERÍA]**

El criterio de priorización dentro del MVP core no es solo "qué depende de qué", sino **qué se ve** cuando el patrocinador (OITSI-MTC) tiene la plataforma delante. La demo debe demostrar, en una sola sesión, que el ciclo cerrado asistencia ↔ KEDB funciona con datos reales, no que cada agente funciona por separado.

**Camino dorado (lo que se muestra en vivo, en este orden):**

1. El operador pega un ticket real (texto coloquial, de una sesión previa del histórico o escrito en el momento) → en segundos recibe categoría, prioridad y Top-5 soluciones similares. Este es el momento que ataca directamente el 82.6% de recurrencia — el argumento más convincente para el patrocinador.
2. Se abre un artículo KEDB ya generado (preprocesado antes de la demo, no en vivo) con su trazabilidad a los tickets fuente — evidencia de que el conocimiento "se escribe solo" a partir del histórico real.
3. El experto aprueba ese artículo con un clic frente al cliente — cierra el ciclo asistencia ↔ KEDB de forma visible.

**Qué se degrada o se saca de la ruta en vivo** (sigue existiendo en el backlog, pero no se ejecuta frente al cliente):

- La generación de KEDB (HU08a clustering + HU08b síntesis LLM) se corre de antemano sobre un clúster bien elegido, como *fixture* de datos. No se ejecuta en vivo, para no depender de que el LLM produzca un buen borrador en el momento frente al cliente.
- El Framework de Evaluación completo (C9: golden set de 200, Kappa, estudio comparativo de tiempo) no se ejecuta en la demo; sus cifras (F1, Recall@5) se presentan como respaldo (slide o panel estático), no como una corrida en vivo.
- Todo el backlog Fase 2 (HU02, HU03, HU05, HU07, HU09, HU11, HU12, HU15, HU16, HU17) es prescindible para la demo — enriquece el producto pero no aporta al impacto visual del ciclo cerrado.

**Etiquetas de historia para la demo**, usadas en la sección 8: 🎯 esencial en vivo · 🧱 prework (corrido antes, mostrado como resultado) · 📦 backlog visible, no crítico para la demo.

---

## 3. Usuarios (personas)

| Rol | Uso del sistema | Historias que le sirven |
| :--- | :--- | :--- |
| **Operador de Mesa de Ayuda** (primario) | Envía tickets, consulta clasificación/prioridad/soluciones, corrige y retroalimenta | HU01-HU07, HU11, HU12, HU16 |
| **Experto técnico del MTC** (secundario) | Valida, edita o rechaza artículos KEDB; recibe alertas de pendientes | HU08a, HU08b, HU09, HU10, HU14, HU17 |
| **Jefe/Coordinador de Mesa de Ayuda** (secundario) | Consulta indicadores de cobertura, prioridad y recurrencia | HU15 |

Detalle de objetivos, frustraciones y motivaciones de cada perfil: `chapter-3.md` §3.1.2 (Tablas 21-23).

---

## 4. Arquitectura del MVP

### 4.1 Vista de componentes

Arquitectura de 3 capas / 9 componentes ya aprobada (`chapter-3.md` §3.2, Figura 10 y Tabla 30; detalle profundo en `knowledge/06-arquitectura-y-diseno.md`):

```
Capa 1 (Datos)        : C1 Anonimización → C2 Ingesta/Normalización → Vector DB
Capa 2 (Agentes)       : C7 Orquestador → { C3 Clasificador, C4 Priorizador, C5 Agente RAG } → C6 Generador KEDB
Capa 3 (Interfaces)   : C8 Interfaz del Operador (React SPA) · C9 Framework de Evaluación
```

Flujo: `ticket nuevo → C1 → C2 → C7 → (C3 ‖ C4) → C5 → C8 (respuesta al operador) → [operador resuelve] → C6 → KEDB Storage → retroalimenta a C5`.

### 4.2 Stack tecnológico (ya decidido, sin componentes abiertos)

Igual a `chapter-3.md` Tabla 32 / `knowledge/06` — no se reabre ninguna decisión:

| Capa | Tecnología | ADR |
| :--- | :--- | :--- |
| Lenguaje | Python 3.11+ | — |
| Backend API | FastAPI (REST + WebSocket) | — |
| LLM | GPT-4o-mini (OpenAI) | ADR-02 |
| Embeddings | text-embedding-3-small (OpenAI) | ADR-04 |
| Vector DB | ChromaDB | ADR-03 |
| Framework de agentes | LangGraph (conditional routing) | ADR-01 / ADR-06 |
| NLP español | spaCy `es_core_news_lg` | ADR-08 |
| Clustering (KEDB) | HDBSCAN | ADR-05 |
| UI | React (SPA) | — |
| Contrato de eventos tiempo real | AsyncAPI sobre WebSocket | — |
| Versionado de datos | DVC + GitHub | — |
| CI/CD | GitHub Actions | — |
| Despliegue | Google Cloud Platform, Cloud Run | — |

### 4.3 Estructura de repositorio **[PROPUESTA DE INGENIERÍA]**

```
app/
  agents/
    classifier/        # C3
    prioritizer/        # C4
    rag/                 # C5
    kedb_generator/      # C6
    orchestrator/       # C7 — grafo LangGraph
  pipeline/
    anonymize/           # C1
    ingest/              # C2
  api/
    routers/            # endpoints REST (§6)
    ws/                  # canal WebSocket (§6.4)
  evaluation/            # C9 — golden set, métricas
  storage/
    vector_db/           # cliente ChromaDB
    kedb_store/          # persistencia de artículos KEDB
  schemas/               # modelos Pydantic (ticket, artículo KEDB, evento)
web/                     # C8 — React SPA
data/
  raw/                   # export GLPI (no versionado en git, sí en DVC)
  processed/             # dataset anonimizado + splits train/eval/holdout
tests/
```

---

## 5. Modelo de datos

Esquema canónico ya definido en `knowledge/06-arquitectura-y-diseno.md` (sección "Diseño de datos"). Se reproduce aquí como contrato vinculante para todas las historias:

**Ticket** (`schemas/ticket.py`): `ticket_id, fecha_apertura, fecha_cierre, canal_origen, categoria, categoria_top9, prioridad_original, titulo_anon, solucion_anon, sede_id, tiene_solucion, longitud_solucion, estado, tipo, grupo_tecnico`.

**Embedding**: `ticket_id (FK), vector, modelo_embeddings, fecha_generacion`.

**KEDB_Articulo** (`schemas/kedb_article.py`): `articulo_id, titulo, categoria, sintoma, causa, solucion, tickets_fuente (string[]), fecha_generacion, version, estado {borrador|validado|obsoleto|archivado}, calidad_experta`.

**Golden_set**: `golden_id, ticket_id (FK), categoria_experto1, categoria_experto2, categoria_sistema, split {train|eval|holdout}`.

**Evento de orquestador** (`schemas/event.py`, contrato AsyncAPI): `evento_id, timestamp, agente {Clasificador|Priorizador|RAG|GeneradorKEDB|Orquestador}, ticket_id, tipo {inicio|fin|error}, entrada, salida, metadata`.

Plantilla del artículo KEDB (usada por C6 al sintetizar, `knowledge/06`):

```markdown
# [Título del problema]
## Síntoma
## Categoría
## Causa probable
## Solución
## Aplicable a
## Trazabilidad
- Tickets fuente: [lista de IDs]
- Última actualización: [fecha]
- Estado: [borrador | validado | obsoleto]
```

---

## 6. Contrato de API **[PROPUESTA DE INGENIERÍA]**

No existe una definición de endpoints en el material fuente; se propone la siguiente superficie mínima, consistente con "REST para solicitud/respuesta + WebSocket para eventos del pipeline" (`chapter-3.md` §3.2.2.4). Ajustable libremente durante la construcción.

### 6.1 Ciclo de asistencia

| Método | Ruta | Historias | Descripción |
| :--- | :--- | :--- | :--- |
| `POST` | `/tickets` | HU01, HU04, HU06 | Envía un ticket nuevo; dispara C7 → C3 ‖ C4 → C5. Responde `{ticket_id, categoria, confianza, prioridad, justificacion_prioridad, soluciones: [{articulo_o_ticket_id, score, tipo}]}` |
| `GET` | `/tickets/{id}` | HU01-HU07 | Estado y resultado del pipeline para un ticket |
| `PATCH` | `/tickets/{id}/categoria` | HU03 | Corrección manual de categoría por el operador |
| `POST` | `/tickets/{id}/resolucion` | C6 (trigger) | Registra la solución aplicada; candidato a entrar al siguiente lote de clustering |
| `POST` | `/tickets/{id}/feedback` | HU11, HU12 | Utilidad de artículo consultado / registro de solución nueva no sugerida |

### 6.2 Ciclo de KEDB

| Método | Ruta | Historias | Descripción |
| :--- | :--- | :--- | :--- |
| `POST` | `/kedb/generate` | HU08a, HU08b | Ejecuta clustering (HDBSCAN) + síntesis LLM sobre tickets resueltos pendientes; crea artículos en estado `borrador` |
| `GET` | `/kedb/articulos` | HU16, HU17 | Lista artículos con filtro por estado/categoría |
| `GET` | `/kedb/articulos/{id}` | HU09 | Detalle de artículo + tickets fuente (trazabilidad N:1) |
| `PATCH` | `/kedb/articulos/{id}` | HU10 | Aprobar / editar / rechazar; cambia `estado` |
| `PATCH` | `/kedb/articulos/{id}/ciclo-vida` | HU17 | Cambia estado a `archivado` |
| `GET` | `/kedb/pendientes` | HU14 | Artículos en `borrador` para alertar al experto |
| `GET` | `/kedb/buscar?q=` | HU16 | Búsqueda semántica libre sobre artículos publicados |

### 6.3 Supervisión

| Método | Ruta | Historias |
| :--- | :--- | :--- |
| `GET` | `/metrics/dashboard` | HU15 — cobertura KEDB, distribución de prioridad, tendencias de recurrencia, con filtros de categoría y rango de fechas |
| `GET` | `/metrics/evaluacion` | C9 — F1, Recall@5, Kappa vigentes sobre el golden set |

### 6.4 Canal en tiempo real

`WS /ws/pipeline/{ticket_id}` — emite un evento (esquema §5) por cada nodo del grafo LangGraph que se ejecuta (inicio/fin/error), consumido por C8 para resaltar el nodo activo.

---

## 7. Especificación de agentes

### 7.1 C1 — Anonimización

**Entrada:** histórico GLPI crudo (CSV/Excel). **Salida:** dataset anonimizado + log de auditoría.
**Técnica (ADR-08):** Regex para patrones estructurados (correos, DNI de 8 dígitos, IPs, teléfonos) + NER con spaCy `es_core_news_lg` para nombres propios + diccionario de instituciones del MTC para no anonimizar entidades públicas. Reemplazo por tokens `[NOMBRE]`, `[CORREO]`, `[DNI]`, `[IP]`, `[TELEFONO]`.
**Criterio de aceptación (DoD del componente):** PII residual = 0 sobre una muestra de 500 tickets.

### 7.2 C2 — Ingesta y normalización

**Entrada:** dataset anonimizado. **Salida:** dataset canónico + splits train/eval/holdout + embeddings en Vector DB.
**Operaciones:** deduplicación por `ticket_id`, fechas a ISO 8601, limpieza de texto (HTML residual, encoding), normalización de categorías, partición temporal (train: mar-2024 a may-2025; eval: jun-sep 2025; holdout: oct 2025), generación de embeddings con `text-embedding-3-small` persistidos en ChromaDB.

### 7.3 C3 — Clasificador (HU01, HU02, HU03)

**Entrada:** ticket canónico (título + descripción implícita). **Salida:** `{categoria, confianza, top3: [...]}`.
**Métrica de aceptación:** F1 macro ≥ 0.80 sobre golden set de 200 tickets (top 9 categorías).
**Nota de implementación:** el material fuente deja abierta la arquitectura interna (embeddings+KNN, LLM few-shot, o híbrido) — decisión de construcción libre, siempre que cumpla la métrica.

### 7.4 C4 — Priorizador (HU04, HU05)

**Entrada:** ticket clasificado + contexto (recurrencia histórica, SLA, área). **Salida:** `{prioridad, score, justificacion}`.
**Fórmula de scoring (ADR-07, fijada por criterio de negocio):**

```
score = 0.30 * impacto_servicio_ciudadano
      + 0.20 * recurrencia_historica
      + 0.25 * SLA_asociado
      + 0.15 * criticidad_solicitante
      + 0.10 * tipo_incidencia
```

**Criterio de aceptación:** ninguna clase de prioridad concentra más del 70% de los tickets (vs. 95.9% actual en el histórico).

### 7.5 C5 — Agente RAG (HU06, HU07, HU16)

**Entrada:** ticket nuevo. **Salida:** Top-K (K=5) soluciones similares con score de similitud.
**Pipeline:** embedding del ticket → similitud coseno en ChromaDB (histórico + artículos KEDB) → re-ranking opcional con LLM → Top-K con metadata.
**Criterio de aceptación:** Recall@5 ≥ 0.85 sobre golden set.

### 7.6 C6 — Generador de KEDB (HU08a, HU08b, HU09, HU10, HU14)

**Entrada:** tickets cerrados con solución. **Salida:** artículos KEDB borrador + trazabilidad N:1.
**Pipeline (ADR-05):** clustering con HDBSCAN sobre embeddings de C2 → filtrar clústeres con ≥5 tickets y coherencia interna alta → síntesis con LLM usando la plantilla de §5 → registrar `tickets_fuente` → disparar notificación al experto (`GET /kedb/pendientes`, HU14).
**Criterios de aceptación:** cobertura ≥80% de incidencias recurrentes; ≥50 artículos trazables; calidad experta ≥4/5 sobre muestra ≥30 artículos.
**Para la demo (§2.4):** HU08a y HU08b se ejecutan antes de la sesión sobre un clúster curado; el artículo que se muestra al cliente es un resultado ya generado, no una corrida en vivo del clustering ni de la síntesis LLM.

### 7.7 C7 — Orquestador

**Función:** coordina C3, C4, C5 y C6 mediante un grafo de estado LangGraph con *conditional routing* (ADR-01, ADR-06): puede omitir C5 si el tipo de incidencia ya tiene resolución directa, o escalar de inmediato ante prioridad alta detectada por C4. Emite el evento de §5 por cada nodo ejecutado (canal `/ws/pipeline/{ticket_id}`) y actualiza estadísticas de uso cuando el operador consulta la KEDB (ciclo de retroalimentación).
**Criterio de aceptación:** tiempo de respuesta ≤30 s por ticket end-to-end (C3+C4+C5+C7).

### 7.8 C8 — Interfaz del Operador (mínima para MVP)

Tres pantallas ya diseñadas en baja fidelidad (`chapter-3.md` §3.1.5, Figuras 6-8): pantalla del operador (asistencia), pantalla de validación experta (KEDB) y tablero del coordinador (Fase 2). Para el MVP core basta la primera y la segunda; el tablero (HU15) es Fase 2.
Consume el backend por REST (envío de ticket, consulta de KEDB) y WebSocket (eventos del pipeline en vivo, §6.4).

### 7.9 C9 — Framework de evaluación (versión inicial para MVP)

Para el MVP core: golden set de 200 tickets estratificados por las top 9 categorías (etiquetado experto, doble etiquetado en ~30 para Kappa) + scripts de cálculo automático de F1 y Recall@5 con semillas fijas (DVC para reproducibilidad). La validación experta de calidad de KEDB y el estudio comparativo de tiempo de búsqueda son parte del framework completo pero no bloquean el ciclo funcional del MVP.
**Para la demo (§2.4):** no se ejecuta en vivo. Las cifras de F1 y Recall@5 se calculan de antemano y se presentan como respaldo (slide o panel estático) que sustenta lo que el cliente acaba de ver funcionar, no como parte del guion interactivo.

---

## 8. Historias de usuario — especificación completa

Formato por historia: narrativa, criterio de aceptación (ya aprobado en `chapter-3.md` Tabla 26), componente(s) y endpoint(s) involucrados, contrato de datos, dependencias, y fase (MVP core / Fase 2).

**Definition of Ready / Definition of Done generales** (`chapter-3.md` §3.1.6): toda historia entra a construcción con formato Como/Quiero/Para, INVEST, criterios de aceptación verificables, estimación en story points y sin dependencias bloqueantes; se da por terminada cuando cumple sus criterios de aceptación, supera las métricas de calidad asociadas, fue revisada por el equipo, aceptada por el Product Owner, documentada y desplegada en el entorno definido.

### HU13 — Anonimización e ingesta del histórico *(tarea técnica, MVP core)* 🧱

Precondición de todo el sistema: sin este dataset anonimizado y con embeddings generados, ningún agente tiene datos sobre los que operar.
**Componentes:** C1, C2. **Datos:** `data/raw` → `data/processed` + Vector DB poblado.
**Dependencias:** ninguna (primer ítem del pipeline).
**Hecho cuando:** PII residual = 0 en muestra de 500 tickets; splits train/eval/holdout materializados; embeddings persistidos en ChromaDB.

### HU01 — Clasificación automática *(MVP core)* 🎯

Como operador, quiero que el sistema clasifique automáticamente cada ticket nuevo en una categoría, para no categorizarlo manualmente.
**Aceptación:** dado un ticket nuevo, cuando ingresa al sistema, entonces se le asigna una de las top 9 categorías con su nivel de confianza.
**Componentes/endpoint:** C3, C7 · `POST /tickets`. **Depende de:** HU13.

### HU02 — Confianza de clasificación *(MVP — adelantada desde Fase 2)* ✅

Como operador, quiero ver el nivel de confianza de la clasificación sugerida, para decidir si la acepto o la corrijo.
**Aceptación:** dada una clasificación sugerida, cuando el operador la visualiza, entonces se muestra el porcentaje de confianza asociado.
**Componentes/endpoint:** C3, C8 · campo `confianza` ya expuesto por `POST /tickets` (§6.1). **Depende de:** HU01.
**Estado:** implementada en pantalla Operador (badge de categoría + `%` de confianza).

### HU03 — Corrección de categoría *(Fase 2)* 📦

Como operador, quiero corregir la categoría cuando sea incorrecta, para que el sistema registre mi retroalimentación.
**Aceptación:** dada una categoría incorrecta, cuando el operador la corrige, entonces el sistema guarda la corrección y la categoría final.
**Componentes/endpoint:** C3, C8 · `PATCH /tickets/{id}/categoria`. **Depende de:** HU01.

### HU04 — Priorización por impacto *(MVP core)* 🎯

Como operador, quiero que el sistema priorice cada ticket por impacto, para atender primero lo más urgente.
**Aceptación:** dado un ticket clasificado, cuando se procesa, entonces recibe una prioridad según su scoring de impacto.
**Componentes/endpoint:** C4, C7 · `POST /tickets` (campo `prioridad`). **Depende de:** HU01.

### HU05 — Justificación de prioridad *(Fase 2)* 📦

Como operador, quiero ver la justificación de la prioridad asignada, para confiar en ella o ajustarla.
**Aceptación:** dada una prioridad asignada, cuando el operador la consulta, entonces se muestran los factores que la determinaron.
**Componentes/endpoint:** C4, C8 · campo `justificacion_prioridad` (desglose de los 5 pesos del ADR-07). **Depende de:** HU04.

### HU06 — Recuperación de soluciones *(MVP core)* 🎯

Como operador, quiero recibir las soluciones similares ya aplicadas a tickets parecidos, para resolver sin reinvestigar.
**Aceptación:** dado un ticket en atención, cuando el operador solicita ayuda, entonces el sistema devuelve las Top-K soluciones más similares del histórico y la KEDB.
**Componentes/endpoint:** C5, C7 · `POST /tickets` (campo `soluciones`). **Depende de:** HU13.

### HU07 — Indicador de similitud *(MVP — adelantada desde Fase 2)* ✅

Como operador, quiero ver qué tan similar es cada solución sugerida, para elegir la más pertinente.
**Aceptación:** dada una lista de soluciones sugeridas, cuando se presentan, entonces cada una muestra su grado de similitud.
**Componentes/endpoint:** C5, C8 · campo `score` ya expuesto en `soluciones[]`. **Depende de:** HU06.
**Estado:** implementada en pantalla Operador (similitud % por cada hit del Top-5).

### HU08a — Agrupación de tickets similares *(MVP core)* 🧱

Como experto técnico, quiero que el sistema agrupe los tickets resueltos similares, para identificar qué conocimiento conviene consolidar.
**Aceptación:** dado el histórico de tickets resueltos, cuando se ejecuta la agrupación, entonces los tickets con solución similar quedan agrupados en clústeres.
**Componentes/endpoint:** C6 (clustering HDBSCAN) · `POST /kedb/generate` (etapa 1). **Depende de:** HU13.

### HU08b — Generación de borrador KEDB *(MVP core)* 🧱

Como experto técnico, quiero que el sistema genere un borrador de artículo KEDB a partir de esos tickets, para no redactarlo desde cero.
**Aceptación:** dado un clúster de tickets similares, cuando se ejecuta la generación, entonces se crea un artículo KEDB borrador con problema, causa y solución.
**Componentes/endpoint:** C6 (síntesis LLM) · `POST /kedb/generate` (etapa 2). **Depende de:** HU08a.

### HU09 — Trazabilidad del artículo *(MVP — adelantada desde Fase 2)* ✅

Como experto técnico, quiero ver los tickets de origen de cada artículo, para verificar su fundamento.
**Aceptación:** dado un artículo KEDB, cuando el experto lo abre, entonces se listan los tickets fuente que lo originaron (trazabilidad N:1).
**Componentes/endpoint:** C6, C8 · `GET /kedb/articulos/{id}` (campo `tickets_fuente`). **Depende de:** HU08b.
**Estado:** implementada en pantalla Experto (conteo + preview de IDs; Escena 2 de la demo).

### HU10 — Validación del artículo *(MVP core)* 🎯

Como experto técnico, quiero aprobar, editar o rechazar los artículos borrador, para garantizar la calidad del conocimiento publicado.
**Aceptación:** dado un artículo borrador, cuando el experto lo revisa, entonces puede aprobarlo, editarlo o rechazarlo y su estado se actualiza.
**Componentes/endpoint:** C6, C8 · `PATCH /kedb/articulos/{id}`. **Depende de:** HU08b.
**Estado:** UI Experto — Editar (título/síntoma/causa/solución/aplicable a) + Guardar; Aprobar (indexa RAG); Rechazar → `obsoleto`.

### HU11 — Utilidad del artículo *(Fase 2)* 📦

Como operador, quiero indicar si un artículo de la KEDB me resultó útil, para mejorar las recomendaciones futuras.
**Aceptación:** dado un artículo consultado, cuando el operador lo califica, entonces el sistema registra la utilidad reportada.
**Componentes/endpoint:** C7 (ciclo de retroalimentación), C8 · `POST /tickets/{id}/feedback`. **Depende de:** HU06.

### HU12 — Registro de nueva solución *(Fase 2)* 📦

Como operador, quiero registrar una nueva solución cuando ninguna sugerencia aplique, para enriquecer la KEDB.
**Aceptación:** dado un ticket sin solución aplicable, cuando el operador documenta una nueva, entonces queda registrada como candidata a artículo KEDB.
**Componentes/endpoint:** C8 · `POST /tickets/{id}/feedback` (candidata a entrar al siguiente lote de HU08a). **Depende de:** HU06.

### HU14 — Notificación al experto *(MVP core)* 🎯

Como experto técnico, quiero recibir una alerta cuando haya artículos KEDB pendientes de validación, para no perder ninguno.
**Aceptación:** dado un artículo KEDB en estado borrador, cuando se genera, entonces el experto técnico recibe una alerta con el enlace al artículo pendiente.
**Componentes/endpoint:** C7 · `GET /kedb/pendientes`. **Depende de:** HU08b.

### HU15 — Tablero del coordinador *(Fase 2)* 📦

Como coordinador, quiero ver la cobertura de la KEDB, la distribución de prioridades y las tendencias de recurrencia, para tomar decisiones de mejora.
**Aceptación:** dado el estado de la operación, cuando el coordinador abre el tablero, entonces visualiza los indicadores actualizados y puede filtrar por categoría y rango de fechas.
**Componentes/endpoint:** C8 · `GET /metrics/dashboard`. **Depende de:** HU01, HU08b.

### HU16 — Búsqueda directa en la KEDB *(Fase 2)* 📦

Como operador, quiero buscar en la KEDB por palabras clave, para consultar soluciones de forma proactiva sin tener un ticket abierto.
**Aceptación:** dado un término de búsqueda, cuando el operador lo consulta en la KEDB, entonces el sistema devuelve los artículos relevantes ordenados por similitud.
**Componentes/endpoint:** C5, C8 · `GET /kedb/buscar?q=`. **Depende de:** HU06.

### HU17 — Gestión del ciclo de vida *(Fase 2)* 📦

Como experto técnico, quiero consultar el listado de artículos KEDB con su estado (borrador, validado o archivado), para gestionar el conocimiento publicado.
**Aceptación:** dado el conjunto de artículos KEDB, cuando el experto accede al listado, entonces visualiza cada artículo con su estado y puede cambiarlo según corresponda.
**Componentes/endpoint:** C8 · `GET /kedb/articulos`, `PATCH /kedb/articulos/{id}/ciclo-vida`. **Depende de:** HU10.

---

## 9. Criterios de éxito del MVP

Tomados de las métricas ya fijadas en el Product Canvas (`chapter-3.md` Tabla 25) y en los atributos de calidad (`chapter-3.md` Tabla 31):

| Dimensión | Criterio |
| :--- | :--- |
| Clasificación | F1 macro ≥ 0.80 sobre golden set de 200 tickets |
| Recuperación | Recall@5 ≥ 0.85 |
| Priorización | Ninguna clase de prioridad concentra más del 70% de los tickets |
| KEDB | ≥50 artículos trazables; cobertura ≥80% de incidencias recurrentes; calidad experta ≥4/5 |
| Confidencialidad | PII residual = 0 en muestra de 500 tickets |
| Rendimiento | Tiempo de respuesta ≤30 s por ticket (o ≤10 s si se exige el estándar del Product Canvas) |
| Reproducibilidad | Variación de F1 ≤ 0.01 al reejecutar el framework de evaluación con semillas fijas |

El MVP se considera "funcional y con valor" cuando estos criterios se cumplen sobre el ciclo completo (asistencia → resolución → generación KEDB → retroalimentación), no sobre agentes aislados.

---

## 10. Orden de construcción sugerido para agentes de código

Prioriza llegar cuanto antes al camino dorado de la demo (§2.4) — todo lo marcado 🎯 se construye antes que lo marcado 🧱, y esto antes que cualquier 📦. Respeta además las dependencias ya declaradas en el Product Backlog (`chapter-3.md` Tabla 27):

1. HU13 🧱 (C1 + C2) — sin esto no hay datos para ningún agente. Alcanza con procesar un subconjunto representativo del histórico si acelera llegar a un demo funcional; el histórico completo no es bloqueante para la demo.
2. HU01 🎯 (C3) y HU06 🎯 (C5) en paralelo — ambos solo dependen de HU13. Son el primer momento visible de la demo.
3. HU04 🎯 (C4) — depende de HU01. Completa la respuesta de `POST /tickets` (categoría + prioridad + soluciones).
4. C7 (Orquestador, versión simple) — integra C3, C4, C5; no es necesario implementar todo el conditional routing de ADR-06 para la demo, con una cadena secuencial que cumpla el tiempo de respuesta basta.
5. C8 (pantalla del operador, mínima) — consume lo anterior; cierra la Escena 1 del guion de demo (§10.1).
6. HU08a 🧱 y HU08b 🧱 (C6) — se corren *offline* sobre un clúster curado para producir el artículo KEDB que se mostrará como *fixture* en la Escena 2; no bloquean a HU01/HU04/HU06.
7. HU10 🎯 y HU14 🎯 — pantalla de validación experta sobre el artículo ya generado; cierra la Escena 2 y 3 del guion de demo.
8. C9 (métricas de respaldo) — F1/Recall@5 calculados sobre lo ya construido, para tener cifra de sustento si el cliente pregunta por desempeño.
9. Backlog Fase 2 📦 (HU02, HU03, HU05, HU07, HU09, HU11, HU12, HU15, HU16, HU17) en el orden de la Tabla 27 — después de que la demo funcione de punta a punta.

Cada historia debe implementarse como unidad cerrada: código + prueba automatizada del criterio de aceptación + actualización de este documento si el contrato de API cambia.

### 10.1 Guion de demo (3 escenas)

| Escena | Qué ve el cliente | Historias que la sustentan | En vivo / prework |
| :--- | :--- | :--- | :--- |
| 1. Asistencia | Se pega un ticket real → aparecen categoría, prioridad y Top-5 soluciones en segundos | HU01, HU04, HU06 (+ C7, C8) | En vivo |
| 2. Conocimiento generado | Se abre un artículo KEDB con su trazabilidad a los tickets fuente | HU08a, HU08b (prework) + HU09 si se quiere mostrar la lista de fuente | Prework, mostrado como resultado |
| 3. Cierre del ciclo | El experto aprueba el artículo con un clic; queda disponible para la siguiente búsqueda | HU10, HU14 | En vivo |

Cifras de respaldo para preguntas del cliente (no se muestran salvo que se pregunte): F1 y Recall@5 del framework de evaluación inicial (C9), y las métricas de negocio ya fijadas en el Product Canvas (`chapter-3.md` Tabla 25): reducción del 50% en tiempo de búsqueda, ninguna clase de prioridad sobre 70%, cobertura KEDB ≥80% de recurrentes.

### 10.2 Curaduría de tickets para la demo (a partir de `artifacts/Tickets_Consolidados.xlsx`)

Fuente: hoja "Datos Consolidados" (96,000 filas, el export en bruto detrás de `knowledge/16`) y hoja "Calidad x Categoría" (rating de aptitud KEDB por categoría, ≥100 tickets). Cruzando ambas contra el Pareto de categorías (`knowledge/16`, mismas 9 categorías al 50% del volumen):

| Categoría (top 9) | Tickets | % soluciones ricas (≥80 ch) | % vacías | Aptitud KEDB |
| :--- | ---: | ---: | ---: | :--- |
| **Impresora Multifuncional** | 4,691 | 52.8% | 0.9% | **Alta** |
| Aplicaciones MTC \> STD | 11,578 | 37.4% | 1.3% | Media |
| Equipos de Escritorio \> CPU | 10,743 | 49.0% | 1.4% | Media |
| VPN \> No accede al servicio | 3,705 | 46.2% | 0.9% | Media |
| VPN \> Habilitación del servicio | 3,169 | 24.9% | 4.0% | Baja |
| Cuenta de usuario (alta / bloqueo / vigencia) | 7,334 / 3,140 / 2,919 | 3-18% | 1-10% | Baja |
| Correo \> Buzón lleno | 2,197 | 49.2% | 0.8% | Media |

**Recomendación: usar "Impresora Multifuncional" como categoría principal de la demo** — es la única de las 9 con aptitud Alta, así que rinde mejor tanto para el Top-5 del Agente RAG (Escena 1) como para la síntesis del Generador KEDB (Escena 2).

**Escena 1 — ticket a ingresar en vivo.** Dentro de esa categoría existe un clúster real de **142 tickets con título idéntico "Configuración de impresora Kyocera 7003"** (429 si se cuenta toda la familia Kyocera: variantes de escaneo, IP, no imprime), 125 de ellos con la solución textualmente idéntica: *"Se configuró impresora predeterminada y se validó con impresión de hoja de prueba correctamente. Atendido"*, cerrados entre marzo-2024 y octubre-2025. Se recomienda ingresar en vivo una variante no vista literalmente en ese subconjunto (p. ej. *"Impresora Kyocera 7003 no imprime, necesito que la configuren"*) para que la demo muestre clasificación + recuperación genuinas, no un match textual trivial. Como respaldo de variedad, otras categorías del top 9 con calidad Media también sirven para mostrar más de un dominio: p. ej. *"Sin acceso a escritorio remoto"* (VPN, ticket real 66487, solución: configuración de credenciales en GlobalProtect) o *"Problemas de conexión remota vía VPN"* (ticket 95813).

**Escena 2 — artículo KEDB (prework).** El propio clúster de 142 tickets "Configuración de impresora Kyocera 7003" (o la familia ampliada de 429) es el candidato natural para HU08a/HU08b: volumen muy por encima del umbral de aceptación (≥5 tickets), alta coherencia interna (mismo título, prácticamente la misma solución) y aptitud KEDB Alta. Un artículo de ejemplo (síntoma: "no configura/no imprime en impresora Kyocera TaskAlfa 7003i"; solución: configurar impresora predeterminada y validar con hoja de prueba) se puede generar de antemano sobre este clúster con alta probabilidad de calidad experta ≥4/5.

**Advertencia de anonimización.** El archivo `artifacts/Tickets_Consolidados.xlsx` es el export **sin anonimizar**: las columnas `Solicitante - Solicitante`, `Asignada a - Técnico` y `Solicitante - Autor` contienen nombres reales. Los títulos y soluciones citados arriba se revisaron y no contienen PII, pero cualquier ticket adicional que se extraiga de este archivo para la demo debe pasar primero por C1 (o al menos por una revisión manual) antes de mostrarse en pantalla — nunca usar el archivo crudo directamente en una demo frente al cliente.

---

## 11. Restricciones no funcionales

De `chapter-3.md` Tabla 29 y Tabla 31: procesamiento offline sobre export estático de GLPI (sin CDC/streaming); anonimización obligatoria como primer paso, no salteable (Ley N.º 29733, D.S. N.º 050-2018-PCM); corpus en español coloquial (sin garantía de desempeño en otros idiomas o registros formales); despliegue en GCP con Cloud Run; el sistema solo emite recomendaciones — la decisión final y el cierre del ticket siempre recaen en el operador; sin soporte productivo post-entrega, cualquier adopción institucional requiere validación adicional con expertos.
