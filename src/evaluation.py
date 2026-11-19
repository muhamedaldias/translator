#!/usr/bin/env python3
"""
Translation Evaluation Module.

Implements automatic evaluation metrics:
  - COMET-MQM (primary)
  - chrF (secondary)
  - AL-BLEU (Arabic-specific)
  - TSR (Term Success Rate)
"""

from __future__ import annotations

import logging
import math
from collections import Counter
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_COMET_MODEL: Any = None  # lazy singleton: load the checkpoint once, not per call

try:
    import nltk  # type: ignore
    from nltk.translate.bleu_score import SmoothingFunction, sentence_bleu
except Exception:  # pragma: no cover
    nltk = None  # type: ignore


class TranslationEvaluator:
    """Evaluates translation quality using multiple metrics."""

    def __init__(self) -> None:
        self.smoothing = SmoothingFunction().method1 if nltk else None

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
        """Compute chrF/chrF+ score (character + optional word n-gram F-score).

        Averages F_beta over character orders 1..char_order and, when
        word_order > 0, word orders 1..word_order (chrF+ behavior).
        """
        f_scores: list[float] = []
        for order in range(1, char_order + 1):
            f = self._ngram_fscore(
                self._char_ngrams(reference, order),
                self._char_ngrams(hypothesis, order),
                beta,
            )
            if f is not None:
                f_scores.append(f)
        if word_order > 0:
            ref_words = reference.split()
            hyp_words = hypothesis.split()
            for order in range(1, word_order + 1):
                f = self._ngram_fscore(
                    self._token_ngrams(ref_words, order),
                    self._token_ngrams(hyp_words, order),
                    beta,
                )
                if f is not None:
                    f_scores.append(f)
        if not f_scores:
            return 0.0
        return (sum(f_scores) / len(f_scores)) * 100

    def _ngram_fscore(
        self, ref_ngrams: Counter, hyp_ngrams: Counter, beta: float
    ) -> float | None:
        """F_beta between two n-gram counters; None if the order is unavailable."""
        if not ref_ngrams or not hyp_ngrams:
            return None
        common = sum((ref_ngrams & hyp_ngrams).values())
        if common == 0:
            return 0.0
        precision = common / sum(hyp_ngrams.values())
        recall = common / sum(ref_ngrams.values())
        return (1 + beta ** 2) * precision * recall / (
            beta ** 2 * precision + recall
        )

    def _char_ngrams(self, text: str, order: int) -> Counter:
        """Extract character n-grams from text."""
        text = text.strip()
        ngrams: Counter = Counter()
        for i in range(len(text) - order + 1):
            ngrams[text[i : i + order]] += 1
        return ngrams

    # ------------------------------------------------------------------
    # BLEU — standard BLEU score
    # ------------------------------------------------------------------
    def bleu(
        self,
        reference: str,
        hypothesis: str,
        max_order: int = 4,
    ) -> float:
        """Compute BLEU score between reference and hypothesis."""
        if nltk is None:
            return self._simple_bleu(reference, hypothesis, max_order)

        ref_tokens = reference.split()
        hyp_tokens = hypothesis.split()

        if not ref_tokens or not hyp_tokens:
            return 0.0

        # Renormalize weights over available n-gram orders so short or
        # identical sentences are not punished for missing 3/4-grams.
        n = min(max_order, len(ref_tokens), len(hyp_tokens))
        weights = tuple(1.0 / n for _ in range(n))
        score = sentence_bleu(
            [ref_tokens],
            hyp_tokens,
            weights=weights,
            smoothing_function=self.smoothing,
        )
        return score * 100

    def _simple_bleu(
        self,
        reference: str,
        hypothesis: str,
        max_order: int = 4,
    ) -> float:
        """Simple BLEU implementation without NLTK."""
        ref_tokens = reference.split()
        hyp_tokens = hypothesis.split()

        if not ref_tokens or not hyp_tokens:
            return 0.0

        # Clipped n-gram precisions over AVAILABLE orders (geometric mean)
        precisions: list[float] = []
        for order in range(1, max_order + 1):
            hyp_ngrams = self._token_ngrams(hyp_tokens, order)
            if not hyp_ngrams:
                continue
            ref_ngrams = self._token_ngrams(ref_tokens, order)
            common = sum((ref_ngrams & hyp_ngrams).values())
            precisions.append(common / sum(hyp_ngrams.values()))

        if not precisions:
            return 0.0
        epsilon = 1e-9  # smoothing for zero-match orders
        log_mean = sum(math.log(p if p > 0 else epsilon) for p in precisions) / len(precisions)
        mean_precision = math.exp(log_mean)

        # Brevity penalty
        ref_len = len(ref_tokens)
        hyp_len = len(hyp_tokens)

        if hyp_len > ref_len:
            bp = 1.0
        else:
            bp = math.exp(1 - ref_len / max(hyp_len, 1))

        return bp * mean_precision * 100

    def _token_ngrams(self, tokens: list[str], order: int) -> Counter:
        """Extract token n-grams."""
        ngrams: Counter = Counter()
        for i in range(len(tokens) - order + 1):
            ngrams[tuple(tokens[i : i + order])] += 1
        return ngrams

    # ------------------------------------------------------------------
    # AL-BLEU — Arabic-specific morphologically-aware BLEU
    # ------------------------------------------------------------------
    def al_bleu(
        self,
        reference: str,
        hypothesis: str,
    ) -> float:
        """Compute AL-BLEU score (morphologically-aware BLEU for Arabic)."""
        # AL-BLEU adapts BLEU with morphological/syntactic/lexical matching
        # for Arabic. Simplified implementation here.

        base_bleu = self.bleu(reference, hypothesis)

        # Morphological bonus for Arabic (character-level overlap)
        chrf_score = self.chrf(reference, hypothesis)

        # Combine: weight chrF higher for Arabic
        al_bleu_score = 0.4 * base_bleu + 0.6 * chrf_score
        return al_bleu_score

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

        found = 0
        for term in glossary_terms:
            target = term.get("target", term.get("ar", ""))
            if target and target in translation:
                found += 1

        return (found / len(glossary_terms)) * 100

    # ------------------------------------------------------------------
    # COMET-MQM placeholder (requires comet model download)
    # ------------------------------------------------------------------
    def comet_mqm(
        self,
        source: str,
        reference: str | None,
        hypothesis: str,
    ) -> float | None:
        """Compute COMET-MQM score (requires COMET model).

        Returns None if COMET is not installed or scoring fails (failures
        are logged, never silent). The model checkpoint is loaded once.
        """
        global _COMET_MODEL
        try:
            from comet import download_model, load_from_checkpoint  # type: ignore
        except ImportError:
            return None  # optional dependency not installed — expected path

        try:
            if _COMET_MODEL is None:
                model_path = download_model("Unbabel/wmt22-comet-mqm")
                _COMET_MODEL = load_from_checkpoint(model_path)

            data = [{"src": source, "mt": hypothesis, "ref": reference or ""}]
            result = _COMET_MODEL.predict(data, batch_size=8, gpus=0)
            scores = getattr(result, "scores", None)
            if scores is not None:
                return float(scores[0])
            return float(getattr(result, "system_score", result))
        except Exception as exc:
            logger.warning("COMET-MQM scoring failed: %s", exc)
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
        """Run full evaluation and return all metrics."""
        result: dict[str, Any] = {}

        result["bleu"] = self.bleu(reference or "", hypothesis)
        result["chrf"] = self.chrf(reference or "", hypothesis)
        result["al_bleu"] = self.al_bleu(reference or "", hypothesis)

        if glossary_terms:
            result["tsr"] = self.tsr(hypothesis, glossary_terms)
        else:
            result["tsr"] = None

        comet_score = self.comet_mqm(source, reference, hypothesis)
        result["comet_mqm"] = comet_score

        # Overall quality assessment
        scores = [s for s in [result["chrf"], result["al_bleu"]] if s is not None]
        result["overall_score"] = sum(scores) / len(scores) if scores else 0.0
        result["passed"] = result["overall_score"] >= 70.0

        return result


def main() -> None:
    """CLI entry point for evaluation."""
    import argparse

    parser = argparse.ArgumentParser(description="Translation Evaluation")
    parser.add_argument("--reference", required=True, help="Reference translation file")
    parser.add_argument("--hypothesis", required=True, help="Hypothesis translation file")
    parser.add_argument("--source", help="Source text file (for COMET-MQM)")
    parser.add_argument("--glossary", help="Glossary JSON file for TSR")

    args = parser.parse_args()

    reference = Path(args.reference).read_text(encoding="utf-8").strip()
    hypothesis = Path(args.hypothesis).read_text(encoding="utf-8").strip()
    source = (
        Path(args.source).read_text(encoding="utf-8").strip() if args.source else ""
    )

    glossary_terms = None
    if args.glossary:
        import json

        glossary_terms = json.loads(Path(args.glossary).read_text(encoding="utf-8"))

    evaluator = TranslationEvaluator()
    result = evaluator.evaluate(source, reference, hypothesis, glossary_terms)

    print("=== Evaluation Results ===")
    for key, value in result.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
