#!/usr/bin/env python3
"""
Translation Evaluation Module — deterministic, key-free metrics.

Metrics (all computed locally, no network in the default path):
  - BLEU (NLTK when available, pure-stdlib fallback otherwise)
  - chrF / chrF+ (character n-grams plus optional word n-grams)
  - AL-BLEU (documented deterministic blend, see ``al_bleu``)
  - TSR (Term Success Rate)
  - COMET-MQM (optional; returns None unless a LOCAL model checkpoint is set)
"""

from __future__ import annotations

import math
import os
from collections import Counter
from pathlib import Path
from typing import Any

try:
    import nltk  # type: ignore
    from nltk.translate.bleu_score import SmoothingFunction, sentence_bleu
except Exception:  # pragma: no cover - optional dependency
    nltk = None  # type: ignore
    sentence_bleu = None  # type: ignore
    SmoothingFunction = None  # type: ignore


class TranslationEvaluator:
    """Evaluates translation quality using multiple local metrics."""

    # AL-BLEU is a deterministic blend of standard BLEU and char-only chrF:
    #   AL-BLEU = 0.40 * BLEU + 0.60 * chrF(char_order=3, word_order=0)
    # Character n-grams are robust to Arabic morphology and word order, so
    # they receive the larger fixed weight. No model or network is involved.
    AL_BLEU_BLEU_WEIGHT = 0.4
    AL_BLEU_CHRF_WEIGHT = 0.6

    def __init__(self) -> None:
        self.smoothing = (
            SmoothingFunction().method1
            if nltk is not None and SmoothingFunction is not None
            else None
        )
        # "not_installed" | "no_local_model" | "ok" | "error: ..."
        self.comet_status = "not_checked"

    # ------------------------------------------------------------------
    # Shared n-gram helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _ngrams(items: Any, order: int) -> Counter:
        """Extract contiguous n-grams from a string or token list."""
        ngrams: Counter = Counter()
        if order <= 0:
            return ngrams
        sequence = list(items)
        for i in range(len(sequence) - order + 1):
            ngrams[tuple(sequence[i : i + order])] += 1
        return ngrams

    @staticmethod
    def _f_score(reference: Counter, hypothesis: Counter, beta: float = 3.0) -> float:
        """F-beta score over clipped n-gram overlaps (0..100)."""
        if not reference or not hypothesis:
            return 0.0
        common = sum((reference & hypothesis).values())
        if common == 0:
            return 0.0
        precision = common / sum(hypothesis.values())
        recall = common / sum(reference.values())
        if precision + recall == 0:
            return 0.0
        return ((1 + beta**2) * precision * recall / (beta**2 * precision + recall)) * 100

    # ------------------------------------------------------------------
    # chrF — character n-gram F-score (robust for Arabic morphology)
    # ------------------------------------------------------------------
    def chrf(
        self,
        reference: str,
        hypothesis: str,
        char_order: int = 3,
        word_order: int = 2,
        beta: float = 3.0,
    ) -> float:
        """Compute chrF (chrF+ when ``word_order > 0``).

        ``word_order`` is honoured: 0 gives char-only chrF, positive values add
        a word n-gram component (chrF+) with the same F-beta formula. The two
        components are averaged deterministically. Identical non-empty strings
        score exactly 100 for any setting.
        """
        if reference == hypothesis and reference.strip():
            return 100.0

        char_f = self._f_score(
            self._ngrams(reference.strip(), char_order),
            self._ngrams(hypothesis.strip(), char_order),
            beta,
        )
        if word_order <= 0:
            return char_f

        word_f = self._f_score(
            self._ngrams(reference.split(), word_order),
            self._ngrams(hypothesis.split(), word_order),
            beta,
        )
        if char_order <= 0:
            return word_f
        return 0.5 * (char_f + word_f)

    def _char_ngrams(self, text: str, order: int) -> Counter:
        """Extract character n-grams from text (kept for compatibility)."""
        return self._ngrams(text.strip(), order)

    # ------------------------------------------------------------------
    # BLEU — standard BLEU score
    # ------------------------------------------------------------------
    def bleu(
        self,
        reference: str,
        hypothesis: str,
        max_order: int = 4,
    ) -> float:
        """Compute BLEU score (0..100); identical strings score exactly 100."""
        if reference == hypothesis and reference.split():
            return 100.0

        if nltk is None or sentence_bleu is None:
            return self._simple_bleu(reference, hypothesis, max_order)

        ref_tokens = reference.split()
        hyp_tokens = hypothesis.split()
        if not ref_tokens or not hyp_tokens:
            return 0.0

        weights = tuple(1.0 / max_order for _ in range(max_order))
        score = sentence_bleu(
            [ref_tokens],
            hyp_tokens,
            weights=weights,
            smoothing_function=self.smoothing,
        )
        return min(100.0, score * 100)

    def _simple_bleu(
        self,
        reference: str,
        hypothesis: str,
        max_order: int = 4,
    ) -> float:
        """Pure-stdlib BLEU fallback (used when NLTK is unavailable)."""
        ref_tokens = reference.split()
        hyp_tokens = hypothesis.split()

        if not ref_tokens or not hyp_tokens:
            return 0.0
        if ref_tokens == hyp_tokens:
            return 100.0

        total_precision = 0.0
        for order in range(1, max_order + 1):
            ref_ngrams = self._ngrams(ref_tokens, order)
            hyp_ngrams = self._ngrams(hyp_tokens, order)
            if not hyp_ngrams:
                continue
            common = sum((ref_ngrams & hyp_ngrams).values())
            total_precision += common / sum(hyp_ngrams.values())

        mean_precision = total_precision / max_order
        bp = (
            1.0
            if len(hyp_tokens) > len(ref_tokens)
            else math.exp(1 - len(ref_tokens) / max(len(hyp_tokens), 1))
        )
        return min(100.0, bp * mean_precision * 100)

    def _token_ngrams(self, tokens: list[str], order: int) -> Counter:
        """Extract token n-grams (kept for compatibility)."""
        return self._ngrams(tokens, order)

    # ------------------------------------------------------------------
    # AL-BLEU — Arabic-specific deterministic BLEU blend
    # ------------------------------------------------------------------
    def al_bleu(self, reference: str, hypothesis: str) -> float:
        """Compute AL-BLEU = 0.4 * BLEU + 0.6 * char-only chrF.

        Deterministic by construction: fixed weights, no trained model, no
        network. See :attr:`AL_BLEU_BLEU_WEIGHT` and
        :attr:`AL_BLEU_CHRF_WEIGHT`; identical strings score exactly 100.
        """
        if reference == hypothesis and reference.strip():
            return 100.0
        base_bleu = self.bleu(reference, hypothesis)
        char_chrf = self.chrf(reference, hypothesis, word_order=0)
        return self.AL_BLEU_BLEU_WEIGHT * base_bleu + self.AL_BLEU_CHRF_WEIGHT * char_chrf

    # ------------------------------------------------------------------
    # TSR — Term Success Rate
    # ------------------------------------------------------------------
    def tsr(
        self,
        translation: str,
        glossary_terms: list[dict[str, str]],
    ) -> float:
        """Compute Term Success Rate: % of glossary terms correctly used."""
        if not glossary_terms:
            return 100.0

        required: dict[str, list[str]] = {}
        for term in glossary_terms:
            source = term.get("en", term.get("source", ""))
            targets = [value for key in ("ar", "target", "arabic") if (value := term.get(key, ""))]
            if source and targets:
                required.setdefault(source.lower(), []).extend(targets)
        if not required:
            return 100.0

        found = sum(1 for targets in required.values() if any(t in translation for t in targets))
        return (found / len(required)) * 100

    # ------------------------------------------------------------------
    # COMET-MQM — optional, honest, offline by default
    # ------------------------------------------------------------------
    def comet_mqm(
        self,
        source: str,
        reference: str | None,
        hypothesis: str,
    ) -> float | None:
        """Return a COMET-MQM score only when a LOCAL checkpoint is available.

        This function never downloads a model and never makes a network call.
        ``None`` means "unavailable" — it is not a score of zero. Set
        ``COMET_MODEL_PATH`` to an existing local checkpoint and install the
        optional ``comet`` package to enable it.
        """
        try:
            import importlib.util

            if importlib.util.find_spec("comet") is None:
                self.comet_status = "not_installed"
                return None

            model_path = os.environ.get("COMET_MODEL_PATH", "").strip()
            if not model_path or not Path(model_path).exists():
                self.comet_status = "no_local_model"
                return None

            from comet import load_from_checkpoint  # type: ignore

            model = load_from_checkpoint(model_path)
            data = [
                {
                    "src": source,
                    "mt": hypothesis,
                    "ref": reference or "",
                }
            ]
            raw = model.predict(data, batch_size=8, gpus=0)
            score = raw[0] if isinstance(raw, list) else getattr(raw, "system_score", None)
            self.comet_status = "ok" if isinstance(score, (int, float)) else "error: bad result"
            return float(score) if isinstance(score, (int, float)) else None
        except (ImportError, OSError, ValueError, RuntimeError, AttributeError) as exc:
            self.comet_status = f"error: {exc}"
            return None

    # ------------------------------------------------------------------
    # Comprehensive evaluation
    # ------------------------------------------------------------------
    def evaluate(
        self,
        source: str,
        reference: str | None,
        hypothesis: str,
        glossary_terms: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Run all local metrics and return an honest assessment."""
        result: dict[str, Any] = {}

        result["bleu"] = self.bleu(reference or "", hypothesis)
        result["chrf"] = self.chrf(reference or "", hypothesis)
        result["al_bleu"] = self.al_bleu(reference or "", hypothesis)
        result["tsr"] = self.tsr(hypothesis, glossary_terms) if glossary_terms else None

        result["comet_mqm"] = self.comet_mqm(source, reference, hypothesis)
        result["comet_mqm_status"] = self.comet_status

        scores = [result["chrf"], result["al_bleu"]]
        result["overall_score"] = sum(scores) / len(scores)
        result["passed"] = result["overall_score"] >= 70.0
        return result


def main() -> None:
    """CLI entry point for evaluation."""
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Translation Evaluation")
    parser.add_argument("--reference", required=True, help="Reference translation file")
    parser.add_argument("--hypothesis", required=True, help="Hypothesis translation file")
    parser.add_argument("--source", help="Source text file (for optional COMET-MQM)")
    parser.add_argument("--glossary", help="Glossary JSON file for TSR")

    args = parser.parse_args()

    reference = Path(args.reference).read_text(encoding="utf-8").strip()
    hypothesis = Path(args.hypothesis).read_text(encoding="utf-8").strip()
    source = Path(args.source).read_text(encoding="utf-8").strip() if args.source else ""

    glossary_terms = None
    if args.glossary:
        glossary_terms = json.loads(Path(args.glossary).read_text(encoding="utf-8"))

    evaluator = TranslationEvaluator()
    result = evaluator.evaluate(source, reference, hypothesis, glossary_terms)

    print("=== Evaluation Results ===")
    for key, value in result.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
