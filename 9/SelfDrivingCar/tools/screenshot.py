"""Run the compiled game headless on the VM Emulator and save the screen as PNG files.

usage: python3 screenshot.py OUT_PREFIX STEP_COUNT[:KEYCODE] [STEP_COUNT[:KEYCODE] ...]

Each argument is "run this many million VM steps, then press KEYCODE" (KEYCODE 0 = release all keys,
omitted = no change). A screenshot is saved after every argument, as OUT_PREFIX_1.png, OUT_PREFIX_2.png ...
All screenshots come from ONE run, so later ones continue the earlier game.

A suffix "f" on the step count ("12f", "12f:130") means: run that many million steps, then keep going
until the current frame is completely drawn (the run stops on entry to Hud.draw), so the picture is never
caught half way through a frame. Use it for every game screenshot.
A suffix "w" ("5w") means: run that many million steps, then keep going until the game starts its
1.5 second pause after a crash (the run stops on entry to Sys.wait), so the CRASHED screen is captured.

Example: the title screen, then press space, then a frame about 12 million steps (about 30 frames)
into the game, then a frame about 20 million steps after that with the left arrow held down:
    python3 screenshot.py shot 6:32 0.2:0 12f 20f:130

Notes
  - Headless runs cannot use the emulator's built-in OS, so the OS .vm files are copied into
    build/game/. Everything is therefore much slower than in the GUI: one game frame costs roughly
    0.4 million VM steps here. The game starts after about 1.2 million steps of OS start-up.
  - Key codes: 32 space, 77 M, 81 Q, 82 R, 130 left, 131 up, 132 right, 133 down.
  - PNGs are the 512x256 screen drawn at 2x. Uses only the standard library.
"""
import os, sys, glob, shutil, struct, subprocess, zlib
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import run_tests

KEYBOARD = 24576
SCREEN = 16384


def write_png(path, words, scale=2):
    """words: 8192 ints (the screen map). Bit 0 of each word is the leftmost of its 16 pixels."""
    w, h = 512, 256
    rows = []
    for y in range(h):
        line = bytearray()
        for x in range(w):
            v = words[y * 32 + (x >> 4)] & 0xFFFF
            px = 0 if (v >> (x & 15)) & 1 else 255
            line += bytes([px]) * scale
        for _ in range(scale):
            rows.append(b"\x00" + bytes(line))
    raw = b"".join(rows)

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w * scale, h * scale, 8, 0, 0, 0, 0)) + \
          chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")
    open(path, "wb").write(png)


def main():
    prefix = sys.argv[1]
    plan = []
    for a in sys.argv[2:]:
        steps, _, key = a.partition(":")
        sync = steps[-1] if steps[-1] in "fw" else ""
        plan.append((int(float(steps.rstrip("fw")) * 1000000), int(key) if key else None, sync))
    d = os.path.join(SRC, "build", "game")
    shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
    for f in glob.glob(os.path.join(SRC, "*.jack")):
        shutil.copy(f, d)
    for vm in glob.glob(os.path.join(run_tests.tools_dir(), "OS", "*.vm")):
        shutil.copy(vm, d)
    r = subprocess.run([os.path.join(run_tests.tools_dir(), "JackCompiler.sh"), d], capture_output=True, text=True)
    if "rror" in r.stdout + r.stderr:
        sys.exit(r.stdout + r.stderr)
    tst = "load,\noutput-file Shot.out,\n"
    for n, (steps, key, sync) in enumerate(plan):
        if steps:
            tst += "repeat %d {\n  vmstep;\n}\n" % steps
        if sync == "f":
            tst += "while currentFunction = Hud.draw {\n  vmstep;\n}\nwhile currentFunction <> Hud.draw {\n  vmstep;\n}\n"
        if sync == "w":
            tst += "while currentFunction <> Sys.wait {\n  vmstep;\n}\n"
        if key is not None:
            tst += "set RAM[%d] %d;\n" % (KEYBOARD, key)
        for i in range(0, 8192, 20):
            tst += "output-list " + " ".join("RAM[%d]%%D1.6.1" % (SCREEN + i + j) for j in range(20) if i + j < 8192) + ";\noutput;\n"
    open(os.path.join(d, "Shot.tst"), "w").write(tst)
    r = subprocess.run([os.path.join(run_tests.tools_dir(), "VMEmulator.sh"), os.path.join(d, "Shot.tst")],
                       capture_output=True, text=True, timeout=1800)
    if "End of script" not in r.stdout + r.stderr:
        sys.exit("VM Emulator problem: " + (r.stdout + r.stderr).strip())
    vals = []
    for line in open(os.path.join(d, "Shot.out")):
        if "RAM" in line or not line.strip(): continue
        vals += [int(v) for v in line.strip().strip("|").split("|")]
    for n in range(len(plan)):
        path = "%s_%d.png" % (prefix, n + 1)
        write_png(path, vals[n * 8192:(n + 1) * 8192])
        print("wrote", path)


if __name__ == "__main__":
    main()
