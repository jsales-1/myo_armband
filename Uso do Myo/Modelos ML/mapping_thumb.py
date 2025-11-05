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


def run_protocol(listener, duration=10, repetitions=5):
    """
    Roda protocolo para o polegar:
    - Flexão
    - Extensão
    - Rotação
    - Pinça 1, Pinça 2, Pinça 3, Pinça 4
    - Movimento Aleatório
    """
    all_data = []

    movimentos = ["Flexão", "Extensão", "Rotação",
                  "Pinça 1", "Pinça 2", "Pinça 3", "Pinça 4",
                  "Aleatório"]

    for movimento in movimentos:
        for rep in range(1, repetitions + 1):
            input(f"\nPolegar - {movimento} (Repetição {rep}/{repetitions}). Pressione Enter para iniciar...")
            listener.emg_data_queue.clear()  # limpa dados antigos

            start_time = time.time()
            while time.time() - start_time < duration:
                time.sleep(0.01)  # coleta contínua

            emg_data = listener.get_emg_data()
            for row in emg_data:
                all_data.append([1, movimento, rep, row[0]] + list(row[1]))

            print(f"Polegar - {movimento} (Repetição {rep}) concluído. {len(emg_data)} amostras coletadas.")

    # Salva CSV
    filename = "emg_protocol_polegar.csv"
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
        run_protocol(listener, duration=0.5, repetitions=10)


if __name__ == "__main__":
    main()
