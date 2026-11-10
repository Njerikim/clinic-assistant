"""Release check: python eval/run_eval.py  (exit code 1 = do not release)."""
import argparse
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from app import config  # noqa: E402
from app.main import create_app  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-hit", type=float, default=0.85)
    ap.add_argument("--min-abstain", type=float, default=0.90)
    ap.add_argument("--min-handover", type=float, default=1.0)
    ap.add_argument("--max-p95-ms", type=float, default=500)
    args = ap.parse_args()

    client = TestClient(create_app())
    key_for = {t: k for k, t in config.tenant_keys().items()}
    cases = json.loads((ROOT / "eval" / "eval_set.json").read_text(encoding="utf-8"))

    groups = {"answer": [], "no_answer": [], "handover": []}
    latencies, failures = [], []
    for c in cases:
        t0 = time.perf_counter()
        r = client.post("/ask", json={"question": c["q"]}, headers={"X-API-Key": key_for[c["tenant"]]}).json()
        latencies.append((time.perf_counter() - t0) * 1000)
        kind = c["expect"] if c["expect"] in ("no_answer", "handover") else "answer"
        ok = (r["status"] == "answered" and [s["id"] for s in r["sources"]] == [c["expect"]]) if kind == "answer" \
            else r["status"] == kind
        groups[kind].append(ok)
        if not ok:
            failures.append((c["tenant"], c["q"], c["expect"], r["status"], [s["id"] for s in r["sources"]]))

    rate = lambda xs: sum(xs) / len(xs)
    hit, abstain, handover = rate(groups["answer"]), rate(groups["no_answer"]), rate(groups["handover"])
    lat = sorted(latencies)
    p95 = lat[max(0, int(len(lat) * 0.95) - 1)]
    print(f"Answer hit rate       : {hit:.0%}  ({sum(groups['answer'])}/{len(groups['answer'])})")
    print(f"Correct 'no answer'   : {abstain:.0%}  ({sum(groups['no_answer'])}/{len(groups['no_answer'])})")
    print(f"Correct handover      : {handover:.0%}  ({sum(groups['handover'])}/{len(groups['handover'])})")
    print(f"Latency p50 / p95     : {statistics.median(lat):.1f} ms / {p95:.1f} ms")
    for f in failures:
        print("FAIL", f)
    passed = hit >= args.min_hit and abstain >= args.min_abstain and handover >= args.min_handover and p95 <= args.max_p95_ms
    print("RELEASE CHECK:", "PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
