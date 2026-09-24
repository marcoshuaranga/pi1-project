# Product requirements

## 1. Problem statement

The help desk faces recurring incidents that are repeatedly solved in a fragmented way. Historical information is spread across tickets and resolutions, so operators spend time redoing work that was already done before.

## 2. Product goal

Build a platform that:

- classifies and prioritizes incoming tickets
- retrieves similar past solutions
- consolidates recurring resolved tickets into a KEDB
- validates that knowledge through a human expert before it is reused

## 3. Core value loop

The product’s differentiator is the closed loop:

1. new ticket arrives
2. system classifies and prioritizes it
3. system retrieves similar known solutions
4. resolved tickets are clustered into KEDB drafts
5. an expert approves or rejects the article
6. validated knowledge feeds future ticket assistance

## 4. Scope

### In scope

- ticket intake and classification
- priority scoring using auditable business rules
- retrieval of top similar historical tickets and KEDB articles
- KEDB generation from resolved ticket clusters
- human review and publication flow
- evaluation and quality tracking

### Out of scope for the MVP

- live GLPI integration in production
- broad coverage beyond the top incident categories
- user governance or enterprise IAM
- full mobile or external-channel support beyond the defined flows

## 5. Success criteria

- classification quality meets the defined quality target
- priority distribution is more balanced than the current historical pattern
- the system can surface relevant solutions in the top-5 results
- expert review can approve KEDB articles that are then reused in RAG
- the end-to-end demo convincingly shows the closed assistance ↔ KEDB loop

## 6. Actors

- Operador de Mesa de Ayuda
- Experto KEDB
- Coordinador / stakeholder

## 7. Product relation to the rest of the repo

This document captures the business intent. For implementation detail, use:

- [../../CONTEXT.md](../../CONTEXT.md) for domain terminology
- [../../PRD.md](../../PRD.md) for full functional specification
- [../architecture/overview.md](../architecture/overview.md) for system design
- [../adr](../adr) for technical decisions
