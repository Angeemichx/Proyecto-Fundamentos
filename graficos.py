"""
StrangerTEC Morse Translator - Interfaz PC
CE-1104 Fundamentos de Sistemas Computacionales
Instituto Tecnológico de Costa Rica, I Sem 2026
"""

import socket
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import random
import time
from datetime import datetime

# Jueos de frases que se pueden elegir 
FRASES_GAMER = ["SOS", "GOOD-GAME", "ARCADE", "BOSS", "CLAN", "FUN", "IN-GAME", "BONUS", "RUN", "TROLL"]

FRASES_FRUTAS = [ "MANGO", "PINA", "UVA", "FRESA", "KIWI", "SANDIA", "BANANO", "MELON", "MANZANA", "PERA"]

FRASES_COLORES = [ "CAFE", "MORADO", "ROJO", "NEGRO", "CELESTE", "AMARILLO", "NARANJA", "AZUL", "VERDE", "ROSADO"]

# Juegos
JUEGOS_FRASES = { "Gamer": FRASES_GAMER, "Frutas": FRASES_FRUTAS, "Colores": FRASES_COLORES}
FRASES_DEFAULT = FRASES_GAMER.copy()

MORSE = {"A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".", "F": "..-.", "G": "--.", "H":"....", "I": "..", "J": ".---", "K": "-.-", "L": ".-..", "M": "--", "N": "-.", "O": "---", "P": ".--.", "Q":"--.-", "R": ".-.", "S": "...", "T": "-",
    "U": "..-", "V": "...-", "W": ".--", "X": "-..-", "Y": "-.--", "Z": "--..", "0": "-----", "1": ".----", "2": "..---", "3": "...--", "4": "....-", "5": ".....", "6": "-....", "7": "--...", "8": "---..", "9": "----.", "+": ".-.-.", "-": "-....-"}

HOST = '0.0.0.0'
PORT = 5000
UNIDADES = {'A': 0.2, 'B': 0.3}


class EstadoJuego:
    def __init__(self):
        self.modo_juego = "Local"       # Local o Versus
        self.modo_transmision = "Simple"  # Simple o Escucha
        self.velocidad = "A"            # A (0.2s) o B (0.3s)
        self.frases: list[str] = FRASES_DEFAULT.copy()
        self.frase_actual: str = ""
        self.turno_actual = 1           # Jugador 1 o 2
        self.ronda_actual = 1
        
        # Puntajes
        self.puntajes = {1: 0, 2: 0}
        self.intentos = {1: "", 2: ""}
        
        # Conexiones
        self.conexiones = {} 
        self.maqueta_1_id = None
        self.maqueta_2_id = None
estado = EstadoJuego()

# Seleccionar frase aleatoria
def seleccionar_frase():
    return random.choice(estado.frases)

# Convertir la frase al códgo Morse
def frase_a_morse(frase):
    resultado = []
    for letra in frase.upper():
        if letra in MORSE:
            resultado.append(MORSE[letra])
        elif letra == ' ':
            resultado.append(' ')  # Espacio entre palabras
    return ' '.join(resultado)

# puntaje por carcteres correctos y precisión
def evaluar_intento(frase_original, intento_morse, tiempo_usado):
    morse_a_letra = {v: k for k, v in MORSE.items()}
    palabras_morse = intento_morse.strip().split(' ')
    texto_intento = ""
    for simbolo in palabras_morse:
        if simbolo in morse_a_letra:
            texto_intento += morse_a_letra[simbolo]
        elif simbolo == '':
            texto_intento += ' '
    # Comparar
    frase_original = frase_original.upper()
    correctos = sum(1 for a, b in zip(frase_original, texto_intento) if a == b)
    total = len(frase_original)
    precision = correctos / total if total > 0 else 0
    # Puntaje por velocidad de 3 niveles
    if tiempo_usado < 5:
        bonus_velocidad = 3
    elif tiempo_usado < 10:
        bonus_velocidad = 2
    else:
        bonus_velocidad = 1
    puntaje = int(correctos * 10 * precision + bonus_velocidad * 5)
    return puntaje, correctos, precision

# Envío a una maqueta específica
def enviar_a_maqueta(maq_id, comando, datos=""):
    if maq_id in estado.conexiones:
        try:
            mensaje = f"{comando}:{datos}"
            estado.conexiones[maq_id].send(mensaje.encode())
            return True
        except:
            return False
    return False

#envío a todas las maquetas conectadas
def broadcast(comando, datos=""):
    for maq_id in estado.conexiones:
        enviar_a_maqueta(maq_id, comando, datos)

# Interfaz
ventana = tk.Tk()
ventana.title("StrangerTEC Morse Translator")
ventana.geometry("900x700")
ventana.configure(bg="#1a1a2e")
style = ttk.Style()
style.theme_use('clam')

# Configuración
frame_config = tk.LabelFrame(ventana, text="Configuración", 
                              bg="#16213e", fg="white", font=("Arial", 12))
frame_config.pack(fill="x", padx=10, pady=5)

# Modo de juego
tk.Label(frame_config, text="Modo:", bg="#16213e", fg="white").grid(row=0, column=0, padx=5)
modo_var = tk.StringVar(value="Local")
ttk.OptionMenu(frame_config, modo_var, "Local", "Local", "Versus").grid(row=0, column=1, padx=5)

# Modo transmisión
tk.Label(frame_config, text="Transmisión:", bg="#16213e", fg="white").grid(row=0, column=2, padx=5)
trans_var = tk.StringVar(value="Simple")
ttk.OptionMenu(frame_config, trans_var, "Simple", "Simple", "Escucha").grid(row=0, column=3, padx=5)

# Velocidad
tk.Label(frame_config, text="Velocidad:", bg="#16213e", fg="white").grid(row=0, column=4, padx=5)
vel_var = tk.StringVar(value="A")
tk.OptionMenu(frame_config, vel_var, "A", "A (0.2s)", "B (0.3s)").grid(row=0, column=5, padx=5)

# Palabras
tk.Label(frame_config, text="Tema:", bg="#16213e", fg="white").grid(row=1, column=0, padx=5)
tema_var = tk.StringVar(value="Gamer")
ttk.OptionMenu(frame_config, tema_var, "Gamer", "Gamer", "Frutas", "Colores").grid(row=1, column=1, padx=5)

# Botón aplicar
def aplicar_config():
    estado.modo_juego = modo_var.get()
    estado.modo_transmision = trans_var.get()
    estado.velocidad = vel_var.get()[0]  # "A" o "B"
    estado.frases = JUEGOS_FRASES[tema_var.get()]
    broadcast("CONFIG", f"{estado.modo_transmision},{estado.velocidad}")
    log_servidor(f"Configuración: {estado.modo_juego}, {estado.modo_transmision}, Vel {estado.velocidad}")
ttk.Button(frame_config, text="Aplicar", command=aplicar_config).grid(row=0, column=6, padx=10)

# Mostrar frase actual
frame_frase = tk.LabelFrame(ventana, text="Frase Actual", bg="#16213e", fg="white", font=("Arial", 12))
frame_frase.pack(fill="x", padx=10, pady=5)
label_frase = tk.Label(frame_frase, text="---", font=("Courier", 36, "bold"), bg="#16213e", fg="#e94560")
label_frase.pack(pady=10)

label_morse = tk.Label(frame_frase, text="", font=("Courier", 16), bg="#16213e", fg="#0f3460")
label_morse.pack(pady=5)

# panel para que se vea el abecedario Morse
frame_abc = tk.LabelFrame(ventana, text="Panel de Referencia Morse", bg="#16213e", fg="white", font=("Arial", 12))
frame_abc.pack(fill="x", padx=10, pady=5)
abc_texto = tk.Text(frame_abc, height=5, bg="#0f3460", fg="white", font=("Courier", 10))
abc_texto.pack(fill="x", padx=5, pady=5)

# Llenar panel con alfabeto Morse
abc_contenido = ""
for letra in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    abc_contenido += f"{letra}: {MORSE[letra]}   "
    if letra in "JQZ":
        abc_contenido += "\n"
abc_contenido += "\n\n"
for num in "0123456789":
    abc_contenido += f"{num}: {MORSE[num]}   "
abc_contenido += f"\n+: {MORSE['+']}   -: {MORSE['-']}"
abc_texto.insert("1.0", abc_contenido)
abc_texto.config(state="disabled")

# Ventana de puntajes
frame_puntajes = tk.LabelFrame(ventana, text="Puntajes", bg="#16213e", fg="white", font=("Arial", 12))
frame_puntajes.pack(fill="x", padx=10, pady=5)

# Jugador 1
frame_j1 = tk.Frame(frame_puntajes, bg="#16213e")
frame_j1.pack(side="left", expand=True, padx=20)
tk.Label(frame_j1, text="JUGADOR 1", font=("Arial", 14, "bold"), bg="#16213e", fg="#e94560").pack()
label_puntaje_j1 = tk.Label(frame_j1, text="0 pts", font=("Arial", 24), bg="#16213e", fg="white")
label_puntaje_j1.pack()
label_turno_j1 = tk.Label(frame_j1, text="ESPERANDO", font=("Arial", 10), bg="#16213e", fg="gray")
label_turno_j1.pack()

# Jugador 2
frame_j2 = tk.Frame(frame_puntajes, bg="#16213e")
frame_j2.pack(side="right", expand=True, padx=20)
tk.Label(frame_j2, text="JUGADOR 2", font=("Arial", 14, "bold"), bg="#16213e", fg="#0f3460").pack()
label_puntaje_j2 = tk.Label(frame_j2, text="0 pts", font=("Arial", 24), bg="#16213e", fg="white")
label_puntaje_j2.pack()
label_turno_j2 = tk.Label(frame_j2, text="ESPERANDO", font=("Arial", 10), bg="#16213e", fg="gray")
label_turno_j2.pack()

# Botones
frame_controles = tk.Frame(ventana, bg="#1a1a2e")
frame_controles.pack(pady=10)

def nueva_ronda():
    estado.frase_actual = seleccionar_frase()
    label_frase.config(text=estado.frase_actual)
    label_morse.config(text=frase_a_morse(estado.frase_actual))
    estado.turno_actual = 1
    estado.intentos = {1: "", 2: ""}
    # Enviar frase a maqueta o a ambas
    broadcast("FRASE", estado.frase_actual)
    # Actualizar turnos
    label_turno_j1.config(text="TRANSMITIENDO", fg="#e94560")
    label_turno_j2.config(text="ESPERANDO", fg="gray")
    log_servidor(f"Nueva ronda: {estado.frase_actual}")

def cambiar_turno():
    estado.turno_actual = 2 if estado.turno_actual == 1 else 1
    if estado.turno_actual == 1:
        label_turno_j1.config(text="TRANSMITIENDO", fg="#e94560")
        label_turno_j2.config(text="ESPERANDO", fg="gray")
    else:
        label_turno_j1.config(text="ESPERANDO", fg="gray")
        label_turno_j2.config(text="TRANSMITIENDO", fg="#e94560")
    broadcast("TURNO", str(estado.turno_actual))
    log_servidor(f"Turno: Jugador {estado.turno_actual}")

#Mostrar resultados al finalizar y realizar nueva ronda
def finalizar_ronda():
    p1 = estado.puntajes[1]
    p2 = estado.puntajes[2]
    if p1 > p2:
        ganador = "JUGADOR 1"
    elif p2 > p1:
        ganador = "JUGADOR 2"
    else:
        ganador = "EMPATE"
    messagebox.showinfo("Fin de Ronda", 
        f"Jugador 1: {p1} pts\nJugador 2: {p2} pts\n\nGanador: {ganador}")
    label_puntaje_j1.config(text=f"{p1} pts")
    label_puntaje_j2.config(text=f"{p2} pts")
ttk.Button(frame_controles, text="🔄 Nueva Ronda", command=nueva_ronda).pack(side="left", padx=5)
ttk.Button(frame_controles, text="↔️ Cambiar Turno", command=cambiar_turno).pack(side="left", padx=5)
ttk.Button(frame_controles, text="🏆 Finalizar Ronda", command=finalizar_ronda).pack(side="left", padx=5)

# Log del servidor
frame_log = tk.LabelFrame(ventana, text="Log del Servidor", bg="#16213e", fg="white", font=("Arial", 12))
frame_log.pack(fill="both", expand=True, padx=10, pady=5)
log_text = tk.Text(frame_log, height=8, bg="#0f3460", fg="#00ff00", font=("Courier", 10))
log_text.pack(fill="both", expand=True, padx=5, pady=5)

# Cargar mensajes en el log
def log_servidor(mensaje):
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_text.insert("end", f"[{timestamp}] {mensaje}\n")
    log_text.see("end")

# Iniciar el servidor del wifi
def iniciar_servidor():
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind((HOST, PORT))
    servidor.listen(2)
    log_servidor(f"Servidor iniciado en puerto {PORT}")
    while True:
        conn, addr = servidor.accept()
        log_servidor(f"Nueva conexión: {addr}")
        threading.Thread(target=manejar_cliente, args=(conn, addr), daemon=True).start()

# Comunicación con Pico 
def manejar_cliente(conn, addr):
    maq_id = None
    while True:
        try:
            datos = conn.recv(1024).decode()
            if not datos:
                break
            partes = datos.split(":", 2)
            if len(partes) >= 2:
                id_recibido = partes[0]
                comando = partes[1]
                datos_extra = partes[2] if len(partes) > 2 else ""
                # Registrar maqueta
                if comando == "CONECTADO":
                    maq_id = id_recibido
                    estado.conexiones[maq_id] = conn
                    log_servidor(f"Maqueta {maq_id} registrada")
                    # Enviar configuración actual
                    enviar_a_maqueta(maq_id, "CONFIG", f"{estado.modo_transmision},{estado.velocidad}")
                # Recibir intento Morse
                elif comando == "MORSE":
                    log_servidor(f"{id_recibido} envió: {datos_extra}")
                    if id_recibido == "MAQ1":
                        estado.intentos[1] += datos_extra
                    elif id_recibido == "MAQ2":
                        estado.intentos[2] += datos_extra
                # Recibir fin de transmisión
                elif comando == "FIN":
                    log_servidor(f"{id_recibido} terminó transmisión")
                    jugador = 1 if id_recibido == "MAQ1" else 2
                    puntaje, correctos, precision = evaluar_intento(estado.frase_actual, estado.intentos[jugador], 5)
                    estado.puntajes[jugador] += puntaje
                    log_servidor(f"Jugador {jugador}: {puntaje} pts ({correctos} correctos)")
                    # Enviar puntaje de vuelta
                    enviar_a_maqueta(id_recibido, "PUNTAJE", str(puntaje))
        except Exception as e:
            log_servidor(f"Error: {e}")
            break
    # Limpiar conexión
    if maq_id and maq_id in estado.conexiones:
        del estado.conexiones[maq_id]
    conn.close()
    log_servidor(f"Conexión cerrada: {addr}")
# Iniciar servidor 
threading.Thread(target=iniciar_servidor, daemon=True).start()

# Iniciar
log_servidor("StrangerTEC Morse Translator iniciado")
log_servidor("Esperando conexiones de las Pico W...")

ventana.mainloop()