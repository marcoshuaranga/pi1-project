# Fixed business-weighted formula for priority scoring

_Also referenced elsewhere in this repo as **ADR-07**._

The Priorizador computes a ticket's priority score as a fixed, business-defined weighted formula:

```
score = 0.30 * impacto_servicio_ciudadano
      + 0.20 * recurrencia_historica
      + 0.25 * SLA_asociado
      + 0.15 * criticidad_solicitante
      + 0.10 * tipo_incidencia
```

instead of asking an LLM to judge priority directly. The weights are a business criterion, not a model output — an operator can inspect the factor-by-factor breakdown (`justificacion_prioridad`) and audit why a ticket got its priority, which "the LLM said High" cannot offer. Business goal: no single priority class should absorb more than 70% of tickets (vs. 95.9% in the current historical baseline).

## Consequences

The five factors are currently estimated with text/category heuristics rather than real GLPI signals (actual SLA data, area, quantitative historical recurrence). That's a known simplification to enrich later with real signals — it doesn't change the fixed-formula, non-LLM approach this ADR commits to.
