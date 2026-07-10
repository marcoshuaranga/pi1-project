# Guion de Demo — Plataforma Multi-Agente RAG + KEDB

> Complementa `PRD.md` §2.4 y §10.1-10.2. Este documento detalla, escena por escena, qué se muestra al patrocinador (OITSI-MTC), con datos reales curados de `artifacts/Tickets_Consolidados.xlsx` (categoría "Impresora Multifuncional", la única de las 9 categorías top con aptitud KEDB **Alta**; clúster real de 142 tickets "Configuración de impresora Kyocera 7003"). Los nombres de solicitante/técnico del archivo original **no se usan** en ningún ejemplo, en línea con el requisito de anonimización (C1) del proyecto.

---

## Resumen de la ruta

| Escena | Qué ve el cliente | En vivo / prework |
| :--- | :--- | :--- |
| 1. Asistencia | Ticket nuevo → categoría + prioridad + Top-5 soluciones en segundos | En vivo |
| 2. Conocimiento generado | Artículo KEDB con trazabilidad a los tickets fuente | Prework, mostrado como resultado |
| 3. Cierre del ciclo | El experto aprueba el artículo con un clic | En vivo |

---

## Escena 1 — Asistencia en vivo

El operador escribe un ticket nuevo, en sus propias palabras, sin copiar literalmente ninguno de los 142 títulos históricos:

> *"Impresora Kyocera 7003 no imprime, necesito que la configuren de nuevo"*

Esto entra por `POST /tickets` y atraviesa el pipeline:

1. **C1 (Anonimización):** revisa el texto en busca de PII (nombres, correos, IPs). En este caso no hay nada que reemplazar — pasa limpio.
2. **C7 (Orquestador) → C3 (Clasificador):** el texto menciona "impresora" y "Kyocera 7003", vocabulario que aparece en miles de tickets de la categoría `Equipos Informáticos > Equipo de impresión y escaneo > Impresora Multifuncional`. El clasificador debería asignar esa categoría con confianza alta (p. ej. 90%+), precisamente porque es una de las 9 categorías de entrenamiento y tiene el mayor volumen de ejemplos "ricos" (52.8% con solución ≥80 caracteres) para aprender el patrón.
3. **C4 (Priorizador):** como es un "no imprime" sin señales de urgencia institucional (no es un caso de alto impacto ciudadano ni SLA crítico), el score sale bajo-medio → prioridad **Media**, coherente con que el histórico real muestra que casi todos los tickets de esta categoría fueron priorizados como Media.
4. **C5 (Agente RAG):** busca por similitud semántica en ChromaDB y encuentra, entre los vecinos más cercanos, varios de los 142 tickets "Configuración de impresora Kyocera 7003" — con score de similitud muy alto (0.90+), porque el vocabulario y el contexto coinciden casi textualmente.

Lo que ve el operador en pantalla (`POST /tickets` responde en ~2-5 s):

```json
{
  "categoria": "Equipos Informáticos > Impresora Multifuncional",
  "confianza": 0.93,
  "prioridad": "Media",
  "soluciones": [
    { "ticket_id": "96044", "score": 0.94,
      "solucion": "Se configuró impresora predeterminada y se validó con impresión de hoja de prueba correctamente. Atendido" },
    { "ticket_id": "95984", "score": 0.92, "solucion": "..." },
    { "ticket_id": "57910", "score": 0.88,
      "solucion": "Se apoyó con la instalación del driver de la impresora en la PC del MTC y ya puede imprimir con normalidad" }
  ]
}
```

**Argumento central:** el operador no tuvo que buscar en GLPI, preguntar a un compañero, ni reinvestigar — en segundos tiene la solución que ya funcionó 125 veces antes.

**Tickets de respaldo para variedad de dominio** (si se quiere mostrar más de una categoría en vivo): *"Sin acceso a escritorio remoto"* (VPN, ticket real 66487, solución: configuración de credenciales en GlobalProtect) o *"Problemas de conexión remota vía VPN"* (ticket 95813).

---

## Escena 2 — El artículo KEDB (mostrado como resultado, no generado en vivo)

Antes de la demo, se corre `POST /kedb/generate` sobre el clúster de 142 tickets (HDBSCAN los agrupa por similitud de embeddings; el LLM sintetiza). El resultado, ya aprobado y listo para mostrar, tiene esta forma (plantilla de `PRD.md` §5):

```markdown
# Configuración de impresora Kyocera TaskAlfa 7003i

## Síntoma
El usuario no puede imprimir o requiere configurar la impresora
multifuncional Kyocera 7003 en su equipo (driver no instalado o
impresora predeterminada mal configurada).

## Categoría
Equipos Informáticos > Impresora Multifuncional

## Causa probable
Impresora predeterminada no configurada correctamente en el equipo,
o driver de la Kyocera 7003 no instalado tras un cambio de equipo
o reinicio de credenciales.

## Solución
1. Instalar/verificar el driver de la impresora Kyocera 7003 en el equipo.
2. Configurar la impresora como predeterminada.
3. Validar con una hoja de prueba de impresión.

## Aplicable a
Impresoras Kyocera TaskAlfa 7003i en Sede Central y sedes desconcentradas.

## Trazabilidad
- Tickets fuente: 96044, 95984, 95645, 95439, 94922, 94595, 94571,
  77962, 77975, 74359 ... (142 en total)
- Última actualización: [fecha de generación]
- Estado: borrador
```

**Argumento central:** el conocimiento **se escribió solo**, a partir de 142 casos reales, sin que nadie del equipo redactara el artículo a mano.

---

## Escena 3 — Cierre del ciclo

El experto técnico abre este artículo en estado `borrador` (llegó a su bandeja porque `GET /kedb/pendientes` lo notificó, HU14), lo revisa en unos segundos porque ya reconoce el problema, y hace clic en "Aprobar" (`PATCH /kedb/articulos/{id}` → `estado: validado`).

**Por qué esto cierra el ciclo frente al cliente:** a partir de ese clic, la próxima vez que un operador reciba un ticket de Kyocera, el Agente RAG (C5) recupera este artículo KEDB ya validado —no solo tickets sueltos del histórico— porque `KEDB Storage` retroalimenta a C5. Es el momento en que se le puede decir al patrocinador: "esto que acaban de ver aprobar ya está disponible para todos los operadores".

---

## Por qué esta secuencia específica

- **Empezar por la Escena 1 y no por la KEDB es deliberado.** La KEDB es el diferenciador técnico, pero lo que un operador de Mesa de Ayuda entiende de inmediato es "le paso un ticket y me da la respuesta ya". Es el gancho.
- **Usar el mismo dominio (Kyocera/impresoras) en las tres escenas**, en vez de tres ejemplos desconectados, hace que el cliente vea la conexión causal: el ticket que se clasifica en la Escena 1 es del mismo tipo de problema que generó el artículo que se aprueba en la Escena 3. Refuerza que es un ciclo, no tres features sueltas.
- **Que la Escena 2 sea prework y no en vivo** no es solo por seguridad técnica (evitar que el LLM improvise mal frente al cliente): también evita que la demo dependa de HDBSCAN encontrando un buen clúster en tiempo real, cuando ya se sabe, con datos, cuál es el mejor clúster disponible.

---

## Cifras de respaldo (solo si el cliente pregunta por desempeño)

De `PRD.md` §9 y `chapter-3.md` Tabla 25: F1 macro ≥0.80, Recall@5 ≥0.85, cobertura KEDB ≥80% de recurrentes, ≥50 artículos trazables, calidad experta ≥4/5, reducción de ≥50% en tiempo de búsqueda, ninguna clase de prioridad sobre 70% (vs. 95.9% actual).

## Advertencia de anonimización

`artifacts/Tickets_Consolidados.xlsx` es el export **sin anonimizar**: las columnas `Solicitante - Solicitante`, `Asignada a - Técnico` y `Solicitante - Autor` contienen nombres reales. Los títulos y soluciones citados en este documento se revisaron y no contienen PII, pero cualquier ticket adicional que se extraiga de ese archivo para ampliar la demo debe pasar primero por C1 (o al menos por una revisión manual) antes de mostrarse en pantalla — nunca usar el archivo crudo directamente frente al cliente.
