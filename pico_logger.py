# (for Raspberry Pi Pico W, MicroPython)
import network, socket, struct, time

SSID = "Al"
PASS = "sashamini"
PORT = 9999
CSV_FILE = "esp_dual_log.csv"

# ----- Wi-Fi connect -----
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(SSID, PASS)

t0 = time.ticks_ms()
while not wlan.isconnected() and time.ticks_diff(time.ticks_ms(), t0) < 20000:
    print("Connecting Wi-Fi...")
    time.sleep_ms(500)

print("Pico Wi-Fi:", wlan.ifconfig())
# wlan.ifconfig()[0] is Pico's IP (e.g., 172.20.10.10)

# ----- UDP socket -----
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", PORT))
print("Listening on UDP port", PORT)

f = open(CSV_FILE, "a")
f.write("pico_time_s,node,esp_time_s,dist_cm\n")
f.flush()

while True:
    pkt, addr = sock.recvfrom(128)
    now_ms = time.ticks_ms()
    pico_time_s = now_ms / 1000.0

    if len(pkt) < 13:
        continue

    dev_id, t_us, dist = struct.unpack(">5sIf", pkt[:13])
    node = dev_id.decode().strip("\x00")
    esp_time_s = t_us / 1_000_000.0

    print("From {} @ {} | Pico={:.3f}s | ESP={:.6f}s | d={:.1f}cm"
          .format(node, addr, pico_time_s, esp_time_s, dist))

    line = "{:.6f},{},{:.6f},{:.3f}\n".format(pico_time_s, node, esp_time_s, dist)
    f.write(line)
    f.flush()
