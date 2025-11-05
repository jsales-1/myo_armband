import time
import threading
import numpy as np
from collections import deque
from flask import Flask, render_template_string, jsonify
import webbrowser
import myo

# ===== CONFIGURAÇÕES =====
SAMPLE_RATE = 200  # Hz
WINDOW_SIZE = 50   # Amostras para suavização
MAX_ANGLE_MCP = 90
MAX_ANGLE_IP = 80

# ===== CLASSE DE COLETA =====
class EmgCollector(myo.DeviceListener):
    def __init__(self):
        self.lock = threading.Lock()
        self.ch1_buffer = deque(maxlen=WINDOW_SIZE)
        self.ch6_buffer = deque(maxlen=WINDOW_SIZE)
        self.current_angle = {"MCP": 0, "IP": 0}

    def on_connected(self, event):
        event.device.stream_emg(True)

    def on_emg(self, event):
        ch1 = event.emg[0]
        ch6 = event.emg[5]
        with self.lock:
            self.ch1_buffer.append(ch1)
            self.ch6_buffer.append(ch6)

    def compute_angles(self):
        with self.lock:
            if len(self.ch1_buffer) == 0 or len(self.ch6_buffer) == 0:
                return {"MCP": 0, "IP": 0}
            
            # Calcula RMS dos dois canais
            rms1 = np.sqrt(np.mean(np.square(self.ch1_buffer)))
            rms6 = np.sqrt(np.mean(np.square(self.ch6_buffer)))

            # Normaliza ambos (faixa 0–1)
            norm1 = np.clip(rms1 / 50, 0, 1)
            norm6 = np.clip(rms6 / 50, 0, 1)

            # Diferença define direção do movimento
            diff = norm6 - norm1

            # Intensidade total suaviza o movimento
            magnitude = abs(diff)

            # Mapeia intensidade → ângulos
            # flexão (diff > 0) → ângulo positivo
            # extensão (diff < 0) → ângulo negativo, menor amplitude
            if diff >= 0:
                mcp = MAX_ANGLE_MCP * magnitude
                ip = MAX_ANGLE_IP * magnitude
            else:
                mcp = -MAX_ANGLE_MCP * 0.6 * magnitude  # extensão menos intensa
                ip = -MAX_ANGLE_IP * 0.6 * magnitude

            self.current_angle["MCP"] = mcp
            self.current_angle["IP"] = ip
            return self.current_angle

# ===== TEMPLATE HTML =====
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Dedo Virtual - Canal 6 e 1</title>
    <style>
        body { margin: 0; overflow: hidden; background: #1a1a1a; }
        #info {
            position: absolute; top: 10px; left: 10px; 
            background: rgba(0,0,0,0.8); color: white; 
            padding: 10px; border-radius: 5px; font-family: Arial;
        }
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
</head>
<body>
    <div id="info">
        <div>Controle Canal 6 ↔ 1</div>
        <div>Ângulo MCP: <span id="angleMCP">0°</span></div>
        <div>Ângulo IP: <span id="angleIP">0°</span></div>
    </div>
    <script>
        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(75, window.innerWidth/window.innerHeight, 0.1, 1000);
        const renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.setClearColor(0x1a1a1a);
        document.body.appendChild(renderer.domElement);

        const light = new THREE.DirectionalLight(0xffffff, 1);
        light.position.set(2, 2, 3);
        scene.add(light);

        const matBone = new THREE.MeshPhongMaterial({ color: 0xcccccc });
        const group = new THREE.Group();
        scene.add(group);

        const meta = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.15, 1.2, 8), matBone);
        meta.rotation.z = Math.PI / 2;
        group.add(meta);

        const proxGroup = new THREE.Group();
        proxGroup.position.x = 0.6;
        group.add(proxGroup);

        const proximal = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.12, 1.0, 8), matBone);
        proximal.rotation.z = Math.PI / 2;
        proximal.position.x = 0.5;
        proxGroup.add(proximal);

        const distGroup = new THREE.Group();
        distGroup.position.x = 1.0;
        proxGroup.add(distGroup);

        const distal = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.09, 0.8, 8), matBone);
        distal.rotation.z = Math.PI / 2;
        distal.position.x = 0.4;
        distGroup.add(distal);

        camera.position.set(2, 2, 3);
        camera.lookAt(0, 0, 0);

        function animate() {
            requestAnimationFrame(animate);
            fetch('/get_angles')
                .then(res => res.json())
                .then(data => {
                    document.getElementById('angleMCP').textContent = data.MCP.toFixed(1) + '°';
                    document.getElementById('angleIP').textContent  = data.IP.toFixed(1) + '°';
                    proxGroup.rotation.z = -THREE.MathUtils.degToRad(data.MCP);
                    distGroup.rotation.z = -THREE.MathUtils.degToRad(data.IP);
                });
            renderer.render(scene, camera);
        }
        animate();
    </script>
</body>
</html>
'''

# ===== FLASK SERVER =====
app = Flask(__name__)
collector = None

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/get_angles')
def get_angles():
    if collector:
        return collector.compute_angles()
    return {"MCP": 0, "IP": 0}

# ===== EXECUÇÃO =====
def main():
    global collector
    myo.init()
    hub = myo.Hub()
    collector = EmgCollector()

    # Executa leitura do Myo em thread separada
    threading.Thread(target=lambda: hub.run_forever(collector), daemon=True).start()

    # Abre navegador
    webbrowser.open('http://localhost:5000', new=2)
    app.run(port=5000, debug=False)

if __name__ == "__main__":
    print("Iniciando controle com flexão/extensão (Canais 6 e 1)...")
    main()
