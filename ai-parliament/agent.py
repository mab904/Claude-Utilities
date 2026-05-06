# ─────────────────────────────────────────────────────────────────────────────
#  agent.py  –  Individual AI agent: state machine + rendering + LLM calls
# ─────────────────────────────────────────────────────────────────────────────

import math
import random
import threading
from enum import Enum, auto

import pygame

from ollama_client import generate as _ollama_gen


# ── States ────────────────────────────────────────────────────────────────────

class St(Enum):
    IDLE          = auto()   # at home, still
    WANDERING     = auto()   # walking to a random spot
    APPROACHING   = auto()   # walking toward another agent
    TALKING       = auto()   # casual daily conversation
    PARL_MOVING   = auto()   # walking to parliament seat
    PARL_THINKING = auto()   # generating internal thought
    PARL_DEBATING = auto()   # parliament open debate
    PARL_VOTING   = auto()   # casting vote
    RETURNING     = auto()   # walking back home


DAILY = {St.IDLE, St.WANDERING, St.APPROACHING, St.TALKING}


# ── Agent ─────────────────────────────────────────────────────────────────────

class Agent:

    # Class-level TTS engine, set once from main.py via Agent.set_tts(engine)
    tts_engine = None

    @classmethod
    def set_tts(cls, engine):
        cls.tts_engine = engine

    def __init__(self, mbti: str, profile: dict):
        self.mbti       = mbti
        self.name       = profile["name"]
        self.color      = profile["color"]
        self.label      = profile["label"]
        self.home       = list(profile["home"])
        self.sys_prompt = profile["system_prompt"]

        # Voice (per-agent settings from MBTI profile, with sensible defaults)
        self.voice_idx  = profile.get("voice_idx",  0)
        self.voice_rate = profile.get("voice_rate", 180)

        self.pos    = [float(self.home[0]), float(self.home[1])]
        self.target = list(self.home)
        self.state  = St.IDLE

        # Daily-life timers
        self.idle_timer   = random.randint(90, 420)
        self.talk_timer   = 0
        self.talk_partner: "Agent | None" = None

        # Parliament
        self.parl_pos:     list[float] = [0.0, 0.0]
        self.thought:      str = ""
        self.last_speech:  str = ""
        self.final_stance: str = ""
        self.vote:         str | None = None      # "favor" | "contra" | "neutral"
        self.vote_reason:  str = ""
        self.ready_to_vote: bool = False

        # LLM busy flag
        self.llm_busy = False

        # Speech bubble
        self.bubble_text:      str  = ""
        self.bubble_timer:     int  = 0
        self.bubble_is_thought: bool = False

        # Visual
        self.pulse     = random.uniform(0, math.pi * 2)
        self.pulse_spd = random.uniform(0.025, 0.045)

    # ── Motion ──────────────────────────────────────────────────────────────

    def _move_toward(self, tx: float, ty: float, speed: float = 2.2) -> bool:
        """Step toward (tx, ty). Returns True when arrived."""
        dx, dy = tx - self.pos[0], ty - self.pos[1]
        dist = math.hypot(dx, dy)
        if dist < speed:
            self.pos[0], self.pos[1] = tx, ty
            return True
        self.pos[0] += dx / dist * speed
        self.pos[1] += dy / dist * speed
        return False

    def dist_to(self, other: "Agent") -> float:
        return math.hypot(self.pos[0] - other.pos[0], self.pos[1] - other.pos[1])

    # ── Bubble ──────────────────────────────────────────────────────────────

    def show_bubble(self, text: str, frames: int = 280, thought: bool = False):
        self.bubble_text       = text[:160]
        self.bubble_timer      = frames
        self.bubble_is_thought = thought

    def speak_aloud(self, text: str):
        """Send text to the global TTS engine using this agent's voice."""
        if Agent.tts_engine is not None:
            Agent.tts_engine.speak(text, self.voice_idx, self.voice_rate)

    def _tick_bubble(self):
        if self.bubble_timer > 0:
            self.bubble_timer -= 1
            if self.bubble_timer == 0:
                self.bubble_text = ""

    # ── Async LLM ───────────────────────────────────────────────────────────

    def gen_async(self, prompt: str, callback, max_tokens: int = 150,
                  delay: float = 0.0):
        def _run():
            if delay > 0:
                import time; time.sleep(delay)
            self.llm_busy = True
            result = _ollama_gen(prompt, self.sys_prompt, max_tokens=max_tokens)
            self.llm_busy = False
            callback(result)
        threading.Thread(target=_run, daemon=True).start()

    # ── Daily life update ────────────────────────────────────────────────────

    def update_daily(self, agents: list["Agent"], sw: int, sh: int):
        self._tick_bubble()
        self.pulse = (self.pulse + self.pulse_spd) % (math.pi * 2)

        if self.state not in DAILY:
            return

        if self.state == St.IDLE:
            self.idle_timer -= 1
            if self.idle_timer <= 0:
                self._decide(agents, sw, sh)

        elif self.state == St.WANDERING:
            if self._move_toward(self.target[0], self.target[1]):
                self.state      = St.IDLE
                self.idle_timer = random.randint(80, 320)

        elif self.state == St.APPROACHING:
            p = self.talk_partner
            if p is None or p.state not in DAILY:
                self._go_home(); return
            if self.dist_to(p) < 74:
                self.state      = St.TALKING
                self.talk_timer = random.randint(280, 580)
                if not self.llm_busy:
                    self._gen_greeting()
            else:
                self.target = list(p.pos)
                self._move_toward(self.target[0], self.target[1])

        elif self.state == St.TALKING:
            self.talk_timer -= 1
            if self.talk_timer <= 0:
                self.state        = St.IDLE
                self.idle_timer   = random.randint(80, 260)
                self.talk_partner = None

    def _decide(self, agents: list["Agent"], sw: int, sh: int):
        r = random.random()
        candidates = [a for a in agents if a is not self and a.state in DAILY]
        if r < 0.25 and candidates:
            self.talk_partner = random.choice(candidates)
            self.target       = list(self.talk_partner.pos)
            self.state        = St.APPROACHING
        elif r < 0.55:
            mg = 65
            self.target = [random.randint(mg, sw - mg), random.randint(mg, sh - mg)]
            self.state  = St.WANDERING
        else:
            self.idle_timer = random.randint(150, 480)

    def _go_home(self):
        self.target       = list(self.home)
        self.state        = St.WANDERING
        self.talk_partner = None

    def _gen_greeting(self):
        ctx = random.choice([
            "Saluda casualmente. 1-2 frases.",
            "Comenta algo interesante o curioso que estás pensando. 1-2 frases.",
            "Pregunta cómo está el otro agente. 1 frase.",
            "Haz una observación breve sobre tu entorno o rutina. 1-2 frases.",
            "Comparte una reflexion breve que tienes hoy. 1-2 frases.",
        ])
        def cb(txt):
            self.show_bubble("", 270)
            self.speak_aloud(txt)
        self.gen_async(
            f"Vida diaria — conversación casual.\nTarea: {ctx}\n"
            f"Responde como {self.name} ({self.mbti}). Natural y breve.",
            cb, max_tokens=75,
        )

    # ── Parliament motion helpers ────────────────────────────────────────────

    def update_parl_move(self) -> bool:
        self._tick_bubble()
        self.pulse = (self.pulse + self.pulse_spd) % (math.pi * 2)
        return self._move_toward(self.parl_pos[0], self.parl_pos[1], speed=2.6)

    def update_returning(self) -> bool:
        self._tick_bubble()
        self.pulse = (self.pulse + self.pulse_spd) % (math.pi * 2)
        return self._move_toward(self.home[0], self.home[1], speed=2.6)

    def update_parl_static(self):
        """Keep pulse + bubble alive while sitting in parliament."""
        self._tick_bubble()
        self.pulse = (self.pulse + self.pulse_spd) % (math.pi * 2)

    # ── Reset after parliament ───────────────────────────────────────────────

    def reset_daily(self):
        self.thought      = ""
        self.last_speech  = ""
        self.final_stance = ""
        self.vote         = None
        self.vote_reason  = ""
        self.ready_to_vote = False
        self.state        = St.IDLE
        self.idle_timer   = random.randint(60, 200)
        self.bubble_text  = ""
        self.bubble_timer = 0

    # ── Draw ────────────────────────────────────────────────────────────────

    def draw(self, surf: pygame.Surface,
             font_sm: pygame.font.Font,
             font_xs: pygame.font.Font):
        x, y = int(self.pos[0]), int(self.pos[1])
        R = 24

        # Ghost home ring
        hx, hy = int(self.home[0]), int(self.home[1])
        _draw_circle_alpha(surf, (*self.color, 30), hx, hy, 30, width=2)

        # Glow ring when active
        glowing = self.state in (
            St.TALKING, St.PARL_THINKING, St.PARL_DEBATING, St.PARL_VOTING
        )
        if glowing:
            pr = int(R + 9 + math.sin(self.pulse) * 5)
            alpha = int(75 + math.sin(self.pulse) * 65)
            gcolor = self._glow_color()
            _draw_circle_alpha(surf, (*gcolor, max(0, min(255, alpha))), x, y, pr, width=3)

        # Body circle
        pygame.draw.circle(surf, self.color, (x, y), R)
        pygame.draw.circle(surf, (255, 255, 255), (x, y), R, 2)

        # Vote badge (top-right corner of circle)
        if self.vote:
            vc = {"favor": (70, 220, 70), "contra": (220, 70, 70), "neutral": (190, 190, 70)}
            badge_s = font_xs.render({"favor": "SI", "contra": "NO", "neutral": "~"}[self.vote],
                                     True, vc[self.vote])
            surf.blit(badge_s, (x + R - 4, y - R - 2))
        elif self.ready_to_vote:
            rs = font_xs.render("OK", True, (80, 240, 80))
            surf.blit(rs, (x + R - 4, y - R - 2))

        # Name ABOVE the body, in agent's own color (with dark backing for legibility)
        name_surf = font_sm.render(self.name, True, self.color)
        name_x = x - name_surf.get_width() // 2
        name_y = y - R - 6 - name_surf.get_height()
        pad = 3
        bg = pygame.Surface(
            (name_surf.get_width() + pad * 2, name_surf.get_height() + pad),
            pygame.SRCALPHA,
        )
        bg.fill((10, 10, 20, 165))
        surf.blit(bg, (name_x - pad, name_y - 1))
        surf.blit(name_surf, (name_x, name_y))

        # Thinking indicator — 3 pulsing dots ABOVE the name label
        if self.llm_busy:
            active = int(self.pulse / (math.pi * 2) * 3) % 3
            dot_y = name_y - 14
            for di in range(3):
                alpha = 255 if di == active else 60
                ds = pygame.Surface((10, 10), pygame.SRCALPHA)
                pygame.draw.circle(ds, (255, 235, 80, alpha), (5, 5), 4)
                surf.blit(ds, (x - 9 + di * 9, dot_y - 5))

        # MBTI tag below body, smaller
        ms = font_xs.render(self.mbti, True, self.color)
        surf.blit(ms, (x - ms.get_width() // 2, y + R + 4))

        # State dot (bottom-left)
        dot_color = _STATE_DOTS.get(self.state, (100, 100, 100))
        pygame.draw.circle(surf, dot_color, (x - R + 6, y + R - 6), 5)

        # Bubble — placed ABOVE the name when present
        if self.bubble_text and self.bubble_timer > 0:
            draw_bubble(surf, self.bubble_text, x, name_y - 2,
                        self.color, font_xs, self.bubble_is_thought)

    def _glow_color(self):
        return {
            St.TALKING:       self.color,
            St.PARL_THINKING: (170, 90, 230),
            St.PARL_DEBATING: (240, 200, 60),
            St.PARL_VOTING:   (255, 140, 50),
        }.get(self.state, self.color)


# ── State dot colours ─────────────────────────────────────────────────────────

_STATE_DOTS = {
    St.IDLE:          (80,  80,  100),
    St.WANDERING:     (80,  200, 100),
    St.APPROACHING:   (200, 200, 80),
    St.TALKING:       (80,  220, 255),
    St.PARL_MOVING:   (255, 100, 100),
    St.PARL_THINKING: (190, 90,  240),
    St.PARL_DEBATING: (240, 200, 60),
    St.PARL_VOTING:   (255, 140, 50),
    St.RETURNING:     (90,  240, 160),
}


# ── Drawing helpers ───────────────────────────────────────────────────────────

def _draw_circle_alpha(surf: pygame.Surface, color_a: tuple,
                       cx: int, cy: int, r: int, width: int = 0):
    s = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
    pygame.draw.circle(s, color_a, (r + 2, r + 2), r, width)
    surf.blit(s, (cx - r - 2, cy - r - 2))


def draw_bubble(surf: pygame.Surface, text: str, ax: int, ay: int,
                color: tuple, font: pygame.font.Font, is_thought: bool = False):
    """Render a speech/thought bubble above (ax, ay).
    Empty text draws a small empty speech bubble icon (no text shown)."""

    if not text.strip():
        # Empty speech bubble — white outline, no text, small pointer at bottom
        bw, bh = 38, 22
        bx = ax - bw // 2
        by = ay - bh - 8
        bg = pygame.Surface((bw, bh), pygame.SRCALPHA)
        bg.fill((30, 30, 50, 190))
        surf.blit(bg, (bx, by))
        pygame.draw.rect(surf, (220, 220, 240), (bx, by, bw, bh), 1, border_radius=4)
        pygame.draw.polygon(surf, (220, 220, 240),
                            [(ax - 4, by + bh), (ax + 4, by + bh), (ax, by + bh + 7)])
        return

    # Thought bubble: render full text
    max_w = 210
    words = text.split()
    lines: list[str] = []
    cur: list[str] = []
    for w in words:
        test = " ".join(cur + [w])
        if font.size(test)[0] > max_w - 10 and cur:
            lines.append(" ".join(cur))
            cur = [w]
        else:
            cur.append(w)
    if cur:
        lines.append(" ".join(cur))
    if not lines:
        return

    lh  = font.get_height() + 2
    bw  = max_w
    bh  = len(lines) * lh + 10
    bx  = max(2, ax - bw // 2)
    by  = ay - bh - 6

    bg = pygame.Surface((bw, bh), pygame.SRCALPHA)
    bg.fill((18, 18, 36, 215))
    surf.blit(bg, (bx, by))
    border = (170, 90, 220) if is_thought else color
    pygame.draw.rect(surf, border, (bx, by, bw, bh), 1)

    for i, ln in enumerate(lines):
        c = (200, 160, 240) if is_thought else (230, 230, 245)
        ts = font.render(ln, True, c)
        surf.blit(ts, (bx + 5, by + 5 + i * lh))
