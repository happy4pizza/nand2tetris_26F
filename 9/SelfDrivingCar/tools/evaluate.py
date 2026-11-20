"""Stress-test a trained network on fresh traffic it has never seen.

usage: python3 -O evaluate.py WEIGHTS.json RUNS FRAMES      e.g.  python3 -O evaluate.py champion.json 200 10000
"""
import sys, os, json
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim


def one(a):
    net, seed, frames = a
    return sim.run(net, seed, frames)


if __name__ == "__main__":
    net = json.load(open(sys.argv[1])); n = int(sys.argv[2]); frames = int(sys.argv[3])
    with Pool(max(1, (os.cpu_count() or 4) - 2)) as p:
        res = p.map(one, [(net, 5000 + i, frames) for i in range(n)])
    crashes = sorted(r[2] for r in res if r[2] >= 0)
    print("%s: %d runs x %d frames: crashed %d (%.1f%%), mean cars passed %.1f, mean progress %.0f U (max possible %d)" % (
        os.path.basename(sys.argv[1]), n, frames, len(crashes), 100 * len(crashes) / n,
        sum(r[1] for r in res) / n, sum(r[0] for r in res) / n, 16 * frames))
    if crashes:
        print("   crash frames: min %d, median %d" % (crashes[0], crashes[len(crashes) // 2]))
