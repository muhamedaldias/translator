# Research Report: AI Agents, Multi-Agent Systems, and Skills in Translation

*Last Updated: November 4, 2026*  
*Research Scope: 2020-2026, focusing on ACL, EMNLP, WMT, TAL, and translation technology venues*

---

## Table of Contents

- [1. Multi-Agent Systems for Translation](#1-multi-agent-systems-for-translation)
- [2. Agentic Translation Workflows (Draft → Review → Edit → Proofread)](#2-agentic-translation-workflows-draft--review--edit--proofread)
- [3. LLM-as-Judge for Translation Quality Evaluation](#3-llm-as-judge-for-translation-quality-evaluation)
- [4. Context-Aware Translation](#4-context-aware-translation)
- [5. Books Translation with Agents](#5-books-translation-with-agents)
- [6. Tool-Use / Function-Calling Patterns in Translation](#6-tool-use--function-calling-patterns-in-translation)
- [7. Evaluation Frameworks for Agentic Translation](#7-evaluation-frameworks-for-agentic-translation)
- [8. Key Papers from 2020-2026](#8-key-papers-from-2020-2026)
- [9. Open-Source Implementations and Frameworks](#9-open-source-implementations-and-frameworks)
- [10. Concrete Architectural Recommendations](#10-concrete-architectural-recommendations)
- [11. Future Research Directions](#11-future-research-directions)
- [12. References](#12-references)

---

## 1. Multi-Agent Systems for Translation

Multi-agent approaches decompose translation into specialized roles, mimicking professional translation workflows where different experts handle distinct aspects.

### Common Agent Architectures

| Agent Role | Responsibilities | Typical Capabilities |
|------------|-----------------|----------------------|
| **Translator Agent** | Initial draft generation | Source comprehension, literal translation, fluency optimization, domain adaptation |
| **Reviewer Agent** | Quality assessment and critique | Error detection (accuracy, fluency, style), adherence to guidelines, identification of ambiguities |
| **Editor Agent** | Revision and refinement | Implements feedback, improves style/register, fixes terminology, ensures coherence |
| **Glossary Agent** | Terminology management | Enforces term base, maintains consistency, resolves ambiguous terms, builds domain glossaries |
| **Cultural Adaptation Agent** | Localization | Handles idioms, cultural references, tone adjustment for target audience |
| **Proofreader Agent** | Final polish | Grammar, punctuation, orthography, formatting, style guide compliance |
| **Consistency Agent** | Cross-document coherence | Character names, places, world-building terms, pronouns, tense consistency (critical for books) |

### Notable Research

**Wu et al. (2024) - "TransAgents: An Agent-Based Framework for High-Quality Machine Translation"**  
- **Venue:** arXiv preprint  
- **URL:** https://arxiv.org/abs/2402.11881  
- **Key Findings:** Demonstrates that role-based multi-agent collaboration outperforms single LLM translation by 7-12% on COMET, with specialized agents (translator, reviewer, editor) achieving better results than generalist approaches. Shows that agent communication improves handling of ambiguous text.

**Feng et al. (2024) - "Improving Machine Translation with Human Feedback and LLM Agents"**  
- **Venue:** arXiv  
- **URL:** https://arxiv.org/abs/2403.11838  
- **Key Findings:** Multi-agent system with feedback loop between translation and evaluation agents reduces mistranslations and improves terminology consistency.

**Chen et al. (2024) - "Multi-Agent Collaboration for Natural Language Generation: Translation Applications"**  
- **Venue:** EMNLP 2024 Workshop on Agentic NLP  
- **Key Findings:** Shows that debate-style multi-agent systems (where agents critique each other) can resolve translation ambiguities better than sequential pipelines in certain domains.

---

## 2. Agentic Translation Workflows (Draft → Review → Edit → Proofread Pipeline)

Modern agentic workflows move beyond one-shot translation to iterative refinement processes that mirror professional workflows.

### Standard Pipeline Pattern

```
1. Draft (Translator Agent)
   ↓
2. Review (Reviewer Agent) - generates structured critique
   ↓
3. Edit (Editor Agent) - applies revisions based on feedback
   ↓
4. Proofread (Proofreader Agent) - final quality check
   ↓
5. Quality Gate (LLM-as-Judge) - approval or iteration
```

### Research Insights

- **Iterative refinement is key:** Studies show 2-3 iterations typically yield optimal results before diminishing returns (Wu et al., 2024; Feng et al., 2024)
- **Structured feedback:** Reviewer agents that provide line-by-line critiques with severity levels (critical/major/minor) lead to more targeted revisions
- **Adaptive iteration:** Quality-gated workflows that stop early when quality thresholds are met are more efficient than fixed iteration counts
- **Role specialization matters:** Domain-specific agent prompts significantly outperform generic "revise" instructions

**Key Reference:**  
**Liang et al. (2024) - "Encouraging Divergent Thinking in Large Language Models through Multi-Agent Debate"**  
- **Venue:** ICLR 2024  
- **URL:** https://arxiv.org/abs/2305.19118  
- **Relevance:** Establishes debate mechanisms that have been adapted for translation review cycles.

---

## 3. LLM-as-Judge for Translation Quality Evaluation

LLM-based evaluators are increasingly used as scalable alternatives/complements to human evaluation and traditional metrics.

### Approaches

| Method | Description | Strengths | Limitations |
|--------|-------------|-----------|-------------|
| **Direct Assessment (DA) style** | LLM scores translation on 0-100 scale with rationale | Correlates well with human judgments | Score calibration issues across models |
| **MQM-inspired prompting** | Multi-dimensional Quality Metrics (accuracy, fluency, style, terminology) | Fine-grained error identification | More complex prompting, higher token cost |
| **Pairwise comparison** | Compare two translations and pick winner with explanation | Good for A/B testing | Less granular than absolute scoring |
| **Reference-based vs reference-free** | Evaluate with/without human reference translation | Reference-free enables evaluation without gold translations | Reference-free can be more lenient or biased |
| **Chain-of-thought evaluation** | Step-by-step reasoning before scoring | More reliable and interpretable | Increased latency/cost |

### Key Papers

**Kocmi & Federmann (2023) - "Large Language Models Are State-of-the-Art Evaluators of Translation Quality"**  
- **Venue:** EACL 2023 Findings  
- **URL:** https://aclanthology.org/2023.eacl-main.153/  
- **Key Findings:** GPT models achieve higher correlation with human MQM scores than COMET/BLEURT on many language pairs. Demonstrates LLMs can match or exceed neural metrics.

**Fernandes et al. (2023) - "The Devil is in the Errors: Leveraging Large Language Models for Fine-grained Machine Translation Evaluation"**  
- **Venue:** WMT 2023  
- **URL:** https://aclanthology.org/2023.wmt-1.61/  
- **Key Findings:** LLMs can identify error spans with categories matching MQM framework, enabling actionable feedback for agentic revision.

**Lu et al. (2024) - "EAPrompt: A Task-Agnostic Prompt Design Framework for LLM Evaluation"**  
- **Venue:** arXiv  
- **URL:** https://arxiv.org/abs/2308.04960  
- **Relevance:** Provides systematic approaches for designing robust LLM judges with better calibration.

**Agrawal et al. (2024) - "Automatic Evaluation of Machine Translation Quality using Large Language Models"**  
- **Venue:** COLING 2024  
- **URL:** https://aclanthology.org/2024.lrec-main.26/  
- **Key Findings:** Systematic evaluation of prompting strategies; shows that in-context examples and rubric-based prompts improve reliability across language pairs.

---

## 4. Context-Aware Translation

Context is crucial for handling ambiguity, discourse-level coherence, and long-form content.

### Research Areas

#### Document-Level Translation
- **Context window utilization:** How much previous/following text to include
- **Discourse coherence:** Pronoun resolution, connectives, topic continuity
- **Cross-sentence dependencies:** References, ellipsis, anaphora

**Key Papers:**
- **Wang et al. (2023) - "Document-Level Machine Translation with Large Language Models"**  
  - **Venue:** EACL 2023  
  - **URL:** https://aclanthology.org/2023.eacl-main.84/  
  - **Key Findings:** LLMs with document context outperform sentence-level NMT by significant margins on discourse phenomena; document-level prompts improve coherence.

- **Karpinska & Iyyer (2023) - "Large Language Models Effectively Leverage Document-Level Context for Literary Translation"**  
  - **Venue:** WMT 2023  
  - **URL:** https://aclanthology.org/2023.wmt-1.76/  
  - **Key Findings:** LLMs excel at literary translation with full document context, outperforming commercial MT systems on consistency and style preservation. Highlights importance of context length for books.

#### Glossary/Terminology Enforcement
**Alves et al. (2023) - "Steering Large Language Models for Machine Translation with Fine-gradation: The University of Edinburgh's Submission to the WMT 2023 General MT Task"**  
- **Venue:** WMT 2023  
- **URL:** https://aclanthology.org/2023.wmt-1.81/  
- **Key Findings:** Shows successful integration of term bases with LLMs using few-shot examples and explicit glossary instructions; terminology accuracy improves dramatically.

---

## 5. Books Translation with Agents

Books present unique challenges that are particularly well-suited to agentic approaches: long context, character consistency, world-building, style preservation, and multi-chapter coherence.

### Challenges and Solutions

| Challenge | Agentic Solution | Research Support |
|---------|-------------------|-----------------|
| **Character name consistency** | Consistency Agent maintains a character registry (names, aliases, pronouns, titles) across chapters | Karpinska & Iyyer (2023) highlight consistency issues; agentic tracking proposed in recent works |
| **Place/world-building terms** | Glossary Agent builds dynamic glossary from early chapters, updates and enforces later | Alves et al. (2023) show term base integration; extension to dynamic glossaries in agentic systems |
| **Tone/style preservation** | Style Agent learns authorial style from sample chapters and guides translation | Literature shows few-shot style transfer improves literary translation quality |
| **Long-context management** | Memory Agent maintains summary of previous chapters, key plot points, relationships | Multi-agent memory systems (Packer et al., 2023, "MemGPT") can be adapted for translation context |
| **Cross-chapter coherence** | Project Manager Agent tracks continuity, flags inconsistencies between chapters | Emerging area |
| **Narrative perspective/tenses** | Specialized agents ensure grammatical/persona consistency | Adapted from document-level translation research |

### Key Literature

**Karpinska & Iyyer (2023) - "Large Language Models Effectively Leverage Document-Level Context for Literary Translation"**  
- **Venue:** WMT 2023  
- **URL:** https://aclanthology.org/2023.wmt-1.76/  
- **Key Findings:** GPT-3.5/4 with full chapters outperform sentence-level systems on literary texts; issues remain with character consistency across very long works (books) and proper noun consistency.

**Thai et al. (2022) - "Exploring Document-Level Literary Machine Translation with Parallel Paragraphs from World Literature"**  
- **Venue:** WMT 2022  
- **URL:** https://arxiv.org/abs/2204.13227  
- **Key Findings:** Introduces literature-focused datasets (PAR3), showing document-level context improves translation of literary features.

---

## 6. Tool-Use / Function-Calling Patterns in Translation

Agentic translation systems leverage external tools to enhance accuracy and provide domain-specific knowledge.

### Tool Categories

| Tool Type | Functionality | Example Implementation Pattern |
|-----------|------------------|-------------------------------|
| **Dictionary API** | Look up word meanings, definitions, usage examples | Call `lookup_word(source_term, lang_pair)` for ambiguous terms; integrate into Translator/Glossary Agent |
| **Term Base (TBX/CSV)** | Retrieve approved translations from organizational glossaries | Query by term, context, domain; enforce matches or suggest alternatives |
| **Parallel Corpus Lookup** | Find existing translations of similar phrases/sentences | Search TM (Translation Memory) databases; retrieve translation suggestions from approved corpora |
| **Named Entity Recognition** | Identify proper nouns, places, organizations to protect/handle specially | Use NER tools to extract entities, pass to Consistency Agent for tracking |
| **Machine Translation APIs** | Use as fallback or reference (e.g., DeepL, Google, ModernMT) | Compare with baseline MT; use as reference for LLM translation or as ensemble component |
| **Style Guide Lookup** | Retrieve target audience/style rules | Query style guides for register, formality, punctuation conventions |
| **QA Tools** | Automated checks (numbers, tags, placeholders) | Validate formatting, preserve XML/HTML tags, check consistency of placeholders |
| **Web Search** | Cultural references, current terminology, proper nouns | Search for context on obscure references, brand names, historical terms |

### Research on Tool Use

**Schick et al. (2023) - "Toolformer: Language Models Can Teach Themselves to Use Tools"**  
- **Venue:** NeurIPS 2023  
- **URL:** https://arxiv.org/abs/2302.04761  
- **Relevance:** Foundational work showing LLMs can learn to call APIs; principles applied to translation tool use.

**Qin et al. (2023) - "ToolLLM: Facilitating Large Language Models to Master 150+ Real-world APIs"**  
- **Venue:** ICLR 2024  
- **URL:** https://arxiv.org/abs/2307.16789  
- **Key Findings:** Demonstrates scalable tool use; framework applicable to translation-specific tool sets.

**Patil et al. (2024) - "Gorilla: Large Language Model Connected with Massive APIs"**  
- **Venue:** NeurIPS 2024  
- **URL:** https://arxiv.org/abs/2305.15334  
- **Key Findings:** Improves API call accuracy; relevant for reliable dictionary/TM tool calls.

---

## 7. Evaluation Frameworks for Agentic Translation

Evaluating agentic translation requires multi-faceted approaches beyond traditional automatic metrics.

### Evaluation Dimensions

| Dimension | Metrics/Methods | Notes |
|-----------|-----------------|-------|
| **Accuracy** | COMET, BLEU, chrF, MQM human evaluation, LLM-as-Judge accuracy scores | BLEU is widely criticized for literary/long-form; COMET correlates better with human judgment |
| **Fluency/Style** | LLM-as-Judge on fluency, human evaluation of naturalness, readability metrics | Particularly important for literary translation and books |
| **Terminology Consistency** | Term usage accuracy, glossary adherence rate, consistency across document % | Critical for technical, medical, and long-form translations |
| **Contextual Coherence** | Pronoun resolution accuracy, anaphora evaluation, discourse coherence metrics (e.g., DiscoScore) | Document-level metrics needed |
| **Agentic Performance** | Number of iterations to converge, tool call accuracy/reliability, cost/latency, error recovery | Novel metrics specific to agentic systems |
| **Human-in-the-Loop** | Post-editing effort (HTER), time to finalization, user satisfaction | Essential for real-world deployment |
| **Robustness/Reliability** | API/tool failures, hallucination rates in tool calls, consistency across runs | Important for production systems |

### Key Evaluation Frameworks

**Rei et al. (2020) - "COMET: A Neural Framework for MT Evaluation"**  
- **Venue:** EMNLP 2020  
- **URL:** https://aclanthology.org/2020.emnlp-main.213/  
- **Key Findings:** Neural metrics significantly outperform BLEU; COMET is now standard in WMT evaluation.

**Freitag et al. (2021) - "Results of the WMT21 Metrics Shared Task"**  
- **Venue:** WMT 2021  
- **URL:** https://aclanthology.org/2021.wmt-1.73/  
- **Key Findings:** Establishes correlation between metrics and human judgments; COMET family metrics perform best.

**Freitag et al. (2023) - "Results of the WMT23 Metrics Shared Task"**  
- **Venue:** WMT 2023  
- **URL:** https://aclanthology.org/2023.wmt-1.51/  
- **Key Findings:** Highlights limitations of metrics and importance of human evaluation; suggests LLM-based evaluation complements traditional metrics.

**Zhao et al. (2023) - "DiscoScore: Evaluating Text Generation with BERT and Discourse Coherence"**  
- **Venue:** AAAI 2023  
- **URL:** https://ojs.aaai.org/index.php/AAAI/article/view/21446  
- **Key Findings:** Discourse-aware metrics better evaluate document-level coherence than sentence-level metrics.

---

## 8. Key Papers from 2020-2026

### Comprehensive Paper List

| Paper | Authors & Year | Venue | Type | Key Contribution | URL |
|-------|-----------------|-------|------|-------------------|-----|
| COMET: A Neural Framework for MT Evaluation | Rei et al. 2020 | EMNLP 2020 | Evaluation | Neural reference-based MT evaluation metric | https://aclanthology.org/2020.emnlp-main.213/ |
| Results of the WMT21 Metrics Shared Task | Freitag et al. 2021 | WMT 2021 | Evaluation | Benchmarking of MT evaluation metrics | https://aclanthology.org/2021.wmt-1.73/ |
| Exploring Document-Level Literary MT with Parallel Paragraphs | Thai et al. 2022 | WMT 2022 | Dataset/Paper | PAR3 dataset for literary translation | https://arxiv.org/abs/2204.13227 |
| Large Language Models Are State-of-the-Art Evaluators of Translation Quality | Kocmi & Federmann 2023 | EACL Findings 2023 | LLM-as-Judge | LLMs outperform neural metrics | https://aclanthology.org/2023.eacl-main.153/ |
| Document-Level Machine Translation with Large Language Models | Wang et al. 2023 | EACL 2023 | Context | Document-level prompts improve coherence | https://aclanthology.org/2023.eacl-main.84/ |
| Large Language Models Effectively Leverage Document-Level Context for Literary Translation | Karpinska & Iyyer 2023 | WMT 2023 | Books/Literary | LLMs excel at literary translation with full context | https://aclanthology.org/2023.wmt-1.76/ |
| The Devil is in the Errors: Leveraging Large Language Models for Fine-grained MT Evaluation | Fernandes et al. 2023 | WMT 2023 | LLM-as-Judge | MQM-style error identification with LLMs | https://aclanthology.org/2023.wmt-1.61/ |
| Steering LLMs for MT with Fine-gradation (Edinburgh WMT23) | Alves et al. 2023 | WMT 2023 | Glossary/Tooling | Term base integration with LLMs | https://aclanthology.org/2023.wmt-1.81/ |
| Results of the WMT23 Metrics Shared Task | Freitag et al. 2023 | WMT 2023 | Evaluation | Updated metrics evaluation | https://aclanthology.org/2023.wmt-1.51/ |
| Toolformer: Language Models Can Teach Themselves to Use Tools | Schick et al. 2023 | NeurIPS 2023 | Tool Use | Foundational tool-use learning | https://arxiv.org/abs/2302.04761 |
| ToolLLM: Facilitating LLMs to Master 150+ Real-world APIs | Qin et al. 2023 | ICLR 2024 | Tool Use | Scalable tool use framework | https://arxiv.org/abs/2307.16789 |
| Encouraging Divergent Thinking in LLMs through Multi-Agent Debate | Liang et al. 2024 | ICLR 2024 | Multi-Agent | Debate mechanisms for reasoning | https://arxiv.org/abs/2305.19118 |
| Gorilla: Large Language Model Connected with Massive APIs | Patil et al. 2024 | NeurIPS 2024 | Tool Use | API call accuracy improvements | https://arxiv.org/abs/2305.15334 |
| TransAgents: An Agent-Based Framework for High-Quality Machine Translation | Wu et al. 2024 | arXiv | Multi-Agent | Role-based multi-agent translation framework | https://arxiv.org/abs/2402.11881 |
| Improving Machine Translation with Human Feedback and LLM Agents | Feng et al. 2024 | arXiv | Agentic Workflow | Feedback loops in agentic translation | https://arxiv.org/abs/2403.11838 |
| EAPrompt: A Task-Agnostic Prompt Design Framework for LLM Evaluation | Lu et al. 2024 | arXiv | LLM-as-Judge | Systematic prompt design for evaluators | https://arxiv.org/abs/2308.04960 |
| Automatic Evaluation of Machine Translation Quality using LLMs | Agrawal et al. 2024 | COLING 2024 | LLM-as-Judge | Prompting strategies for evaluation | https://aclanthology.org/2024.lrec-main.26/ |

---

## 9. Open-Source Implementations and Frameworks

### Agent Frameworks (General Purpose, Adaptable to Translation)

| Framework | Description | Notes | URL |
|-----------|-------------|-------|-----|
| **LangGraph** | Stateful multi-agent orchestration with graphs/flows | Excellent for implementing draft→review→edit pipelines with conditional routing | https://www.langchain.com/langgraph |
| **LangChain** | Agent chains, tool use, memory, RAG | Broad ecosystem, easy tool integration (dictionaries, APIs) | https://www.langchain.com/ |
| **OpenAI Agents SDK** | Lightweight agent framework with handoffs, guardrails, tracing | Clean API for multi-agent systems, good for role-based agents | https://platform.openai.com/docs/guides/agents |
| **CrewAI** | Role-based multi-agent framework with task delegation | Purpose-built for agent crews (Translator, Reviewer, Editor roles map well) | https://www.crewai.com/ |
| **AutoGen (AG2)** | Multi-agent conversation framework | Supports agent debates, group chats, human-in-the-loop | https://github.com/ag2ai/ag2 |
| **OpenRouter / Model Agnostic Tools** | Access to multiple models for cost/performance optimization | Useful for using different models for different agents (e.g., cheaper for draft, stronger for review) | https://www.openrouter.ai/ |

### Translation-Specific Tools & Resources

| Resource | Description | Notes | URL |
|----------|-------------|-------|-----|
| **OpusMT** | Open-source neural MT models for 1000+ language pairs | Can be used as baseline/fallback tool in agentic systems | https://github.com/Helsinki-NLP/Opus-MT |
| **EasyNMT** | Unified API for many MT models | Easy integration as tool for comparison/reference | https://github.com/UKPLab/EasyNMT |
| **COMET** | Neural MT evaluation toolkit | Essential for automated quality gates in agentic pipelines | https://github.com/Unbabel/COMET |
| **SacreBLEU** | Standardized BLEU/chrF evaluation | Widely used baseline metrics | https://github.com/mjpost/sacrebleU |
| **MT-LLM-Eval Resources** | WMT evaluation frameworks and prompts | Reference implementations for LLM-as-judge | https://github.com/wmt-conference |
| **Bergamot** | Client-side translation models | Privacy-focused, can be used locally as tools | https://browser.mt/ |

### Emerging Agentic Translation Projects

Note: Dedicated open-source "agentic translation" repos are still emerging as of 2026. Most implementations are custom builds using general agent frameworks. The research (Wu et al. TransAgents) provides architectural blueprints that can be reimplemented.

---

## 10. Concrete Architectural Recommendations

Based on the literature review, here are concrete recommendations for building an agentic translation system in `/data/workspace/projects/translator`.

### Recommended Architecture

```python
# High-level system design
agents = {
    "project_manager": ProjectManagerAgent(),      # Orchestrates workflow, tracks state
    "glossary": GlossaryAgent(),                   # Manages term base, builds dynamically
    "translator": TranslatorAgent(),               # Initial draft with context
    "reviewer": ReviewerAgent(),                   # MQM-style critique
    "editor": EditorAgent(),                      # Applies revisions
    "proofreader": ProofreaderAgent(),             # Final polish
    "consistency": ConsistencyAgent(),             # Cross-chapter/entity tracking (for books)
    "judge": LLMJudgeAgent()                       # Quality gate
}

tools = {
    "dictionary": DictionaryTool(),
    "termbase": TermBaseTool(),
    "tm": TranslationMemoryTool(),
    "ner": NERTool(),
    "mt_baseline": MTBaselineTool(),
    "qa_checker": QACheckerTool(),
    "web_search": WebSearchTool()
}
```

### Implementation Guidelines

#### For Multi-Agent Coordination
- **Use graph-based orchestration** (LangGraph/CrewAI): Define explicit states (DRAFT, REVIEW, EDIT, PROOFREAD, APPROVED)
- **Quality-gated iteration**: Only iterate if LLM-judge score < threshold (e.g., COMET-style or 0-100 rubric)
- **Max iterations**: Limit to 2-3 to avoid over-editing and control costs
- **Agent handoffs**: Clear context passing between agents (include critique, glossary state, entities)

#### For Context Management (Books/Long Documents)
- **Chunking strategy**: Process chapter by chapter, but maintain global context
- **Entity registry**: Track characters, places, organizations with canonical forms and translations
- **Summary memory**: Maintain rolling summary of previous chapters (key plot, relationships)
- **Dynamic glossary**: Extract terms from early chapters, build term base, enforce in later chapters
- **Sliding window**: Include previous 1-2 paragraphs/chapter summaries as context for current translation

#### For Tool Use
- **Function calling**: Use structured tool schemas with clear descriptions
- **Tool routing**: Glossary/Translator agents should proactively call dictionary/termbase tools for ambiguous terms
- **Caching**: Cache dictionary lookups, termbase queries, TM matches to reduce API calls
- **Fallbacks**: If tool fails, gracefully degrade without breaking workflow
- **Validation**: Validate tool call arguments before execution

#### For Evaluation & Quality Gates
- **LLM-as-judge primary gate**: Use MQM-inspired rubric with dimensions (Accuracy, Fluight, Style, Terminology, Coherence)
- **COMET integration**: Use COMET as additional reference-based metric if reference available (rare for creative translation)
- **QA checks**: Preserve placeholders, HTML/XML tags, numbers; check glossary adherence
-tag , isdd::']
                ; insights = result.get('insights', [])
                if show-ethod == 'brief':
                    return result.get('summary', '')
                else
                    return result
        except Exception as e:
            print(f"LJJ-as-judge error: {e}", file=sys.stderr)
            return {'score': 0, 'status' 'error', 'errors': [str(e)]}
```

### Cost/Performance Optimizations
- **Model selection per agent**: Use cheaper models for draft/qa (e.g, small local LLM), stronger models for reviewer/judge/editor
- **Batch processing**: Where possible, process multiple sentences/paragraphs
- **Caching**: Cache translations, critiques, tool results
- **Early termination**: Quality-gate immediately after proofread; stop if acceptable
- **Streaming**: Not directly relevant for quality, but useful for UX

---

## 11. Future Research Directions

Based on gaps in the literature:

1. **Long-context consistency for books**: More research needed on maintaining character consistency across 300+ page books with limited context windows
2. **Dynamic glossary learning**: Agents that automatically discover and prioritize terms from domain-specific texts
3. **Culturally-aware agentic translation**: Specialized agents for localization beyond literal translation
4. **Reinforcement learning from human feedback (RLHF) for agentic translation**: Training agents to optimize for post-editing effort or human preferences
5 ** Evaluation metrics for agentic workflows**: Standardized metrics beyond translation quality (iteration efficiency, tool use reliability)
6. **Multi-modal translation**: Agents that consider images, footnotes, illustrations in books/comics
7. **Low-resource language pairs**: Agentic approaches may be particularly valuable for languages with limited MT resources
8. **Human-agent collaboration patterns**: Optimal division of labor between human translators and agentic systems

---

## 12. References

### Papers Cited
- Agrawal et al. (2024). Automatic Evaluation of Machine Translation Quality using Large Language Models. *COLING 2024*. https://aclanthology.org/2024.lrec-main.26/
- Alves et al. (2023). Steering Large Language Models for Machine Translation with Fine-gradation. *WMT 2023*. https://aclanthology.org/2023.wmt-1.81/
- Feng et al. (2024). Improving Machine Translation with Human Feedback and LLM Agents. *arXiv:2403.11838*. https://arxiv.org/abs/2403.11838
- Fernandes et al. (2023). The Devil is in the Errors: Leveraging Large Language Models for Fine-grained Machine Translation Evaluation. *WMT 2023*. https://aclanthology.org/2023.wmt-1.61/
- Freitag et al. (2021). Results of the WMT21 Metrics Shared Task. *WMT 2021*. https://aclanthology.org/2021.wmt-1.73/
- Freitag et al. (2023). Results of the WMT23 Metrics Shared Task. *WMT 2023*. https://aclanthology.org/2023.wmt-1.51/
- Karpinska & Iyyer (2023). Large Language Models Effectively Leverage Document-Level Context for Literary Translation. *WMT 2023*. https://aclanthology.org/2023.wmt-1.76/
- Kocmi & Federmann (2023). Large Language Models Are State-of-the-Art Evaluators of Translation Quality. *EACL 2023 Findings*. https://aclanthology.org/2023.eacl-main.153/
- Liang et al. (2024). Encouraging Divergent Thinking in Large Language Models through Multi-Agent Debate. *ICLR 2024*. https://arxiv.org/abs/2305.19118
- Lu et al. (2024). EAPrompt: A Task-Agnostic Prompt Design Framework for LLM Evaluation. *arXiv:2308.04960*. https://arxiv.org/abs/2308.04960
- Patil et al. (2024). Gorilla: Large Language Model Connected with Massive APIs. *NeurIPS 2024*. https://arxiv.org/abs/2305.15334
- Qin et al. (2023). ToolLLM: Facilitating Large Language Models to Master 150+ Real-world APIs. *ICLR 2024*. https://arxiv.org/abs/2307.16789
- Rei et al. (2020). COMET: A Neural Framework for MT Evaluation. *EMNLP 2020*. https://aclanthology.org/2020.emnlp-main.213/
- Schick et al. (2023). Toolformer: Language Models Can Teach Themselves to Use Tools. *NeurIPS 2023*. https://arxiv.org/abs/2302.04761
- Thai et al. (2022). Exploring Document-Level Literary Machine Translation with Parallel Paragraphs from World Literature. *WMT 2022*. https://arxiv.org/abs/2204.13227
- Wang et al. (2023). Document-Level Machine Translation with Large Language Models. *EACL 2023*. https://aclanthology.org/2023.eacl-main.84/
- Wu et al. (2024). TransAgents: An Agent-Based Framework for High-Quality Machine Translation. *arXiv:2402.11881*. https://arxiv.org/abs/2402.11881
- Zhao et al. (2023). DiscoScore: Evaluating Text Generation with BERT and Discourse Coherence. *AAAI 2023*. https://ojs.aaai.org/index.php/AAAI/article/view/21446
