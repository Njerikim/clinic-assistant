"""Answer generation. The default is extractive: it returns the approved document text verbatim,
so it cannot invent facts. Ollama is optional and falls back to extractive if it fails (fail-open)."""
import json
import os
import re
import urllib.request

from .store import Doc

_SW_MARKERS = {
    "je", "saa", "gani", "lini", "wapi", "nini", "kuna", "mnafungua", "unafungua", "jumamosi",
    "jumapili", "jumatatu", "ijumaa", "jumanne", "jumatano", "alhamisi", "kipimo", "vipimo",
    "matokeo", "malipo", "lipa", "naweza", "nitumie", "nahitaji", "mtoto", "watoto", "chanjo",
    "kwa", "na", "ya", "wa", "cha", "la", "mna", "ninaweza", "miadi", "ngapi", "siku", "huduma",
    "zahanati", "kliniki", "wajawazito", "meno", "dawa", "dozi", "kunywa", "uzazi", "mpango",
}


def detect_language(text: str) -> str:
    tokens = set(re.findall(r"[a-zA-Z']+", text.lower()))
    return "sw" if tokens & _SW_MARKERS else "en"


class ExtractiveGenerator:
    def generate(self, question: str, doc: Doc, lang: str) -> str:
        return doc.sw if lang == "sw" else doc.en


class OllamaGenerator:
    def __init__(self) -> None:
        self.url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
        self.model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
        self._fallback = ExtractiveGenerator()

    def generate(self, question: str, doc: Doc, lang: str) -> str:
        context = doc.sw if lang == "sw" else doc.en
        prompt = (
            "Answer the question using ONLY the context. If the context does not contain the "
            "answer, say you do not know. Reply in the language of the question.\n\n"
            f"Context: {context}\n\nQuestion: {question}\nAnswer:"
        )
        try:
            req = urllib.request.Request(
                self.url,
                data=json.dumps({"model": self.model, "prompt": prompt, "stream": False}).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                text = json.loads(resp.read())["response"].strip()
            return text or self._fallback.generate(question, doc, lang)
        except Exception:
            return self._fallback.generate(question, doc, lang)


def build_generator():
    return OllamaGenerator() if os.getenv("GENERATOR") == "ollama" else ExtractiveGenerator()
