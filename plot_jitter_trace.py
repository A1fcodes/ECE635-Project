import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

CSV_FILE = "esp_dual_log.csv"

df = pd.read_csv(CSV_FILE)

# Ensure numeric
df["pico_time_s"] = pd.to_numeric(df["pico_time_s"], errors="coerce")
df["esp_time_s"]  = pd.to_numeric(df["esp_time_s"], errors="coerce")
df = df.dropna(subset=["pico_time_s", "esp_time_s", "node"]).copy()

# Time axis starts at 0
t0 = df["pico_time_s"].min()
df["t_s"] = df["pico_time_s"] - t0

# Helper: drop extreme corrupted timestamps using an IQR filter on raw offset
def iqr_mask(x, k=8.0):
    q1 = np.nanpercentile(x, 25)
    q3 = np.nanpercentile(x, 75)
    iqr = q3 - q1
    if not np.isfinite(iqr) or iqr == 0:
        return np.isfinite(x)
    lo = q1 - k * iqr
    hi = q3 + k * iqr
    return np.isfinite(x) & (x >= lo) & (x <= hi)

plt.figure()

for node, g in df.groupby("node"):
    g = g.sort_values("t_s").copy()

    # Raw offset (includes network delay + clock offset)
    raw_offset = g["esp_time_s"].to_numpy() - g["pico_time_s"].to_numpy()
    keep = iqr_mask(raw_offset, k=8.0)  # removes crazy spikes like 1001008.xxx
    g = g.loc[keep]

    if len(g) < 10:
        continue

    pico = g["pico_time_s"].to_numpy()
    esp  = g["esp_time_s"].to_numpy()
    t    = g["t_s"].to_numpy()

    # Fit clock mapping: esp ≈ a*pico + b
    a, b = np.polyfit(pico, esp, 1)

    # Residual = "jitter" proxy
    residual_s = esp - (a * pico + b)
    residual_ms = residual_s * 1000.0

    plt.plot(t, residual_ms, label=f"Node {node}")

plt.xlabel("Time since start (s)")
plt.ylabel("Apparent delay / jitter (ms)  [residual after clock fit]")
plt.title("Delay vs Time (Jitter Trace)")
plt.legend()
plt.tight_layout()
plt.savefig("jitter_trace_vs_time.png", dpi=200)
plt.show()

print("Saved: jitter_trace_vs_time.png")
