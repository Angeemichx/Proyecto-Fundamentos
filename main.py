"""
StrangerTEC Morse Translator - Pico W Firmware
CE-1104 Fundamentos de Sistemas Computacionales
Instituto Tecnológico de Costa Rica, I Sem 2026
Profesora: Kimberly Calderón Prado
Estudiantes: Lisandro Monge Quiros y Angélica Obregón Arguedas

"""

import network
import socket
import time
from machine import Pin, PWM, UART

WIFI_SSID = "Ange"      
WIFI_PASSWORD = "konnor0912"  
PC_IP = "10.27.174.157"    
PC_PORT = 5000
MAQ_ID = "MAQ1"            

# Conexión de pines:
BOTON_MORSE_PIN = 13
BUZZER_PIN = 16
DIP_SWITCH_1_PIN = 5
DIP_SWITCH_5_PIN = 6
SWITCH_ONOFF_PIN = 4
DATA_PIN_74HC164 = 0
CLOCK_PIN_74HC164 = 1
UART_TX_PIN = 8
UART_RX_PIN = 9

boton_morse = Pin(BOTON_MORSE_PIN, Pin.IN, Pin.PULL_UP)
buzzer = PWM(Pin(BUZZER_PIN))
buzzer.freq(1000)
buzzer.duty_u16(0)  # Buzzer apagado

dip_velocidad = Pin(DIP_SWITCH_1_PIN, Pin.IN, Pin.PULL_UP)
dip_modo_trans = Pin(DIP_SWITCH_5_PIN, Pin.IN, Pin.PULL_UP)
switch_onoff = Pin(SWITCH_ONOFF_PIN, Pin.IN, Pin.PULL_UP)

data_pin = Pin(DATA_PIN_74HC164, Pin.OUT)
clock_pin = Pin(CLOCK_PIN_74HC164, Pin.OUT)

uart = UART(1, baudrate=115200, tx=Pin(UART_TX_PIN), rx=Pin(UART_RX_PIN))

socket_pc = None 

# Código Morse
MORSE = {"A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".", "F": "..-.", "G": "--.", "H":"....", "I": "..", "J": ".---", "K": "-.-", "L": ".-..", "M": "--", "N": "-.", "O": "---", "P": ".--.", "Q":"--.-", "R": ".-.", "S": "...", "T": "-",
    "U": "..-", "V": "...-", "W": ".--", "X": "-..-", "Y": "-.--", "Z": "--..", "0": "-----", "1": ".----", "2": "..---", "3": "...--", "4": "....-", "5": ".....", "6": "-....", "7": "--...", "8": "---..", "9": "----.", "+": ".-.-.", "-": "-....-"}

# Mapeo de letras a LED
MAPA_LEDS = {"A": 0, "C": 1, "E": 2, "G": 3, "I": 4, "K": 5, "M": 6, "O": 7, "Q": 8, "S": 9, "U": 10, "W": 11, "Y": 12, "B": 13, "D": 14, "F": 15, "H": 0, "J": 1, "L": 2, "N": 3, "P": 4, "R": 5, "T": 6, "V": 7, "X": 8, "Z": 9,"0": 10, "1": 11,
              "2": 12, "3": 13, "4": 14, "5": 15,"6": 0, "7": 1, "8": 2, "9": 3, "+":4, "-": 5}

#Variables 
unidad = 0.2  # Velocidad A por defecto
modo_transmision = "Simple"  # Simple o Escucha
frase_actual = ""
buffer_morse = ""
transmitiendo = False

#WIFI
def conectar_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Conectando a WiFi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        intentos = 0
        while not wlan.isconnected() and intentos < 20:
            time.sleep(0.5)
            intentos += 1
    if wlan.isconnected():
        print("WiFi conectado:", wlan.ifconfig())
        return True
    else:
        print("Error: No se pudo conectar a WiFi")
        return False

# Enviar información hasta la pc
def enviar_a_pc(comando, datos=""):
    global socket_pc
    if socket_pc is None:
        if not conectar_pc():
            return False
        if socket_pc is None:
            return False
    try:
        mensaje = f"{MAQ_ID}:{comando}:{datos}"
        socket_pc.send(mensaje.encode())
        return True
    except Exception as e:
        print(f"Error enviando: {e}, reintentando conexión...")
        socket_pc = None
        if conectar_pc():
            try:
                socket_pc.send(mensaje.encode())
                return True
            except:
                socket_pc = None
        return False

def conectar_pc():
    global socket_pc
    try:
        if socket_pc:
            socket_pc.close()
        socket_pc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_pc.settimeout(None)  
        socket_pc.connect((PC_IP, PC_PORT))
        # Enviar mensaje de registro de maquetas
        socket_pc.send(f"{MAQ_ID}:CONECTADO:".encode())
        print("Conectado persistentemente a la PC")
        return True
    except Exception as e:
        print(f"Error conectando a PC: {e}")
        socket_pc = None
        return False

# Funcionalidad de las leds
def shift_out(byte_val):
    """Envía 8 bits al registro de corrimiento"""
    for i in range(8):
        clock_pin.value(0)
        data_pin.value((byte_val >> (7 - i)) & 1)
        clock_pin.value(1)

def apagar_todos_leds():
    """Apaga todos los LEDs"""
    shift_out(0x00)  # Primer registro
    shift_out(0x00)  # Segundo registro

def encender_led_letra(letra):
    letra = letra.upper()
    if letra in MAPA_LEDS:
        num_led = MAPA_LEDS[letra]
        apagar_todos_leds()
        
        if num_led < 8:
            shift_out(1 << num_led)   # Primer registro
            shift_out(0x00)           # Segundo apagado
        else:
            shift_out(0x00)           # Primero apagado
            shift_out(1 << (num_led - 8))  # Segundo registro

def mostrar_frase_leds(frase):
    for letra in frase.upper():
        if letra in MAPA_LEDS or letra == ' ':
            if letra != ' ':
                encender_led_letra(letra)
            else:
                apagar_todos_leds()
            time.sleep(unidad * 3)  # Tiempo entre letras
    
    apagar_todos_leds()

# Conectar buzzer
def buzzer_punto():
    buzzer.duty_u16(32768) 
    time.sleep(unidad)
    buzzer.duty_u16(0)
    time.sleep(unidad)

def buzzer_raya():
    buzzer.duty_u16(32768)
    time.sleep(unidad * 3)
    buzzer.duty_u16(0)
    time.sleep(unidad)

def transmitir_morse_buzzer(frase):
    for letra in frase.upper():
        if letra in MORSE:
            for simbolo in MORSE[letra]:
                if simbolo == '.':
                    buzzer_punto()
                elif simbolo == '-':
                    buzzer_raya()
            time.sleep(unidad * 2)  # Espacio entre letras
        elif letra == ' ':
            time.sleep(unidad * 4)  # Espacio entre palabras

# Configurar botón
def leer_boton_morse():
    if boton_morse.value() == 0: 
        # Botón presionado
        buzzer.duty_u16(32768)
        tiempo_inicio = time.ticks_ms()
        while boton_morse.value() == 0:
            time.sleep(0.01)
        tiempo_fin = time.ticks_ms()
        buzzer.duty_u16(0)
        duracion = time.ticks_diff(tiempo_fin, tiempo_inicio) / 1000.0
        if duracion < unidad * 2:  # Presión corta = punto
            return '.'
        else:                       # Presión larga = raya
            return '-'
    return ''  # No se presionó nada

# Configurar dip switch
def leer_configuracion_dip():
    global unidad, modo_transmision
    # Velocidad
    if dip_velocidad.value() == 0:
        unidad = 0.2
        velocidad_texto = "A (0.2s)"
    else:
        unidad = 0.3
        velocidad_texto = "B (0.3s)"
    # Modo transmisión
    if dip_modo_trans.value() == 0:
        modo_transmision = "Simple"
    else:
        modo_transmision = "Escucha"
    print(f"Config: Vel={velocidad_texto}, Modo={modo_transmision}")
    return unidad, modo_transmision

# Lógica del modo local - dos jugadores en la misma maqueta
def modo_local():
    global buffer_morse, transmitiendo
    buzzer.duty_u16(0)
    print("Modo Local iniciado")
    ultimo_tiempo = time.ticks_ms()
    pausa_detectada = False
    while True:
        # Leer botón
        simbolo = leer_boton_morse()
        if simbolo:
            buffer_morse += simbolo
            ultimo_tiempo = time.ticks_ms()
            pausa_detectada = False
            print(f"Símbolo: {simbolo}", end='')
        # Detectar pausa entre letras (> 3 unidades)
        tiempo_actual = time.ticks_ms()
        if not pausa_detectada and buffer_morse and \
           time.ticks_diff(tiempo_actual, ultimo_tiempo) > (unidad * 3 * 1000):
            # Enviar letra completa
            enviar_a_pc("MORSE", buffer_morse)
            print(f" -> Letra: {buffer_morse}")
            buffer_morse = ""
            pausa_detectada = True
        time.sleep(0.05)

# Lógica del modo versus - 2 maqutas por wifi
def modo_versus():
    global buffer_morse, frase_actual
    buzzer.duty_u16(0)
    print("Modo Versus iniciado")
    print(f"Frase a transmitir: {frase_actual}")
    # Mostrar frase en LEDs
    if modo_transmision == "Simple":
        mostrar_frase_leds(frase_actual)
    else:
        transmitir_morse_buzzer(frase_actual)
    buzzer.duty_u16(0)
    # Esperar entrada del jugador
    ultimo_tiempo = time.ticks_ms()
    while True:
        simbolo = leer_boton_morse()
        if simbolo:
            buffer_morse += simbolo
            ultimo_tiempo = time.ticks_ms()
            print(f"Símbolo: {simbolo}", end='')
        # Enviar a PC cuando hay pausa
        tiempo_actual = time.ticks_ms()
        if buffer_morse and \
           time.ticks_diff(tiempo_actual, ultimo_tiempo) > (unidad * 3 * 1000):
            enviar_a_pc("MORSE", buffer_morse)
            buffer_morse = ""
        time.sleep(0.05)

#Cofigurar main
def main():
    global unidad, modo_transmision, frase_actual
    print(f"\n{'='*40}")
    print(f"StrangerTEC Morse Translator")
    print(f"Maqueta: {MAQ_ID}")
    print(f"{'='*40}\n")
    
    # Conectar WiFi
    if not conectar_wifi():
        print("Error: Sin WiFi - entrando en modo offline")
    
    # Registrar con PC
    if conectar_wifi():
        conectar_pc()
    
    # Inicializar LEDs
    apagar_todos_leds()
    
    # Loop principal
    while True:
        # 1. Leer configuración del DIP switch (velocidad y modo transmisión)
        if dip_velocidad.value() == 0:
            unidad = 0.2
        else:
            unidad = 0.3
        
        if dip_modo_trans.value() == 0:
            modo_transmision = "Simple"
        else:
            modo_transmision = "Escucha"
        
        # 2. Leer switch ON/OFF para modo Local/Versus
        if switch_onoff.value():
            print(f"Modo Versus | Vel: {unidad}s | Trans: {modo_transmision}")
            modo_versus()
        else:
            print(f"Modo Local | Vel: {unidad}s | Trans: {modo_transmision}")
            modo_local()
        time.sleep(0.1)

#Iniciar todo el juego
if __name__ == "__main__":
    main()