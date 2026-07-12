# Q&A de defensa — Demo Plataforma RAG + KEDB (OITSI-MTC)

Preguntas probables en una defensa universitaria o sesión con jurado técnico.  
Respuestas alineadas a `PRD.md`, ADRs del diseño y a lo **realmente implementado** en el repo.

**Complementa:** [`DEMO.md`](../DEMO.md) (guion) · [`DEMO_RUNBOOK.md`](DEMO_RUNBOOK.md) (checklist).

---

## Cómo usar este documento

1. Memoriza las respuestas de **Negocio** y **Validación** (suelen ser las más estrictas).
2. En tecnología, di primero el *qué* y el *por qué* (ADR); el detalle de hiperparámetros solo si lo piden.
3. Si algo del MVP está simplificado respecto a la tesis, **admítelo** y cita la meta del PRD vs. el estado actual. Queda mejor que inventar.

**Cifras de respaldo actuales** (`data/processed/evaluation_results.json`, pueden variar tras re-evaluación):

| Métrica | Valor de ejemplo | Meta PRD |
| :--- | ---: | ---: |
| F1 macro | ~0.95 (muestra 50) | ≥ 0.80 |
| Recall@5 | ~0.22 | ≥ 0.85 |
| Kappa | no calculado aún | doble etiquetado ~30 |

---

## 1. Negocio y problema

### ¿Cuál es el problema de negocio que resuelven?

La Mesa de Ayuda OITSI-MTC enfrenta alta **recurrencia** de incidencias (~**82.6%** según el análisis del proyecto): el mismo tipo de problema se vuelve a investigar una y otra vez porque el conocimiento queda en tickets sueltos de GLPI, no en una base reutilizable. El operador pierde tiempo buscando; la prioridad real se diluye (históricamente casi todo cae en una sola clase de prioridad).

### ¿Cómo lo resuelve su solución, en términos de proceso (no de ML)?

Ciclo cerrado de tres momentos:

1. **Asistencia:** ticket nuevo → categoría + prioridad + Top-5 soluciones ya aplicadas.
2. **Consolidación:** tickets resueltos similares → borrador de artículo KEDB (error conocido).
3. **Gobernanza:** experto valida → el artículo entra al mismo buscador que usa el operador.

El diferenciador no es “un chatbot”: es que **cada resolución puede alimentar la siguiente atención**.

### ¿Quién decide al final: el sistema o la persona?

Siempre la persona. El sistema **recomienda**; el operador cierra el ticket y el experto publica el conocimiento. Eso es restricción de diseño (no automatizar el cierre ni la publicación sin humano).

### ¿Por qué no integran GLPI en vivo?

Fuera de alcance del MVP: se trabaja sobre **export estático** del histórico. Evita dependencia de APIs productivas, permisos institucionales y riesgo en demo. La tesis/PRD lo dejan explícito: sin conexión activa a GLPI de producción.

### ¿Por qué solo 9 categorías?

Pareto: las 9 de mayor volumen cubren ~**50%** del total. El MVP prioriza profundidad ahí (datos, métricas, KEDB) en lugar de cobertura superficial de todo el catálogo.

### ¿Por qué la demo usa Impresora / Kyocera y no otra categoría?

Es la única del top-9 con **aptitud KEDB Alta** (muchas soluciones ricas y un clúster coherente de ~142 tickets “Configuración de impresora Kyocera 7003”). Otras (VPN, correo, STD) sirven para variedad; **cuenta de usuario** es mala para “wow” de RAG (pocas soluciones documentadas).

### ¿Cuál es el valor medible que prometen?

Metas de producto (Product Canvas / PRD §9), no promesas de producción:

- Reducir tiempo de búsqueda de soluciones (meta orientativa ≥50% en el estudio de diseño).
- Ninguna clase de prioridad >70% (vs. ~95.9% histórico concentrado).
- Cobertura KEDB ≥80% de incidencias recurrentes; ≥50 artículos trazables; calidad experta ≥4/5.
- F1 ≥0.80; Recall@5 ≥0.85; respuesta ≤30 s.

En demo se **muestra el ciclo**; las métricas se citan como respaldo, no como corrida en vivo.

### ¿Esto reemplaza a la Mesa de Ayuda?

No. Asiste al operador y al experto. No sustituye roles, SLAs institucionales ni la herramienta de ticketing.

---

## 2. Arquitectura y tecnologías

### ¿Cuál es la arquitectura en una frase?

Tres capas / **9 componentes**: Datos (C1–C2) → Agentes (C3–C7) → Interfaces y evaluación (C8–C9). Flujo: ticket → anonimización → orquestador → clasificar ‖ priorizar → RAG → UI; en paralelo/offline, generador KEDB → validación experta → retroalimenta RAG.

### ¿Por qué multi-agente y no un solo prompt LLM?

Separación de responsabilidades y trazabilidad:

| Componente | Rol | Técnica principal |
| :--- | :--- | :--- |
| C3 Clasificador | Categoría + confianza | Embeddings + kNN sobre Chroma (train) |
| C4 Priorizador | Prioridad + score | Fórmula de negocio ADR-07 (no LLM) |
| C5 RAG | Top-5 soluciones | Similitud coseno tickets + KEDB validados |
| C6 Generador KEDB | Borradores | HDBSCAN + síntesis LLM |
| C7 Orquestador | Coordina el pipeline | LangGraph (grafo de estado) |

Un solo LLM mezclaría clasificación, scoring de negocio y recuperación sin controles claros ni métricas por componente.

### ¿Por qué LangGraph (ADR-01 / ADR-06)?

Orquestación explícita de nodos (anonimizar → clasificar → priorizar → RAG) con eventos por paso (WebSocket). En esta build el grafo es **secuencial**; el *conditional routing* completo del diseño (saltar RAG, escalar por prioridad alta) es extensión prevista, no requisito para demostrar el ciclo MVP.

### ¿Por qué ChromaDB y no Pinecone / FAISS solo?

ADR-03: vector DB embebible, adecuada a prototipo/MVP académico y despliegue contenedorizado, sin vendor lock-in cloud obligatorio. Colecciones separadas: tickets históricos y artículos KEDB.

### ¿Qué modelo de embeddings usan y por qué?

`text-embedding-3-small` (OpenAI), ADR-04. Fallback de ingeniería: `EMBEDDING_PROVIDER=local` si hay cuota insuficiente. El mismo espacio vectorial alimenta clasificación kNN, RAG y clustering KEDB.

### ¿Qué LLM usan?

GPT-4o-mini (ADR-02), principalmente para **síntesis de artículos KEDB** (C6), no para el scoring de prioridad. Clasificación y recuperación en el camino caliente son embedding + similitud (más barato, más reproducible, más fácil de medir).

### ¿Por qué HDBSCAN y no K-Means para KEDB?

ADR-05: no exige fijar *k* a priori; detecta clústeres de densidad variable y deja ruido fuera. Encaja con “agrupar lo que se parece lo suficiente” y filtrar clústeres con ≥5 tickets antes de sintetizar.

### ¿Cómo anonimizan (Ley 29733)?

C1 (ADR-08): regex (correo, DNI 8 dígitos, IP, teléfono) + NER spaCy `es_core_news_lg` + diccionario de instituciones MTC (para no borrar entidades públicas). Tokens `[NOMBRE]`, `[CORREO]`, etc. Criterio: PII residual = 0 en muestra de control. **En demo no se abre el Excel crudo.**

### Stack resumido para si piden “enumere tecnologías”

Python 3.11+, FastAPI, LangGraph, OpenAI (LLM + embeddings), ChromaDB, spaCy, HDBSCAN, React (SPA), Redis/worker en compose, evaluación con scikit-learn (F1), DVC/GitHub para versionado de datos (diseño).

---

## 3. Cómo funciona cada agente (detalle defendible)

### Clasificador (C3) — ¿cómo decide la categoría?

1. Embedding del texto del ticket.
2. Consulta k vecinos en Chroma filtrando `split=train` (k≈15).
3. Voto ponderado por similitud → categoría ganadora + confianza + top-3.
4. Fallback por palabras clave si no hay vecinos.

No es fine-tuning de un clasificador supervisado clásico en el camino caliente; es **clasificación por vecinos en el espacio de embeddings**, alineada al mismo corpus que RAG.

### Priorizador (C4) — ¿de dónde sale la prioridad?

Fórmula fija ADR-07 (criterio de negocio, no “lo que diga el LLM”):

```
score = 0.30·impacto_ciudadano
      + 0.20·recurrencia_histórica
      + 0.25·SLA
      + 0.15·criticidad_solicitante
      + 0.10·tipo_incidencia
```

En la implementación actual los factores se estiman con heurísticas sobre texto/categoría (p. ej. “caído/masivo” ↑ impacto; Kyocera/impresora ↑ recurrencia). Umbrales mapean score → prioridad. Meta de negocio: evitar que una sola clase concentre >70% de los tickets.

### RAG (C5) — ¿qué recupera exactamente?

Embedding de la consulta → similitud en colección de **tickets** y en colección **KEDB** (artículos en estado `validado`) → fusión, deduplicación y Top-5 con score. Tras la Escena 3 de la demo, un hit puede ser `tipo: kedb`: evidencia del ciclo cerrado.

### Generador KEDB (C6) — ¿por qué no lo corren en vivo en la demo?

HDBSCAN + LLM pueden variar o producir un borrador flojo frente al jurado. El PRD lo marca como **prework**: se siembra el clúster Kyocera (~142 tickets fuente) y se muestra el resultado. La validación experta (aprobar) sí es en vivo: es el acto de gobernanza.

### Orquestador — ¿emiten eventos en tiempo real?

Sí: canal WebSocket `/ws/pipeline/{ticket_id}` con eventos inicio/fin por agente. Si WS falla, la UI usa fallback REST; la demo no se detiene.

---

## 4. Validación, métricas y rigor metodológico

### ¿Cómo validan el clasificador?

Framework C9: muestra del split **eval** (semilla fija), se compara `categoria_top9` real vs. predicción del C3; se reporta **F1 macro** (scikit-learn). Meta PRD: ≥0.80 sobre golden set de 200 (diseño completo). En la build de demo suele usarse una muestra menor (p. ej. 50) precomputada.

### ¿Qué es el golden set?

Conjunto etiquetado para evaluación (diseño: 200 tickets estratificados por top-9; doble etiquetado en ~30 para **Kappa** inter-anotador). En el repo hay muestra/`tickets_eval` + caché de métricas. Kappa en esta versión: **aún no calculado** (`null`) — dilo si preguntan; es parte del framework completo, no del guion en vivo.

### ¿Cómo miden Recall@5?

**Meta de tesis/PRD:** proporción de casos en que una solución semánticamente útil aparece en el Top-5 (≥0.85).

**Implementación actual (simplificada):** cuenta hit solo si el **mismo `ticket_id`** del ticket de evaluación reaparece en el Top-5. Eso es muy estricto y **subestima** el Recall de negocio (otras soluciones útiles de tickets distintos no cuentan). Por eso un Recall@5 ~0.22 **no contradice** una Escena 1 con Top-5 relevante: son definiciones distintas. Ante el jurado:

> “La cifra automática actual es un proxy estricto por ID; la relevancia operativa se juzga por las soluciones mostradas y, en el estudio completo, por un Recall semántico / juicio experto.”

### ¿Por qué el F1 puede verse alto y el Recall@5 bajo a la vez?

Miden cosas distintas: F1 = acierto de **categoría**; Recall@5 (proxy) = reaparición del **mismo ticket** en recuperación. Un clasificador fuerte no implica que el proxy de Recall sea alto.

### ¿Cómo validan la KEDB?

Tres capas previstas:

1. **Estructural:** clúster ≥5 tickets, trazabilidad N:1 (`tickets_fuente`).
2. **Experta (HU10):** aprobar / editar / rechazar; meta calidad ≥4/5 en muestra.
3. **Uso:** el artículo validado debe poder aparecer en RAG (Escena 3).

La generación automática no publica sola: sin experto no hay ciclo cerrado de calidad.

### ¿Tienen estudio de tiempo de búsqueda operador vs. sistema?

Está en el diseño del framework completo (C9); **no se ejecuta en la demo**. Si preguntan, es trabajo de evaluación empírica posterior/paralelo, no el camino dorado de 15 minutos.

### ¿Reproducibilidad?

Semilla fija en evaluación; datos versionados (DVC en el diseño); pipeline determinista de ingesta → embeddings. Variación de F1 objetivo ≤0.01 al reejecutar (meta PRD).

### ¿Train / eval / holdout?

Partición temporal en C2 (diseño: train mar-2024–may-2025; eval jun–sep 2025; holdout oct 2025) para evitar fuga temporal típica de tickets. El clasificador consulta vecinos del split train.

---

## 5. Preguntas difíciles / trampas académicas

### «¿No es solo un buscador semántico bonito?»

El buscador (C5) es una pieza. El producto añade: clasificación y priorización con criterios de negocio, generación de conocimiento consolidado (C6), validación humana (HU10) y **retroalimentación** al índice. Sin KEDB + experto, sería solo recuperación sobre tickets.

### «¿Por qué no fine-tunean un BERT/RoBERTa en español para clasificar?»

Decisión de construcción abierta en el material fuente mientras se cumpla F1≥0.80. Se eligió embeddings + kNN por: reutilizar el mismo índice que RAG, menos costo de entrenamiento, iteración rápida en MVP. Un clasificador supervisado clásico es alternativa válida si en holdout el kNN no sostiene la métrica.

### «¿El priorizador no es demasiado heurístico?»

Sí es heurístico en la implementación actual, pero la **fórmula de pesos es de negocio (ADR-07)**, no arbitraria del modelo. Los factores pueden enriquecerse después con señales reales de GLPI (SLA, área, recurrencia histórica cuantitativa). Lo defendible es: scoring transparente y auditable vs. “el LLM dijo Alta”.

### «¿ChatGPT solo no bastaba?»

Un LLM genérico no garantiza: anonimización normativa, métricas por componente, trazabilidad N:1 a tickets, priorización con pesos institucionales, ni gobernanza de publicación KEDB. El valor está en el **sistema** y el proceso, no en un prompt suelto.

### «¿Dónde está el ground truth de las soluciones del Top-5?»

Para clasificación: categoría del histórico / golden. Para recuperación: en el diseño, juicio de utilidad o Recall semántico; en código demo, proxy por `ticket_id`. Sé explícito con esa brecha: es deuda metodológica conocida de la build, no un secreto.

### «¿Pueden afirmar reducción del 50% del tiempo?»

Solo como **meta de producto** del canvas, no como resultado medido en esta demo. Afirmarlo como hecho empírico sin estudio comparativo sería incorrecto.

### ¿Cumplen ya todas las métricas del PRD §9?

No necesariamente todas en esta build. Ejemplo típico: F1 por encima de meta en muestra pequeña; Recall@5 proxy por debajo de 0.85; Kappa pendiente; cobertura KEDB ≥50 artículos es meta de escala, la demo muestra el **mecanismo** con un artículo estrella (Kyocera). Posición honesta: MVP demuestra ciclo funcional; el framework de evaluación respalda y se completa hacia las metas.

### ¿Qué queda fuera de alcance? (si quieren “límites”)

Sin AD/correo/GLPI live; sin app móvil; sin gobernanza completa de usuarios; sin analítica avanzada del coordinador como foco de demo; cobertura limitada a top-9; sin soporte productivo post-entrega.

---

## 6. Preguntas sobre la demo en vivo

### ¿Por qué el texto del ticket no es idéntico al histórico?

Para mostrar clasificación y RAG **genuinos** (similitud semántica), no un match exacto de título. Variante coloquial del clúster Kyocera.

### ¿Qué debo ver en Escena 1?

Categoría Impresora Multifuncional (o ruta completa), confianza alta, prioridad Media, Top-5 con soluciones tipo “impresora predeterminada / hoja de prueba / driver”.

### ¿Qué debo ver en Escena 3?

Tras aprobar, un ticket Kyocera similar debe traer un hit **`tipo: kedb`**. Ese es el cierre visual del ciclo.

### ¿Por qué no generan borradores con el botón en vivo?

Riesgo de clúster/LLM inconsistente. Prework + `seed-demo` / `reset_demo`.

### Si el Recall@5 en pantalla/API es bajo, ¿la demo falló?

No. Explicar definición simplificada (sección 4) y juzgar por relevancia del Top-5 en Escena 1.

### Textos de reserva (si piden otro dominio)

Ver `DEMO.md` — prioridad: VPN → correo buzón lleno → STD. Evitar cuenta de usuario para lucir RAG.

---

## 7. Preguntas de implementación / ingeniería

### ¿API?

REST para comando/consulta (`POST /tickets`, KEDB, métricas) + WebSocket para eventos del pipeline. Contratos marcados como propuesta de ingeniería en el PRD.

### ¿Dónde persiste la KEDB?

Store propio (SQLite en el diseño de construcción) + indexación en Chroma al validar + proyección Markdown (Live Docs) para artículos publicados.

### ¿Qué pasa al rechazar un artículo?

Estado `obsoleto`; no debe alimentar RAG como conocimiento publicado.

### ¿Anonimización en el ticket en vivo de la demo?

El texto pasa por C1 en el orquestador; los ejemplos curados no traen PII. Igual no improvisar nombres/DNI/correos “para probar” frente al jurado.

### ¿Tiempo de respuesta?

Meta ≤30 s end-to-end (C3+C4+C5+C7). En práctica suele ser pocos segundos si embeddings/API responden.

---

## 8. Respuestas de una frase (cheat sheet)

| Tema | Frase |
| :--- | :--- |
| Problema | Recurrencia alta: se reinvestiga lo ya resuelto. |
| Solución | Asistencia + KEDB generada + validación experta que vuelve a RAG. |
| Decisión | El humano decide; el sistema recomienda. |
| Clasificar | Embeddings + kNN en Chroma (train). |
| Priorizar | Fórmula ADR-07 con pesos de negocio. |
| Recuperar | Similitud coseno tickets + KEDB validados → Top-5. |
| KEDB | HDBSCAN agrupa; LLM sintetiza; experto publica. |
| Orquestar | LangGraph, eventos por nodo. |
| F1 | Calidad de categoría; meta ≥0.80. |
| Recall@5 demo | Proxy por mismo ID; no confundir con Recall semántico de tesis. |
| Demo Kyocera | Mejor clúster (aptitud Alta, ~142 fuentes). |
| Límites | Export GLPI, top-9, sin cierre automático, métricas completas en curso. |

---

## 9. Actitud ante el jurado

1. **Separa** meta de tesis / PRD vs. evidencia de esta build.
2. **Nombra el ADR** cuando justifiques una tecnología (demuestra diseño, no moda).
3. Si no sabes un hiperparámetro, vuelve al **criterio de aceptación** (F1, Recall, PII=0, ≤30 s).
4. Nunca digas que el sistema “ya redujo 50% el tiempo” sin estudio; di “es la meta de valor del canvas”.
5. El hilo conductor siempre: **ciclo cerrado asistencia ↔ KEDB** frente a recurrencia.
