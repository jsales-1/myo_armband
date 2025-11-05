from matplotlib import pyplot as plt
from matplotlib.animation import FuncAnimation
from collections import deque
from threading import Lock

import myo
import numpy as np


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
    def __init__(self, listener):
        self.n = listener.n
        self.listener = listener

        # Cores diferentes para cada gráfico
        self.colors = ['b', 'g', 'r', 'c', 'm', 'y', 'orange', 'purple']

        self.fig, self.axes = plt.subplots(8, 1, figsize=(10, 12), sharex=True)
        for i, ax in enumerate(self.axes, start=1):
            ax.set_ylim([-100, 100])
            ax.set_ylabel("EMG")
            ax.grid(True)
            ax.set_title(f"Canal {i}", loc='left', fontsize=10, pad=2)  

        self.graphs = [
            ax.plot(np.arange(self.n), np.zeros(self.n), color=color)[0]
            for ax, color in zip(self.axes, self.colors)
        ]
        self.fig.tight_layout()


    def update_plot(self, frame):
        emg_data = self.listener.get_emg_data()
        if not emg_data:
            return self.graphs
        emg_data = np.array([x[1] for x in emg_data]).T
        for g, data in zip(self.graphs, emg_data):
            if len(data) < self.n:
                data = np.concatenate([np.zeros(self.n - len(data)), data])
            g.set_ydata(data)
        return self.graphs

    def main(self):
        ani = FuncAnimation(self.fig, self.update_plot, interval=33, blit=False)
        plt.show()


def main():
    myo.init()
    hub = myo.Hub()
    listener = EmgCollector(512)
    with hub.run_in_background(listener.on_event):
        Plot(listener).main()


if __name__ == '__main__':
    main()
