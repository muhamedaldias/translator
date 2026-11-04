# Authoritative English Language References for Translation Agents & Skills

**Project:** `/data/workspace/projects/translator`
**Report file:** `research/dictionaries_references.md`
**Prepared:** 2026-11-04
**Scope:** English dictionaries, lexical databases, bilingual (EN-AR) dictionaries, thesauri, corpora, style guides, programmatic APIs/datasets, and translation-theory books relevant to powering agent-based translation skills.

---

## Executive Summary

This report surveys authoritative English-language references that can be integrated as "skills" (programmable data sources or APIs) into coding/translation agents. The findings are organized into seven categories:

1. Public-domain English dictionaries & lexical databases (WordNet, Wiktionary, Webster's 1913, Century Dictionary, OED access, Collins, Merriam-Webster API)
2. English-Arabic bilingual dictionaries (ALMAANY, Oxford Arabic Dictionary, Lane's Lexicon, Hans Wehr, public-domain Arabic-English lexicons)
3. Thesauri & synonym resources (WordNet, Thesaurus.com unofficial APIs, Roget's, Datamuse)
4. Corpora & EN-AR parallel corpora (UN Parallel Corpus, OpenSubtitles, TED talks, Quran parallel corpus, news corpora)
5. Style guides & translation references (Chicago Manual of Style, Oxford Style Guide, UNESCO guidelines, Arabic translation style guides)
6. Programmatically accessible APIs & datasets for "skill" integration
7. Book references on translation theory & practice (Newmark, Nida, Catford, Baker, Bassnett, etc.)

**Top integration recommendations (priority order):**

| Priority | Resource | Role | Access | License | Best for |
|----------|----------|------|--------|---------|----------|
| P1 | Open English Wordnet / Princeton WordNet 3.1 | EN lexicon + synonym sets | GitHub download / local DB | CC-BY-4.0 (OEWN) / Princeton (free, attribution) | Word-sense disambiguation, synonym expansion, hypernymy |
| P1 | Wiktionary (EN + AR) | Bilingual & monolingual lexical data | XML dumps / API | CC-BY-SA 3.0 / GFDL | EN-AR headwords, translations, etymology |
| P1 | UN Parallel Corpus (ar-en) | High-quality EN-AR parallel text | OPUS / HF `Helsinki-NLP/un_pc` | UN (free, attribution, no warranty) | MT training, terminology extraction, formal register |
| P1 | OpenSubtitles (ar-en) | Colloquial/dialogue EN-AR pairs | OPUS | OPUS (attribution required) | Conversational register, subtitling |
| P1 | Merriam-Webster Collegiate API | Authoritative EN definitions | `dictionaryapi.com` | Free non-commercial, 1000 q/day/key, key required | EN sense definitions, audio, usage labels |
| P2 | ALMAANY (EN-AR) | Broad EN-AR bilingual coverage | Web (`almaany.com/en/dict/en-ar/`) | Proprietary (scraping discouraged; app/API not public) | EN-AR lookup (use with caution re: ToS) |
| P2 | Lane's Lexicon / Hans Wehr | Classical & MSA Arabic reference | Internet Archive / `lanelexicon.com` / `hanswehr.com` | Public domain (Lane, 1863-93) / CC-BY-SA (Alpheios digitization) | Classical Arabic, root-based lookup |
| P2 | Datamuse API | Free synonym/related-word API | `api.datamuse.com` | Free, no key | Lightweight synonym expansion |
| P2 | TED2020 / TED-Multilingual (ar-en) | Spoken-register EN-AR parallel | OPUS / GitHub | CC BY-NC-ND (mTEDx) / scientific-use (TED) | Spoken register, talks |
| P3 | UNESCO Style Manual (2004) | EN house style & Arabic transliteration | `unesdoc.unesco.org` | UNESCO (free) | Institutional translation style |
| P3 | AUSIT Arabic Style Guide | AR translation style | `ausit.org` PDF | Free | Community/public-service AR translation |
| P3 | Chicago Manual of Style / Oxford Style Guide | EN style reference | Subscription/print | Proprietary | Formal EN editing |

---

## 1. Public-Domain English Dictionaries & Lexical Databases

### 1.1 WordNet (Princeton University)

**Role:** Core English lexical database; organizes words into synonym sets (synsets) with semantic relations (hypernymy, hyponymy, meronymy, antonymy, entailment). Essential for word-sense disambiguation and synonym expansion in translation agents.

**Home:** https://wordnet.princeton.edu/

**Download:** https://wordnet.princeton.edu/download

**Versions:**
- WordNet 3.0 (Unix/Linux, Dec 2006)
- WordNet 3.1 (database files only; Dec 2006; usable with 3.0 application)
- WordNet 2.1 (Windows, Mar 2005)

**License:** Princeton WordNet License (free for research and commercial use; attribution required; name of Princeton may not be used in advertising). Full text at https://spdx.org/licenses/WordNet.html. No fee or royalty. "AS IS" disclaimer.

**Data format:** ASCII database files (8 files, two per POS: `index.pos` + `data.pos` for noun/verb/adj/adv). Documented in `wndb(5WN)`: https://wordnet.princeton.edu/documentation/wndb5wn. C API provided; bindings exist for Python (NLTK), Java, etc.

**Open English Wordnet (OEWN) — community-maintained fork:**
- Home: https://en-word.net/
- GitHub: https://github.com/globalwordnet/english-wordnet
- Downloads: https://en-word.net/downloads
- Latest: Open English Wordnet 2025 (2025-12-31) and 2025+ (with Open English Namenet proper nouns)
- Formats: WNDB (Princeton DB), WN-LMF XML (gzipped), RDF/Turtle (gzipped), JSON
- License: CC-BY 4.0 (OEWN 2023+); WordNet 3.1 portions remain under Princeton license (attribution required). See `WNDB_License.txt`: https://github.com/globalwordnet/english-wordnet/blob/main/WNDB_License.txt

**Agent-skill viability:** HIGH. Can be embedded locally as a read-only SQLite/LMF database; no network required; ideal for offline synonym/hypernym lookup.

### 1.2 Wiktionary (Wikimedia)

**Role:** Multilingual, collaboratively built dictionary; includes English headwords, definitions, translations (incl. EN-AR), etymology, pronunciation, inflection. Provides bilingual translation pairs usable as a seed EN-AR lexicon.

**Home:** https://www.wiktionary.org/

**Data dumps:** https://dumps.wikimedia.org/ (enwiktionary, arwiktionary)
- English: `enwiktionary-latest-pages-articles.xml.bz2`
- Arabic: `arwiktionary-latest-pages-articles.xml.bz2`

**API:** MediaWiki API — https://en.wiktionary.org/w/api.php (action=query, list=search, prop=revisions, etc.)

**License:** CC-BY-SA 3.0 (and GFDL for older content). Attribution + share-alike required.

**Format:** XML wikitext dumps; parse with mwparserfromhell or similar. Structured data also available via Wikidata (lexemes).

**Agent-skill viability:** HIGH (offline dump) / MEDIUM (live API, rate-limited). Good for EN-AR translation pairs and etymology; quality varies by entry.

### 1.3 Webster's 1913 Dictionary (Public Domain)

**Role:** Public-domain English dictionary (1913 edition). Useful as a no-cost lexical baseline and for historical/archaic senses. Not suitable for modern usage but free of licensing constraints.

**Source:** Project Gutenberg (e.g., various "Webster's Revised Unabridged Dictionary" etexts) and Internet Archive.
- Gutenberg catalog: https://www.gutenberg.org/ (search "Webster's 1913")
- Internet Archive: https://archive.org/ (search "Webster's 1913 dictionary")

**License:** Public domain (US, pre-1930 publication).

**Format:** Plain text / HTML etexts; various community conversions to XML/JSON exist on GitHub.

**Agent-skill viability:** MEDIUM. Good as a zero-cost fallback lexicon; outdated senses require disambiguation from modern sources.

### 1.4 Century Dictionary (Public Domain)

**Role:** The Century Dictionary (1889-1911), a large public-domain English dictionary with encyclopedic content. Good for historical and technical vocabulary.

**Source:** Internet Archive (scans), Gutenberg, various XML/TEI conversions.

**License:** Public domain.

**Agent-skill viability:** MEDIUM. Similar position to Webster's 1913.

### 1.5 Oxford English Dictionary (OED)

**Role:** The authoritative historical dictionary of English; records the development of words over time with dated quotations. Distinct from current-usage Oxford dictionaries.

**Home:** https://www.oed.com/

**Access:** Institutional subscription (libraries); individual subscription. Free institutional trial available.

**OED API / Researcher API:** OUP offers an OED Researcher API for academic researchers (contact via oed.com). Not the same as the Oxford Dictionaries API (current usage).

**License:** Proprietary (Oxford University Press). Commercial use requires license; API access is metered and paid.

**Agent-skill viability:** LOW for agent integration (no public free API; institutional access only). Useful as a human reference, not as an automated skill unless an institutional license is held.

### 1.6 Oxford Dictionaries API (Oxford Languages)

**Role:** Current-usage English dictionary data (Oxford Dictionary of English + New Oxford American Dictionary); definitions, pronunciations, synonyms, antonyms, example sentences, domains, registers.

**Home:** https://developer.oxforddictionaries.com/

**Endpoint pattern:** `https://od-api.oxforddictionaries.com/api/v2/words/{lang-code}/{word}` (e.g., `en-gb`)

**Authentication:** App ID + App Key headers.

**Plans:**
- Sandbox (free trial): 500 calls, limited to first letter of alphabet
- API Lite: £50/mo (£600/yr), 1,000 calls/mo, £0.05/call overage
- Growing: from £200/mo
- Enterprise: £415/mo, bespoke, allows caching/offline use

**License:** Proprietary. Non-commercial research license available (3 months, institutional affiliation required). Caching/offline storage only under Enterprise. API content must not be used to train AI tools (per T&C). Full terms: https://developer.oxforddictionaries.com/api-terms-and-conditions

**Note:** The FAQ explicitly prohibits using content with AI tools ("you will not ... use our materials in combination with any artificial intelligence (AI) tool"). This is a significant constraint for agent-based translation.

**Agent-skill viability:** MEDIUM (paid, metered, AI-use restrictions). Viable for non-AI reference lookup; restricted for agent/AI grounding under standard terms.

### 1.7 Collins Dictionary API

**Role:** Collins monolingual and bilingual dictionaries; definitions, translations, examples, phrases, audio pronunciations, thesaurus topics.

**Home:** https://www.collinsdictionary.com/us/collins-api
**Docs:** https://api.collinsdictionary.com/api/v1/documentation/html
**Endpoint pattern:** `https://api.collinsdictionary.com/api/v1/dictionaries/{dictCode}/entries/{entryId}` etc. (WADL/JSON)
**Apply for key:** https://blog.collinsdictionary.com/collins-api-apply-for-a-key/

**Pricing (English only):**
- Up to 5,000 calls/month: Free
- 5,001–20,000: £50/mo + VAT
- 20,001–75,000: £170/mo + VAT
- 75,001–175,000: £375/mo + VAT

**Bilingual/mixed:** Up to 5,000 free; 5,001–30,000: £75/mo; 30,001–100,000: £400/mo

**License:** Proprietary (HarperCollins). API key required per application. No offline caching/storage that bypasses API requests. Attribution required: "www.collinsdictionary.com © HarperCollins Publishers Ltd". CORS not enabled; proxy required for browser frontends.

**Agent-skill viability:** MEDIUM. Free tier usable for low-volume non-commercial skills; key application required; no caching allowed.

### 1.8 Merriam-Webster Dictionary API

**Role:** Merriam-Webster's Collegiate Dictionary (250,000+ definitions, 111,000 audio pronunciations, 3,500+ idioms), Collegiate Thesaurus, Spanish-English, Medical, Learner's, Elementary/Intermediate/School dictionaries. JSON.

**Home:** https://dictionaryapi.com/
**Products:** https://www.dictionaryapi.com/products/index
**Collegiate product:** https://www.dictionaryapi.com/products/api-collegiate-dictionary
**FAQ:** https://www.dictionaryapi.com/info/frequently-asked-questions
**Terms:** https://www.dictionaryapi.com/info/terms-of-service

**Endpoint pattern:** `https://www.dictionaryapi.com/api/v3/references/collegiate/json/{word}?key={api-key}`

**Authentication:** API key (query param `key`). Two keys issued on registration.

**Rate limits:** 1,000 queries per API key per day (non-commercial). Commercial use requires licensing fee (contact MW). Max two reference APIs per free key.

**License:** Proprietary. Non-commercial use free; commercial use licensed case-by-case. Logo/branding required. No automated/recorded queries beyond approved use; no derivative works of the software; no benchmarking against third parties.

**OpenAPI spec:** Not officially published; Jentic maintains an agent-ready OpenAPI spec: https://jentic.com/apis/merriam-webster.com/merriam-webster

**Agent-skill viability:** HIGH (free tier, JSON, simple key auth, 1000 q/day). Best authoritative EN dictionary API for non-commercial agents; must cache to stay within quota.

---

## 2. English-Arabic Bilingual Dictionaries (Data/APIs)

### 2.1 ALMAANY (Almaany)

**Role:** Popular English↔Arabic multilingual dictionary covering many domains (General, Medical, Legal, Quran, etc.). Widely used by Arabic learners.

**Home:** https://www.almaany.com/
**EN-AR search URL pattern:** `https://www.almaany.com/en/dict/en-ar/{word}` and `https://www.almaany.com/en/dict/ar-en/{word}`
**Appendix (browse by category):** https://www.almaany.com/appendix.php?category=All&lang_name=English&language=english
**Mobile apps:** Arabic-English / English-Arabic offline apps (Google Play, e.g. `com.almaany.aren`)

**License:** Proprietary. No official public API documented; access is via website/webview. Community NVDA addon uses `urllib2` requests with a User-Agent header: https://github.com/ibrahim-h/dictionariesAlmaany. A community database extract exists on FreeMdict (`almaanyEnAr-ArEn.zip`, ~4 MB) compiled from the Android app.

**Agent-skill viability:** LOW-MEDIUM. No official API; scraping may violate ToS. Use only if no better alternative; prefer Wiktionary or UN corpus for EN-AR lexical data.

### 2.2 Oxford Arabic Dictionary

**Role:** Oxford University Press's modern Arabic-English / English-Arabic dictionary; includes syntax and morphology information valuable for Arabic translation.

**Note:** Referenced in the LingQ forum thread as a valuable built-in iOS dictionary, but not available via the Oxford Dictionaries API for Arabic at time of research (Arabic dataset availability to confirm via Oxford Dictionaries Licensing, 35+ languages available to license).

**License:** Proprietary (OUP).

**Agent-skill viability:** LOW (licensing required; no confirmed public EN-AR API).

### 2.3 Lane's Lexicon (An Arabic-English Lexicon)

**Role:** The most comprehensive classical Arabic-English lexicon (E. W. Lane, 1863-1893, 8 volumes). Root-based arrangement; exhaustive meanings, derivatives, grammar notes, Quranic usage examples. Essential for classical and MSA Arabic translation.

**Home:** https://lanelexicon.com/
**Downloads:** https://lanelexicon.com/updates/
- Scanned PDFs (2024 KIC Bookeye scan, Washington University): ~2.49 GB
- 8-part PDF set (~58 MB total), CC-BY-SA 3.0 first page
- Complete scan: ~379.96 MB

**Text/digitization:**
- Perseus Digital Library (Tufts) original digitization
- Alpheios Project text version under proofreading (GitHub): https://github.com/alpheios-project/lan — CC-BY-SA 3.0 US
- Online search: https://www.hanswehr.com/ (includes Lane's Lexicon alongside Hans Wehr)

**License:** Public domain (original, 1863-93); Alpheios digitization CC-BY-SA 3.0 US.

**Agent-skill viability:** HIGH (public domain, root-based, classical/MSA). Large OCR/parse effort to convert to structured DB; best used as reference or after conversion.

### 2.4 Hans Wehr Dictionary of Modern Written Arabic

**Role:** The standard modern standard Arabic-English dictionary (Hans Wehr, ed. J. Milton Cowan, 1961/1976). Alphabetical by root; MSA focus; widely used by translators.

**Source:**
- Internet Archive: https://archive.org/details/hans-wehr-j.-milton-cowan-arabic-english-dictionary-the-hans-wehr-dictionary-of- (1976, Spoken Language Services)
- Searchable PDF: https://gulfarabicresources.com/wp-content/uploads/2021/02/Hans-Wehr-Searchable-dictionary.pdf
- Online search (with Lane's, Mukhtār al-Ṣiḥāḥ, al-Mufradāt): https://www.hanswehr.com/

**License:** Proprietary (copyrighted; the 1976 edition is not public domain). Internet Archive offers "borrowing" (controlled digital lending), not unrestricted redistribution.

**Agent-skill viability:** LOW-MEDIUM (copyrighted; no structured data/API). Human reference only unless a licensed/structured edition is obtained.

### 2.5 Other Public-Domain Arabic-English Lexicons

- **Al-Mufradāt fī Gharīb al-Qur'ān** (al-Rāghib al-Iṣfahānī, 11th c.) — Arabic-Arabic, Quranic; included at hanswehr.com.
- **Mukhtār al-Ṣiḥāḥ** (al-Rāzī, 13th c.) — Arabic-Arabic; included at hanswehr.com.
- **Lisan al-Arab** (Ibn Manẓūr, 13th c.) — classical Arabic-Arabic; public domain scans on Internet Archive.
- **Tanzil Quran project** — Quran word-by-word and translation data: https://tanzil.net/ (see Section 4.4).

---

## 3. Thesauri & Synonym Resources

### 3.1 WordNet (see Section 1.1)

Primary synonym resource; synsets provide synonym groups with POS and glosses. Best-in-class free option.

### 3.2 Roget's Thesaurus (1911, Public Domain)

**Role:** Semantically organized thesaurus (concept-hierarchy rather than alphabetical). Public domain (1911 edition).

**Source:** Project Gutenberg ebook 10681 — https://www.gutenberg.org/ebooks/10681 (also mirror used by roget-thesaurus-parser: https://archive.org/details/rogetsthesauruso10681gut)

**Parser/libraries:**
- `roget-thesaurus-parser` (Python, PyPI `RogetThesaurus`): https://github.com/MoserMichael/roget-thesaurus-parser
- `thesaurus` (Java, LGPL-3.0, uses Roget 1911 + WordNet 2.0 LibreOffice data): https://github.com/caarmen/thesaurus

**License:** Public domain (1911 text); library licenses vary (MIT/LGPL).

**Agent-skill viability:** MEDIUM. Good for concept-based synonym expansion; requires parsing the Gutenberg text.

### 3.3 Datamuse API

**Role:** Free, no-key REST API for synonyms, related words, rhymes, etc. Uses WordNet + other sources.

**Endpoint:** `https://api.datamuse.com/words?rel_syn={word}` (also `rel_ant`, `rel_spc`, `rel_gen`, `rel_com`, `rel_jja`, etc.)

**Home:** https://www.datamuse.com/api/

**License:** Free; no formal key; rate-limit courtesy expected.

**Agent-skill viability:** HIGH. Zero-auth, lightweight synonym expansion. Good fallback/lightweight skill.

### 3.4 Thesaurus.com (Unofficial / Scraped)

**Role:** Popular commercial thesaurus; no official public API. Unofficial wrappers exist but are fragile (site randomizes classes/IDs to prevent scraping).

**Unofficial libraries:**
- `synonymous` (unofficial JSON API, GPL-3.0): https://github.com/toroidal-code/synonymous (Heroku, likely defunct)
- `thesaurus-api` / `manwholikespie/thesaurus-api` (Python, MIT): https://github.com/bradleyfowler123/thesaurus-api
- `mhinz/node-thesaurus-com` (Node, MIT): https://github.com/mhinz/node-thesaurus-com
- `bradleyfowler123/thesaurus-api` (fork, MIT)

**License:** Unofficial; scraping may violate Thesaurus.com ToS. Dictionary.com (owner) terms apply.

**Agent-skill viability:** LOW. Fragile, ToS-risky. Prefer WordNet or Datamuse.

### 3.5 LibreOffice Thesaurus Data

English thesaurus data used in LibreOffice (OpenOffice-derived): https://github.com/LibreOffice/dictionaries/tree/master/en (WordNet 2.0-based). MPL/community licenses.

---

## 4. Corpora & EN-AR Parallel Corpora

### 4.1 United Nations Parallel Corpus (UNPC)

**Role:** Manually translated UN documents (1990-2014) in six official languages including Arabic and English. Sentence-aligned. The premier formal-register EN-AR parallel corpus.

**Home:** https://opus.nlpl.eu/legacy/UNPC.php
**Paper:** Ziemski, Junczys-Dowmunt, Pouliquen (2016), LREC — https://aclanthology.org/L16-1561/
**HF dataset:** `Helsinki-NLP/un_pc` — https://huggingface.co/datasets/Helsinki-NLP/un_pc (config `ar-en`: 20,044,478 train examples; ~8.04 GB)

**Stats (ar-en):** ~20.0M sentence alignment units; 570.5M Arabic tokens / 779.7M English tokens (monolingual totals).

**Formats:** XML (TEI), TMX, plain text (Moses/GIZA++), XCES sentence alignments. OPUS also provides word alignments, phrase tables, bilingual dictionaries, frequency counts.

**License:** UN disclaimer — free, no warranty, attribution to UN required, cite Ziemski et al. (2016). No other restrictions apply.

**Agent-skill viability:** HIGH. Downloadable via OPUS or `datasets` library (`load_dataset("Helsinki-NLP/un_pc", "ar-en")`). Excellent for MT fine-tuning and terminology extraction in formal register.

### 4.2 UN Documents Corpus (MultiUN / UN v1.0)

**Role:** UN documents in six official languages; downloadable from DGACM.

**Download:** https://www.un.org/dgacm/en/content/uncorpus/Download
- XML files organized by language/year/symbol with alignment link files
- Plain-text bitexts per language pair
- Fully aligned subcorpus; test/dev sets (`UNv1.0.testsets.tar.gz`)
- Archives split into ≤1 GB chunks; reassemble with `cat ... | tar -xzf -`

**License:** UN (public domain official documents; attribution).

**Agent-skill viability:** HIGH. Complements UNPC; raw UN document translations.

### 4.3 OpenSubtitles (ar-en)

**Role:** Movie/TV subtitles; colloquial, dialogue register EN-AR parallel text. Largest subtitle parallel collection.

**Home:** OPUS OpenSubtitles: https://opus.nlpl.eu/legacy/OpenSubtitles-v2018.php (v2018: 62 languages, 3.35G sentence fragments); also v2016, v1.
**Paper:** Lison & Tiedemann (2016), LREC — OpenSubtitles2016.
**Condition:** Add a link to http://www.opensubtitles.org/ in reports/publications using the data.

**Stats (ar subset):** Arabic ~83.6M subtitle tokens; English ~441.5M tokens (monolingual). ar-en bitext in the tens of millions of sentence pairs.

**Formats:** XML, TMX, plain text (Moses), XCES alignments; intra-lingual alternative alignments (insert/other/pct/spell).

**License:** OPUS (free to redistribute per OPUS belief); attribution to opensubtitles.org requested. Subtitle copyrights remain with original holders (OPUS disclaimer).

**Agent-skill viability:** HIGH. Good for conversational/dialogue register; noisier than UNPC; useful for subtitling and informal translation skills.

### 4.4 Quran Parallel Corpus (Tanzil)

**Role:** Quran with word-by-word and multiple translations in many languages including English and Arabic. Valuable for religious/classical Arabic-English parallel text.

**Home:** https://tanzil.net/
**Translations:** Multiple English translations (Sahih International, Pickthall, Yusuf Ali, etc.) aligned to Arabic ayahs.

**License:** Quran text (public domain/religious text); translations vary (many public domain, e.g., Pickthall, Yusuf Ali; Sahih International more restricted). Check per-translation license.

**Agent-skill viability:** MEDIUM. Domain-specific (religious/classical); useful for Quranic Arabic reference.

### 4.5 TED / TEDx Talks Parallel Corpora (ar-en)

**Role:** Spoken-register EN-AR parallel transcripts from TED/TEDx talks.

**Resources:**
- **TED2020 (OPUS):** https://opus.nlpl.eu/legacy/TED2020.php — ~4,000 TED/TEDx transcripts, 108 languages, 11.46M sentence fragments (Reimers & Gurevych). Volunteer translations.
- **TED-Multilingual-Parallel-Corpus (GitHub):** https://github.com/ajinkyakulkarni14/TED-Multilingual-Parallel-Corpus — includes Arabic paired with English (and 11 other languages); ~500k Arabic-English sentence pairs; scientific-use only, not for third-party transfer.
- **Multitarget TED Talks Task (MTTT, JHU):** https://www.cs.jhu.edu/~kevinduh/a/multitarget-tedtalks/ — 20 languages incl. Arabic; derived from WIT^3/IWSLT; train/dev/test splits.
- **mTEDx (OpenSLR 100):** https://openslr.org/100/ — multilingual TEDx speech+translation corpus; Arabic `mtedx_ar.tgz` (3.6 GB) and aligned pairs e.g. `mtedx_ar-en` (not listed explicitly but ar-en derivable); CC BY-NC-ND 4.0.

**License:** Varies — TED talks: scientific/research use only (TED-Multilingual); mTEDx: CC BY-NC-ND 4.0; WIT^3/IWSLT: research use.

**Agent-skill viability:** HIGH (for spoken register). Good for dialogue/subtitling-style EN-AR.

### 4.6 News Corpora (EN-AR)

**OPUS News Commentary:** https://opus.nlpl.eu/ (News Commentary v11, v9.1, v9) — news parallel text. Check ar-en availability on OPUS.
**UNESCO/UN documents:** see UN v1.0 (Section 4.2) — formal/news-adjacent.
**Other:** WikiMatrix / Wikipedia parallel sentences (OPUS) — Wikipedia-derived EN-AR sentence pairs.

---

## 5. Style Guides & Translation References

### 5.1 The Chicago Manual of Style (CMOS)

**Role:** Preeminent US English style, usage, and citation guide. Authoritative for EN editing and translation house style.

**Home:** https://www.chicagomanualofstyle.org/
**Online:** Subscription (Chicago Manual of Style Online).
**Edition:** 18th edition (2024).
**License:** Proprietary (University of Chicago Press).

**Agent-skill viability:** LOW (subscription, no API). Human reference; cite in agent instructions as style authority.

### 5.2 Oxford Style Guide / New Oxford Style Manual

**Role:** UK English style reference (Hart's Rules + Oxford Dictionary for Writers and Editors). Basis for UNESCO style (British precedents).

**Home:** Oxford University Press; https://oxforddictionaries.com/ (legacy)
**License:** Proprietary (OUP). Print/online subscription.

**Agent-skill viability:** LOW (no API). Human reference.

### 5.3 UNESCO Style Manual (English)

**Role:** UN house style for English-language texts; spelling, punctuation, capitalization, terminology, bibliographic references, transliteration (incl. Arabic transliteration, Appendix 7). Basis: British precedents, Concise Oxford Dictionary, Hart's Rules.

**Edition:** Second revised edition, 2004 (first 1981).
**PDF:** https://unesdoc.unesco.org/ark:/48223/pf0000141812 (80 pp.)
**Related:** UNESCO publications guidelines (2009): https://ich.unesco.org/doc/src/07100-EN.pdf; 2026 guide to preparation of documents: https://unesdoc.unesco.org/ark:/48223/pf0000397033
**License:** UNESCO (free).

**Key content:** Transliteration appendix incl. Arabic (App. 7); geographical names; foreign words; bias-free language; hyphenation; numbers/currencies; author-date references.

**Agent-skill viability:** HIGH (free PDF; embed as style reference in agent system prompt/knowledge base). No API but text can be ingested.

### 5.4 UNESCO Recommendation on Translators (1976)

**Role:** International normative instrument on legal protection of translators and working conditions.
**Page:** https://www.unesco.org/en/legal-affairs/recommendation-legal-protection-translators-and-translations-and-practical-means-improve-status

### 5.5 UN / UNTERM

**Role:** UN multilingual terminology database (UNTERM) for consistent UN terminology across the six official languages. Referenced in UNESCO GEM translation RFQ ("Use relevant portals (e.g., UNTERM)").

**Agent-skill viability:** MEDIUM (web portal; API availability to confirm).

### 5.6 Arabic Translation Style Guides

| Guide | Publisher | URL | Focus |
|-------|-----------|-----|-------|
| AUSIT Style Guide for Community Translations into Arabic | AUSIT (Mustapha Taibi) | https://ausit.org/wp-content/uploads/2024/03/AUSIT-Style-Guide-for-Arabic-Community-Translations_042023.pdf | Community/public-service Arabic; MSA default; functionalist approach |
| Arabic Style Guide | Mozilla Localization | https://mozilla-l10n.github.io/styleguides/ar/ | Software/UI localization; Microsoft/Apple glossaries |
| Arabic Style Guide | Translators without Borders (TWB/Katō) | https://community.translatorswb.org/uploads/short-url/nE8huZPwK3BnRORy83KmLBQQ7PK.pdf | Humanitarian translation; accuracy/fluency/terminology/style/design |
| Arabic Timed Text Style Guide | Netflix | https://partnerhelp.netflixstudios.com/hc/en-us/articles/215517947 | Subtitling; MSA only; transliteration rules |
| Arabic Language Guidelines | Unbabel | https://help.unbabel.com/hc/en-us/articles/360008930373 | Crowdsourced translation QA |
| Arabic Style Guide | WordPress.com | https://translate.wordpress.com/glossaries-and-style-guides/arabic-style-guide/ | Software localization |

**Common Arabic translation guidance:** default to Modern Standard Arabic (MSA) for written text; avoid dialect/regionalisms unless audience-specific; use diacritics (tashkīl) to aid readability; avoid Anglicisms; prefer succinct, unambiguous wording; transliterate terms lacking established Arabic equivalents (Netflix: double quotes for first-use transliteration).

**Agent-skill viability:** HIGH (free PDFs/web; ingest into agent knowledge base as style reference).

---

## 6. Programmatically Accessible APIs & Datasets ("Skills")

### 6.1 Dictionary / Lexicon APIs (ready for agent tool-wrapping)

| API | Endpoint | Auth | Cost/Limit | License | JSON? | Notes |
|-----|----------|------|------------|---------|-------|-------|
| Merriam-Webster Collegiate | `dictionaryapi.com/api/v3/references/collegiate/json/{word}` | `key` query | Free non-comm; 1000 q/day/key; max 2 refs | Proprietary (free tier) | Yes | Best free EN dictionary API |
| Oxford Dictionaries | `od-api.oxforddictionaries.com/api/v2/...` | App-ID + App-Key | Sandbox 500 calls; Lite £50/mo; Growing £200/mo; Enterprise £415/mo | Proprietary | Yes | AI-tool use restricted; no caching except Enterprise |
| Collins | `api.collinsdictionary.com/api/v1/...` | API key | 5,000 free/mo; tiers to £375/mo | Proprietary | Yes | Key by application; no caching |
| Datamuse | `api.datamuse.com/words?rel_syn=...` | None | Free (courtesy rate limit) | Free | Yes | Lightweight synonyms |

**Agent-wrapper pattern:** Expose each as a skill tool: `lookup_definition(word, dictionary)`, `lookup_synonyms(word)`, `lookup_pronunciation(word)`. Cache results to respect quotas (MW 1000/day; Collins/ Oxford metered).

### 6.2 Thesaurus APIs

- Datamuse (`rel_syn`, `rel_ant`) — free, no key (recommended)
- WordNet (local LMF/JSON/DB) — offline, no network
- Roget's 1911 (local parse of Gutenberg text) — offline, public domain

### 6.3 Corpus / Parallel Data Access (programmatic)

- **Hugging Face `datasets`:** `load_dataset("Helsinki-NLP/un_pc", "ar-en")`; also `opus100`, `ted_talks`, etc.
- **OPUS:** https://opus.nlpl.eu/ — direct file downloads (XML/TMX/plain text); OPUS-API for searching; OpusTools (Python) and OpusFilter for processing: https://github.com/Helsinki-NLP/OPUS
- **Tanzil:** https://tanzil.net/ — Quran text/translations; API-ish URL patterns for ayah-level access.
- **Wiktionary MediaWiki API:** `https://en.wiktionary.org/w/api.php` — EN-AR translation pairs.

### 6.4 Skill Integration Architecture (recommendation)

Implement a `reference_skills` module with sub-skills:

1. `en_lexicon` — WordNet (local OEWN JSON/LMF) + Merriam-Webster API (definitions, audio)
2. `en_ar_bilingual` — Wiktionary (EN-AR pairs) + UNPC/OpenSubtitles (context examples)
3. `synonym_expansion` — Datamuse + WordNet + Roget's (local)
4. `style_reference` — Ingested UNESCO Style Manual + CMOS + Arabic style guides (RAG)
5. `terminology` — UNTERM concept + domain glossaries (medical, legal, Quranic)

Prefer **offline/local-first** for WordNet, Wiktionary dumps, Roget's, and style guides (zero rate limits, no API keys, works air-gapped). Use **metered APIs** (Merriam-Webster, Oxford, Collins) only for lookups not coverable offline, with caching and quota guards.

---

## 7. Book References on Translation Theory & Practice

These works inform agent design (translation strategies, equivalence, skopos, corpus-based translation, post-editing). Treat as reference literature for agent prompts/evaluation, not as data APIs.

| Author(s) | Key Work(s) | Relevance to Agent-Based Translation |
|-----------|-------------|--------------------------------------|
| Peter Newmark | *A Textbook of Translation* (1988); *Approaches to Translation* (1981); *Translation and Text Linguistics* | Semantic vs. communicative translation; text-type analysis; useful for agent strategy selection by genre |
| Eugene A. Nida | *Toward a Science of Translating* (1964); *The Theory and Practice of Translation* (with Taber, 1969, 1982) | Formal vs. dynamic equivalence; foundational for equivalence metrics in MT evaluation |
| John C. Catford | *A Linguistic Theory of Translation* (1965) | Translation shifts (level, structure, class, unit, intra-system); useful for rule-based shift detection in agents |
| Mona Baker | *In Other Words: A Coursebook on Translation* (1992, 2nd ed. 2018); *Routledge Encyclopedia of Translation Studies* (ed., 1998, 2009) | Equivalence at word/grammar/text level; collocation, idiom; practical for lexical choice agents |
| Susan Bassnett | *Translation Studies* (1980, multiple eds.); *Post-Colonial Translation* (co-ed.) | Skopos/functionality; cultural turn; useful for agent target-audience adaptation |
| Lawrence Venuti | *The Translator's Invisibility* (1995); *The Translation Studies Reader* | Domestication vs. foreignization; agent tone/register control |
| Anthony Pym | *Method in Translation History* (1998); *Translation and Text Transfer* (2014) | Minimalist translation; risk management; relevant to agent confidence scoring |
| Gideon Toury | *Descriptive Translation Studies and Beyond* (1995) | Norms and acceptability; useful for agent evaluation against target norms |
| Dorothy Kelly | *A Handbook for Translator Trainers* (2005) | Translation competence model; informs agent capability assessment |
| Christopher Taylor | *Language and Language in Translation* | Contrastive analysis EN-AR |
| Mona Baker / Gabriela Saldanha (eds.) | *Routledge Encyclopedia of Translation Studies* | Reference encyclopedia of concepts |

**EN-AR specific:**
- *Arabic-English Translation: Theory and Practice* (various)
- Works on Arabic translation pedagogy (e.g., Mustapha Taibi, AUSIT guide cited in Section 5.6)

**Agent-skill viability:** These are textual references; ingest key chapters into the agent's knowledge base / RAG corpus for strategy and quality-rationale generation. Not callable as APIs.

---

## 8. Concrete Recommendations for Integration as Skills

**Phase 1 (immediate, offline, zero cost):**
1. Embed **Open English Wordnet 2025** (JSON/LMF) locally — synonym sets, hypernyms, glosses.
2. Download **Wiktionary EN + AR dumps**; extract EN-AR translation pairs and headwords.
3. Parse **Roget's Thesaurus 1911** (Gutenberg 10681) for concept-based synonym expansion.
4. Ingest **UNESCO Style Manual (2004)** + **AUSIT Arabic Style Guide** + **Mozilla Arabic style guide** into agent knowledge base as style reference.
5. Wrap **Datamuse API** as a no-key synonym skill.

**Phase 2 (metered APIs, with caching + quota guards):**
6. **Merriam-Webster Collegiate API** (free tier, 1000 q/day) for authoritative EN definitions/audio.
7. **Oxford Dictionaries API** (paid) — only if AI-use restriction can be honored; verify current ToS before agent use.
8. **Collins API** (free tier 5,000/mo) for bilingual coverage if needed.

**Phase 3 (parallel corpora for MT fine-tuning / context examples):**
9. **UNPC (ar-en)** via HF `Helsinki-NLP/un_pc` — formal register.
10. **OpenSubtitles (ar-en)** via OPUS — colloquial register.
11. **TED2020 / mTEDx** — spoken register.

**Avoid / low priority:**
- Thesaurus.com unofficial wrappers (ToS risk, fragile).
- OED / Oxford current dictionaries for agent automation (institutional access; AI-use restrictions).
- Hans Wehr / Lane's as structured data (copyrighted / OCR effort) — human reference only.
- ALMAANY scraping (no official API; ToS risk).

---

## 9. Quick-Reference URLs

- WordNet: https://wordnet.princeton.edu/ ; Download: https://wordnet.princeton.edu/download ; DB format: https://wordnet.princeton.edu/documentation/wndb5wn
- Open English Wordnet: https://en-word.net/ ; GitHub: https://github.com/globalwordnet/english-wordnet ; Downloads: https://en-word.net/downloads ; License: https://github.com/globalwordnet/english-wordnet/blob/main/WNDB_License.txt
- Wiktionary: https://www.wiktionary.org/ ; Dumps: https://dumps.wikimedia.org/ ; API: https://en.wiktionary.org/w/api.php
- Webster's 1913: https://www.gutenberg.org/ ; https://archive.org/
- OED: https://www.oed.com/ ; Oxford Dictionaries API: https://developer.oxforddictionaries.com/ ; Terms: https://developer.oxforddictionaries.com/api-terms-and-conditions ; Pricing: https://account.oxforddictionaries.com/pricing
- Merriam-Webster API: https://dictionaryapi.com/ ; Products: https://www.dictionaryapi.com/products/index ; FAQ: https://www.dictionaryapi.com/info/frequently-asked-questions ; Terms: https://www.dictionaryapi.com/info/terms-of-service ; Jentic OpenAPI: https://jentic.com/apis/merriam-webster.com/merriam-webster
- Collins API: https://www.collinsdictionary.com/us/collins-api ; Docs: https://api.collinsdictionary.com/api/v1/documentation/html ; Apply: https://blog.collinsdictionary.com/collins-api-apply-for-a-key/ ; Terms: https://blog.collinsdictionary.com/terms-conditions-collins-api/
- Datamuse: https://www.datamuse.com/api/
- Roget's 1911: https://www.gutenberg.org/ebooks/10681 ; Parser: https://github.com/MoserMichael/roget-thesaurus-parser
- ALMAANY: https://www.almaany.com/ ; EN-AR: https://www.almaany.com/en/dict/en-ar/ ; Community addon: https://github.com/ibrahim-h/dictionariesAlmaany
- Lane's Lexicon: https://lanelexicon.com/ ; Downloads: https://lanelexicon.com/updates/ ; Alpheios (CC-BY-SA): https://github.com/alpheios-project/lan ; Combined search: https://www.hanswehr.com/
- Hans Wehr: https://archive.org/details/hans-wehr-j.-milton-cowan-arabic-english-dictionary-the-hans-wehr-dictionary-of- ; Searchable PDF: https://gulfarabicresources.com/wp-content/uploads/2021/02/Hans-Wehr-Searchable-dictionary.pdf
- UNPC: https://opus.nlpl.eu/legacy/UNPC.php ; Paper: https://aclanthology.org/L16-1561/ ; HF: https://huggingface.co/datasets/Helsinki-NLP/un_pc
- UN corpus download: https://www.un.org/dgacm/en/content/uncorpus/Download
- OpenSubtitles: https://opus.nlpl.eu/legacy/OpenSubtitles-v2018.php ; OPUS home: https://opus.nlpl.eu/ ; OPUS GitHub: https://github.com/Helsinki-NLP/OPUS ; OpusTools/OpusFilter
- Quran (Tanzil): https://tanzil.net/
- TED2020: https://opus.nlpl.eu/legacy/TED2020.php ; TED-Multilingual: https://github.com/ajinkyakulkarni14/TED-Multilingual-Parallel-Corpus ; MTTT: https://www.cs.jhu.edu/~kevinduh/a/multitarget-tedtalks/ ; mTEDx: https://openslr.org/100/
- UNESCO Style Manual: https://unesdoc.unesco.org/ark:/48223/pf0000141812 ; UNESCO pubs guidelines: https://ich.unesco.org/doc/src/07100-EN.pdf ; 2026 docs guide: https://unesdoc.unesco.org/ark:/48223/pf0000397033
- Translators' Recommendation: https://www.unesco.org/en/legal-affairs/recommendation-legal-protection-translators-and-translations-and-practical-means-improve-status
- AUSIT Arabic guide: https://ausit.org/wp-content/uploads/2024/03/AUSIT-Style-Guide-for-Arabic-Community-Translations_042023.pdf
- Mozilla Arabic: https://mozilla-l10n.github.io/styleguides/ar/ ; TWB Arabic: https://community.translatorswb.org/uploads/short-url/nE8huZPwK3BnRORy83KmLBQQ7PK.pdf ; Netflix Arabic TT: https://partnerhelp.netflixstudios.com/hc/en-us/articles/215517947 ; Unbabel Arabic: https://help.unbabel.com/hc/en-us/articles/360008930373 ; WordPress Arabic: https://translate.wordpress.com/glossaries-and-style-guides/arabic-style-guide/
- Chicago Manual of Style: https://www.chicagomanualofstyle.org/
