# Scripts

## Documentation validation

```bash
python scripts/validate_docs.py
```

The validator uses only the Python standard library. It checks required documentation and section anchors, fenced Mermaid blocks, placeholders, duplicate headings, local Markdown links, ADR coverage, harness coverage, core entities, API/technology consistency, and phase ordering.

The optional Mermaid CLI check in CI runs only when a supported CLI is available.
