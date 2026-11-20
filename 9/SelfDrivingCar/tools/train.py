"""Genetic algorithm that trains the integer network directly on the integer simulator (sim.py).

usage: python3 -O train.py POP GENERATIONS SEEDS_PER_GEN OUT.json [INIT.json] [--pen N] [--masks a,b,c,d,e,f]

    POP             population size
    GENERATIONS     how many generations to run
    SEEDS_PER_GEN   traffic layouts every network is driven on each generation (new ones each time)
    OUT.json        where the best network found so far is written (the "champion")
    INIT.json       optional: start from this network instead of from random ones
    --pen N         score lost for a crash (default 4000). A larger value makes crashes costlier.
    --masks ...     six lane masks to TRAIN on instead of sim.MASKS, e.g. 1,2,4,3,5,6 for harder
                    traffic that includes two cars in adjacent lanes. The champion is still chosen
                    on the real traffic (sim.MASKS).

Score of one drive = distance gained on the traffic stream (U) - N if it crashed.
The champion is the network with the best average score on a FIXED set of validation layouts,
so one lucky generation cannot win.

Standard library only. -O switches off the simulator's overflow asserts (about twice as fast);
export.py and run_tests.py run with them on.
"""
import random, sys, json, time, os
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim

FRAMES    = 3000                        # length of one drive
VAL_SEEDS = list(range(20001, 20097))   # 96 fixed validation layouts
HEAVY     = 0.10                        # share of children that get a large mutation (keeps exploring)


def layout():
    """(index, is_bias) for each of the 272 parameters."""
    idx = []; p = 0
    for li in range(3):
        for _ in range(sim.SIZES[li + 1]):
            idx.append((p, True)); p += 1
            for _ in range(sim.SIZES[li]):
                idx.append((p, False)); p += 1
    return idx
LAYOUT = layout()


def random_net(rng):
    return [rng.randint(-2048, 2048) if b else rng.randint(-sim.W_MAX, sim.W_MAX) for _, b in LAYOUT]


def mutate(net, rng, rate, strength):
    out = list(net)
    for i, b in LAYOUT:
        if rng.random() < rate:
            if b: out[i] = max(-sim.B_MAX, min(sim.B_MAX, out[i] + rng.randint(-32 * strength, 32 * strength)))
            else: out[i] = max(-sim.W_MAX, min(sim.W_MAX, out[i] + rng.randint(-strength, strength)))
    return out


def cross(a, b, rng):
    return [x if rng.random() < 0.5 else y for x, y in zip(a, b)]


REAL_MASKS = sim.MASKS


def score(args):
    """Average score of one network over several traffic layouts."""
    net, seeds, pen, masks = args
    sim.MASKS = masks                   # worker processes: training traffic or the real traffic
    total = 0; crashes = 0; passed = 0; progress = 0
    for s in seeds:
        pr, pa, cr = sim.run(net, s, FRAMES)
        total += pr - (pen if cr >= 0 else 0)
        crashes += cr >= 0; passed += pa; progress += pr
    return total / len(seeds), crashes, passed, progress / len(seeds)


def main():
    args = sys.argv[1:]
    pen = 4000
    if "--pen" in args:
        i = args.index("--pen"); pen = int(args[i + 1]); del args[i:i + 2]
    masks = REAL_MASKS
    if "--masks" in args:
        i = args.index("--masks"); masks = tuple(int(v) for v in args[i + 1].split(",")); del args[i:i + 2]
        assert len(masks) == 6
    pop_n, gens, nseeds, out = int(args[0]), int(args[1]), int(args[2]), args[3]
    rng = random.Random(12345)
    if len(args) > 4:
        base = json.load(open(args[4]))
        pop = [base] + [mutate(base, rng, 0.08, 12) for _ in range(pop_n - 1)]
    else:
        pop = [random_net(rng) for _ in range(pop_n)]
    t0 = time.time(); champ = None
    with Pool(max(1, (os.cpu_count() or 4) - 2)) as pool:
        for g in range(gens):
            seeds = [rng.randint(1, 30000) for _ in range(nseeds)]
            res = pool.map(score, [(n, seeds, pen, masks) for n in pop], chunksize=4)
            order = sorted(range(pop_n), key=lambda i: -res[i][0])
            elite = [pop[i] for i in order[:pop_n // 8]]
            note = ""
            for n, v in zip(elite[:3], pool.map(score, [(n, VAL_SEEDS, pen, REAL_MASKS) for n in elite[:3]])):
                if champ is None or v[0] > champ[0]:
                    champ = (v[0], n)
                    json.dump(n, open(out, "w"))
                    note = "  <- new champion: validation crashes %d/%d, cars passed per drive %.2f, progress %.0f" % (
                        v[1], len(VAL_SEEDS), v[2] / len(VAL_SEEDS), v[3])
            b = res[order[0]]
            print("gen %3d  best %7.0f  crashes %d/%d  median %7.0f  %4.0fs%s" % (
                g, b[0], b[1], nseeds, res[order[pop_n // 2]][0], time.time() - t0, note), flush=True)
            nxt = elite[:6] + [champ[1]]
            while len(nxt) < pop_n:
                a, c = rng.choice(elite), rng.choice(elite)
                child = cross(a, c, rng) if rng.random() < 0.5 else list(a)
                nxt.append(mutate(child, rng, 0.25, 24) if rng.random() < HEAVY else mutate(child, rng, 0.08, 12))
            pop = nxt


if __name__ == "__main__":
    main()
