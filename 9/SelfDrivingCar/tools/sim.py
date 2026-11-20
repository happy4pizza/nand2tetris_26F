"""Integer model of the self-driving car game, in Python 3 (standard library only).

Used to train the network and to cross-check the Jack program: both implement the same rules and
must produce exactly the same numbers, frame for frame (tools/run_tests.py compares them).
Every operation used here also exists in Jack:

    +  -  *            on values that stay inside a signed 16-bit word
    /                  integer division that TRUNCATES TOWARD ZERO  (tdiv / int(a / b) below)
    &  <  >  =         bitwise and, comparisons

Run without -O and every product or sum that could overflow 16 bits is asserted (ok()).
Run with -O (training) and the asserts are skipped for speed.

Units
    U      position unit: 1 U = 1/16 of a "world pixel" of the original Java game
                          = 1/32 of a Hack screen pixel (the game is drawn at half scale)
    angle  0..719, one unit = 0.5 degree. 0 = straight up the road. 1..30 = turned LEFT,
           719..690 = turned RIGHT (the heading is clamped to +-15 degrees).
    speed  U per frame, 0..48

Controls
    The network has four outputs. Each one is a switch: output > 0 means "on".
    They are packed into one number, the control mask: 1 accelerate, 2 brake, 4 steer right, 8 steer left.
    Steering self-centres: on a frame with no steering (or both directions at once) the heading
    moves one unit back toward straight ahead.

The car never moves in y: it sits at y = 0 and the traffic rows move relative to it.
Negative y = ahead of the car (up the screen), positive y = behind.
"""
import math

# ---------------------------------------------------------------- constants
ROAD_W   = 4608                    # road width in U (288 world px, 144 screen px)
LANE_X   = (768, 2304, 3840)       # lane centres in U from the left border (lane = 1536 U = 96 world px)
HALF_W   = 400                     # every car: half width  (25 world px)
HALF_L   = 800                     # every car: half length (50 world px)
ACC, FRIC, VMAX, VT = 3, 1, 48, 31 # U/frame: accelerate, friction, top speed, traffic speed
NROWS    = 4                       # traffic rows kept alive (a ring)
SPACING  = 4800                    # 300 world px between rows
WRAP     = NROWS * SPACING         # 19200
Y_BEHIND = 4800                    # a row further behind than this jumps to the front
Y_AHEAD  = Y_BEHIND - WRAP         # -14400: a row further ahead than this jumps to behind
MASKS    = (1, 2, 4, 5, 2, 5)      # lane bit masks (bit0 = left lane) a new row is drawn from:
                                   # left, middle, right, left+right, middle, left+right.
                                   # Two cars side by side in ADJACENT lanes (masks 3 and 6) are left out
                                   # on purpose: the trained network never learned to handle them.
RAY_OFF  = (144, 72, 0, -72, -144) # ray angles relative to heading: +72 +36 0 -36 -72 degrees
RAY_LEN  = 150                     # ray length in screen px (300 world px)
ROAD_PX  = 144                     # road width in screen px
IN_MAX   = 32                      # sensor readings are 0..32
NN_SHIFT = 64                      # hidden-layer divisor
ACT_MAX  = 32                      # hidden activations are clamped to 0..32
W_MAX, B_MAX = 63, 4096            # legal weight / bias range (keeps every layer sum below 32,767)
SIZES    = (10, 12, 8, 4)          # network layer sizes
N_PARAMS = 272                     # 12*(1+10) + 8*(1+12) + 4*(1+8)
THINK_EVERY = 3                    # the network runs on frames 0, 3, 6, ...
SEED_WARMUP = 8
TH_MAX   = 30                      # heading clamp, angle units (15 degrees)
BEAM     = 13                      # the centre traffic ray is 3 parallel beams this many screen px apart

# control mask bits
M_ACCEL, M_BRAKE, M_RIGHT, M_LEFT = 1, 2, 4, 8

# quarter sine table, scale 128: QSIN[i] = round(128 * sin(i * 0.5 deg)), i = 0..180
QSIN = [int(round(128 * math.sin(i * math.pi / 360))) for i in range(181)]

def _sin(a):
    neg = a >= 360
    if neg: a -= 360
    if a > 180: a = 360 - a
    return -QSIN[a] if neg else QSIN[a]

SIN = [_sin(a) for a in range(720)]                 # Jack builds these two 720-entry tables
COS = [SIN[(a + 180) % 720] for a in range(720)]    # at start-up from QSIN, the same way


def ok(v):
    """Assert that v fits a Jack int."""
    assert -32768 <= v <= 32767, v
    return v


def tdiv(a, b):
    """Jack's '/': truncate toward zero. (int(a / b) is exact for 16-bit operands.)"""
    return int(a / b)


def rnd(seed):
    """seed * 171 mod 30269 in Schrage form, so no intermediate value leaves 16 bits.
    seed must be 1..30268 (never 0). Period 30268."""
    q = seed // 177                                 # seed is positive: same as Jack '/'
    seed = ok(171 * (seed - q * 177)) - 2 * q
    if seed < 0: seed += 30269
    return seed


# ---------------------------------------------------------------- network
def think(net, x):
    """net: flat list of 272 ints. For each layer, for each neuron: [bias, w0, w1, ...].
    x: the 10 sensor readings. Returns (control mask 0..15, the 4 raw outputs)."""
    p = 0
    for li in range(3):
        nin, nout = SIZES[li], SIZES[li + 1]
        y = []
        for _ in range(nout):
            s = net[p]; p += 1
            for i in range(nin):
                s += net[p] * x[i]; p += 1
            assert -32768 <= s <= 32767, s
            if li < 2:
                s = int(s / NN_SHIFT)
                if s < 0: s = 0
                if s > ACT_MAX: s = ACT_MAX
            y.append(s)
        x = y
    mask = 0
    if x[0] > 0: mask += M_ACCEL
    if x[1] > 0: mask += M_BRAKE
    if x[2] > 0: mask += M_RIGHT
    if x[3] > 0: mask += M_LEFT
    return mask, x


# ---------------------------------------------------------------- sensors
def sense(carx, theta, rowy, rowmask, out, dist):
    """Cast the 5 rays. All geometry in whole screen px relative to the car centre.
    out[0..4]  = traffic readings, out[5..9] = road-border readings (0 = nothing, 32 = touching)
    dist[0..4] = distance in screen px to the nearest thing on each ray (150 = nothing), for drawing.

    The centre TRAFFIC ray (k = 2) is as wide as the car: three parallel beams, one from the centre
    and one from each side of the car, nearest hit wins. A single thin ray looks straight through
    the 46 px gap between two cars in neighbouring lanes, which the car cannot fit through."""
    cx = int(carx / 32)
    wx = int(BEAM * COS[theta] / 128); wy = -int(BEAM * SIN[theta] / 128)   # side-beam offset, screen px
    for k in range(5):
        a = theta + RAY_OFF[k]
        if a < 0: a += 720
        if a >= 720: a -= 720
        dx = -SIN[a]; dy = -COS[a]                  # ray direction, length 128
        # --- road borders: the vertical lines x = 0 and x = ROAD_PX
        sb = RAY_LEN + 1
        if dx < 0:
            sb = int(ok(cx * 128) / -dx)
        elif dx > 0:
            sb = int(ok((ROAD_PX - cx) * 128) / dx)
        if sb > RAY_LEN: sb = RAY_LEN + 1
        # --- traffic: axis-aligned rectangles [x1..x2] x [y1..y2]
        st = RAY_LEN + 1
        for r in range(NROWS):
            m = rowmask[r]
            if m == 0: continue
            y1 = int((rowy[r] - HALF_L) / 32); y2 = int((rowy[r] + HALF_L) / 32)
            if y1 > RAY_LEN or y2 < -RAY_LEN: continue
            for lane in range(3):
                if m & (1 << lane) == 0: continue
                bx1 = int((LANE_X[lane] - HALF_W - carx) / 32)
                bx2 = int((LANE_X[lane] + HALF_W - carx) / 32)
                for beam in range(3 if k == 2 else 1):
                    if beam == 0:   x1 = bx1;      x2 = bx2;      ya = y1;      yb = y2
                    elif beam == 1: x1 = bx1 - wx; x2 = bx2 - wx; ya = y1 - wy; yb = y2 - wy
                    else:           x1 = bx1 + wx; x2 = bx2 + wx; ya = y1 + wy; yb = y2 + wy
                    if x1 > RAY_LEN or x2 < -RAY_LEN or ya > RAY_LEN or yb < -RAY_LEN: continue
                    if dx > 0 and x1 > 0:               # left face of a car to our right
                        d = int(ok(x1 * 128) / dx)
                        if d < st:
                            h = int(ok(x1 * dy) / dx)
                            if ya <= h <= yb: st = d
                    if dx < 0 and x2 < 0:               # right face of a car to our left
                        d = int(ok(x2 * 128) / dx)
                        if d < st:
                            h = int(ok(x2 * dy) / dx)
                            if ya <= h <= yb: st = d
                    if dy < 0 and yb < 0:               # rear face of a car ahead
                        d = int(ok(yb * 128) / dy)
                        if d < st:
                            h = int(ok(yb * dx) / dy)
                            if x1 <= h <= x2: st = d
                    if dy > 0 and ya > 0:               # front face of a car behind
                        d = int(ok(ya * 128) / dy)
                        if d < st:
                            h = int(ok(ya * dx) / dy)
                            if x1 <= h <= x2: st = d
        out[k]     = 0 if st > RAY_LEN else IN_MAX - int(ok(st * IN_MAX) / RAY_LEN)
        out[k + 5] = 0 if sb > RAY_LEN else IN_MAX - int(ok(sb * IN_MAX) / RAY_LEN)
        dist[k] = min(st, sb, RAY_LEN)


# ---------------------------------------------------------------- collision
def corners(theta):
    """The car's 4 corners relative to its centre, in U:
    front-right, front-left, rear-left, rear-right."""
    sn = SIN[theta]; cs = COS[theta]
    rx = int(25 * cs / 8);  ry = -int(25 * sn / 8)      # half-width  vector (points to the car's right)
    fx = -int(25 * sn / 4); fy = -int(25 * cs / 4)      # half-length vector (points forward)
    return (rx + fx, -rx + fx, -rx - fx, rx - fx), (ry + fy, -ry + fy, -ry - fy, ry - fy)


def crashed(carx, theta, rowy, rowmask):
    sn = SIN[theta]; cs = COS[theta]
    cxs, cys = corners(theta)
    for i in range(4):                                   # road borders
        if carx + cxs[i] < 0 or carx + cxs[i] > ROAD_W: return True
    for r in range(NROWS):
        m = rowmask[r]
        if m == 0: continue
        y = rowy[r]
        if y > 1800 or y < -1800: continue
        for lane in range(3):
            if m & (1 << lane) == 0: continue
            ox = LANE_X[lane] - carx
            if ox > 1400 or ox < -1400: continue
            for i in range(4):                           # (a) one of our corners inside their rectangle
                ex = cxs[i] - ox; ey = cys[i] - y
                if -HALF_W <= ex <= HALF_W and -HALF_L <= ey <= HALF_L: return True
            for sx in (-HALF_W, HALF_W):                 # (b) one of their corners inside our rectangle
                for sy in (-HALF_L, HALF_L):
                    ex = ox + sx; ey = y + sy
                    if ex > 1024 or ex < -1024 or ey > 1024 or ey < -1024: continue
                    ex = int(ex / 16); ey = int(ey / 16)         # world px, at most 64
                    u = ok(ok(ex * cs) - ok(ey * sn))            # across the car, x128
                    v = ok(-ok(ex * sn) - ok(ey * cs))           # along the car,  x128
                    if -3200 <= u <= 3200 and -6400 <= v <= 6400: return True
    return False


# ---------------------------------------------------------------- one episode
def run(net, seed, frames, trace=None, sense_all=False, driver=None):
    """Simulate up to `frames` frames. Returns (progress in U relative to traffic,
    traffic cars passed, frame of the crash or -1).

    driver:    None -> the network drives. Otherwise driver(frame) -> control mask, asked on think frames.
    sense_all: cast rays every frame (what the Jack game does, for drawing). Sensing has no side
               effects, so training leaves this off and only senses on think frames.
    trace:     if a list, one 20-value record per frame is appended (see record() below)."""
    carx = LANE_X[1]; theta = 0; speed = 0; action = M_ACCEL
    rowy = [-6400, -11200, -1600, 3200]
    rowmask = [0, 0, 0, 0]; counted = [False] * NROWS
    for _ in range(SEED_WARMUP): seed = rnd(seed)
    seed = rnd(seed); rowmask[0] = MASKS[seed % 6]
    seed = rnd(seed); rowmask[1] = MASKS[seed % 6]
    x = [0] * 10; dist = [RAY_LEN] * 5
    progress = 0; passed = 0; dead = False
    for f in range(frames):
        # 1. the car, using the control mask chosen earlier
        if action & M_ACCEL: speed += ACC
        if action & M_BRAKE:
            speed -= ACC
            if speed < 0: speed = 0
        if speed > 0:
            th = theta if theta < 360 else theta - 720          # signed heading
            steer = action & 12
            if steer == M_RIGHT: th -= 1
            elif steer == M_LEFT: th += 1
            elif th > 0: th -= 1                                # self-centring
            elif th < 0: th += 1
            if th > TH_MAX: th = TH_MAX
            if th < -TH_MAX: th = -TH_MAX
            theta = th if th >= 0 else th + 720
        if speed > VMAX: speed = VMAX
        if speed > 0: speed -= FRIC
        carx -= int(ok(speed * SIN[theta]) / 128)
        fwd = int(ok(speed * COS[theta]) / 128)
        # 2. traffic rows slide by (our forward speed - their speed); rows are recycled as a ring
        rel = fwd - VT
        progress += rel
        for r in range(NROWS):
            y = rowy[r] + rel
            if y > Y_BEHIND:
                y -= WRAP; seed = rnd(seed); rowmask[r] = MASKS[seed % 6]; counted[r] = False
            elif y < Y_AHEAD:                            # traffic pulled away and comes round from behind:
                y += WRAP; seed = rnd(seed); rowmask[r] = MASKS[seed % 6]; counted[r] = True   # not a pass
            rowy[r] = ok(y)
            if y < -2 * HALF_L: counted[r] = False       # fully ahead of us: can be passed (again)
            if (not counted[r]) and y > 2 * HALF_L:      # their front bumper is behind our rear bumper
                counted[r] = True
                m = rowmask[r]
                passed += (m & 1) + ((m >> 1) & 1) + ((m >> 2) & 1)
        # 3. collision
        dead = crashed(carx, theta, rowy, rowmask)
        # 4. sensors   5. decision for the following frames
        thinking = (f % THINK_EVERY == 0)
        if thinking or sense_all:
            sense(carx, theta, rowy, rowmask, x, dist)
        if thinking and not dead:
            if driver is None: action = think(net, x)[0]
            else: action = driver(f)
        if trace is not None:
            trace.append(record(carx, theta, speed, action, dead, passed, rowy, x))
        if dead: break
    return progress, passed, (f if dead else -1)


def record(carx, theta, speed, action, dead, passed, rowy, x):
    """The 20 values the Jack trace test logs per frame, in this order."""
    return [carx, theta, speed, action, 1 if dead else 0, passed] + list(rowy) + list(x)


def worst_case_sums(net):
    """Largest |sum| each layer could ever reach with THIS net (inputs/activations 0..32)."""
    out = []; p = 0
    for li in range(3):
        worst = 0
        for _ in range(SIZES[li + 1]):
            b = net[p]; p += 1
            pos = sum(32 * w for w in net[p:p + SIZES[li]] if w > 0)
            neg = sum(32 * w for w in net[p:p + SIZES[li]] if w < 0)
            p += SIZES[li]
            worst = max(worst, abs(b + pos), abs(b + neg))
        out.append(worst)
    return out


if __name__ == "__main__":
    import random
    assert QSIN[0] == 0 and QSIN[180] == 128 and len(QSIN) == 181
    s = 1; seen = set()
    for _ in range(30268):
        s = rnd(s); assert 1 <= s <= 30268; seen.add(s)
    assert len(seen) == 30268 and s == 1
    print("rng: full period 30268, all intermediates inside 16 bits")
    rng = random.Random(1)
    for t in range(300):
        net = []
        for li in range(3):
            for _ in range(SIZES[li + 1]):
                net.append(rng.randint(-B_MAX, B_MAX))
                net += [rng.randint(-W_MAX, W_MAX) for _ in range(SIZES[li])]
        assert len(net) == N_PARAMS
        run(net, 1 + t, 1500, sense_all=True)
    print("300 random networks x 1500 frames with every overflow assert on: OK")
    print("worst-case layer sums with all weights at +63 and biases at +4096:",
          [10 * 32 * 63 + 4096, 12 * 32 * 63 + 4096, 8 * 32 * 63 + 4096], "(limit 32767)")
    for sd in (1, 2, 3, 4, 5):
        print("always accelerate, seed %d -> (progress, passed, crash frame) = %s" % (sd, run(None, sd, 4000, driver=lambda f: M_ACCEL),))
