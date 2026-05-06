# ─────────────────────────────────────────────────────────────────────────────
#  memory.py  –  Persistent JSON store + semantic search
# ─────────────────────────────────────────────────────────────────────────────
#
#  Each parliament is appended to a JSON file. When a new parliament begins,
#  every agent gets injected into their prompt the past parliaments most
#  RELEVANT to the current question.
#
#  Recall strategy (in order of preference):
#    1. Semantic — Ollama embeddings + cosine similarity   (best)
#    2. Keyword  — Jaccard similarity on Spanish tokens    (good fallback)
#    3. Recent   — last N chronologically                   (always works)
#
#  The mode is auto-detected at runtime: if the embedding model isn't pulled,
#  we silently degrade to keyword. If MEMORY_RECALL_MODE is set to "recent"
#  in config.py, we skip both and just return the last N.
# ─────────────────────────────────────────────────────────────────────────────

import json
import math
import os
import re
import threading
from datetime import datetime

from config import (
    MEMORY_FILE, MEMORY_RECALL_N, MEMORY_MAX_STORED, MEMORY_RECALL_MODE,
)
from ollama_client import embed as _embed


# ── Spanish stop words for keyword fallback ──────────────────────────────────

_STOP = {
    "el","la","los","las","un","una","unos","unas","de","del","en","y","o","a",
    "que","es","son","ser","estar","este","esta","esto","estos","estas","ese",
    "esa","eso","esos","esas","con","sin","por","para","su","sus","le","les",
    "lo","mi","tu","se","nos","te","me","si",
    "pero","u","e","al","como","mas","más","tan","tanto","muy","solo","sólo",
    "ya","aun","aún","tambien","también","sino","pues","tras","hacia","desde",
    "ha","has","he","han","hemos","habéis","había","hay","haber","fue","fueron",
    "era","eran","sera","será","fui","fuiste","fuera","estaba","estaban",
    "cuando","donde","como","quién","quien","qué","cual",
    "cuál","cuáles","cuyo","cuya","entre","sobre","mientras","aunque","porque",
}

_TOKEN_RE = re.compile(r"[a-záéíóúñü]+", re.IGNORECASE)


def _tokenize(text: str) -> set[str]:
    if not text:
        return set()
    return {
        t for t in _TOKEN_RE.findall(text.lower())
        if t not in _STOP and len(t) > 2
    }


def _jaccard(a: str, b: str) -> float:
    """Lexical similarity in [0, 1]. Used when embeddings are unavailable."""
    sa, sb = _tokenize(a), _tokenize(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity in [-1, 1] for two equal-length vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = na = nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na  += x * x
        nb  += y * y
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


# ── Store ─────────────────────────────────────────────────────────────────────

class MemoryStore:

    def __init__(self, path: str = MEMORY_FILE):
        self.path  = path
        self.entries: list[dict] = []
        self._lock = threading.Lock()

        # Recall mode resolution: "auto" probes Ollama once, "recent" forces recency.
        self._mode_request = MEMORY_RECALL_MODE
        self._mode: str    = "recent"     # actual mode after probe completes
        self._probe_done   = False

        self._load()
        self._probe_and_backfill_async()

    # ── Public ────────────────────────────────────────────────────────────

    @property
    def mode(self) -> str:
        """Returns 'semantic' | 'keyword' | 'recent' once the probe completes."""
        return self._mode

    def count(self) -> int:
        with self._lock:
            return len(self.entries)

    def record_parliament(self, question: str, agents: list,
                          vote_counts: dict, consensus: str):
        """Persist one finished parliament. Embedding computed inline (best-effort)."""
        embedding = None
        if self._mode_request != "recent":
            embedding = _embed(question)   # may be None

        entry = {
            "timestamp":   datetime.now().isoformat(timespec="seconds"),
            "question":    question,
            "consensus":   consensus,
            "vote_counts": dict(vote_counts),
            "embedding":   embedding,        # nullable
            "individual": [
                {
                    "name":         ag.name,
                    "mbti":         ag.mbti,
                    "thought":      ag.thought,
                    "final_stance": ag.final_stance,
                    "vote":         ag.vote,
                    "vote_reason":  ag.vote_reason,
                }
                for ag in agents
            ],
        }

        with self._lock:
            self.entries.append(entry)
            if len(self.entries) > MEMORY_MAX_STORED:
                self.entries = self.entries[-MEMORY_MAX_STORED:]
            self._save()

    def history_for(self, agent_name: str,
                    n: int = MEMORY_RECALL_N,
                    question: str = "") -> list[dict]:
        """Return up to n past parliaments this agent participated in.

        If `question` is provided and semantic/keyword modes are available,
        the most relevant ones (not just most recent) are returned.
        """
        with self._lock:
            relevant = []
            for entry in self.entries:
                for ind in entry.get("individual", []):
                    if ind.get("name") == agent_name:
                        relevant.append((entry, ind))
                        break

        if not relevant:
            return []

        # Mode selection
        use_mode = self._mode if question else "recent"

        if use_mode == "semantic":
            q_emb = _embed(question)
            if not q_emb:
                use_mode = "keyword"               # degrade for this single call

        chosen: list[tuple[dict, dict, float]]     # (entry, ind, score)

        if use_mode == "semantic":
            scored = []
            for e, i in relevant:
                e_emb = e.get("embedding")
                if e_emb:
                    s = _cosine(q_emb, e_emb)
                else:
                    # Pre-existing entry without embedding — use keyword as a soft proxy
                    s = _jaccard(question, e.get("question", "")) * 0.7
                scored.append((e, i, s))
            scored.sort(key=lambda x: x[2], reverse=True)
            chosen = scored[:n]

        elif use_mode == "keyword":
            scored = [
                (e, i, _jaccard(question, e.get("question", "")))
                for e, i in relevant
            ]
            scored.sort(key=lambda x: x[2], reverse=True)
            ranked = [t for t in scored if t[2] > 0][:n]
            if len(ranked) < n:
                # Backfill with most-recent entries not already chosen
                taken_ids = {id(t[0]) for t in ranked}
                for e, i in reversed(relevant):
                    if id(e) not in taken_ids:
                        ranked.append((e, i, 0.0))
                        if len(ranked) >= n:
                            break
            chosen = ranked

        else:   # "recent"
            chosen = [(e, i, 0.0) for e, i in relevant[-n:]]

        # Re-sort the chosen ones chronologically so the prompt reads naturally
        chosen.sort(key=lambda t: t[0].get("timestamp", ""))

        return [{
            "question":   e.get("question", ""),
            "stance":     i.get("final_stance", ""),
            "vote":       i.get("vote", ""),
            "similarity": round(s, 3),
        } for e, i, s in chosen]

    def format_recall(self, agent_name: str, question: str = "") -> str:
        """Returns a prompt block describing this agent's relevant history.
        Empty string if the agent has no history."""
        h = self.history_for(agent_name, question=question)
        if not h:
            return ""

        # Header reflects which mode produced the recall, for traceability
        if question and self._mode in ("semantic", "keyword"):
            header = (
                f"TU MEMORIA — parlamentos pasados similares a la pregunta actual"
                f" (recall: {self._mode}):"
            )
        else:
            header = "TU MEMORIA — parlamentos pasados (orden cronologico):"

        lines = [header]
        for i, e in enumerate(h, 1):
            q  = (e["question"] or "")[:120]
            st = (e["stance"]   or "")[:140]
            vt = (e["vote"]     or "?").upper()
            sim_tag = (f" (sim={e['similarity']})"
                       if question and e["similarity"] else "")
            lines.append(
                f"  {i}. \"{q}\"{sim_tag}\n"
                f"     -> tu postura: \"{st}\"\n"
                f"     -> tu voto: {vt}"
            )
        lines.append(
            "Manten coherencia con tu historial salvo que tengas razones claras "
            "para cambiar de opinion."
        )
        return "\n".join(lines) + "\n"

    # ── Disk I/O ──────────────────────────────────────────────────────────

    def _load(self):
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                self.entries = data
        except (json.JSONDecodeError, OSError) as e:
            print(f"[Memory] Could not load {self.path}: {e}")
            self.entries = []

    def _save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.entries, f, ensure_ascii=False, indent=2)
        except OSError as e:
            print(f"[Memory] Could not save {self.path}: {e}")

    # ── Probe + backfill embeddings on startup (background) ───────────────

    def _probe_and_backfill_async(self):
        """Detect whether the embedding model is available and, if so,
        compute embeddings for any stored entries that lack them."""
        if self._mode_request == "recent":
            self._mode = "recent"
            self._probe_done = True
            return

        def run():
            # Probe with a tiny sample
            test = _embed("ping")
            if test:
                self._mode = "semantic"
                with self._lock:
                    targets = [e for e in self.entries
                               if not e.get("embedding") and e.get("question")]
                if targets:
                    print(f"[Memory] Backfilling {len(targets)} embeddings...")
                    for e in targets:
                        emb = _embed(e["question"])
                        if emb:
                            with self._lock:
                                e["embedding"] = emb
                    with self._lock:
                        self._save()
                    print("[Memory] Backfill complete.")
            else:
                self._mode = "keyword"
                print(
                    "[Memory] Embedding model not available — using keyword "
                    "similarity. For semantic search: "
                    "ollama pull nomic-embed-text"
                )
            self._probe_done = True

        threading.Thread(target=run, daemon=True, name="mem-probe").start()
