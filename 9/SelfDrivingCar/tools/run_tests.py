"""Check the Jack code against the Python implementation (sim.py) on the real VM Emulator.

usage: python3 run_tests.py            (run the fast tests: units and the six traces, about a minute)
       python3 run_tests.py units      (run one test)
       python3 run_tests.py view       (the drawing test, about five minutes; not part of the default run)

How a test works
  1. A scratch folder build/<test>/ gets: the Jack classes under test, the test's own Main.jack,
     a generated Cases.jack, and the 8 OS .vm files (see below).
  2. JackCompiler.sh compiles it, VMEmulator.sh runs a generated .tst script headless.
  3. The Jack test writes its results into the screen memory map (RAM 16384...), the script dumps
     them to a .out file, and this program compares them with sim.py, value by value.

VM Emulator facts this relies on (all measured)
  - Headless (command-line) runs CANNOT use the emulator's built-in OS, so the OS .vm files from
    tools/OS must be copied into the test folder. (The game itself, run in the GUI, uses the built-in OS.)
  - With the OS as VM code, start-up alone takes about 1.1 million vmsteps.
  - An output-list may hold at most 20 values, and repeat blocks cannot be nested.
  - A script `while RAM[x] <> marker { vmstep; }` stops as soon as the test program is finished.
"""
import sys, os, json, shutil, subprocess, random, glob
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.dirname(HERE)                       # the Jack program folder
sys.path.insert(0, HERE)
import sim, export

BASE = 16384                                      # screen memory map: free scratch RAM in a headless test


def tools_dir():
    d = os.environ.get("N2T_TOOLS")
    if not d:
        w = shutil.which("JackCompiler.sh")
        if w: d = os.path.dirname(os.path.realpath(w))
    if not d or not os.path.isdir(os.path.join(d, "OS")):
        sys.exit("cannot find the nand2tetris tools folder: put it on PATH or set N2T_TOOLS=/path/to/nand2tetris/tools")
    return d


def lets(name, vals):
    return "\n".join("        let %s[%d] = %d;" % (name, i, v) for i, v in enumerate(vals))


def build(name, jack_from_src, extra_files, main_dir=None):
    """Create build/<name>/ with the listed project classes, tests/<main_dir or name>/Main.jack and the OS.
    Several tests can share one Main.jack and differ only in their generated Cases.jack."""
    d = os.path.join(SRC, "build", name)
    shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
    for f in jack_from_src:
        shutil.copy(os.path.join(SRC, f), d)
    shutil.copy(os.path.join(SRC, "tests", main_dir or name, "Main.jack"), d)
    for fname, text in extra_files.items():
        open(os.path.join(d, fname), "w").write(text)
    for vm in glob.glob(os.path.join(tools_dir(), "OS", "*.vm")):
        shutil.copy(vm, d)
    r = subprocess.run([os.path.join(tools_dir(), "JackCompiler.sh"), d], capture_output=True, text=True)
    made = {os.path.basename(p)[:-3] for p in glob.glob(os.path.join(d, "*.vm"))}
    want = {os.path.basename(p)[:-5] for p in glob.glob(os.path.join(d, "*.jack"))}
    if not want <= made:
        sys.exit("compile failed for %s:\n%s%s" % (name, r.stdout, r.stderr))
    n = sum(1 for p in glob.glob(os.path.join(d, "*.vm")) for line in open(p)
            if line.strip() and not line.strip().startswith("//"))
    assert n < 32768, "program too big for the VM Emulator: %d VM commands (limit 32767)" % n
    return d


def run_vm(d, steps, n_values, until_marker=None):
    """Run `steps` vmsteps (or, with until_marker = RAM offset from BASE, until that cell holds 12345,
    giving up after 4 minutes), then dump RAM[BASE .. BASE+n_values-1]. Returns the list of ints."""
    if until_marker is None:
        tst = "load,\noutput-file Test.out,\nrepeat %d {\n  vmstep;\n}\n" % steps
    else:
        tst = "load,\noutput-file Test.out,\nwhile RAM[%d] <> 12345 {\n  vmstep;\n}\n" % (BASE + until_marker)
    for i in range(0, n_values, 20):
        cells = range(i, min(i + 20, n_values))
        tst += "output-list " + " ".join("RAM[%d]%%D1.6.1" % (BASE + c) for c in cells) + ";\noutput;\n"
    open(os.path.join(d, "Test.tst"), "w").write(tst)
    try:
        r = subprocess.run([os.path.join(tools_dir(), "VMEmulator.sh"), os.path.join(d, "Test.tst")],
                           capture_output=True, text=True, timeout=240)
    except subprocess.TimeoutExpired:
        subprocess.run(["pkill", "-f", os.path.join(d, "Test.tst")])
        sys.exit("the Jack test never finished (an OS error halted it, or it has an infinite loop): " + d)
    if "End of script" not in r.stdout + r.stderr:
        sys.exit("VM Emulator problem: " + (r.stdout + r.stderr).strip())
    vals = []
    for line in open(os.path.join(d, "Test.out")):
        if "RAM" in line or not line.strip(): continue
        vals += [int(v) for v in line.strip().strip("|").split("|")]
    return vals


# ------------------------------------------------------------------ test: units
def test_units():
    """Tables + Sensor + Net: 24 car/traffic situations -> 10 readings, 5 distances, control mask, 4 outputs."""
    net = json.load(open(os.path.join(HERE, "champion.json")))
    export.export(net, SRC)
    rng = random.Random(7); cases = []
    for seed in (11, 22, 33):                     # situations sampled from real drives
        tr = []; sim.run(net, seed, 2500, trace=tr, sense_all=True)
        for t in rng.sample(tr, 6):
            cases.append((t[0], t[1], t[6:10], [rng.choice(sim.MASKS) for _ in range(4)]))
    for th in (90, 180, 359, 360, 540, 700):      # awkward headings the network never visits
        cases.append((rng.randint(500, 5900), th, [rng.randint(-4000, 4000), -9000, 3000, -14000],
                      [rng.choice(sim.MASKS), 3, 6, 5]))
    flat, expected = [], []
    for carx, th, rowy, mask in cases:
        flat += [carx, th] + list(rowy) + list(mask)
        x = [0] * 10; dist = [0] * 5
        sim.sense(carx, th, rowy, mask, x, dist)
        act, outs = sim.think(net, x)
        expected += x + dist + [act] + outs
    cases_jack = ("class Cases {\n    function int count() { return %d; }\n    function void fill(Array c) {\n%s\n"
                  "        return;\n    }\n}\n" % (len(cases), lets("c", flat)))
    d = build("units", ["Sensor.jack", "Net.jack", "Tables.jack", "Weights.jack"], {"Cases.jack": cases_jack})
    got = run_vm(d, 12000000, len(expected))
    names = ["traffic%d" % i for i in range(5)] + ["border%d" % i for i in range(5)] + \
            ["dist%d" % i for i in range(5)] + ["mask"] + ["out%d" % i for i in range(4)]
    bad = [(i // 20, names[i % 20], e, g) for i, (e, g) in enumerate(zip(expected, got)) if e != g]
    for case, what, e, g in bad[:10]:
        print("   case %d %s: python %d, jack %d" % (case, what, e, g))
    return len(cases), len(bad)


# ------------------------------------------------------------------ tests: trace
TRACE_MAX = 400                                   # records the driver can log (RAM 16384..24383)
TRACE_NAMES = ["carX", "theta", "speed", "mask", "dead", "passed"] + \
              ["rowY%d" % i for i in range(4)] + ["in%d" % i for i in range(10)]
# Control-mask scripts for mode 1: 16 entries, each held for 24 frames. Found by searching sim.py
# for drives that reach the parts of the collision code the other tests do not.
PATTERN = [1, 1, 9, 9, 1, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5]              # hard left, then right into the border
P_REAR  = [3, 3, 8, 4, 8, 3, 2, 2, 0, 8, 1, 2, 13, 1, 4, 2]             # stops; traffic laps it and hits it from behind
P_TURN  = [1, 1, 5, 13, 9, 5, 9, 5, 1, 4, 5, 13, 1, 9, 1, 5]            # hits a car ahead while turned 5 degrees
P_CORNER = [3, 3, 9, 2, 4, 8, 4, 2, 2, 3, 5, 5, 1, 8, 2, 1]             # a traffic car's corner enters the turned car


def trace_test(name, mode, seed, frames, stride, pattern=PATTERN):
    """The whole simulation (Rng + Sim + Sensor + Net), frame by frame, against sim.run()."""
    net = json.load(open(os.path.join(HERE, "champion.json")))
    export.export(net, SRC)
    tr = []
    if mode == 0:
        sim.run(net, seed, frames, trace=tr, sense_all=True)
    elif mode == 1:
        sim.run(None, seed, frames, trace=tr, sense_all=True, driver=lambda f: pattern[(f // 24) & 15])
    else:
        sim.run(None, seed, frames, trace=tr, sense_all=True, driver=lambda f: 1)
    recs = [t for i, t in enumerate(tr) if i % stride == 0 or (i == len(tr) - 1 and t[4] == 1)]
    assert len(recs) <= TRACE_MAX, "too many records for the driver"
    expected = [v for r in recs for v in r]
    expected += [0] * (TRACE_MAX * 20 - len(expected)) + [12345, len(recs)]
    cases_jack = ("class Cases {\n    function int seed() { return %d; }\n    function int frames() { return %d; }\n"
                  "    function int mode() { return %d; }\n    function int stride() { return %d; }\n"
                  "    function void pattern(Array p) {\n%s\n        return;\n    }\n}\n"
                  % (seed, frames, mode, stride, lets("p", pattern)))
    d = build(name, ["Rng.jack", "Sim.jack", "Sensor.jack", "Net.jack", "Tables.jack", "Weights.jack"],
              {"Cases.jack": cases_jack}, main_dir="trace")
    got = run_vm(d, 0, len(expected), until_marker=TRACE_MAX * 20)
    bad = [(i, e, g) for i, (e, g) in enumerate(zip(expected, got)) if e != g]
    for i, e, g in bad[:8]:
        if i < TRACE_MAX * 20:
            print("   record %d (frame %d) %s: python %d, jack %d" % (
                i // 20, (i // 20) * stride, TRACE_NAMES[i % 20], e, g))
        else:
            print("   %s: python %d, jack %d" % ("marker" if i == TRACE_MAX * 20 else "record count", e, g))
    outcome = "ended alive" if not recs[-1][4] else "crashed on frame %d" % (len(tr) - 1)
    print("   %s: %d records, %s, %d cars passed" % (name, len(recs), outcome, recs[-1][5]))
    return len(recs), len(bad)


def test_trace_ai():     return trace_test("trace_ai", 0, 1234, 1200, 3)
def test_trace_script(): return trace_test("trace_script", 1, 77, 400, 1)
def test_trace_ram():    return trace_test("trace_ram", 2, 2, 400, 1)
def test_trace_rear():   return trace_test("trace_rear", 1, 19015, 400, 1, P_REAR)
def test_trace_turn():   return trace_test("trace_turn", 1, 2151, 400, 1, P_TURN)
def test_trace_corner(): return trace_test("trace_corner", 1, 12222, 400, 1, P_CORNER)


# ------------------------------------------------------------------ test: view
def build_game(name, patches):
    """Create build/<name>/ with the whole game, text patches applied, and the OS. patches = {file: [(old, new)]}."""
    d = os.path.join(SRC, "build", name)
    shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
    for f in glob.glob(os.path.join(SRC, "*.jack")):
        text = open(f).read()
        for old, new in patches.get(os.path.basename(f), []):
            assert old in text, "patch target not found in %s: %s" % (f, old)
            text = text.replace(old, new, 1)
        open(os.path.join(d, os.path.basename(f)), "w").write(text)
    for vm in glob.glob(os.path.join(tools_dir(), "OS", "*.vm")):
        shutil.copy(vm, d)
    r = subprocess.run([os.path.join(tools_dir(), "JackCompiler.sh"), d], capture_output=True, text=True)
    made = {os.path.basename(p)[:-3] for p in glob.glob(os.path.join(d, "*.vm"))}
    want = {os.path.basename(p)[:-5] for p in glob.glob(os.path.join(d, "*.jack"))}
    if not want <= made:
        sys.exit("compile failed for %s:\n%s%s" % (name, r.stdout, r.stderr))
    return d


FRAME_CELL = 24575        # last word of the screen map (bottom right corner): nothing is drawn there
KEYBOARD = 24576
# Test builds write the frame number here right after View.draw, so a script can stop on an exact frame.
P_FRAME = ("                    do View.draw();\n",
           "                    do View.draw();\n                    do Memory.poke(24575, frame + 1);\n")
# Reference renderer: wipe the road view and forget everything drawn before, every frame.
P_FULL = ("        // 1. erase the old rays, then the old car outline\n",
          "        do Screen.setColor(false);\n        do Screen.drawRectangle(0, 0, 255, 255);\n"
          "        do Screen.setColor(true);\n        do Screen.drawRectangle(53, 0, 55, 255);\n"
          "        do Screen.drawRectangle(201, 0, 203, 255);\n        let r = 0;\n"
          "        while (r < 4) { let oldMask[r] = 0; let r = r + 1; }\n        let haveOld = false;\n"
          "        // 1. erase the old rays, then the old car outline\n")
# (what to do, argument): run to a frame and compare the road view, or set the keyboard.
VIEW_SCRIPT = [("shot", 60), ("shot", 250), ("shot", 400), ("shot", 550), ("shot", 700), ("shot", 900),
               ("key", 77), ("frame", 902), ("key", 130),        # M: manual mode, then hold the left arrow
               ("shot", 925), ("shot", 960), ("shot", 1000),     # turning left, drifting toward the border
               ("frame", 3), ("key", 0),                         # crashed, new game has started: release
               ("shot", 40), ("key", 82), ("frame", 2), ("key", 0), ("shot", 30)]   # R: restart


def view_run(d):
    """Run the game through VIEW_SCRIPT. Returns one 256x256 bitmap (list of rows of 0/1) per shot."""
    cells = [16384 + y * 32 + w for y in range(256) for w in range(16)]       # left half of the screen
    tst = "load,\noutput-file Test.out,\nrepeat 6000000 {\n  vmstep;\n}\nset RAM[%d] 32;\n" % KEYBOARD
    tst += "repeat 200000 {\n  vmstep;\n}\nset RAM[%d] 0;\n" % KEYBOARD
    shots = 0
    for what, arg in VIEW_SCRIPT:
        if what == "key":
            tst += "set RAM[%d] %d;\n" % (KEYBOARD, arg)
            continue
        tst += "while RAM[%d] <> %d {\n  vmstep;\n}\n" % (FRAME_CELL, arg)
        if what == "shot":
            shots += 1
            for i in range(0, len(cells), 20):
                tst += "output-list " + " ".join("RAM[%d]%%D1.6.1" % c for c in cells[i:i + 20]) + ";\noutput;\n"
    open(os.path.join(d, "Test.tst"), "w").write(tst)
    try:
        r = subprocess.run([os.path.join(tools_dir(), "VMEmulator.sh"), os.path.join(d, "Test.tst")],
                           capture_output=True, text=True, timeout=1500)
    except subprocess.TimeoutExpired:
        subprocess.run(["pkill", "-f", os.path.join(d, "Test.tst")])
        sys.exit("the game never reached a frame the script was waiting for: " + d)
    if "End of script" not in r.stdout + r.stderr:
        sys.exit("VM Emulator problem: " + (r.stdout + r.stderr).strip())
    vals = []
    for line in open(os.path.join(d, "Test.out")):
        if "RAM" in line or not line.strip(): continue
        vals += [int(v) for v in line.strip().strip("|").split("|")]
    assert len(vals) == shots * len(cells), (len(vals), shots)
    out = []
    for n in range(shots):
        words = vals[n * len(cells):(n + 1) * len(cells)]
        out.append([[(words[y * 16 + (x >> 4)] >> (x & 15)) & 1 for x in range(256)] for y in range(256)])
    return out


def test_view():
    """The road view after many frames of drawing only what changed must equal the same frames drawn from
    scratch. Catches stale pixels, missed erases and missed redraws. Covers AI driving, a manual turn,
    a crash and two restarts."""
    net = json.load(open(os.path.join(HERE, "champion.json")))
    export.export(net, SRC)
    inc = view_run(build_game("view_inc", {"Game.jack": [P_FRAME]}))
    full = view_run(build_game("view_full", {"Game.jack": [P_FRAME], "View.jack": [P_FULL]}))
    labels = ["frame %d" % a for w, a in VIEW_SCRIPT if w == "shot"]
    bad = 0
    for label, a, b in zip(labels, inc, full):
        diff = [(x, y) for y in range(256) for x in range(256) if a[y][x] != b[y][x]]
        black = sum(map(sum, b))
        if diff:
            bad += 1
            print("   %s: %d pixels differ, e.g. %s (incremental has %s there)" % (
                label, len(diff), diff[:6], ["white", "black"][a[diff[0][1]][diff[0][0]]]))
        else:
            print("   %s: identical (%d black pixels)" % (label, black))
    return len(labels), bad


TESTS = {"units": test_units, "trace_ai": test_trace_ai, "trace_script": test_trace_script,
         "trace_ram": test_trace_ram, "trace_rear": test_trace_rear, "trace_turn": test_trace_turn,
         "trace_corner": test_trace_corner, "view": test_view}
SLOW = {"view"}

if __name__ == "__main__":
    failed = False
    for name in (sys.argv[1:] or [t for t in TESTS if t not in SLOW]):
        n, bad = TESTS[name]()
        print("%-12s %s  (%d cases, %d mismatching values)" % (name, "PASS" if bad == 0 else "FAIL", n, bad))
        failed = failed or bad > 0
    sys.exit(1 if failed else 0)
