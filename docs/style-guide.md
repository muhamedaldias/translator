# EN↔AR Style Guide (portable translation pack)

This guide governs typography and formatting for every English↔Arabic stage in the pack. It is the authoritative reference named by `skills/translator-skill/SKILL.md`, `skills/reference-skills/SKILL.md` and all seven `agents/*.md`. Register, diacritics and terminology defaults come from `config/translator.yaml`; where this guide and the brief's `style_profile` disagree, the brief wins.

## 1. Directionality and bidi text (RTL)

- Arabic output is **right-to-left**. Keep characters in logical (typing) order in the source file; never reverse strings by hand.
- In Markdown/HTML, declare direction explicitly: `<div dir="rtl" lang="ar">…</div>`. In plain Markdown, set the document language in metadata where supported and let the renderer apply RTL.
- Mixed LTR content inside RTL text (numbers, Latin acronyms, URLs, code) is handled by Unicode bidi marks. Insert the isolated marks where a renderer cannot infer boundaries:
  - RLM `U+200F` before a Latin token at the start of an Arabic line; LRM `U+200E` after a Latin token at the end.
  - Use RLE/PDF or `<bdi>`/`<span dir="ltr">…</span>` for longer embedded LTR runs.
- Punctuation: use Arabic punctuation `،` (comma), `؛` (semicolon), `؟` (question mark) and `…` (ellipsis). The Arabic comma occupies the same role as `,`; do not mix the two in one document.
- Numbers: keep ASCII `0-9` digits (or the Arabic-Indic digits `٠-٩` only if the `style_profile` requires it — be consistent across the document). Decimal separator follows the target locale.

## 2. Headings and structure

- Preserve the source heading hierarchy exactly: `#` → `##` → `###` map one-to-one; never skip a level or merge headings.
- Translate heading text; do **not** translate heading anchors, IDs or link fragments (`{#section-3}`, `## Heading {#id}`) — copy them verbatim.
- List markers (`-`, `1.`) and nesting/indentation are preserved. Ordered-list numbering restarts as in the source.
- Tables keep the same number of columns and the same delimiter row; only cell text is translated. Do not reorder columns.
- Blank lines and paragraph breaks are preserved so the Markdown master stays diff-friendly.

## 3. Quotes and quotation marks

- Arabic uses « » (guillemets) as the primary quotation marks; „ “ or “ ” are acceptable only if the `style_profile` selects them. Never use the English `"` pair inside Arabic prose.
- Nested quotations: outer « », inner “ ”.
- Keep emphatic structure: italics in Markdown (`*text*`) remain italics; do not substitute bold for italic.
- Quotations attributed to a source must keep the source's citation markers and footnote references byte-for-byte.

## 4. Placeholders and non-translatables

- Copy every placeholder **byte-for-byte**: `{{name}}`, `{id}`, `%s`, `%1$s`, `$VAR`, `:id`, XML/HTML tags (`<b>`, `<a href="…">`), and template delimiters.
- Never translate, inflect, reorder, add tashkīl to, or "fix" a placeholder. A missing or altered placeholder is a critical error and fails validation (`TranslationPipeline.validate`).
- The `placeholder_map` in the brief lists each protected span. After translation, every entry must still appear the same number of times.
- URLs, email addresses, file paths, package names and identifiers are never translated.

## 5. Code blocks and inline code

- Fenced code blocks (```), indented code blocks and inline code spans (backticks) are copied verbatim, including language tags, spacing and line breaks.
- Do not translate comments inside code unless the brief's `style_profile.code_comments` is explicitly `translate`.
- Backtick fences are preserved exactly (count and type); a code block must not become a quoted block.

## 6. Diacritics (tashkīl)

- Follow `style_profile.diacritics_policy`:
  - `retain` — keep diacritics present in the source; do not add new ones.
  - `remove` — strip all diacritics from the Arabic output; normalise the underlying letters.
  - `automatic` — omit diacritics by default, add them only to disambiguate a genuinely ambiguous form, and be consistent across the document.
- MSA is the default register; dialect only on explicit request. When omitting diacritics, still respect the six CLDR plural forms and the mandatory dual in MSA.
- Orthography normalisation: alef variants (أ إ آ ا), ya variants (ي ى) and ta-marbuta (ة ه) follow the project's normalisation table in `config/translator.yaml`.

## 7. Terminology

- `data/glossary.tbx` (ISO 30042) is authoritative. The approved target rendering is used verbatim for every occurrence of a source term; a lookup synonym never replaces an approved term.
- Glossary terms are injected at **every** stage (Analysis, Translator, Post-edit, Review, Edit, Judge, Consistency). Terminology contributes 15% of the MQM score.
- Named entities: persons/places/organisations are transliterated or translated per the `analysis.entities` decisions and kept identical across chapters. Consistency (stage 7) enforces this for books.
- Loanwords/technical terms not in the glossary: prefer an established Arabic term; flag the choice in `confidence_flags` rather than deciding silently.

## 8. Punctuation, spacing and emphasis

- No space before `،` `؛` `؟`; one space after. Colon `:` and semicolon follow Arabic typography when `style_profile` requests it.
- Parentheses `()` and brackets `[]` are retained; use Arabic or mirrored forms only if the style profile says so.
- Avoid over-translating emphasis: bold/italic in the source stays bold/italic. Do not add emphasis that the source lacks.
- Preserve URLs and inline code exactly as in section 4–5.
