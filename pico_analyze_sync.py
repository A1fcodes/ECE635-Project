# pico_analyze_sync.py -- run on the Pico after logging
import math

CSV_FILE = "esp_dual_log.csv"

pico_times = {}
esp_times = {}

try:
    f = open(CSV_FILE, "r")
except OSError:
    print("Cannot open", CSV_FILE)
    raise

first = True
for line in f:
    line = line.strip()
    if not line:
        continue
    # skip header
    if first and line.startswith("pico_time_s"):
        first = False
        continue
    first = False

    parts = line.split(",")
    if len(parts) < 3:
        continue

    try:
        pico_s = float(parts[0])
        node = parts[1].strip()
        esp_s = float(parts[2])
    except ValueError:
        continue

    if node == "":
        continue

    if node not in pico_times:
        pico_times[node] = []
        esp_times[node] = []

    pico_times[node].append(pico_s)
    esp_times[node].append(esp_s)

f.close()


def linear_fit(tp, te):
    """
    Fit tp ≈ a * te + b (least squares).
    tp, te are lists of floats.
    Returns (a, b) or None.
    """
    n = len(tp)
    if n < 5:
        return None

    # Make times relative to first sample to reduce numerical issues
    tp0 = tp[0]
    te0 = te[0]
    tp_rel = [t - tp0 for t in tp]
    te_rel = [t - te0 for t in te]

    sum_x = 0.0
    sum_y = 0.0
    sum_xx = 0.0
    sum_xy = 0.0

    for x, y in zip(te_rel, tp_rel):
        sum_x += x
        sum_y += y
        sum_xx += x * x
        sum_xy += x * y

    denom = n * sum_xx - sum_x * sum_x
    if denom == 0:
        return None

    a = (n * sum_xy - sum_x * sum_y) / denom
    b_rel = (sum_y - a * sum_x) / n

    # Convert back to absolute offset:
    # tp ≈ a*te + (b_rel + tp0 - a*te0)
    b = b_rel + tp0 - a * te0
    return a, b


# Store per-node results so we can compute A vs B later
results = {}

for node in pico_times.keys():
    tp = pico_times[node]
    te = esp_times[node]
    n = len(tp)
    if n < 5:
        continue

    fit = linear_fit(tp, te)
    if fit is None:
        continue

    a, b = fit
    drift_ppm = (a - 1.0) * 1_000_000.0

    # Residuals = pico - (a*esp + b)
    residuals_ms = []
    for tp_i, te_i in zip(tp, te):
        res = tp_i - (a * te_i + b)
        residuals_ms.append(res * 1000.0)

    # Stats for approximate one-way delay
    mean_delay = sum(residuals_ms) / n
    var = 0.0
    for r in residuals_ms:
        diff = r - mean_delay
        var += diff * diff
    var /= n
    std_delay = math.sqrt(var)
    min_delay = min(residuals_ms)
    max_delay = max(residuals_ms)

    results[node] = {
        "drift_ppm": drift_ppm,
        "mean_delay": mean_delay,
        "std_delay": std_delay,
        "min_delay": min_delay,
        "max_delay": max_delay,
        "samples": n,
    }

# 1) Print per-ESP network delay stats (ESP <-> Pico)
for node in sorted(results.keys()):
    r = results[node]
    print("Node", node, "(ESP <-> Pico) network delay (ms):")
    print("  samples :", r["samples"])
    print("  mean    : {:.3f} ms".format(r["mean_delay"]))
    print("  std     : {:.3f} ms".format(r["std_delay"]))
    print("  min, max: {:.3f} ms , {:.3f} ms".format(r["min_delay"], r["max_delay"]))
    print()

# 2) Clock drift between the two ESP32s (A vs B) in ppm
if "A" in results and "B" in results:
    dA = results["A"]["drift_ppm"]
    dB = results["B"]["drift_ppm"]
    drift_AB = dA - dB
    print("Clock drift A vs B ≈ {:.2f} ppm".format(drift_AB))
