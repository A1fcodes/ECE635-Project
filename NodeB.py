import gc
import network, time, socket, struct
from machine import Pin, time_pulse_us

SSID = "Al"
PASS = "sashamini"
PI_IP = "172.20.10.7"    # Pico IP
PI_PORT = 9999
DEVICE_ID = b'B'

TRIG_PIN = 5
ECHO_PIN = 7
trig = Pin(TRIG_PIN, Pin.OUT)
echo = Pin(ECHO_PIN, Pin.IN)

SPEED_CM_PER_US = 0.0343 / 2
PERIOD_S = 1/25

MAX_CM = 30.0
MIN_CM = 2.0
TIMEOUT_US = int(MAX_CM / SPEED_CM_PER_US) + 500

# Wi-Fi connect
w = network.WLAN(network.STA_IF)
w.active(True)
w.connect(SSID, PASS)

t0 = time.ticks_ms()
while not w.isconnected() and time.ticks_diff(time.ticks_ms(), t0) < 20000:
    print("Connecting Wi-Fi...")
    time.sleep_ms(500)

print("Wi-Fi:", w.ifconfig())

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Pre-allocate 13-byte packet buffer: 5s I f
pkt = bytearray(13)

def measure_distance_cm():
    trig.value(0)
    time.sleep_us(5)
    trig.value(1)
    time.sleep_us(10)
    trig.value(0)

    dur = time_pulse_us(echo, 1, TIMEOUT_US)   # <-- changed 30000 -> TIMEOUT_US
    if dur < 0:
        return None

    dist = dur * SPEED_CM_PER_US
    if dist < MIN_CM or dist > MAX_CM:         # <-- ignore out of “short range”
        return None
    return dist

send_err_count = 0
loop_count = 0

while True:
    t_us = time.ticks_us()
    dist = measure_distance_cm()

    if dist is not None:
        # Fill packet in-place (no new bytes object)
        struct.pack_into(">5sIf", pkt, 0, DEVICE_ID, t_us & 0xFFFFFFFF, float(dist))
        try:
            sock.sendto(pkt, (PI_IP, PI_PORT))
            # Optional: print less often to reduce allocations
            if loop_count % 20 == 0:
                print(DEVICE_ID, "t_us =", t_us, "dist_cm =", dist)
        except OSError as e:
            # ENOMEM happens here sometimes
            if e.args and e.args[0] == 12:
                send_err_count += 1
                # Collect garbage and keep going, but don't spam prints
                gc.collect()
                # You can uncomment this if you want to see *some* info:
                # if send_err_count % 10 == 0:
                #     print("SEND ENOMEM (total):", send_err_count)
            else:
                # Other error, show it
                print("SEND ERROR:", e)
        loop_count += 1
    else:
        # Optional: print less often here too
        if loop_count % 20 == 0:
            print(DEVICE_ID, "out of range")

    time.sleep(PERIOD_S)
