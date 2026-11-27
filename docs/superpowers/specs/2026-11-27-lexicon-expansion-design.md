# Lexicon Expansion Design (approved 2026-11-27)

**Intent:** multiply the useful term count of the EN↔AR skill pack without shipping
proprietary dictionaries or multi-gigabyte dumps into Git.

**Approaches considered:**
1. Commit Merriam-Webster / Oxford / Collins data - rejected: their terms forbid bulk
   redistribution; legally unsafe for a public repo.
2. Commit raw Wiktionary / WordNet dumps - rejected: kaikki raw data is 2.9 GB
   compressed (24.8 GB expanded); GitHub blocks files over 100 MiB.
3. **Chosen:** keep a curated, provenance-tagged `data/glossary.tbx` in Git, and add an
   opt-in downloader that fetches open data (Open English WordNet, Wiktionary Arabic),
   caches it outside Git, and extracts a compact JSONL into `data/dictionaries/` with a
   root `NOTICE` carrying attribution and license terms. CI rejects oversized files,
   proprietary dictionary names inside `data/`, and a missing NOTICE.

**Why:** this preserves the pack's key-free, portable, auditable contract while making
large lexicons available on demand rather than baked into the repository.

**Parts left to the builder:** exact upstream URLs, extraction heuristics and limits.
