"""MicoVIO USB-C (Micolink) 讀取。直接執行 = 連線測試。"""
import glob
import os
import struct
import sys
import time

import serial


def frame(msg_id, payload, seq=0):
    body = bytes([0xEF, 1, 0, msg_id, seq & 0xFF, len(payload)]) + payload
    return body + bytes([sum(body) & 0xFF])


def parse(buf):
    """從 buf 取出完整封包 (msg_id, payload), 會消耗 buf。"""
    out = []
    while (i := buf.find(0xEF)) >= 0:
        del buf[:i]
        if len(buf) < 6 or len(buf) < 7 + buf[5]:
            break
        f = bytes(buf[:7 + buf[5]])
        if buf[5] <= 64 and f[-1] == sum(f[:-1]) & 0xFF:
            out.append((f[3], f[6:-1]))
            del buf[:len(f)]
        else:
            del buf[:1]
    else:
        buf.clear()
    return out


def decode(p):
    x, y, z, vx, vy, vz, roll, pitch, yaw = struct.unpack_from("<9f", p, 16)
    return dict(tracking=p[1] == 15, quality=None if p[3] == 255 else p[3],
                t_ms=struct.unpack_from("<I", p, 4)[0], x=x, y=y, h=-z,
                vx=vx, vy=vy, vz=vz, roll=roll, pitch=pitch, yaw=yaw,
                tof=struct.unpack_from("<H", p, 52)[0] / 1000)


class MicoVIO:
    def __init__(self, port=None):
        port = port or os.environ.get("MICOVIO_PORT") or next(iter(sorted(glob.glob("/dev/cu.usbmodem*"))), None)
        if not port:
            sys.exit("找不到 /dev/cu.usbmodem*")
        self.ser = serial.Serial(port, 921600, timeout=0)
        self.buf, self.seq, self.t_hb, self.t0 = bytearray(), 0, 0.0, time.time()

    def read(self):
        """回傳新收到的 VIO 資料 (list of dict)。會定時送 heartbeat 讓模組持續輸出。"""
        if time.time() - self.t_hb > 0.5:
            hb = struct.pack("<IBBBBBI", int((time.time() - self.t0) * 1000), 30, 0, 1, 0, 1, 0)
            self.ser.write(frame(1, hb, self.seq))
            self.seq, self.t_hb = self.seq + 1, time.time()
        self.buf += self.ser.read(self.ser.in_waiting or 1)
        return [decode(p) for m, p in parse(self.buf) if m == 86 and len(p) >= 56]

    def close(self):
        self.ser.close()


if __name__ == "__main__":
    vio, n, t_end = MicoVIO(next((a for a in sys.argv[1:] if a.startswith("/dev/")), None)), 0, time.time() + 5
    while time.time() < t_end:
        for d in vio.read():
            n += 1
    print(f"5 秒收到 {n} 筆 ({n / 5:.0f} Hz)")
    if n:
        print(f"{'追蹤中' if d['tracking'] else '初始化中 (晃一下)'}  x {d['x']:+.2f}  y {d['y']:+.2f}  "
              f"高 {d['h']:.2f}  yaw {d['yaw']:+.0f}°  ToF {d['tof']:.2f} m  品質 {d['quality']}")
