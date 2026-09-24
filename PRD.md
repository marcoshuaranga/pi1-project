# PRD — Plataforma Multi-Agente RAG + KEDB (Mesa de Ayuda OITSI-MTC)

> **Naturaleza de este documento.** Este PRD es un artefacto de **ingeniería de construcción**, complementario a la tesis (`resources/chapter-3.md`, `resources/chapter-4.md`) pero no forma parte de ella. Se basa en la incepción ágil y la arquitectura ya aprobadas (Product Vision Board, Product Canvas, Historias de Usuario, arquitectura de 9 componentes, stack tecnológico y ADR-01 a ADR-08 de `knowledge/06-arquitectura-y-diseno.md`). Donde se propone un detalle de implementación que **no está en el material fuente** (endpoints REST concretos, payloads, estructura de carpetas, prompts de agente), se marca explícitamente como **[PROPUESTA DE INGENIERÍA]** — es una decisión de construcción libre de ajustar, no un dato de tesis que requiera trazabilidad académica.
>
> **Objetivo del documento.** Servir de especificación ejecutable para que agentes de codificación (p. ej. Claude Code) construyan el producto historia por historia, con criterios de aceptación verificables, contratos de datos explícitos y dependencias declaradas, sin necesidad de releer la tesis completa en cada tarea.

## Mapa del documento

- [1. Resumen ejecutivo](#1-resumen-ejecutivo)
- [2. Alcance](#2-alcance)
- [3. Usuarios](#3-usuarios-personas)
- [4. Referencias de arquitectura y diseño](#4-referencias-de-arquitectura-y-diseno)
- [5. Requisitos funcionales clave](#5-requisitos-funcionales-clave)
- [6. Criterios de éxito del MVP](#6-criterios-de-exito-del-mvp)
- [7. Historias principales](#7-historias-principales)
- [8. No alcance](#8-no-alcance)
- [9. Fuente de verdad](#9-fuente-de-verdad)

> Este documento está pensado como una especificación modular: cada sección es un bloque autónomo para lectura, pero todas comparten el mismo modelo de negocio y el mismo ciclo cerrado asistencia ↔ KEDB.

---

## 1. Resumen ejecutivo

Construir una plataforma multi-agente con RAG que, ante un ticket de la Mesa de Ayuda OITSI-MTC, lo clasifique, lo priorice y recupere soluciones similares ya aplicadas; y que, a partir de tickets resueltos, genere automáticamente artículos de una base de errores conocidos (KEDB) con trazabilidad N:1, validados por un experto. El ciclo cerrado **asistencia ↔ KEDB** es el diferenciador del producto: cada resolución retroalimenta la base que acelera las siguientes.

**Definición de "funcional con valor" (MVP):** un operador puede enviar un ticket de texto libre y recibir, en menos de 30 segundos, categoría + prioridad + Top-5 soluciones similares; y un experto puede revisar y aprobar artículos KEDB generados automáticamente a partir de tickets resueltos, quedando esos artículos disponibles para la siguiente búsqueda. Ese ciclo completo, de punta a punta, es el criterio de "listo" del MVP — no una demo parcial de un solo agente.

---

## 2. Alcance

### 2.1 Dentro de alcance (MVP funcional — Fase Core)

Corresponde al ciclo cerrado completo, ya validado en la incepción ágil y construido en Sprint 1 + Sprint 2 de la tesis (`chapter-4.md`):

| Bloque       | Componentes                                                   | Historias de usuario                    |
| :----------- | :------------------------------------------------------------ | :-------------------------------------- |
| Datos        | C1 Anonimización, C2 Ingesta/Normalización                    | HU13 (tarea técnica)                    |
| Asistencia   | C3 Clasificador, C4 Priorizador, C5 Agente RAG                | HU01, HU02 ✅, HU04, HU06, HU07 ✅      |
| Conocimiento | C6 Generador KEDB (agrupación + síntesis)                     | HU08a, HU08b, HU09 ✅, HU10, HU14       |
| Orquestación | C7 Orquestador (LangGraph, grafo secuencial hoy; conditional routing pendiente, ADR-0006) | tarea técnica (sustenta HU01/04/06/14)  |
| Interfaz     | C8 Interfaz del Operador (mínima)                             | soporte de HU01, HU04, HU06, HU10, HU14 |
| Evaluación   | C9 Framework de evaluación (métricas de respaldo, no en vivo) | soporte de F1/Recall@5                  |

> **Nota de construcción:** HU02, HU07 y HU09 se adelantaron al MVP (ya estaban en API/UI del camino dorado). Siguen listadas en §2.2 por trazabilidad del backlog original, marcadas como ✅ hechas.

### 2.2 Capacidades implementadas y backlog evolutivo

La siguiente tabla conserva la trazabilidad del backlog original, pero separa las
capacidades que ya existen en el código de las que todavía requieren trabajo de
producto. "Implementada" no significa que todas sus métricas objetivo estén
demostradas en producción:

| ID      | Título                      | Depende de  | Notas                                                                 |
| :------ | :-------------------------- | :---------- | :-------------------------------------------------------------------- |
| HU02 ✅ | Confianza de clasificación  | HU01        | Adelantada a MVP — hecha                                              |
| HU03    | Corrección de categoría     | HU01        | Implementada en API; UI/flujo completo requiere validación adicional  |
| HU05    | Justificación de prioridad  | HU04        | Implementada en la respuesta; desglose visible sigue siendo evolutivo |
| HU07 ✅ | Indicador de similitud      | HU06        | Adelantada a MVP — hecha                                              |
| HU09 ✅ | Trazabilidad del artículo   | HU08b       | Adelantada a MVP — hecha (Escena 2)                                   |
| HU11    | Utilidad del artículo       | HU06        | Implementada en API; medición de impacto es evolutiva                 |
| HU12    | Registro de nueva solución  | HU06        | Implementada en API; flujo operativo es evolutivo                     |
| HU15    | Tablero del coordinador     | HU01, HU08b | Implementado en `web/`; métricas requieren evidencia etiquetada       |
| HU16    | Búsqueda directa en la KEDB | HU06        | Implementada en API/UI                                                |
| HU17    | Gestión del ciclo de vida   | HU10        | Implementada en API/UI                                                |

Las capacidades marcadas como adelantadas (`HU02`, `HU07`, `HU09`) y las
capacidades implementadas en esta tabla forman parte del estado actual del
producto. El trabajo pendiente se gestiona mediante las especificaciones bajo
`specs/`, no mediante una interpretación implícita de "Fase 2".

### 2.3 Fuera de alcance (todo el producto, MVP y Fase 2)

Según `chapter-3.md` §3.1.9: cobertura limitada a las 9 categorías de mayor volumen (50% del total); sin gestión de accesos/gobernanza de usuarios; sin integración con Active Directory, correo o sistemas administrativos externos; sin interfaz móvil; sin analítica avanzada más allá del tablero del coordinador; sin conexión activa a una instancia GLPI en producción (el histórico se consume como export estático); sin soporte productivo post-entrega.

### 2.4 Ruta de demo (valor visible al cliente) **[PROPUESTA DE INGENIERÍA]**

El criterio de priorización dentro del MVP core no es solo "qué depende de qué", sino **qué se ve** cuando el patrocinador (OITSI-MTC) tiene la plataforma delante. La demo debe demostrar, en una sola sesión, que el ciclo cerrado asistencia ↔ KEDB funciona con datos reales, no que cada agente funciona por separado.

**Camino dorado (lo que se muestra en vivo, en este orden):**

1. El operador pega un ticket real (texto coloquial, de una sesión previa del histórico o escrito en el momento) → en segundos recibe categoría, prioridad y Top-5 soluciones similares. Este es el momento que ataca directamente el 82.6% de recurrencia — el argumento más convincente para el patrocinador.
2. Se abre un artículo KEDB ya generado (preprocesado antes de la demo, no en vivo) con su trazabilidad a los tickets fuente — evidencia de que el conocimiento "se escribe solo" a partir del histórico real.
3. El experto aprueba ese artículo con un clic frente al cliente — cierra el ciclo asistencia ↔ KEDB de forma visible.

**Qué se degrada o se saca de la ruta en vivo** (sigue existiendo en el backlog, pero no se ejecuta frente al cliente):

- La generación de KEDB (HU08a clustering + HU08b síntesis LLM) se corre de antemano sobre un clúster bien elegido, como _fixture_ de datos. No se ejecuta en vivo, para no depender de que el LLM produzca un buen borrador en el momento frente al cliente.
- El Framework de Evaluación completo (C9: golden set de 200, Kappa, estudio comparativo de tiempo) no se ejecuta en la demo; sus cifras (F1, Recall@5) se presentan como respaldo (slide o panel estático), no como una corrida en vivo.
- Las capacidades fuera de la ruta de demo pueden estar implementadas y seguir
  siendo prescindibles para la sesión; la demo no debe confundirse con una
  medición completa del producto.

**Etiquetas de historia para la demo**, usadas en la sección 8: 🎯 esencial en vivo · 🧱 prework (corrido antes, mostrado como resultado) · 📦 backlog visible, no crítico para la demo.

---

## 3. Usuarios (personas)

| Rol                                                | Uso del sistema                                                                     | Historias que le sirven              |
| :------------------------------------------------- | :---------------------------------------------------------------------------------- | :----------------------------------- |
| **Operador de Mesa de Ayuda** (primario)           | Envía tickets, consulta clasificación/prioridad/soluciones, corrige y retroalimenta | HU01-HU07, HU11, HU12, HU16          |
| **Experto técnico del MTC** (secundario)           | Valida, edita o rechaza artículos KEDB; recibe alertas de pendientes                | HU08a, HU08b, HU09, HU10, HU14, HU17 |
| **Jefe/Coordinador de Mesa de Ayuda** (secundario) | Consulta indicadores de cobertura, prioridad y recurrencia                          | HU15                                 |

Detalle de objetivos, frustraciones y motivaciones de cada perfil: `chapter-3.md` §3.1.2 (Tablas 21-23).

---

## 4. Referencias de arquitectura y diseño

Este PRD define el producto y su alcance funcional. Los detalles de implementación, diseño técnico y operación se documentan en otras secciones del repositorio:

- [docs/product/README.md](docs/product/README.md): visión del producto, roles y flujo de valor.
- [docs/product/requirements.md](docs/product/requirements.md): alcance, problema de negocio y criterios del MVP.
- [docs/architecture/README.md](docs/architecture/README.md): arquitectura del sistema y vista general.
- [docs/architecture/overview.md](docs/architecture/overview.md): capas, flujo de ejecución y componentes.
- [docs/architecture/repo-map.md](docs/architecture/repo-map.md): estructura del repositorio y responsabilidades.
- [docs/operations/setup.md](docs/operations/setup.md): arranque, validación y troubleshooting.
- [docs/adr/README.md](docs/adr/README.md): decisiones y trade-offs técnicos.
- [demo/README.md](demo/README.md): narrativa y flujo de la demo.

> Este documento es la fuente de verdad para requisitos del producto. No sustituye la documentación técnica ni la operación.

---

## 5. Requisitos funcionales clave

### RF-1 — Asistencia al operador

El sistema debe clasificar y priorizar un ticket nuevo y devolver soluciones similares ya aplicadas en tickets o artículos KEDB validados.

### RF-2 — Ciclo cerrado KEDB

El sistema debe consolidar tickets resueltos en borradores de artículos KEDB con trazabilidad a los tickets fuente y permitir su aprobación por parte de un experto.

### RF-3 — Validación humana

La aprobación, edición o rechazo de un artículo KEDB debe ser una decisión humana. El sistema debe alimentar RAG solo con artículos validados.

### RF-4 — Métricas y monitoreo

Debe existir una capa mínima de evaluación de calidad para clasificación, recuperación y cobertura de conocimiento.

### RF-5 — Privacidad y cumplimiento

La anonimización de datos personales debe aplicarse antes de cualquier uso del histórico y no debe ser omitida.

---

## 6. Criterios de éxito del MVP

El MVP se considera funcional cuando se cumple el ciclo completo:

1. ticket nuevo → clasificado + priorizado + soluciones sugeridas
2. resolución del operador → material para KEDB
3. generación de borradores + trazabilidad N:1
4. validación humana + publicación a RAG
5. reutilización del artículo validado en un ticket futuro

### Métricas de referencia

Estos valores son **objetivos** (`objetivo`), no resultados medidos. Hoy la API
reporta Recall@5 como `proxy` (coincidencia del ticket fuente) y ninguna métrica
como `medido`; ver `specs/001-mvp-closed-assistance-kedb-loop/contracts/metrics.md`.

- F1 macro de clasificación: ≥ 0.80
- Recall@5: ≥ 0.85
- prioridad: evitar concentración excesiva en una sola clase
- KEDB: artículos trazables y calidad experta aceptable
- privacidad: PII residual = 0 en muestra controlada
- rendimiento: respuesta end-to-end dentro del umbral definido por el producto

---

## 7. Historias principales

Las historias de usuario siguen siendo las que definen el valor del producto, pero la especificación detallada ya no vive en este archivo:

- HU01: clasificación automática
- HU04: priorización
- HU06: recuperación de soluciones
- HU08a/HU08b: generación de KEDB
- HU10: validación experta
- HU14: alertas de KEDB pendiente

Su detalle operativo y de aceptación se mantiene en la documentación de producto y en la implementación asociada.

---

## 8. No alcance

- integración productiva en vivo con GLPI
- cobertura total del catálogo de incidencias
- gestión completa de usuarios y permisos
- soporte móvil o canales externos adicionales no definidos
- despliegue de producción sin validación adicional por parte de expertos y stakeholders

---

## 9. Fuente de verdad

Para evitar ambigüedad, la estructura de documentación queda así:

- [CONTEXT.md](CONTEXT.md): vocabulario del dominio
- [PRD.md](PRD.md): requisitos y alcance del producto
- [docs/product](docs/product): narrativa y flujo de valor del negocio
- [docs/architecture](docs/architecture): sistema, componentes y repositorio
- [docs/operations](docs/operations): setup y ejecución
- [docs/adr](docs/adr): decisiones técnicas
- [demo](demo): narrativa y guía de demostración

La intención de este PRD es ser un contrato de negocio claro, no un compendio de diseño técnico, implementación o operación.
