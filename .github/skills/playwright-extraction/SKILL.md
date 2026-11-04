---
name: playwright-extraction
description: Implement policy-controlled Playwright extraction with isolated browser lifecycle and typed evidence.
---

# Playwright Extraction

1. Verify source allowlist and destination policy before browser launch.
2. Create isolated contexts, fixed timeouts, locale/timezone, and source-specific limits.
3. Capture status, content type, bytes, artifact hash, browser/parser version, and run identity.
4. Use stable semantic selectors/APIs before fragile layout selectors.
5. Detect challenge/CAPTCHA outcomes; never bypass them.
6. Close contexts/pages/processes and clean downloads or screenshots by retention policy.
7. Return typed evidence plus parser errors, with no live-source assumptions in tests.
