"""One physically separate index per tenant.

Isolation is structural: search() can only ever touch the index of the tenant it is given,
so there is no shared collection to filter and no filter to forget.
"""
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .embeddings import make_embedder


@dataclass(frozen=True)
class Doc:
    id: str
    title: str
    en: str
    sw: str


class _TenantIndex:
    def __init__(self, docs: list[Doc]) -> None:
        self.docs = docs
        self.embedder = make_embedder()
        texts = [f"{d.title}. {d.en} {d.sw}" for d in docs]
        self.embedder.fit(texts)
        self.matrix = self.embedder.encode(texts)


class IndexStore:
    def __init__(self) -> None:
        self._indexes: dict[str, _TenantIndex] = {}

    @classmethod
    def load(cls, data_dir: Path) -> "IndexStore":
        store = cls()
        for path in sorted(Path(data_dir).glob("*.json")):
            docs = [Doc(**d) for d in json.loads(path.read_text(encoding="utf-8"))]
            store._indexes[path.stem] = _TenantIndex(docs)  # tenant id = file name
        return store

    def doc_ids(self, tenant: str) -> set[str]:
        return {d.id for d in self._indexes[tenant].docs}

    def search(self, tenant: str, query: str, k: int = 3) -> list[tuple[Doc, float]]:
        idx = self._indexes[tenant]  # KeyError for unknown tenants, never a fallback
        q = idx.embedder.encode([query], is_query=True)[0]
        scores = idx.matrix @ q
        order = np.argsort(-scores)[:k]
        return [(idx.docs[i], float(scores[i])) for i in order]
