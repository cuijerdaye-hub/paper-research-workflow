# Third-party design references

This repository contains an original Codex orchestration skill. It does not vendor third-party CNKI clients, browser scripts, credentials, selectors, downloaders, or repository files.

The workflow was informed by publicly visible capability descriptions from the following projects:

## ExquisiteCore/CNKI-search

- Repository: https://github.com/ExquisiteCore/CNKI-search
- License: MIT
- Relationship: optional external runtime that provides the `cnki` CLI. It is not included in this repository.

## cookjohn/cnki-skills

- Repository: https://github.com/cookjohn/cnki-skills
- Repository README states MIT; the reviewed source archive did not contain a standalone LICENSE file.
- Relationship: browser task categories were reviewed, but no implementation code is included here.

## LongMarching/cnki-search-skill

- Repository: https://github.com/LongMarching/cnki-search-skill
- License status: the repository states that no open-source license has been added and all rights are reserved.
- Relationship: workspace and structured-state concepts were reviewed; no code or files were copied.

## hansel6666666/cnki-trawl-pick-skill

- Repository: https://github.com/hansel6666666/cnki-trawl-pick-skill
- License status: personal learning/evaluation is allowed by default; modification, redistribution, or use in another published project requires prior permission.
- Relationship: general safety concepts such as screening before download and stopping on guarded states were reviewed; no code, selectors, bridge implementation, or files were copied.

Users must comply with CNKI terms, institutional access rules, copyright law, and the licenses of every optional dependency they install separately.
