# Regex + spaCy NER anonymization pipeline

_Also referenced elsewhere in this repo as **ADR-08**._

Raw ticket text contains PII (names, emails, 8-digit DNI numbers, phone numbers, IPs) and must be anonymized before any data enters the rest of the pipeline, to comply with Peru's Ley 29733 (data protection law). We combine regex (for structured patterns: emails, DNI, IPs, phone numbers) with spaCy NER (`es_core_news_lg`, for proper names) plus an MTC institution dictionary so public-entity names are excluded from anonymization — replacing matches with tokens (`[NOMBRE]`, `[CORREO]`, `[DNI]`, `[IP]`, `[TELEFONO]`).

Regex alone misses names; NER alone misses structured identifiers. Combining both is what makes the acceptance criterion achievable: zero residual PII on a 500-ticket sample. This step is a hard precondition — no agent operates on ticket data that hasn't passed anonymization first.
