---
applyTo: "**/*.md"
---

# Documentation

- Keep docs repository-specific, concise, actionable, and linked to implementation contracts.
- Treat `00-project-constitution.md` as invariant, `01-product-requirements-document.md` as behavior, architecture/ADRs as boundaries, and domain/API docs as contracts.
- Preserve one terminology model: campaign, source policy, extraction run, evidence, company, contact, lead, and human review.
- Do not describe a live, automated, or production capability as implemented unless executable code and tests exist.
- Keep implementation-readiness status separate from authorization to scrape or process personal data.
- Preserve exact heading names when validation references them.
- Use Mermaid only for diagrams that clarify architecture, lifecycle, sequence, or workflow.
- Do not add placeholders or claimed legal conclusions.
- Update indexes and README links when adding a document.
- Run `python scripts/validate_docs.py` after documentation edits.
