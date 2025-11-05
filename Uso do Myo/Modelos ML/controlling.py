import time
from collections import deque
from threading import Lock
import myo
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# ----------------------
# Classe para coletar EMG
# ----------------------
class EmgCollector(myo.DeviceListener):
    def __init__(self, n=512):
        self.n = n
        self.lock = Lock()
        self.emg_data_queue = deque(maxlen=n)

    def get_emg_data(self):
        with self.lock:
            return list(self.emg_data_queue)

    def on_connected(self, event):
        event.device.stream_emg(True)

    def on_emg(self, event):
        with self.lock:
            self.emg_data_queue.append((event.timestamp, np.array(event.emg)))

# ----------------------
# Classificador e cálculo de ângulos
# ----------------------
def classify_and_angle(sample, mcp_range=(-18, 27), ip_range=(0, 27)):
    ch1, ch2 = sample[0], sample[1]
    intensity = (abs(ch1) + abs(ch2)) / 2

    if intensity < 10:  # sinal muito baixo -> sem movimento
        return None, None

    norm_intensity = min(intensity / 100, 1.0)

    if (ch1 + ch2) / 2 > 0:
        mcp_angle = mcp_range[1] * norm_intensity
        ip_angle = ip_range[1] * norm_intensity
    else:
        mcp_angle = mcp_range[0] * norm_intensity
        ip_angle = 0
    return mcp_angle, ip_angle

# ----------------------
# Função para desenhar o polegar 3D
# ----------------------
def draw_thumb(ax, mcp_angle, ip_angle):
    ax.cla()  # limpa figura
    ax.set_xlim([-2,2])
    ax.set_ylim([0,3])
    ax.set_zlim([0,2])
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")
    ax.set_title("Polegar Virtual - Dedo 1")

    base = np.array([0,0,0])

    # MCP
    mcp_rad = np.radians(mcp_angle)
    proximal = base + np.array([np.cos(mcp_rad), np.sin(mcp_rad), 0])

    # IP
    ip_rad = np.radians(ip_angle)
    distal = proximal + np.array([np.cos(ip_rad)*0.8, np.sin(ip_rad)*0.8, 0])

    # Desenha segmentos
    ax.plot([base[0], proximal[0]], [base[1], proximal[1]], [base[2], proximal[2]], 'r', linewidth=5)
    ax.plot([proximal[0], distal[0]], [proximal[1], distal[1]], [proximal[2], distal[2]], 'g', linewidth=5)

# ----------------------
# Loop principal com Myo e 3D
# ----------------------
def main():
    myo.init()
    hub = myo.Hub()
    listener = EmgCollector(n=512)

    plt.ion()
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    with hub.run_in_background(listener.on_event):
        print("Controlando polegar virtual com o Myo. Pressione Ctrl+C para sair.")
        try:
            while True:
                emg_data = listener.get_emg_data()
                if not emg_data:
                    time.sleep(0.01)
                    continue

                _, last_sample = emg_data[-1]
                mcp_angle, ip_angle = classify_and_angle(last_sample)
                if mcp_angle is not None:
                    draw_thumb(ax, mcp_angle, ip_angle)
                    plt.draw()
                    plt.pause(0.01)

        except KeyboardInterrupt:
            print("Finalizando...")

if __name__ == "__main__":
    main()
