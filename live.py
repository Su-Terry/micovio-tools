"""即時軌跡。r = 設原點, c = 清軌跡。每 2 秒存 live.png。"""
import math
import threading
import time
from collections import deque

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

from micolink import MicoVIO

vio, lock = MicoVIO(), threading.Lock()
S = dict(d=None, xy=deque(maxlen=30000), t=deque(maxlen=1800), h=deque(maxlen=1800),
         tof=deque(maxlen=1800), o=None, path=0.0, run=True, snap=0.0)


def reader():
    while S["run"]:
        for d in vio.read():
            with lock:
                S["d"] = d
                if not d["tracking"]:
                    continue
                S["o"] = S["o"] or (d["x"], d["y"])
                p = (d["x"] - S["o"][0], d["y"] - S["o"][1])
                if S["xy"]:
                    S["path"] += math.dist(p, S["xy"][-1])
                S["xy"].append(p)
                for k, v in (("t", time.time() - vio.t0), ("h", d["h"]), ("tof", d["tof"])):
                    S[k].append(v)
        time.sleep(0.002)


def key(ev):
    with lock:
        if ev.key in ("r", "c"):
            S["xy"].clear()
            S["path"] = 0.0
        if ev.key == "r" and S["d"]:
            S["o"] = (S["d"]["x"], S["d"]["y"])


def update(_):
    with lock:
        d, xy, t, h, tof = S["d"], list(S["xy"]), list(S["t"]), list(S["h"]), list(S["tof"])
    if not d:
        return ()
    if xy:
        xs, ys = zip(*xy)
        trail.set_data(ys, xs)
        dot.set_data([ys[-1]], [xs[-1]])
        a = math.radians(d["yaw"])
        head.set_data([ys[-1], ys[-1] + 0.12 * math.sin(a)], [xs[-1], xs[-1] + 0.12 * math.cos(a)])
        span = max(0.5, 1.2 * max(map(abs, xs + ys)))
        ax1.set_xlim(-span, span)
        ax1.set_ylim(-span, span)
    if t:
        lh.set_data(t, h)
        lt.set_data(t, tof)
        ax2.set_xlim(max(0, t[-1] - 30), t[-1] + 0.5)
        ax2.set_ylim(0, max(h + tof) + 0.2)
    off = math.dist(xy[-1], (0, 0)) if xy else 0
    info.set_text(f"{'追蹤中' if d['tracking'] else '初始化中 (晃一下)'}  品質 {d['quality']}  |  "
                  f"x {d['x']:+.2f}  y {d['y']:+.2f}  高 {d['h']:.2f}  yaw {d['yaw']:+.0f}°  ToF {d['tof']:.2f} m  |  "
                  f"路徑 {S['path']:.2f} m  離原點 {off:.2f} m")
    if time.time() - S["snap"] > 2:
        S["snap"] = time.time()
        fig.savefig("live.png", dpi=70)
    return ()


plt.rcParams.update({"font.sans-serif": ["Heiti TC", "PingFang TC", "Arial Unicode MS", "DejaVu Sans"],
                     "axes.unicode_minus": False})
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6), gridspec_kw={"width_ratios": [1.2, 1]})
(trail,), (dot,), (head,) = ax1.plot([], [], lw=1), ax1.plot([], [], "o"), ax1.plot([], [], lw=2.5)
ax1.plot(0, 0, "k+", ms=14)
ax1.set(title="俯視軌跡 [m]", xlabel="y (右)", ylabel="x (前 / 箭頭)", aspect="equal")
(lh,), (lt,) = ax2.plot([], [], label="VIO 高度"), ax2.plot([], [], label="ToF", alpha=0.7)
ax2.set(title="高度 [m]", xlabel="時間 [s]")
for ax in (ax1, ax2):
    ax.grid(alpha=0.3)
ax2.legend(loc="upper left")
info = fig.text(0.01, 0.01, "等待資料 ... (上電約 12 秒)", fontsize=10)
fig.canvas.mpl_connect("key_press_event", key)
threading.Thread(target=reader, daemon=True).start()
anim = FuncAnimation(fig, update, interval=50, cache_frame_data=False)
plt.tight_layout(rect=(0, 0.04, 1, 1))
plt.show()
S["run"] = False
off = math.dist(S["xy"][-1], (0, 0)) if S["xy"] else 0
print(f"路徑 {S['path']:.2f} m, 離原點 {off:.3f} m" + (f", 漂移 {off / S['path']:.1%}" if S["path"] > 1 else ""))
