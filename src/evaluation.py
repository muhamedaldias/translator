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

import math
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import nltk  # type: ignore
    from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
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
        """Compute chrF score between reference and hypothesis."""
        ref_chars = self._char_ngrams(reference, char_order)
        hyp_chars = self._char_ngrams(hypothesis, char_order)

        if not ref_chars or not hyp_chars:
            return 0.0

        common = sum((ref_chars & hyp_chars).values())
        precision = common / sum(hyp_chars.values())
        recall = common / sum(ref_chars.values())

        if precision + recall == 0:
            return 0.0

        f_score = (1 + beta ** 2) * (precision * recall) / (
            beta ** 2 * precision + recall
        )
        return f_score * 100

    def _char_ngrams(self, text: str, order: int) -> Counter:
        """Extract character n-grams from text."""
        text = text.strip()
        ngrams = Counter()
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

        score = sentence_bleu(
            [ref_tokens],
            hyp_tokens,
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

        # Clipped n-gram counts
        total_precision = 0.0
        for order in range(1, max_order + 1):
            ref_ngrams = self._token_ngrams(ref_tokens, order)
            hyp_ngrams = self._token_ngrams(hyp_tokens, order)

            if not hyp_ngrams:
                continue

            common = sum((ref_ngrams & hyp_ngrams).values())
            precision = common / sum(hyp_ngrams.values())
            total_precision += precision

        mean_precision = total_precision / max_order

        # Brevity penalty
        ref_len = len(ref_tokens)
        hyp_len = len(hyp_tokens)

        if hyp_len > ref_len:
            bp = 1.0
        else:
            bp = math.exp(1 - ref_len / max(hyp_len, 1))

        return bp * mean_precision * 100

    def _token_ngrams(self, tokens: List[str], order: int) -> Counter:
        """Extract token n-grams."""
        ngrams = Counter()
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
        glossary_terms: List[Dict[str, str]],
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
        reference: Optional[str],
        hypothesis: str,
    ) -> Optional[float]:
        """Compute COMET-MQM score (requires COMET model).

        Returns None if COMET is not installed or model not available.
        """
        try:
            from comet import download_model, load_from_checkpoint  # type: ignore

            model_path = download_model("Unbabel/wmt22-comet-mqm")
            model = load_from_checkpoint(model_path)

            data = [
                {
                    "src": source,
                    "mt": hypothesis,
                    "ref": reference or "",
                }
            ]
            result = model.predict(data, batch_size=8, gpus=0)
            return result[0] if isinstance(result, list) else result.system_score
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Comprehensive evaluation
    # ------------------------------------------------------------------
    def evaluate(
        self,
        source: str,
        reference: Optional[str],
        hypothesis: str,
        glossary_terms: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Run full evaluation and return all metrics."""
        result: Dict[str, Any] = {}

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
