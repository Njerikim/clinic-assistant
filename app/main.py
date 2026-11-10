import hmac
import logging
import time
from pathlib import Path
from typing import Literal

import json

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field

from . import config
from .cache import TenantCache
from .guards import needs_handover, redact
from .llm import build_generator, detect_language
from .store import IndexStore

log = logging.getLogger("clinic_assistant")

MESSAGES = {
    "no_answer": {
        "en": "I don't have that information. Please ask at the reception desk.",
        "sw": "Sina taarifa hiyo. Tafadhali uliza kwenye dawati la mapokezi.",
    },
    "handover": {
        "en": "I can't give medical or medication advice. Please speak to a clinician or pharmacist at the clinic.",
        "sw": "Siwezi kutoa ushauri wa matibabu au dawa. Tafadhali ongea na daktari au mfamasia wa zahanati.",
    },
}


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")  # clients can never name a tenant
    question: str = Field(min_length=2, max_length=500)


class Source(BaseModel):
    id: str
    title: str


class AskResponse(BaseModel):
    status: Literal["answered", "no_answer", "handover"]
    answer: str
    sources: list[Source]
    index_version: str


def create_app(data_dir: Path | None = None, keys: dict | None = None,
               min_score: float | None = None, generator=None) -> FastAPI:
    data_dir = Path(data_dir) if data_dir else config.data_dir()
    keys = keys if keys is not None else config.tenant_keys()
    threshold = config.min_score() if min_score is None else min_score
    version = data_dir.name
    store = IndexStore.load(data_dir)
    generator = generator or build_generator()
    cache = TenantCache()

    app = FastAPI(title="Clinic assistant (demo, fictional data only)")
    app.state.store = store

    def tenant_from_key(x_api_key: str | None = Header(default=None)) -> str:
        if not x_api_key:
            raise HTTPException(status_code=401, detail="Missing API key")
        found = None
        for key, tenant in keys.items():  # compare against all keys: no early exit
            if hmac.compare_digest(key.encode(), x_api_key.encode()):
                found = tenant
        if found is None:
            raise HTTPException(status_code=401, detail="Invalid API key")
        return found

    page = (Path(__file__).parent / "static" / "index.html").read_text(encoding="utf-8")
    # Only the built-in demo keys are ever shown in the page; real keys are typed in by the user.
    demo = {t: k for k, t in keys.items()} if keys == config.DEMO_KEYS else {}
    page = page.replace("__DEMO_KEYS__", json.dumps(demo))

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def home():
        return page

    @app.get("/health")
    def health():
        return {"status": "ok", "index_version": version}

    @app.post("/ask", response_model=AskResponse)
    def ask(req: AskRequest, tenant: str = Depends(tenant_from_key)):
        start = time.perf_counter()
        question = req.question.strip()
        lang = detect_language(question)
        top_score = 0.0

        cached = cache.get(tenant, version, question)
        if cached is not None:
            result = cached
        elif needs_handover(question):
            result = AskResponse(status="handover", answer=MESSAGES["handover"][lang],
                                 sources=[], index_version=version)
        else:
            doc, top_score = store.search(tenant, question, k=1)[0]
            if top_score < threshold:
                result = AskResponse(status="no_answer", answer=MESSAGES["no_answer"][lang],
                                     sources=[], index_version=version)
            else:
                result = AskResponse(status="answered",
                                     answer=generator.generate(question, doc, lang),
                                     sources=[Source(id=doc.id, title=doc.title)],
                                     index_version=version)
            cache.set(tenant, version, question, result)

        log.info("ask tenant=%s status=%s score=%.2f ms=%.0f q=%s", tenant, result.status,
                 top_score, (time.perf_counter() - start) * 1000, redact(question))
        return result

    return app


app = create_app()
