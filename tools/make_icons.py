#!/usr/bin/env python3
"""Pure-stdlib PNG icon generator for the Kinmiya drink picker PWA.

Renders a neon "highball glass" app icon at 2x supersampling and writes
PNGs for the PWA manifest and the iOS apple-touch-icon.
"""
import math
import struct
import zlib

SS = 2  # supersample factor


def lerp(a, b, t):
    return a + (b - a) * t


def mix(c1, c2, t):
    return tuple(lerp(c1[i], c2[i], t) for i in range(3))


class Canvas:
    def __init__(self, size):
        self.size = size
        self.buf = [[(0.0, 0.0, 0.0) for _ in range(size)] for _ in range(size)]

    def set(self, x, y, color, alpha=1.0):
        if 0 <= x < self.size and 0 <= y < self.size:
            old = self.buf[y][x]
            self.buf[y][x] = tuple(lerp(old[i], color[i], alpha) for i in range(3))

    def fill_bg(self):
        s = self.size
        cx, cy = s * 0.5, s * 0.42
        for y in range(s):
            for x in range(s):
                # vertical base gradient (deep indigo -> violet)
                t = y / s
                base = mix((26, 0, 51), (12, 0, 40), t)
                # radial neon glow (magenta -> cyan)
                d = math.hypot(x - cx, y - cy) / (s * 0.75)
                glow_t = max(0.0, 1.0 - d)
                glow = mix((255, 40, 180), (60, 220, 255), min(1.0, d * 1.3))
                col = mix(base, glow, glow_t * 0.55)
                self.buf[y][x] = col

    def circle(self, cx, cy, r, color, alpha=1.0, soft=1.5):
        s = self.size
        x0, x1 = int(cx - r - 2), int(cx + r + 2)
        y0, y1 = int(cy - r - 2), int(cy + r + 2)
        for y in range(max(0, y0), min(s, y1)):
            for x in range(max(0, x0), min(s, x1)):
                d = math.hypot(x - cx, y - cy)
                a = max(0.0, min(1.0, (r - d) / soft + 0.5))
                if a > 0:
                    self.set(x, y, color, a * alpha)

    def glow_ring(self, cx, cy, r, width, color, alpha=1.0):
        s = self.size
        rr = r + width + 3
        for y in range(max(0, int(cy - rr)), min(s, int(cy + rr))):
            for x in range(max(0, int(cx - rr)), min(s, int(cx + rr))):
                d = math.hypot(x - cx, y - cy)
                a = max(0.0, 1.0 - abs(d - r) / width)
                if a > 0:
                    self.set(x, y, color, a * a * alpha)

    def downsample(self, factor):
        out = Canvas(self.size // factor)
        for y in range(out.size):
            for x in range(out.size):
                r = g = b = 0.0
                for dy in range(factor):
                    for dx in range(factor):
                        c = self.buf[y * factor + dy][x * factor + dx]
                        r += c[0]; g += c[1]; b += c[2]
                n = factor * factor
                out.buf[y][x] = (r / n, g / n, b / n)
        return out

    def to_png(self, path):
        s = self.size
        raw = bytearray()
        for y in range(s):
            raw.append(0)
            for x in range(s):
                c = self.buf[y][x]
                raw += bytes(max(0, min(255, int(round(v)))) for v in c)
        comp = zlib.compress(bytes(raw), 9)

        def chunk(tag, data):
            return (struct.pack(">I", len(data)) + tag + data +
                    struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff))

        png = b"\x89PNG\r\n\x1a\n"
        png += chunk(b"IHDR", struct.pack(">IIBBBBB", s, s, 8, 2, 0, 0, 0))
        png += chunk(b"IDAT", comp)
        png += chunk(b"IEND", b"")
        with open(path, "wb") as f:
            f.write(png)


def draw_glass(c):
    s = c.size
    cx = s * 0.5
    top = s * 0.30
    bot = s * 0.78
    half_top = s * 0.20
    half_bot = s * 0.155

    def half_at(y):
        t = (y - top) / (bot - top)
        return lerp(half_top, half_bot, t)

    liquid_top = lerp(top, bot, 0.32)

    for y in range(int(top), int(bot)):
        hw = half_at(y)
        for x in range(int(cx - hw - 2), int(cx + hw + 2)):
            edge = hw - abs(x - cx)
            a = max(0.0, min(1.0, edge / 2.0 + 0.5))
            if a <= 0:
                continue
            if y >= liquid_top:
                lt = (y - liquid_top) / (bot - liquid_top)
                color = mix((255, 190, 70), (255, 120, 30), lt)  # amber highball
                self_a = a * 0.92
            else:
                color = (210, 245, 255)
                self_a = a * 0.16  # empty upper glass, glassy
            c.set(x, y, color, self_a * 1.0)
        # glass rim highlight
        if y < liquid_top:
            c.set(int(cx - hw), y, (255, 255, 255), 0.5)
            c.set(int(cx + hw), y, (255, 255, 255), 0.5)

    # liquid surface highlight
    for x in range(int(cx - half_at(liquid_top)), int(cx + half_at(liquid_top))):
        c.set(x, int(liquid_top), (255, 240, 200), 0.7)
        c.set(x, int(liquid_top) - 1, (255, 240, 200), 0.35)

    # bubbles
    bubbles = [
        (0.46, 0.62, 0.012), (0.54, 0.55, 0.016), (0.50, 0.70, 0.010),
        (0.57, 0.66, 0.009), (0.44, 0.72, 0.013), (0.52, 0.48, 0.011),
        (0.48, 0.58, 0.008),
    ]
    for bx, by, br in bubbles:
        c.circle(cx if False else s * bx, s * by, s * br, (255, 255, 255), 0.85, soft=1.2)

    # lemon wedge on rim
    lx, ly, lr = s * 0.63, top + 2, s * 0.075
    c.circle(lx, ly, lr, (255, 220, 60), 0.95, soft=1.5)
    c.circle(lx, ly, lr * 0.72, (255, 240, 120), 0.9, soft=1.2)
    c.circle(lx, ly, lr * 0.30, (255, 250, 190), 0.9, soft=1.0)

    # straw
    for t in range(0, 100):
        tt = t / 100.0
        x = lerp(cx + s * 0.02, cx + s * 0.10, tt)
        y = lerp(liquid_top + 4, top - s * 0.06, tt)
        c.circle(x, y, s * 0.012, (80, 230, 255), 0.9, soft=1.0)

    # neon glow around glass
    c.glow_ring(cx, (top + bot) / 2, s * 0.235, s * 0.045, (120, 240, 255), 0.5)


def build(size, path):
    c = Canvas(size * SS)
    c.fill_bg()
    draw_glass(c)
    small = c.downsample(SS)
    small.to_png(path)
    print("wrote", path, small.size)


if __name__ == "__main__":
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    build(512, os.path.join(root, "icons", "icon-512.png"))
    build(192, os.path.join(root, "icons", "icon-192.png"))
    build(180, os.path.join(root, "icons", "apple-touch-icon.png"))
    build(96, os.path.join(root, "icons", "favicon-96.png"))
