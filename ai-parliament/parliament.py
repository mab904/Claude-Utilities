# ─────────────────────────────────────────────────────────────────────────────
#  parliament.py  –  Orchestrates the 8 parliament phases (A-H)
# ─────────────────────────────────────────────────────────────────────────────

import math
import random
import threading
from collections import deque
from enum import Enum, auto

from agent import Agent, St
from ollama_client import generate as _gen
from config import (
    PARLIAMENT_CENTER, PARLIAMENT_RADIUS, DEBATE_ROUNDS,
    SYSTEM_CLR, RESULT_CLR,
)


# ── Phase enum ────────────────────────────────────────────────────────────────

class Phase(Enum):
    IDLE        = auto()   # no parliament running
    ASSEMBLING  = auto()   # A — agents moving to seats
    THINKING    = auto()   # B — internal thoughts (parallel)
    DEBATING    = auto()   # C — open debate (sequential)
    FINAL       = auto()   # E — final stances (parallel)
    VOTING      = auto()   # F — casting votes (parallel)
    CONCLUDING  = auto()   # G — consensus display
    DISSOLVING  = auto()   # H — agents returning home


# ── Parliament ────────────────────────────────────────────────────────────────

class Parliament:
    def __init__(self, agents: list[Agent],
                 thought_log: deque, speech_log: deque,
                 memory=None):
        self.agents    = agents
        self.tlog      = thought_log
        self.slog      = speech_log
        self.memory    = memory                # MemoryStore | None
        self.phase     = Phase.IDLE
        self.question  = ""

        # Debate state
        self.debate_history: list[tuple[str, str]] = []
        self.speaker_idx   = 0
        self.debate_round  = 0
        self.speaker_busy  = False

        # Thread-safe counters (GIL protects simple int +=)
        self._think_done = 0
        self._final_done = 0
        self._vote_done  = 0

        self.vote_counts    = {"favor": 0, "contra": 0, "neutral": 0}
        self.consensus      = ""
        self.conclude_timer = 0

    # ── Public ────────────────────────────────────────────────────────────

    def start(self, question: str):
        """Kick off a new parliament session with the given question."""
        self.question       = question
        self.phase          = Phase.ASSEMBLING
        self.debate_history = []
        self.speaker_idx    = 0
        self.debate_round   = 0
        self.speaker_busy   = False
        self._think_done    = 0
        self._final_done    = 0
        self._vote_done     = 0
        self.vote_counts    = {"favor": 0, "contra": 0, "neutral": 0}
        self.consensus      = ""
        self.conclude_timer = 0

        # Assign circular seats
        n  = len(self.agents)
        cx, cy = PARLIAMENT_CENTER
        for i, ag in enumerate(self.agents):
            angle = 2 * math.pi * i / n - math.pi / 2
            ag.parl_pos = [
                cx + PARLIAMENT_RADIUS * math.cos(angle),
                cy + PARLIAMENT_RADIUS * math.sin(angle),
            ]
            ag.state         = St.PARL_MOVING
            ag.ready_to_vote = False
            ag.thought       = ""
            ag.last_speech   = ""
            ag.final_stance  = ""
            ag.vote          = None
            ag.vote_reason   = ""
            ag.bubble_text   = ""
            ag.bubble_timer  = 0

        self._sys(f"[CONVOCADO] {question}")

    def update(self):
        """Called every frame from the main loop to advance phases."""

        # ── A: Assembling ─────────────────────────────────────────────────
        if self.phase == Phase.ASSEMBLING:
            all_seated = all(
                math.hypot(ag.pos[0] - ag.parl_pos[0],
                           ag.pos[1] - ag.parl_pos[1]) < 5
                for ag in self.agents
            )
            if all_seated:
                self.phase = Phase.THINKING
                self._start_thinking()

        # ── B: Thinking ───────────────────────────────────────────────────
        elif self.phase == Phase.THINKING:
            if self._think_done >= len(self.agents):
                self.phase = Phase.DEBATING
                self._sys("[DEBATE] Iniciando debate externo...")
                self._next_speaker()

        # ── C: Debating  ──────────────────────────────────────────────────
        elif self.phase == Phase.DEBATING:
            pass  # driven entirely by LLM callbacks via _next_speaker()

        # ── E: Final stances ──────────────────────────────────────────────
        elif self.phase == Phase.FINAL:
            if self._final_done >= len(self.agents):
                self.phase = Phase.VOTING
                self._start_voting()

        # ── F: Voting ─────────────────────────────────────────────────────
        elif self.phase == Phase.VOTING:
            if self._vote_done >= len(self.agents):
                self.phase = Phase.CONCLUDING
                self._gen_consensus()

        # ── G: Concluding ─────────────────────────────────────────────────
        elif self.phase == Phase.CONCLUDING:
            self.conclude_timer += 1
            if self.conclude_timer > 420:          # 7 s at 60 fps
                self.phase = Phase.DISSOLVING
                self._sys("[DISOLUCION] Agentes volviendo a sus casas...")
                for ag in self.agents:
                    ag.state = St.RETURNING

        # ── H: Dissolving ─────────────────────────────────────────────────
        elif self.phase == Phase.DISSOLVING:
            all_home = all(
                math.hypot(ag.pos[0] - ag.home[0],
                           ag.pos[1] - ag.home[1]) < 5
                for ag in self.agents
            )
            if all_home:
                self.phase = Phase.IDLE
                for ag in self.agents:
                    ag.reset_daily()

    def interrupt(self):
        """Force-dissolve the parliament (e.g. user pressed ESC)."""
        if self.phase == Phase.IDLE:
            return
        self._sys("[INTERRUPCION] Parlamento disuelto manualmente.")
        self.phase = Phase.DISSOLVING
        for ag in self.agents:
            ag.state = St.RETURNING

    # ── Phase B: Internal thinking (parallel) ────────────────────────────

    def _start_thinking(self):
        self._sys("[PENSAMIENTO] Fase de reflexion interna privada...")
        for i, ag in enumerate(self.agents):
            ag.state = St.PARL_THINKING
            self._think_async(ag, delay=i * 0.15)

    def _think_async(self, ag: Agent, delay: float = 0.0):
        recall = (self.memory.format_recall(ag.name, self.question)
                  if self.memory else "")
        prompt = (
            f'Pregunta del parlamento: "{self.question}"\n\n'
            f"{recall}"
            f"Genera tu PENSAMIENTO INTERNO sobre esta pregunta. "
            f"Reflexiona honestamente desde tu perspectiva MBTI {ag.mbti}. "
            f"Este pensamiento es privado — nadie mas lo ve. "
            f"2-3 frases concretas."
        )

        def cb(txt):
            ag.thought = txt
            self.tlog.append((ag.name, ag.color, txt))
            ag.show_bubble(txt[:115], frames=340, thought=True)
            # Internal thought is PRIVATE — no TTS
            self._think_done += 1

        ag.gen_async(prompt, cb, max_tokens=90, delay=delay)

    # ── Phase C: Open debate (sequential) ────────────────────────────────

    def _next_speaker(self):
        if self.speaker_busy:
            return

        # Advance round counter when all agents have spoken
        if self.speaker_idx >= len(self.agents):
            self.speaker_idx  = 0
            self.debate_round += 1

        if self.debate_round >= DEBATE_ROUNDS:
            # Move to phase E
            self.phase = Phase.FINAL
            self._sys("[POSTURAS] Cada IA expone su postura final...")
            for ag in self.agents:
                self._final_async(ag)
            return

        ag = self.agents[self.speaker_idx]
        ag.state      = St.PARL_DEBATING
        self.speaker_busy = True
        self._debate_async(ag)

    def _debate_async(self, ag: Agent):
        hist = "\n".join(
            f"  {n}: {t}" for n, t in self.debate_history[-8:]
        ) or "  (Eres el primero en hablar)"

        prompt = (
            f"DEBATE — Ronda {self.debate_round + 1}/{DEBATE_ROUNDS}\n"
            f'Pregunta: "{self.question}"\n'
            f"Tu pensamiento interno (privado): \"{ag.thought}\"\n"
            f"Historial reciente del debate:\n{hist}\n\n"
            f"Expresa tu postura EN VOZ ALTA para el parlamento. "
            f"Puedes responder a lo que han dicho los demas si aplica. "
            f"2-3 frases argumentadas."
        )

        def cb(txt):
            ag.last_speech = txt
            self.slog.append((ag.name, ag.color, txt))
            ag.show_bubble("", frames=310)
            ag.speak_aloud(txt)                    # ← spoken in debate
            self.debate_history.append((ag.name, txt))
            self.speaker_idx  += 1
            self.speaker_busy  = False
            self._next_speaker()

        ag.gen_async(prompt, cb, max_tokens=160)

    # ── Phase E: Final stances (parallel) ────────────────────────────────

    def _final_async(self, ag: Agent):
        hist = "\n".join(f"  {n}: {t}" for n, t in self.debate_history)
        prompt = (
            f"POSTURA FINAL\n"
            f'Pregunta: "{self.question}"\n'
            f"Debate completo:\n{hist}\n"
            f"Tu pensamiento inicial (privado): \"{ag.thought}\"\n\n"
            f"Expresa tu postura FINAL de forma breve y definitiva. "
            f"1-2 frases. Esta es tu ultima palabra antes de votar."
        )

        def cb(txt):
            # Si el LLM falló (timeout, error de conexión...) usamos lo que
            # el agente ya dijo en el debate como postura final, o su
            # pensamiento interno como último recurso.
            if not txt or txt.startswith("["):
                txt = ag.last_speech or ag.thought or "Mi postura ya fue expresada durante el debate."

            ag.final_stance = txt
            self.slog.append((ag.name, ag.color, f"[POSTURA FINAL] {txt}"))
            ag.show_bubble("", frames=370)
            ag.speak_aloud(txt)
            self._final_done += 1

        ag.gen_async(prompt, cb, max_tokens=110)

    # ── Phase F: Voting (parallel) ────────────────────────────────────────

    def _start_voting(self):
        self._sys("[VOTACION] Cada IA emite su voto...")
        for i, ag in enumerate(self.agents):
            ag.state = St.PARL_VOTING
            self._vote_async(ag, delay=i * 0.15)

    def _vote_async(self, ag: Agent, delay: float = 0.0):
        stances = "\n".join(
            f"  {a.name}: {a.final_stance}" for a in self.agents
        )
        prompt = (
            f"VOTACION FINAL\n"
            f'Pregunta original: "{self.question}"\n'
            f"Posturas finales de todos:\n{stances}\n"
            f"Tu postura: \"{ag.final_stance}\"\n\n"
            f"Responde EXACTAMENTE en este formato:\n"
            f"Voto [A FAVOR / EN CONTRA] porque [razon en 1-2 frases].\n"
            f"Solo puedes votar A FAVOR o EN CONTRA. No existe el voto neutral."
        )

        def cb(txt):
            tl = txt.lower()
            if "a favor" in tl or "afavor" in tl:
                vote = "favor"
            else:
                vote = "contra"

            ag.vote          = vote
            ag.vote_reason   = txt
            ag.ready_to_vote = True
            self.vote_counts[vote] += 1

            sym = {"favor": "(+)", "contra": "(-)", "neutral": "(~)"}[vote]
            self.slog.append((ag.name, ag.color,
                              f"{sym} VOTO {vote.upper()}: {txt}"))
            ag.show_bubble("", frames=420)
            ag.speak_aloud(txt)
            self._vote_done += 1

        ag.gen_async(prompt, cb, max_tokens=70, delay=delay)

    # ── Phase G: Consensus generation ─────────────────────────────────────

    def _gen_consensus(self):
        self.conclude_timer = 0
        stances  = "\n".join(
            f"  {ag.name} ({ag.mbti}): {ag.final_stance}"
            for ag in self.agents
        )
        votes_txt = "\n".join(
            f"  {ag.name}: {ag.vote} — {ag.vote_reason}"
            for ag in self.agents
        )
        vc = self.vote_counts

        def run():
            prompt = (
                f"SINTESIS DEL PARLAMENTO\n"
                f'Pregunta debatida: "{self.question}"\n'
                f"Posturas finales:\n{stances}\n"
                f"Votos:\n{votes_txt}\n"
                f"Recuento: A favor={vc['favor']}, "
                f"En contra={vc['contra']}, Neutral={vc['neutral']}\n\n"
                f"Genera:\n"
                f"1. Respuesta consensuada del parlamento (1-2 frases)\n"
                f"2. Postura minoritaria si existe (1 frase)\n"
                f"Se objetivo y sintetiza las perspectivas reales del debate."
            )
            result = _gen(
                prompt,
                system=(
                    "Eres el secretario del Parlamento de IAs. "
                    "Sintetiza el debate de forma neutral, en espanol."
                ),
                max_tokens=150,
            )
            self.consensus = result
            bar = "=" * 38
            self.slog.append(("===", RESULT_CLR, bar))
            self.slog.append(("CONSENSO", RESULT_CLR, f"[RESULTADO] {result}"))
            self.slog.append(("VOTOS", RESULT_CLR,
                              f"(+) {vc['favor']}  (-) {vc['contra']}  (~) {vc['neutral']}"))
            self.slog.append(("===", RESULT_CLR, bar))

            # Persist this parliament so agents remember it next time
            if self.memory is not None:
                self.memory.record_parliament(
                    self.question, self.agents, vc, result
                )

        threading.Thread(target=run, daemon=True).start()

    # ── Helpers ───────────────────────────────────────────────────────────

    def _sys(self, msg: str):
        self.slog.append(("SISTEMA", SYSTEM_CLR, msg))
