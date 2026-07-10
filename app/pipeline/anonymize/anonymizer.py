"""C1 — Anonymization pipeline (regex + spaCy NER)."""

import re
from dataclasses import dataclass, field

import spacy

# MTC public entities — do not anonymize
MTC_ENTITIES = {
    "mtc",
    "ministerio de transportes y comunicaciones",
    "oitsi",
    "glpi",
    "globalprotect",
    "kyocera",
    "taskalfa",
}

PII_PATTERNS: list[tuple[str, str]] = [
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[CORREO]"),
    (r"\b\d{8}\b", "[DNI]"),
    (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[IP]"),
    (r"\b(?:\+?51\s?)?(?:9\d{2}|\d{2})\s?\d{3}\s?\d{4}\b", "[TELEFONO]"),
    (r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{3}\b", "[TELEFONO]"),
]


@dataclass
class AnonymizationResult:
    text: str
    replacements: list[dict[str, str]] = field(default_factory=list)


class Anonymizer:
    def __init__(self):
        try:
            self.nlp = spacy.load("es_core_news_lg")
        except OSError:
            self.nlp = None

    def _is_mtc_entity(self, text: str) -> bool:
        return text.lower().strip() in MTC_ENTITIES

    def anonymize(self, text: str) -> AnonymizationResult:
        if not text:
            return AnonymizationResult(text="")
        result = text
        replacements: list[dict[str, str]] = []

        for pattern, token in PII_PATTERNS:
            for match in re.finditer(pattern, result):
                replacements.append({"original": match.group(), "token": token, "type": "regex"})
            result = re.sub(pattern, token, result)

        if self.nlp:
            doc = self.nlp(result)
            spans = []
            for ent in doc.ents:
                if ent.label_ == "PER" and not self._is_mtc_entity(ent.text):
                    spans.append((ent.start_char, ent.end_char, "[NOMBRE]"))
            for start, end, token in sorted(spans, reverse=True):
                original = result[start:end]
                replacements.append({"original": original, "token": token, "type": "ner"})
                result = result[:start] + token + result[end:]

        return AnonymizationResult(text=result, replacements=replacements)
