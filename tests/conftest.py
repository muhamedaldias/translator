"""Shared pytest fixtures: path setup + sqlite connection hygiene."""
import contextlib
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src.pipeline import TranslationPipeline


@pytest.fixture(autouse=True)
def _close_pipelines(monkeypatch):
    """Close every TranslationPipeline created during a test (sqlite hygiene)."""
    created = []
    orig_init = TranslationPipeline.__init__

    def tracking_init(self, *args, **kwargs):
        created.append(self)  # track BEFORE init: failed constructors must be closed too
        orig_init(self, *args, **kwargs)

    monkeypatch.setattr(TranslationPipeline, "__init__", tracking_init)
    yield
    for p in created:
        with contextlib.suppress(Exception):
            p.close()