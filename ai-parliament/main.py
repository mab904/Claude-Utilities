# ─────────────────────────────────────────────────────────────────────────────
#  main.py  –  Parlamento de IAs (entry point)
#
#  Run with:  python main.py
#
#  Requires:
#    - Ollama running locally:  ollama serve
#    - A model pulled, e.g.:    ollama pull llama3.2
#    - pip install pygame requests
# ─────────────────────────────────────────────────────────────────────────────

import os
import sys
from collections import deque

# DPI awareness — must be set before pygame.init() so Windows doesn't
# apply its own blurry DPI scaling on top of pygame's rendering.
import ctypes as _ctypes
try:
    _ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        _ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# Use SDL linear filtering so upscaling is smooth instead of pixelated.
os.environ.setdefault("SDL_RENDER_SCALE_QUALITY", "1")

import pygame

from config import (
    SCREEN_W, SCREEN_H, SIM_W, SIM_H, PANEL_X, PANEL_W,
    FPS, DARK_BG, SIM_BG, BORDER_CLR, MBTI_PROFILES,
    PARLIAMENT_CENTER, PARLIAMENT_RADIUS, THOUGHT_HDR, SPEECH_HDR,
)
from agent import Agent
from parliament import Parliament, Phase
from ui import InputBox, draw_log_panel, draw_header, draw_footer
from memory import MemoryStore
from tts import TTSEngine
from config import TTS_ENABLED_DEFAULT


PHASE_LABELS = {
    Phase.IDLE:       "Vida diaria",
    Phase.ASSEMBLING: "A. Convocatoria",
    Phase.THINKING:   "B. Pensamiento interno",
    Phase.DEBATING:   "C. Debate externo",
    Phase.FINAL:      "E. Postura final",
    Phase.VOTING:     "F. Votacion",
    Phase.CONCLUDING: "G. Resultado",
    Phase.DISSOLVING: "H. Disolucion",
}


def draw_parliament_circle(surf):
    cx, cy = PARLIAMENT_CENTER
    r = PARLIAMENT_RADIUS
    s = pygame.Surface((r * 2 + 60, r * 2 + 60), pygame.SRCALPHA)
    pygame.draw.circle(s, (60, 70, 110, 50), (r + 30, r + 30), r + 28, 2)
    pygame.draw.circle(s, (40, 50, 80, 35),  (r + 30, r + 30), r + 8,  1)
    surf.blit(s, (cx - r - 30, cy - r - 30))
    pygame.draw.circle(surf, (50, 60, 95), (cx, cy), 6)
    pygame.draw.circle(surf, (90, 110, 165), (cx, cy), 6, 1)


def draw_grid(surf):
    for x in range(0, SIM_W, 40):
        pygame.draw.line(surf, (24, 24, 42), (x, 40), (x, SIM_H - 80), 1)
    for y in range(40, SIM_H - 80, 40):
        pygame.draw.line(surf, (24, 24, 42), (0, y), (SIM_W, y), 1)


def main():
    pygame.init()
    pygame.display.set_caption("Parlamento de IAs — Simulacion Multi-Agente")
    # SCALED: pygame renders at SCREEN_W×SCREEN_H logically and scales to window.
    # Mouse coords are always in logical space — no manual transformation needed.
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.RESIZABLE | pygame.SCALED)

    # Maximizar la ventana al arrancar (Windows)
    try:
        hwnd = pygame.display.get_wm_info()["window"]
        _ctypes.windll.user32.ShowWindow(hwnd, 3)  # SW_MAXIMIZE
    except Exception:
        pass

    clock  = pygame.time.Clock()

    # Fonts
    font_lg    = pygame.font.SysFont("Arial",     20, bold=True)
    font_md    = pygame.font.SysFont("Arial",     14)
    font_sm    = pygame.font.SysFont("Arial",     12, bold=True)
    font_xs    = pygame.font.SysFont("Arial",     11)
    font_body  = pygame.font.SysFont("Consolas",  12)
    font_input = pygame.font.SysFont("Arial",     15)

    # Build agents
    agents = [Agent(mbti, prof) for mbti, prof in MBTI_PROFILES.items()]

    # Persistent memory across runs
    memory = MemoryStore()

    # Local Text-to-Speech engine (V to toggle at runtime)
    tts = TTSEngine(enabled=TTS_ENABLED_DEFAULT)
    Agent.set_tts(tts)
    if not tts.available:
        print("[TTS] pyttsx3 not installed — voice disabled. "
              "Install with: pip install pyttsx3")

    # Logs (deque keeps memory bounded)
    thought_log = deque(maxlen=80)
    speech_log  = deque(maxlen=120)

    # Parliament
    parl = Parliament(agents, thought_log, speech_log, memory=memory)

    if memory.count() > 0:
        speech_log.append(("SISTEMA", (115, 175, 255),
                           f"Memoria cargada: {memory.count()} parlamentos previos."))

    # Tell the user once the probe finishes which recall mode is active
    def _announce_mode():
        import time
        for _ in range(40):           # up to ~10 s
            if memory._probe_done:
                speech_log.append((
                    "SISTEMA", (115, 175, 255),
                    f"Memoria — modo de recuperacion: {memory.mode.upper()}"
                ))
                return
            time.sleep(0.25)
    import threading as _t
    _t.Thread(target=_announce_mode, daemon=True).start()

    # Input box
    inputbox = InputBox(font_input)

    # Scrolling
    thought_scroll = 0
    speech_scroll  = 0

    running = True
    while running:
        # ── Events ────────────────────────────────────────────────────────
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False

            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE and parl.phase != Phase.IDLE:
                    parl.interrupt()
                elif ev.key == pygame.K_F2:
                    # F2 toggles TTS (avoids conflict with typing in the input box)
                    new_state = tts.toggle()
                    speech_log.append((
                        "SISTEMA", (115, 175, 255),
                        f"Voz {'ACTIVADA' if new_state else 'DESACTIVADA'}"
                        + ("" if tts.available else " (pyttsx3 no instalado)")
                    ))

            elif ev.type == pygame.MOUSEWHEEL:
                mx, my = pygame.mouse.get_pos()  # SCALED: already in logical coords
                if mx >= PANEL_X:
                    if my < SCREEN_H // 2:
                        thought_scroll = max(0, thought_scroll + ev.y * 18)
                    else:
                        speech_scroll  = max(0, speech_scroll  + ev.y * 18)

            # Input box only accepts events when parliament is idle
            if parl.phase == Phase.IDLE:
                inputbox.disabled = False
                submitted = inputbox.handle_event(ev)
                if submitted:
                    parl.start(submitted)
                    speech_log.append(("USUARIO", (255, 255, 100),
                                       f"PREGUNTA: {submitted}"))
                    speech_scroll = 0
            else:
                inputbox.disabled = True

        # ── Update ────────────────────────────────────────────────────────
        inputbox.update()
        parl.update()

        if parl.phase == Phase.IDLE:
            for ag in agents:
                ag.update_daily(agents, SIM_W, SIM_H - 80)
        elif parl.phase == Phase.ASSEMBLING:
            for ag in agents:
                ag.update_parl_move()
        elif parl.phase == Phase.DISSOLVING:
            for ag in agents:
                ag.update_returning()
        else:
            # Any active parliament phase: agents are seated, just animate
            for ag in agents:
                ag.update_parl_static()

        # ── Draw ──────────────────────────────────────────────────────────────
        screen.fill(DARK_BG)

        # Simulation area
        pygame.draw.rect(screen, SIM_BG, (0, 0, SIM_W, SIM_H))
        draw_grid(screen)
        draw_parliament_circle(screen)

        for ag in agents:
            ag.draw(screen, font_sm, font_xs)

        # Header / footer
        tts_str = "Voz: ON" if tts.enabled else "Voz: OFF"
        if not tts.available:
            tts_str = "Voz: N/D"
        draw_header(screen, font_lg, font_md,
                    f"{PHASE_LABELS[parl.phase]}  |  {tts_str}",
                    len(agents))

        hint = ("ENTER convocar  -  F2 voz on/off  -  ESC interrumpir  -  Rueda raton: scroll"
                if parl.phase == Phase.IDLE else
                "Parlamento activo  -  F2 voz on/off  -  ESC interrumpir")
        draw_footer(screen, font_xs, hint)

        # Input box
        inputbox.draw(screen)

        # Side panels
        ph = (SCREEN_H - 8) // 2
        draw_log_panel(
            screen, PANEL_X + 4, 4, PANEL_W - 8, ph - 4,
            "Pensamientos internos", THOUGHT_HDR,
            list(thought_log),
            font_body, font_lg, font_sm, scroll=thought_scroll,
        )
        draw_log_panel(
            screen, PANEL_X + 4, ph + 4, PANEL_W - 8, ph - 4,
            "Conversacion / Debate", SPEECH_HDR,
            list(speech_log),
            font_body, font_lg, font_sm, scroll=speech_scroll,
        )

        # Border between sim and panels
        pygame.draw.line(screen, BORDER_CLR, (PANEL_X, 0), (PANEL_X, SCREEN_H), 1)

        pygame.display.flip()
        clock.tick(FPS)

    tts.shutdown()
    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
