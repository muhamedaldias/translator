# Claude Code Rules — Multi-Agent Translation System (EN ↔ Arabic)

This file configures Claude Code for the translator project. It defines project-wide behavior,
translation procedures, and agent invocation patterns.

## Project Context

- **Project:** Multi-Agent Translation System (EN ↔ Arabic)
- **Root:** `/data/workspace/projects/translator/`
- **Pipeline:** Analysis → Translator → Post-editor → Reviewer → Judge
- **Evaluation:** COMET-MQM (primary), chrF, AL-BLEU, TSR

## Translation Procedures

### When translating text (EN ↔ Arabic):

1. **Invoke the translator skill** — lazy-load `skills/translator-skill/`
2. **Run Analysis Agent first** — detect register (MSA/dialect), domain, entities, gender context
3. **Inject glossary** — load `data/glossary.tbx` and inject into every agent stage
4. **Run pipeline sequentially** — never parallelize agent stages for the same segment
5. **Apply quality gate** — LLM Judge score ≥ 85 required; max 3 iterations
6. **Preserve formatting** — code blocks, placeholders, XML/HTML tags, RTL markers unchanged

### Arabic-Specific Rules

- Default target: Modern Standard Arabic (MSA) for written text
- Dialect only when explicitly requested (Egyptian, Gulf, Levantine)
- Normalize orthography (alef/ya/ta-marbuta variants) before processing
- Handle 6 Arabic plural forms (zero/one/two/few/many/other)
- Gender agreement: verb-subject, noun-adjective, definiteness
- Broken plurals agree in gender + definiteness only
- Diacritics policy per `config/translator.yaml`

## Agent Invocation Pattern

```
skills/translator-skill/tools/analysis.py    → structured analysis JSON
skills/translator-skill/tools/translate.py   → draft translation
skills/translator-skill/tools/postedit.py    → Arabic grammar correction
skills/translator-skill/tools/review.py      → MQM-style critique
skills/translator-skill/tools/judge.py       → quality gate (0–100)
```

## Skill Installation

```bash
# Install into current project:
cp -r /data/workspace/projects/translator/skills/translator-skill .claude/skills/translator

# Or via npx:
npx skills add /data/workspace/projects/translator/skills/translator-skill
```

## Commands

```bash
# Translate a single file
python src/pipeline.py --source input.txt --target ar --output output_ar.txt

# Translate a book
python scripts/translate_book.py --input book.epub --target ar --output book_ar.epub

# Run evaluation
python src/evaluation.py --reference ref_ar.txt --hypothesis hyp_ar.txt

# Run tests
pytest tests/ -v
```
