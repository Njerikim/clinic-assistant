"""Embedders share one interface: fit(texts) then encode(texts, is_query) -> L2-normalised rows.

TF-IDF over character n-grams is the dependency-light baseline (works across English and
Kiswahili spellings). Set EMBEDDER=e5 to use a real multilingual embedding model.
"""
import os

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer


class TfidfEmbedder:
    def __init__(self) -> None:
        self._vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)

    def fit(self, texts: list[str]) -> None:
        self._vec.fit(texts)

    def encode(self, texts: list[str], is_query: bool = False) -> np.ndarray:
        return self._vec.transform(texts).toarray().astype(np.float32)  # l2-normalised by default


class SentenceTransformerEmbedder:
    """Optional: multilingual-e5 expects 'query: ' / 'passage: ' prefixes."""

    def __init__(self) -> None:
        from sentence_transformers import SentenceTransformer  # lazy import

        self._model = SentenceTransformer(os.getenv("EMBED_MODEL", "intfloat/multilingual-e5-small"))

    def fit(self, texts: list[str]) -> None:  # nothing to fit
        return None

    def encode(self, texts: list[str], is_query: bool = False) -> np.ndarray:
        prefix = "query: " if is_query else "passage: "
        return self._model.encode([prefix + t for t in texts], normalize_embeddings=True)


def make_embedder():
    return SentenceTransformerEmbedder() if os.getenv("EMBEDDER") == "e5" else TfidfEmbedder()
