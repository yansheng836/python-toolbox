---
title: Keep PDF output modes inside the existing architecture component
author: Yansheng836
date: 2026-11-10
branch: main
cost: { minutes: 13, tokens: 1413799 }
id: l-558a5a45
scope: repo
status: active
src: agent
touches:
  - ".superpowers/brainstorm/1849-1794277608/content/update-scope.html"
  - ".superpowers/brainstorm/1849-1794277608/content/waiting.html"
  - plugins/image_to_pdf.py
  - ".archify/architecture-python-toolbox-20261024-224144/candidate.json"
  - CLAUDE.md
---

## Decided
- Keep the Python Toolbox architecture diagram at its existing component-and-connection level. For the image-to-PDF change, refresh the pinned revision and source references and describe merged versus per-image PDF output in the existing plugin explanation rather than adding nodes or edges.

## Tried and ruled out
- Keeping the diagram unchanged would leave its repository revision and source evidence stale.
- Expanding the graph with output-mode nodes or connections would overstate a plugin-internal behavior as a change to the application architecture.

## Watch out
- The feature is in plugins/image_to_pdf.py; retain this as an annotation on the existing image/PDF processing component when updating the Archify candidate.
