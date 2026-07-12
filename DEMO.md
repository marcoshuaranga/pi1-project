# Guion de Demo — Plataforma Multi-Agente RAG + KEDB

> Uso: leer en voz alta o como teleprompter. Checklist técnica: [`docs/DEMO_RUNBOOK.md`](docs/DEMO_RUNBOOK.md).  
> Preguntas difíciles (negocio, stack, validación): [`docs/DEMO_QA.md`](docs/DEMO_QA.md).  
> Datos: categoría **Impresora Multifuncional** (aptitud KEDB Alta), clúster Kyocera ~142 tickets.  
> Duración objetivo: **12–15 min** (+ 5 min preguntas).

---

## Antes de abrir la sala (30 s)

| Check | Criterio |
| :--- | :--- |
| http://localhost:3000 | Operador carga |
| http://localhost:3000/experto | Exactamente **1** borrador Kyocera (TaskAlfa 7003i) |
| Badge trazabilidad | ~142 tickets fuente |
| No tocar | «Generar borradores» / `POST /kedb/generate` |

Si falla el pendiente: `curl -X POST http://localhost:8000/kedb/seed-demo`

---

## Apertura (1 min)

**Decir:**

> Hoy vamos a ver el ciclo cerrado que ataca la recurrencia de la Mesa: el operador pega un ticket y en segundos recibe categoría, prioridad y soluciones ya aplicadas; el sistema ya consolidó ese conocimiento en un artículo KEDB; y el experto lo valida con un clic para que vuelva a estar disponible en la siguiente búsqueda.

**Mostrar:** pantalla Operador abierta, campo de ticket vacío.

---

## Escena 1 — Asistencia en vivo (4–5 min)

### Caso principal (obligatorio)

**Pegar exactamente:**

```
Impresora Kyocera 7003 no imprime, necesito que la configuren de nuevo
```

**Clic:** Enviar ticket.

**Mientras corre el pipeline, decir:**

> El texto es coloquial, como lo escribiría un usuario. No es un título histórico copiado: es una variante nueva. El orquestador clasifica, prioriza y busca soluciones similares en el histórico.

**Señalar en pantalla (en este orden):**

1. Steps del pipeline (Clasificador → Priorizador → RAG)
2. **Categoría** esperada: Impresora Multifuncional (o la ruta completa `Equipos Informáticos > … > Impresora Multifuncional`)
3. **Confianza** alta (típicamente >80 %)
4. **Prioridad** Media (sin señales de urgencia institucional)
5. **Top-5** con similitud %; al menos una solución del tipo:
   - *«Se configuró impresora predeterminada y se validó con impresión de hoja de prueba…»*
   - o instalación de driver Kyocera

**Decir (argumento central):**

> Este patrón se repitió más de cien veces en el histórico. El operador ya no tiene que reinvestigar en GLPI: en segundos tiene la solución que ya funcionó.

### Casos de respaldo (si piden variedad o falla Kyocera)

Usar **uno** solo; no saturar.

| # | Texto a pegar | Dominio esperado | Para qué sirve |
| :--- | :--- | :--- | :--- |
| B1 | `Sin acceso a escritorio remoto` | VPN / GlobalProtect | Otro dominio del top-9 |
| B2 | `Problemas de conexión remota vía VPN` | VPN | Variante del mismo dominio |
| B3 | `La Kyocera TaskAlfa no imprime hojas de prueba desde mi PC` | Impresora Multifuncional | Refuerzo semántico (no literal) |

**No pegar en vivo** (riesgo PII o match trivial):

- Títulos literales del Excel crudo sin revisar
- Nombres, correos, DNI o IPs inventados “para probar anonimización” frente al cliente

---

## Escena 2 — Conocimiento generado (3 min)

**Navegar a:** http://localhost:3000/experto

**Decir:**

> Esto no se generó ahora. Antes de la sesión el sistema agrupó ~142 tickets del mismo problema Kyocera y sintetizó un borrador. La bandeja de pendientes es la alerta al experto: hay conocimiento esperando validación humana.

**Abrir** el artículo único pendiente.

**Señalar:**

| Campo | Qué decir |
| :--- | :--- |
| Título | Configuración de impresora Kyocera TaskAlfa 7003i |
| Síntoma / causa / solución | El conocimiento consolidado (pasos: driver → predeterminada → hoja de prueba) |
| Tickets fuente (HU09) | Badge ~142 — trazabilidad N:1; el artículo no es inventado |
| Estado | `borrador` — aún no publicado a todos los operadores |

**Opcional (30 s, si hay tiempo):** Editar una palabra del título → Guardar → mostrar que sigue en borrador.

**Decir (argumento central):**

> El conocimiento se escribió a partir de casos reales. El experto no redacta desde cero: revisa y decide.

---

## Escena 3 — Cierre del ciclo (3–4 min)

### Paso A — Aprobar

**Clic:** Aprobar.

**Decir:**

> Con este clic el artículo pasa a validado y se indexa en el buscador de soluciones. A partir de ahora alimenta al mismo Agente RAG que vieron en la Escena 1.

### Paso B — Probar que volvió a RAG (obligatorio para cerrar el ciclo)

Volver a **Operador**. Pegar una variante distinta del caso Kyocera (no la misma frase exacta de la Escena 1):

```
Necesito configurar la impresora Kyocera 7003, no sale impresión de prueba
```

**Señalar en el Top-5:** un hit con tipo **`kedb`** (artículo validado), no solo tickets históricos.

**Decir (cierre):**

> Ese es el ciclo cerrado: asistencia → conocimiento consolidado → validación experta → de vuelta a la siguiente atención. Cada resolución puede acelerar la siguiente.

---

## Escenarios de reserva (si preguntan «¿y con otro tipo de ticket?»)

No forman parte del camino dorado. Úsalos **solo si te retan** o quieren ver otro dominio.  
Máximo **1–2** en la sesión. Pegar → Enviar → señalar categoría + Top-5 → volver al ciclo Kyocera.

### A. Variedad de dominio (top-9)

| ID | Pregunta del cliente | Texto a pegar | Categoría esperada | Qué señalar |
| :--- | :--- | :--- | :--- | :--- |
| R1 | ¿Solo funciona con impresoras? | `Sin acceso a escritorio remoto` | VPN > No accede (GlobalProtect) | Otro dominio; solución típica: credenciales / cliente VPN |
| R2 | ¿VPN también? | `Problemas de conexión remota vía VPN` | VPN | Variante; mismo mensaje que R1 |
| R3 | ¿Correo? | `No puedo enviar ni recibir correos, me sale que el buzón está lleno` | Correo > Buzón lleno | Aptitud Media; soluciones de limpieza/archivo de buzón |
| R4 | ¿Equipos / PC? | `La PC no enciende, se queda en pantalla negra al arrancar` | Equipos de Escritorio > CPU | Hardware; Top-5 puede ser más disperso que Kyocera |
| R5 | ¿Aplicaciones internas? | `No puedo ingresar al STD, me sale error al iniciar sesión` | Aplicaciones MTC > STD | Alto volumen en el histórico; clasificador debería acertar |
| R6 | ¿Cuentas de usuario? | `Necesito el alta de una cuenta de usuario nueva para un personal` | Cuenta de usuario > Alta | **Advertencia:** aptitud KEDB Baja (pocas soluciones ricas); el Top-5 puede ser débil — úsalo solo para clasificación, no para “wow” de RAG |

### B. Variantes Kyocera (si piden otra redacción del mismo caso)

| ID | Texto a pegar | Para qué |
| :--- | :--- | :--- |
| K1 | `Impresora Kyocera 7003 no imprime, necesito que la configuren de nuevo` | Principal Escena 1 |
| K2 | `Necesito configurar la impresora Kyocera 7003, no sale impresión de prueba` | Escena 3 (hit `kedb`) |
| K3 | `La Kyocera TaskAlfa no imprime hojas de prueba desde mi PC` | Misma familia, otra phrasing |
| K4 | `No imprime en la multifuncional Kyocera, faltaría instalar el driver` | Empuja recuperación hacia soluciones de driver |

### C. Preguntas de producto / proceso (sin pegar ticket)

| Si preguntan… | Respuesta corta |
| :--- | :--- |
| ¿Y si la categoría está mal? | En el MVP el operador ve la sugerencia + confianza. Corregir y guardar feedback es Fase 2 (HU03); hoy la decisión final sigue siendo del operador. |
| ¿Por qué prioridad Media? | El score combina impacto, recurrencia, SLA, criticidad y tipo. Este caso no dispara urgencia institucional → Media, coherente con el histórico. |
| ¿El sistema cierra el ticket solo? | No. Solo recomienda. Cierre y resolución los hace el operador (regla de negocio). |
| ¿Por qué no generan el artículo ahora? | Clustering + síntesis LLM se corren de antemano sobre un clúster curado (~142 Kyocera) para no depender de una corrida improvisada. |
| ¿Y si el experto rechaza? | Pasa a `obsoleto`; no se indexa en RAG. Pueden mostrar Rechazar solo si ya aprobaron en un ensayo previo y re-sembraron. |
| ¿Anonimizan? | Sí, C1 (regex + NER). En demo usamos textos sin PII. El Excel crudo no se abre frente al cliente. |
| ¿Conecta con GLPI en vivo? | No en este MVP: trabaja sobre export histórico. Integración productiva queda fuera de alcance. |
| ¿Cuántas categorías cubre? | Las 9 de mayor volumen (~50% del total). El resto está fuera del MVP. |
| ¿Sirve para cuentas de usuario igual de bien? | Clasifica; recuperar soluciones es más débil porque esa categoría tiene pocas soluciones documentadas (aptitud Baja). Por eso la demo principal es Impresora Multifuncional (Alta). |

### D. Si algo falla en vivo

| Síntoma | Qué hacer / decir |
| :--- | :--- |
| Top-5 vacío o irrelevante | Pegar **K3** o **R1**. Si sigue mal: “el índice vectorial necesita re-pipeline; el flujo de UI ya lo vieron”. |
| Categoría incorrecta | Mostrar confianza; decir que el operador decide. Opcional: probar **R5** (STD) o **R3** (buzón), suelen ser claros. |
| No hay pendiente en Experto | Fuera de cámara: `POST /kedb/seed-demo`. Decir: “reponemos el borrador de demo”. |
| WS no anima steps | La UI cae a REST; el resultado llega igual — no parar la demo. |
| Piden métricas | Ver sección siguiente; no abrir Dashboard Fase 2. |

---

## Si preguntan por números (solo bajo demanda)

No proyectar métricas salvo que pregunten.

| Pregunta típica | Respuesta corta |
| :--- | :--- |
| ¿Qué tan bien clasifica? | F1 macro sobre muestra de evaluación; meta del PRD ≥ 0.80. Cifra actual: `GET /metrics/evaluacion`. |
| ¿Recall@5 bajo? | En esta build es métrica simplificada (hit por mismo `ticket_id`). La demo se juzga por relevancia de las soluciones mostradas, no por esa cifra sola. |
| ¿Cuánto tarda? | Meta ≤ 30 s; en práctica suele ser pocos segundos. |
| ¿Por qué no generan KEDB en vivo? | Clustering + LLM se corren de antemano sobre un clúster curado para no depender de una corrida improvisada frente a ustedes. |

---

## Orden de los ejemplos (cheat sheet)

**Camino dorado (siempre):**

| Momento | Texto | Pantalla |
| :--- | :--- | :--- |
| Escena 1 | `Impresora Kyocera 7003 no imprime, necesito que la configuren de nuevo` | Operador |
| Escena 2 | *(ninguno — abrir artículo pendiente)* | Experto |
| Escena 3A | *(clic Aprobar)* | Experto |
| Escena 3B | `Necesito configurar la impresora Kyocera 7003, no sale impresión de prueba` | Operador |

**Si retan (elige 1):**

| Prioridad | Texto | Dominio |
| :--- | :--- | :--- |
| 1º | `Sin acceso a escritorio remoto` | VPN |
| 2º | `No puedo enviar ni recibir correos, me sale que el buzón está lleno` | Correo |
| 3º | `No puedo ingresar al STD, me sale error al iniciar sesión` | STD |

---

## Qué no hacer en vivo

1. No ejecutar «Generar borradores» / `POST /kedb/generate`.
2. No abrir el Excel crudo (`Tickets_Consolidados.xlsx`) en pantalla.
3. No improvisar tickets con datos personales.
4. No abrir el tablero del coordinador ni búsqueda libre KEDB (Fase 2; fuera del camino dorado).
5. No insistir con más de un ticket de respaldo: uno basta para variedad.

---

## Por qué este guion

- **Mismo dominio (Kyocera) en las 3 escenas** → el cliente ve un ciclo, no tres features sueltas.
- **Texto no literal del histórico** → clasificación y RAG genuinos, no match exacto.
- **KEDB como prework** → resultado estable; la validación experta sí es en vivo (el clic que cierra el ciclo).
