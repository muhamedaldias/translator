---
status: accepted
date: 2026-11-26
decision: portable-skill-pack-no-api-key
---

# Portable skill pack with no API key

The translation workflow ships as a portable skill pack whose linguistic intelligence comes from the host coding agent, never from a provider key. This architectural boundary is deliberate and hard to reverse; it was approved by the repository owner on 2026-11-26.

## Context

The goal is professional English ↔ Arabic translation available inside any coding agent — Claude Code, Codex, OpenCode, Hermes or a generic agent. A provider-key design would make every user create an account, store a secret, pay per call and grant the tool network access. It would also tie quality and availability to a vendor, and it invites the failure mode of emitting a fabricated translation when no model answers. Coding agents already carry their own model and can execute role-specific prompts; the repository's contribution is the method, not the model.

## Decision

Translation is performed entirely by the host agent. No API key, provider SDK call or network request exists in the default translation path: `src/llm_client.py` is deprecated and is never called from that path. Python is a deterministic support layer only — it prepares a context-rich brief, protects placeholders, handles the term base, validates host-produced output, converts formats and computes scores. The seven sequential agents carry the quality method, and an explicit MQM gate (score ≥ 85, at most 3 revision rounds) decides acceptance. When no host translation is supplied, the tool reports that explicitly instead of inventing target text.

## Consequences

- **Positive:** zero setup secrets, no per-call provider bill from this repository, no vendor lock-in, and a workflow that works air-gapped and installs into any supported host.
- **Positive:** the brief/validation boundary is testable offline, so CI can verify the pack with a key-free smoke test.
- **Negative:** output quality and consistency depend on the host model; two hosts can produce different results, so no hosted-service-level guarantee is offered.
- **Negative:** optional automatic metrics such as COMET-MQM must degrade honestly when their model is unavailable; no test may require a model download.
- **Operational:** documentation must never instruct a user to set a credential, and the installer must not configure one.

## Alternatives

1. **Provider API key (OpenAI/Anthropic or similar):** rejected — setup friction, secret handling, recurring cost, network dependency and vendor lock-in, with no portability gain.
2. **Hosted translation service:** rejected — turns a local skill pack into an operated service with privacy, credential and availability obligations.
3. **Bundled offline MT model:** rejected — heavy download, weaker literary quality than a host model, and still not portable across hosts.
4. **Optional key with automatic fallback:** rejected — it blurs the contract, encourages silent fallback paths and reintroduces the fake-translation failure mode. The single, clear rule is host-agent-only translation.
