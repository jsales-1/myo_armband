import myo
import threading
import time
from collections import deque
import matplotlib.pyplot as plt

# Número de sensores EMG do Myo
NUM_SENSORS = 8
MAX_POINTS = 100  # quantos pontos mostrar no gráfico

# Cria listas de deques, uma para cada sensor
emg_data = [deque([0]*MAX_POINTS, maxlen=MAX_POINTS) for _ in range(NUM_SENSORS)]

class EMGListener(myo.DeviceListener):
    def on_connect(self, device, timestamp, firmware_version):
        print("Myo conectado!")
        device.vibrate(myo.VibrationType.short)
        device.request_rssi()  # opcional, para checar força do sinal

    def on_emg(self, device, timestamp, emg):
        # emg é uma tupla de 8 valores
        for i in range(NUM_SENSORS):
            emg_data[i].append(emg[i])

def plot_thread():
    plt.ion()  # modo interativo
    fig, ax = plt.subplots()
    lines = []
    colors = ['r','g','b','c','m','y','k','orange']
    for i in range(NUM_SENSORS):
        line, = ax.plot(range(MAX_POINTS), emg_data[i], label=f'Sensor {i+1}', color=colors[i])
        lines.append(line)

    ax.set_ylim(-128, 128)  # faixa típica do EMG
    ax.set_title("EMG Myo em tempo real")
    ax.legend()

    while True:
        for i in range(NUM_SENSORS):
            lines[i].set_ydata(emg_data[i])
        fig.canvas.draw()
        fig.canvas.flush_events()
        time.sleep(0.05)

if __name__ == "__main__":
    myo.init()
    hub = myo.Hub()
    listener = EMGListener()

    # roda o gráfico em uma thread separada
    threading.Thread(target=plot_thread, daemon=True).start()

    try:
        while True:
            hub.run(listener.on_event, 50)
    except KeyboardInterrupt:
        print("Encerrando...")
