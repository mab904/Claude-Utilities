# ─────────────────────────────────────────────────────────────────────────────
#  ui.py  –  Side panels (thoughts / speech), input box, status header
# ─────────────────────────────────────────────────────────────────────────────

try:
    import win32clipboard as _w32cb
    _HAS_W32CB = True
except ImportError:
    _HAS_W32CB = False

import pygame

from config import (
    PANEL_X, PANEL_W, SCREEN_H, SIM_W,
    PANEL_BG, BORDER_CLR, TEXT_CLR, DIM_CLR,
    THOUGHT_HDR, SPEECH_HDR, INPUT_BG, RESULT_CLR, SYSTEM_CLR, WHITE,
)


# ── Clipboard helpers (Windows) ──────────────────────────────────────────────

def _clipboard_get() -> str:
    if not _HAS_W32CB:
        return ""
    try:
        _w32cb.OpenClipboard()
        try:
            text = _w32cb.GetClipboardData(_w32cb.CF_UNICODETEXT)
        finally:
            _w32cb.CloseClipboard()
        return text.replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ')
    except Exception:
        return ""


# ── Word wrap ────────────────────────────────────────────────────────────────

def wrap_text(text: str, font: pygame.font.Font, max_w: int) -> list[str]:
    out: list[str] = []
    for raw in text.split("\n"):
        words = raw.split(" ")
        line  = ""
        for w in words:
            test = (line + " " + w).strip()
            if font.size(test)[0] <= max_w:
                line = test
            else:
                if line:
                    out.append(line)
                line = w
        if line:
            out.append(line)
        if not raw:
            out.append("")
    return out


# ── Panel renderer ───────────────────────────────────────────────────────────

def draw_log_panel(surf: pygame.Surface, x: int, y: int, w: int, h: int,
                   title: str, header_color: tuple,
                   entries, font_text: pygame.font.Font,
                   font_header: pygame.font.Font, font_meta: pygame.font.Font,
                   scroll: int = 0):
    """Draw a scrolling log panel.

    `entries` is iterable of (name, color, text).
    `scroll` is # of pixels to shift content up (0 = newest at bottom).
    """
    pygame.draw.rect(surf, PANEL_BG, (x, y, w, h))
    pygame.draw.rect(surf, BORDER_CLR, (x, y, w, h), 1)

    # Title bar
    bar_h = 30
    pygame.draw.rect(surf, header_color, (x, y, w, bar_h))
    ts = font_header.render(title, True, WHITE)
    surf.blit(ts, (x + 10, y + 7))

    # Build flat list of rendered lines (name header + wrapped body, oldest→newest)
    inner_x = x + 8
    inner_y = y + bar_h + 6
    inner_w = w - 16
    inner_h = h - bar_h - 12
    line_h  = font_text.get_height() + 1

    rendered: list[tuple[pygame.Surface, int]] = []  # (surface, indent)

    for entry in entries:
        try:
            name, color, body = entry
        except Exception:
            continue

        meta = font_meta.render(f"{name}", True, color)
        rendered.append((meta, 0))

        for ln in wrap_text(body, font_text, inner_w - 8):
            txt_color = (
                RESULT_CLR  if name in ("CONSENSO", "VOTOS", "===") else
                SYSTEM_CLR  if name == "SISTEMA" else
                TEXT_CLR
            )
            ts = font_text.render(ln, True, txt_color)
            rendered.append((ts, 8))

        rendered.append((None, 0))   # spacer

    # Total content height
    content_h = sum(line_h for s, _ in rendered if s is not None) \
              + sum(4      for s, _ in rendered if s is None)

    # Auto-anchor newest at bottom (scroll=0). scroll>0 = scroll up into history.
    if content_h <= inner_h:
        start_y = inner_y
    else:
        max_scroll = content_h - inner_h
        scroll = min(scroll, max_scroll)
        start_y = inner_y + inner_h - content_h + scroll

    # Clip & draw
    prev_clip = surf.get_clip()
    surf.set_clip(pygame.Rect(x, inner_y, w, inner_h))

    cy = start_y
    for s, indent in rendered:
        if s is None:
            cy += 4
            continue
        if cy + line_h >= inner_y and cy <= inner_y + inner_h:
            surf.blit(s, (inner_x + indent, cy))
        cy += line_h

    surf.set_clip(prev_clip)


# ── Header / status bar ──────────────────────────────────────────────────────

def draw_header(surf: pygame.Surface,
                font_lg: pygame.font.Font, font_md: pygame.font.Font,
                phase_name: str, n_agents: int):
    pygame.draw.rect(surf, (12, 12, 24), (0, 0, SIM_W, 40))
    pygame.draw.line(surf, BORDER_CLR, (0, 40), (SIM_W, 40), 1)

    title = font_lg.render("Parlamento de IAs", True, WHITE)
    surf.blit(title, (12, 8))

    info = font_md.render(
        f"Fase: {phase_name}   |   Agentes: {n_agents}",
        True, (180, 200, 240)
    )
    surf.blit(info, (SIM_W - info.get_width() - 12, 13))


# ── Footer hint bar ──────────────────────────────────────────────────────────

def draw_footer(surf: pygame.Surface, font_sm: pygame.font.Font, hint: str):
    y = SCREEN_H - 24
    pygame.draw.rect(surf, (12, 12, 24), (0, y, SIM_W, 24))
    pygame.draw.line(surf, BORDER_CLR, (0, y), (SIM_W, y), 1)
    s = font_sm.render(hint, True, DIM_CLR)
    surf.blit(s, (10, y + 5))


# ── Input box ────────────────────────────────────────────────────────────────

class InputBox:
    """Text input below the simulation canvas."""

    def __init__(self, font: pygame.font.Font):
        self.font   = font
        self.rect   = pygame.Rect(10, SCREEN_H - 70, SIM_W - 20, 38)
        self.text   = ""
        self.active = True
        self.cursor_visible = True
        self.cursor_timer   = 0
        self.placeholder    = "Escribe una pregunta y pulsa ENTER para convocar al parlamento..."
        self.disabled       = False

    def handle_event(self, ev) -> str | None:
        """Returns submitted text on ENTER, else None."""
        if self.disabled or not self.active:
            return None

        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_RETURN:
                if self.text.strip():
                    submitted = self.text.strip()
                    self.text = ""
                    return submitted
            elif ev.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif ev.key == pygame.K_ESCAPE:
                self.text = ""
            elif ev.key == pygame.K_v and (ev.mod & pygame.KMOD_CTRL):
                clip = _clipboard_get()
                if clip:
                    space = 200 - len(self.text)
                    self.text += clip[:space]
            else:
                ch = ev.unicode
                if ch and ch.isprintable() and len(self.text) < 200:
                    self.text += ch
        return None

    def update(self):
        self.cursor_timer = (self.cursor_timer + 1) % 60
        self.cursor_visible = self.cursor_timer < 30

    def draw(self, surf: pygame.Surface):
        bg = INPUT_BG if not self.disabled else (24, 24, 38)
        pygame.draw.rect(surf, bg, self.rect, border_radius=6)
        border = (90, 130, 220) if (self.active and not self.disabled) else BORDER_CLR
        pygame.draw.rect(surf, border, self.rect, 1, border_radius=6)

        inner_w = self.rect.width - 18  # usable text width inside the box

        if self.disabled:
            display = "[Parlamento en sesion — espera a que termine]"
            color   = DIM_CLR
            text_x  = self.rect.x + 8
        elif self.text:
            display = self.text
            color   = WHITE
            text_w  = self.font.size(display)[0]
            # Scroll so cursor (end of text) is always visible
            if text_w > inner_w:
                text_x = self.rect.x + 8 - (text_w - inner_w)
            else:
                text_x = self.rect.x + 8
        else:
            display = self.placeholder
            color   = DIM_CLR
            text_x  = self.rect.x + 8

        ts     = self.font.render(display, True, color)
        text_y = self.rect.y + (self.rect.h - ts.get_height()) // 2

        prev_clip = surf.get_clip()
        surf.set_clip(self.rect.inflate(-6, -4))
        surf.blit(ts, (text_x, text_y))
        surf.set_clip(prev_clip)

        # Cursor — always drawn at the right edge when text overflows
        if self.active and not self.disabled and self.cursor_visible and self.text:
            text_w = self.font.size(self.text)[0]
            cx = self.rect.x + 8 + min(text_w, inner_w) + 1
            cy = self.rect.y + 7
            pygame.draw.line(surf, WHITE, (cx, cy), (cx, cy + self.rect.h - 14), 2)
