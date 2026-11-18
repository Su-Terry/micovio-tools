"""把 VIO 資料存成 CSV, Ctrl+C 停止。用法: python3 record.py [檔名]"""
import sys
import time

from micolink import MicoVIO

KEYS = ["tracking", "quality", "x", "y", "h", "vx", "vy", "vz", "roll", "pitch", "yaw", "tof"]
out = sys.argv[1] if len(sys.argv) > 1 else time.strftime("vio_%m%d_%H%M%S.csv")
vio, n = MicoVIO(), 0
with open(out, "w") as f:
    f.write("t," + ",".join(KEYS) + "\n")
    try:
        while True:
            for d in vio.read():
                f.write(f"{time.time() - vio.t0:.3f}," + ",".join(f"{d[k]:.4f}" if isinstance(d[k], float) else str(d[k]) for k in KEYS) + "\n")
                n += 1
            time.sleep(0.002)
    except KeyboardInterrupt:
        pass
print(f"\n存了 {n} 筆到 {out}")
