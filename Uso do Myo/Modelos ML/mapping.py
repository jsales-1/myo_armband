import time
import csv
from collections import deque
from threading import Lock

import myo
import numpy as np


class EmgCollector(myo.DeviceListener):
    """Coleta EMG em uma fila com tamanho máximo n."""
    def __init__(self, n):
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
            self.emg_data_queue.append((event.timestamp, event.emg))


def run_protocol(listener, duration=10, fingers=5, repetitions=5):
    all_data = []

    for finger in range(1, fingers + 1):
        # Invertida a ordem dos movimentos
        for movement in ['Extensão', 'Flexão']:
            for rep in range(1, repetitions + 1):
                input(f"\nDedo {finger} - {movement} (Repetição {rep}/{repetitions}). Pressione Enter para iniciar...")
                listener.emg_data_queue.clear()

                start_time = time.time()
                while time.time() - start_time < duration:
                    time.sleep(0.01)

                emg_data = listener.get_emg_data()
                for row in emg_data:
                    all_data.append([finger, movement, rep, row[0]] + list(row[1]))

                print(f"Dedo {finger} - {movement} (Repetição {rep}) concluído. {len(emg_data)} amostras coletadas.")

    filename = "emg_protocol_dados_gabriel2.csv"
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Dedo", "Movimento", "Repetição", "Timestamp"] + [f"Canal{i+1}" for i in range(8)])
        for row in all_data:
            writer.writerow(row)

    print(f"\nProtocolo concluído! Dados salvos em '{filename}'.")


def main():
    myo.init()
    hub = myo.Hub()
    listener = EmgCollector(512)
    with hub.run_in_background(listener.on_event):
        run_protocol(listener, duration=1, fingers=5, repetitions=30)


if __name__ == "__main__":
    main()
