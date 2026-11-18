# 如何在 Mac 上用 Python 讀取 MicoVIO 定位資料

MicoVIO 是 MicoAir 的下視 VIO 模組，模組內部自己算好位置、速度、姿態和離地高度。這篇教你用 USB-C 把它接上 Mac，用 Python 讀出定位資料並畫出即時軌跡。

內容分成**已實測**和**未實測**兩部分。已實測又分兩種：

- **實機**：接上真的模組跑過
- **重播**：用實機錄到的資料（`data/`）重播測過，還沒接真模組跑

## 前置需求

- MicoVIO 模組
- 能傳資料的 USB-C 線（有些線只能充電）
- macOS + Python 3.8 以上

```bash
pip install -r requirements.txt
```

## 第一部分：已實測

### Step 1：找到序列埠（實機）

USB-C 接上後，Mac 會把 MicoVIO 認成一個序列埠。

```bash
ls /dev/cu.usb*
```

**Output:**

```text
/dev/cu.usbmodem101
```

**Explanation:** 編號每台電腦可能不同，程式會自動找 `/dev/cu.usbmodem*`。Mac 的相機清單裡沒有它，所以 USB 拿不到鏡頭影像。

### Step 2：先打招呼，模組才會輸出（實機）

USB 口講的是 MicoAir 自家的 Micolink 協定，不是 MAVLink。電腦不先送 heartbeat（msg 1），模組一個 byte 都不送。

**Output（探測實驗）:**

```text
只聽 5 秒                    → 0 bytes
送 MAVLink heartbeat 6 秒     → 0 bytes
送 Micolink heartbeat 6 秒    → 34887 bytes，msg 86 x545
```

**Explanation:** msg 86 就是 VIO 資料。打過招呼後模組會持續輸出，`micolink.py` 每 0.5 秒自動補送一次。

### Step 3：讀取並解碼（重播）

[`micolink.py`](micolink.py) 負責連線、打招呼、解碼，另外兩支程式都 import 它。直接執行就是 5 秒連線測試。

```python
from micolink import MicoVIO

vio = MicoVIO()            # 自動找 /dev/cu.usbmodem*
while True:
    for d in vio.read():   # 每筆是一個 dict
        print(d["x"], d["y"], d["h"], d["yaw"], d["tracking"])
```

```bash
python3 micolink.py
```

**Output（範例）:**

```text
5 秒收到 285 筆 (57 Hz)
追蹤中  x +0.02  y +0.04  高 0.51  yaw -2°  ToF 0.52 m  品質 80
```

**Explanation:** 範例的頻率和數值來自實機錄到的資料。顯示「初始化中」就輕輕晃一下模組，靜止不會開始追蹤。

### Step 4：畫即時軌跡（重播）

```bash
python3 live.py
```

**Output:** 跳出一個視窗，左邊是俯視軌跡，右邊是高度與 ToF。關掉視窗後 Terminal 印出：

```text
路徑 4.84 m, 離原點 0.101 m, 漂移 2.1%
```

**Explanation:** 按 `r` 把目前位置設成原點，按 `c` 清軌跡。繞一圈回到起點再關視窗，就是漂移測試。畫面每 2 秒存成 `live.png`。

### Step 5：存成 CSV（重播）

```bash
python3 record.py
```

**Output:**

```text
存了 2526 筆到 vio_1118_183000.csv
```

**Explanation:** 按 Ctrl+C 停止。沒給檔名就用時間當檔名，欄位是 `t, tracking, quality, x, y, h, vx, vy, vz, roll, pitch, yaw, tof`。

### 實測數據與已知限制（實機，2026-11-18 手持）

| 項目 | 結果 |
| --- | --- |
| 更新率 | 約 57 Hz |
| 漂移 | 走 4.84 m 回到起點差 10 cm，約 2.1%（官方典型約 1%） |
| 座標方向 | x = 箭頭方向（前），y = 右，高度 = −z |
| 高度來源 | 幾乎就是 ToF（相關係數 0.91），地面有東西會跟著跳 |
| 初始化 | 靜止不會開始追蹤，晃一下約半秒就開始 |
| 鏡頭影像 | USB 拿不到 |

**常見錯誤：** 在 zsh 裡，指令後面接 `# 註解` 會被當成參數，導致 `could not open port #`。指令後面不要加註解。

## 第二部分：未實測

以下內容來自官方文件或推測，實測後移到第一部分。

| 項目 | 要確認什麼 | 怎麼測 |
| --- | --- | --- |
| 接飛控 | GVRT 4-pin 輸出 MAVLink ODOMETRY + DISTANCE_SENSOR（921600） | 接 TELEM，在 QGC MAVLink Inspector 看有沒有約 50 Hz |
| GVRT 腳位 | 推測是 GND / 5V / RX / TX | 上電前先用電表量 |
| PX4 參數 | 官方建議值能不能讓 EKF 融合 | 手推飛機：往前 x 變大、往右 y 變大 |
| 裝上飛機的漂移 | 比手持的 2.1% 好多少 | 低空 Position 模式繞一圈回起點 |
| 飛過障礙物時的高度 | ToF 量到門框、桌面時高度會不會跳 | 低速飛過，看高度曲線 |
| 多機對齊座標 | 固定位置、同方向開機夠不夠 | 多台同時錄，比較起點偏移 |

官方建議的 PX4 參數（未測）：

```text
MAV_1_CONFIG  = TELEM n   (重開飛控)
MAV_1_MODE    = Onboard
MAV_1_FORWARD = Disabled
SER_TELn_BAUD = 921600
EKF2_EV_CTRL  = 9         (水平位置 + yaw)
EKF2_HGT_REF  = 2         (高度用 ToF)
```

## 參考

**msg 86（VIO，56 bytes）格式**：從實機資料反推，不是官方格式。封包外框是 `EF dev sys msg seq len payload sum8`。

| 位置 | 內容 |
| --- | --- |
| `[1]` u8 | 狀態：8 = 初始化中，15 = 追蹤中 |
| `[3]` u8 | 品質 0–100（255 = 無效） |
| `[4]` u32 | 模組時間 ms（`[8]` 是影像時間，約早 40 ms） |
| `[16]` 9×f32 | x, y, z (m)、vx, vy, vz (m/s)、roll, pitch, yaw (°) |
| `[52]` u16 | ToF 距離 mm |

`data/2026-11-18_handheld_raw.csv` 是實機手持錄到的原始封包（`payload_hex` 欄），可以拿來測試解碼。

來源：

- [MicoAir 官方文件：MicoVIO](https://micoair.com/en/docs/sensors/visual-inertial-odometry-sensor/micovio)（規格、安裝、PX4 參數）
- [mtf01-protocol](https://github.com/GlassOnTin/mtf01-protocol)（Micolink 封包外框，第三方整理）
