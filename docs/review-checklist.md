# Documentation Review Checklist

**Document ID:** REVIEW-001  
**Status:** DRAFT  
**Linked:** All docs, [`PLAN.md`](../PLAN.md)

## 1. Cross-document consistency

- [ ] All locked decisions in PLAN.md preserved unchanged across all docs
- [ ] Stable identifiers (BR-, PR-, REQ-, US-, UC-, ADR-, AC-, TC-, THR-, SEC-) used consistently
- [ ] No requirement duplicated across files without linking to authoritative source
- [ ] Service boundaries match PLAN.md table exactly
- [ ] Event names match between `events.md`, `api-contracts.md`, `hld.md`, and `PLAN.md`
- [ ] Order state machine (pending → reserved → confirmed → cancelled) consistent everywhere
- [ ] DOA state extension (confirmed → doa_claimed → refunded/replacement_shipped) documented
- [ ] Payment success ≠ order confirmed rule stated consistently
- [ ] Aquarium domain terminology (livestock, water type, WYSIWYG, DOA) used consistently

## 2. Completeness checks

- [ ] All 17 required documents created
- [ ] Each document has a stable ID and status
- [ ] All user stories have acceptance criteria
- [ ] All acceptance criteria map to at least one test case
- [ ] All threats have mitigations
- [ ] All open questions marked with `(OPEN)` and impact described
- [ ] All assumptions marked as assumptions
- [ ] Mermaid diagrams match written architecture (HLD diagram matches service table)

## 3. Quality checks

- [ ] Measurable acceptance criteria wherever possible
- [ ] No invented business requirements, compliance obligations, or deployment capabilities
- [ ] No unsupported production infrastructure claims
- [ ] Security requirements not weakened to work around missing tooling
- [ ] Ponytail principles applied (no over-engineering, YAGNI, stdlib-first)
- [ ] `.gitignore` excludes `.venv/`, `.env`, `*.db`, caches
- [ ] Aquarium domain features documented: livestock attributes, DOA guarantee, water types, compatibility

## 4. PLAN.md linkage

- [ ] PLAN.md remains the implementation execution tracker
- [ ] PLAN.md task list (12 items) referenced from relevant docs
- [ ] PLAN.md validation steps referenced from test strategy and operations
- [ ] PLAN.md issues & fixes section updated with all implementation learnings

## 5. Review outcome

| Reviewer | Date | Result | Notes |
|---|---|---|---|
| | | | |

## 6. Open items carried forward

| Item | Doc | Impact |
|---|---|---|
| DOA claim window: 3 days or 7 days? | security.md, traceability.md, srs.md | DOA claim validation logic deferred |
| Storefront implementation (React) | PLAN.md task 8 | UI not yet built |
| Production monitoring/alerting | operations.md | Not in MVP scope |
