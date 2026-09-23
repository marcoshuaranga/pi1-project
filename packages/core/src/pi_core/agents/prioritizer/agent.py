"""C4 — Prioritizer (ADR-07 scoring formula)."""

import re

from pi_core.constants import PRIORIDADES


class PrioritizerAgent:
    WEIGHTS = {
        "impacto_servicio_ciudadano": 0.30,
        "recurrencia_historica": 0.20,
        "sla_asociado": 0.25,
        "criticidad_solicitante": 0.15,
        "tipo_incidencia": 0.10,
    }

    def prioritize(self, texto: str, categoria: str, context: dict | None = None) -> dict:
        context = context or {}
        t = texto.lower()

        impacto = self._score_impacto(t, categoria)
        recurrencia = context.get("recurrencia", self._score_recurrencia(t, categoria))
        sla = self._score_sla(t, categoria)
        criticidad = context.get("criticidad", 0.3)
        tipo = self._score_tipo(t)

        factors = {
            "impacto_servicio_ciudadano": impacto,
            "recurrencia_historica": recurrencia,
            "sla_asociado": sla,
            "criticidad_solicitante": criticidad,
            "tipo_incidencia": tipo,
        }
        score = sum(factors[k] * self.WEIGHTS[k] for k in self.WEIGHTS)
        prioridad = self._score_to_prioridad(score)

        return {
            "prioridad": prioridad,
            "score": round(score, 3),
            "justificacion": {k: round(v, 3) for k, v in factors.items()},
        }

    def _score_impacto(self, t: str, categoria: str) -> float:
        high = ("caído", "caido", "masivo", "todos", "ciudadano", "portal", "público", "publico")
        if any(w in t for w in high):
            return 0.9
        if "vpn" in categoria.lower() or "correo" in categoria.lower():
            return 0.6
        return 0.35

    def _score_recurrencia(self, t: str, categoria: str) -> float:
        if "impresora" in categoria.lower() or "kyocera" in t:
            return 0.85
        if "vpn" in t or "vpn" in categoria.lower():
            return 0.7
        return 0.4

    def _score_sla(self, t: str, categoria: str) -> float:
        urgent = ("urgente", "crítico", "critico", "inmediato", "no puedo trabajar")
        if any(w in t for w in urgent):
            return 0.85
        if "no imprime" in t or "sin acceso" in t:
            return 0.55
        return 0.4

    def _score_tipo(self, t: str) -> float:
        if re.search(r"\b(solicitud|habilitación|habilitacion|alta)\b", t):
            return 0.35
        if re.search(r"\b(incidencia|falla|error|no funciona)\b", t):
            return 0.65
        return 0.5

    def _score_to_prioridad(self, score: float) -> str:
        if score >= 0.75:
            return PRIORIDADES[3]
        if score >= 0.55:
            return PRIORIDADES[2]
        if score >= 0.35:
            return PRIORIDADES[1]
        return PRIORIDADES[0]
