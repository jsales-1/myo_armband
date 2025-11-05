import pandas as pd
import numpy as np
from sklearn.tree import DecisionTreeClassifier

from matplotlib import pyplot as plt
from matplotlib.animation import FuncAnimation
from collections import deque
from threading import Lock
import myo

# ==============================================================
#  TREINO DO MODELO A PARTIR DO DATAFRAME (df)
# ==============================================================

# Carrega seu DataFrame (ajuste o caminho se necessário)
df = pd.read_csv("emg_protocol.csv", encoding='latin-1')

# Cria dataset com médias por dedo/movimento/repetição
dataset = df.groupby(["Dedo", "Movimento", "Repetição"])[[f"Canal{i}" for i in range(1, 9)]].mean().reset_index()
dataset["Label"] = dataset["Dedo"].astype(str) + "_" + dataset["Movimento"]

X = dataset[[f"Canal{i}" for i in range(1, 9)]].values
y = dataset["Label"].values

# Treina a Árvore de Decisão com todo o dataset
tree = DecisionTreeClassifier(random_state=42, max_depth=None)  # você pode ajustar max_depth, min_samples_split, etc.
tree.fit(X, y)

print("Modelo de Árvore de Decisão treinado com todo o dataset (sem split).")

# ==============================================================
#  COLETA DE SINAL DO MYO
# ==============================================================

class EmgCollector(myo.DeviceListener):
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


class Plot:
    def __init__(self, listener, model):
        self.n = listener.n
        self.listener = listener
        self.model = model
        self.last_prediction = "Aguardando sinais..."

        self.colors = ['b', 'g', 'r', 'c', 'm', 'y', 'orange', 'purple']

        self.fig, self.axes = plt.subplots(8, 1, figsize=(10, 12), sharex=True)
        for ax in self.axes:
            ax.set_ylim([-100, 100])
            ax.set_ylabel("EMG")
            ax.grid(True)
        self.graphs = [
            ax.plot(np.arange(self.n), np.zeros(self.n), color=color)[0]
            for ax, color in zip(self.axes, self.colors)
        ]
        self.fig.tight_layout(rect=[0, 0, 1, 0.96])
        self.fig.suptitle(f"Predição: {self.last_prediction}", fontsize=16)

    def update_plot(self, frame):
        emg_data = self.listener.get_emg_data()
        if not emg_data:
            return self.graphs

        emg_data = np.array([x[1] for x in emg_data]).T  # shape (8, n)

        # Atualiza gráficos
        for g, data in zip(self.graphs, emg_data):
            if len(data) < self.n:
                data = np.concatenate([np.zeros(self.n - len(data)), data])
            g.set_ydata(data)

        # Se já temos uma janela cheia (512 amostras), faz predição
        if emg_data.shape[1] == self.n:
            features = emg_data.mean(axis=1).reshape(1, -1)  # médias dos 8 canais
            self.last_prediction = self.model.predict(features)[0]
            print("Movimento detectado:", self.last_prediction)

            # Atualiza título da figura com a predição
            self.fig.suptitle(f"Predição: {self.last_prediction}", fontsize=16)

        return self.graphs

    def main(self):
        ani = FuncAnimation(self.fig, self.update_plot, interval=33, blit=False)
        plt.show()


def main():
    myo.init()
    hub = myo.Hub()
    listener = EmgCollector(512)
    with hub.run_in_background(listener.on_event):
        Plot(listener, tree).main()


if __name__ == '__main__':
    main()
