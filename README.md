# Clinic Assistant: multi-tenant RAG API (fictional data only)

A small, honest practice project for an AI platform / MLOps role. Two fictional clinics share one
API. Each asks questions in English or Kiswahili and gets answers only from its own approved
documents. No real patient data is used anywhere.

## What it demonstrates
| Concern | How it is handled |
|---|---|
| Authentication | `X-API-Key` maps to a tenant id. Clients cannot send a tenant field (request is rejected with 422). |
| Tenant isolation | One physically separate index per tenant, plus a tenant-scoped cache key. 33 tests, including a sweep of every document against the other clinic's key. |
| Missing answers | Below `MIN_SCORE` the API returns `no_answer` instead of guessing. |
| Medicine questions | Out of scope: `handover` response, never answered. |
| No hallucination | Default generator is extractive (returns approved text verbatim). Optional Ollama generator falls back to extractive on failure. |
| Logging | Queries are PII-redacted (phones, emails, IDs) before logging. |
| Release safety | Versioned index folders. Rollback = `INDEX_VERSION=v1`. `eval/run_eval.py` is a pass/fail release gate. |

## Run
    pip install -r requirements.txt
    uvicorn app.main:app --reload
    curl -s localhost:8000/ask -H "X-API-Key: demo-key-clinic-a" \
         -H "Content-Type: application/json" -d '{"question":"Mnafungua saa ngapi Jumamosi?"}'
    pytest -q
    python eval/run_eval.py

## Measured results (30-question bilingual eval, baseline TF-IDF retriever)
- Answer hit rate: **100% (20/20)**: the right document is always retrieved.
- Correct "no answer": **50% (3/6)**: FAILS the release gate.
- Correct handover: **100% (4/4)**.
- Latency: p50 about 2 ms, p95 about 3 ms (in-process, tiny corpus, no model call).

## Known gap (the interesting finding)
Character n-gram TF-IDF ranks correctly but its confidence scores overlap: correct matches score
0.20 to 0.57 while some out-of-scope questions score up to 0.26 (e.g. "eye tests" matches the
blood-test document). No single threshold separates them. I tried a hybrid char+word scorer and
it did not help. Next steps, in order:
1. Swap in multilingual embeddings (`EMBEDDER=e5`, `intfloat/multilingual-e5-small`) and re-run the eval.
2. Add a reranker or a score-margin rule (top-1 vs top-2).
3. Grow the eval set; the current 30 were written by the same person who wrote the documents, so
   they overstate real-world performance.

## Limits
Fictional data, tiny corpus, Kiswahili text needs review by a native speaker, no rate limiting,
keys come from env vars rather than a secrets manager, the Ollama path is not tested here.

## Demo page
`GET /` serves a single-file chat page (no build step). It shows the answer, status and source for
each question. The built-in demo keys are shown only when the demo keys are active; with real
`TENANT_KEYS` you type the key in yourself. API docs remain at `/docs`.
