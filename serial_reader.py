import serial
import time
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque
from serial.tools import list_ports

# --- PARAMÈTRES DE COMMUNICATION SÉRIE ---
# ATTENTION : Remplacez 'COMx' par le port de votre carte Nucleo (ex: 'COM4' ou '/dev/ttyACM0')
COM_PORT_TO_USE = 'COM3'  
BAUD_RATE = 115200
DATA_POINTS = 50  # Nombre de points affichés sur la courbe

# Listes circulaires (deque) pour stocker les données historiques (optimisé pour les ajouts/suppressions rapides)
time_data = deque(maxlen=DATA_POINTS)
ldr_data = deque(maxlen=DATA_POINTS)
hum_data = deque(maxlen=DATA_POINTS)
temp_data = deque(maxlen=DATA_POINTS)
press_data = deque(maxlen=DATA_POINTS)

# Initialisation de la connexion série
ser = None
start_time = time.time()

def find_stlink_port(vid=0x0483, pid=0x374B):
    """ Tente de trouver le port ST-Link Virtual COM Port. """
    ports = list(list_ports.comports())
    for port, desc, hwid in ports:
        if f"VID:PID={vid:04X}:{pid:04X}" in hwid:
            return port
    return None

def init_serial():
    """ Initialise la connexion série. """
    global ser
    
    port_name = find_stlink_port() or COM_PORT_TO_USE
    
    try:
        ser = serial.Serial(port_name, BAUD_RATE, timeout=0.1)
        print(f"Connexion établie sur {port_name} @ {BAUD_RATE} bauds.")
    except serial.SerialException as e:
        print(f"Erreur de connexion série : {e}")
        print(f"Veuillez vérifier que le port '{port_name}' est correct et que le STM32 est branché.")
        exit()

def get_data():
    """ Lit une ligne de données CSV et met à jour les listes. """
    global ser
    
    if ser is None or not ser.is_open:
        return
        
    try:
        line = ser.readline().decode('utf-8').strip()
        
        if line:
            # Séparer les valeurs basées sur la virgule
            values = line.split(',')
            
            # On vérifie qu'on a bien 4 valeurs (LDR, HUM, TEMP, PRESS)
            if len(values) == 4:
                try:
                    # Conversion en entiers
                    ldr, hum, temp, press = map(int, values)
                    
                    # Ajout des données
                    time_data.append(time.time() - start_time)
                    ldr_data.append(ldr)
                    hum_data.append(hum)
                    temp_data.append(temp)
                    press_data.append(press)
                    
                    # Affichage console pour vérification
                    print(f"Temps: {time_data[-1]:.1f}s | LDR: {ldr} | Hum: {hum} | Temp: {temp} | Press: {press}")
                    
                except ValueError:
                    # Gère les erreurs de conversion (si des caractères non numériques sont reçus)
                    # print(f"Erreur de format de données: {line}")
                    pass

    except serial.SerialException:
        print("Déconnexion série.")
        ser.close()
        ser = None
    except Exception as e:
        # print(f"Erreur inattendue : {e}")
        pass

def animate(i, lines, axes):
    """ Fonction appelée par l'animation pour mettre à jour les graphiques. """
    get_data()
    
    if not time_data:
        return lines # Retourne les lignes non modifiées si pas de données
        
    # Mise à jour des données de temps
    x = list(time_data)
    
    # Mise à jour de chaque courbe
    lines[0].set_data(x, list(ldr_data))
    lines[1].set_data(x, list(hum_data))
    lines[2].set_data(x, list(temp_data))
    lines[3].set_data(x, list(press_data))
    
    # Ajustement automatique des limites X (le temps)
    axes[0].set_xlim(max(0, x[-1] - DATA_POINTS), x[-1] + 1)
    
    # Ajustement automatique des limites Y pour chaque sous-graphique
    for ax, data in zip(axes, [ldr_data, hum_data, temp_data, press_data]):
        if data:
            # On donne un peu de marge (min - 50, max + 50)
            ax.set_ylim(min(data) - 50, max(data) + 50)
            
    return lines

# --- INITIALISATION ET AFFICHAGE ---

# 1. Initialisation de la connexion série
init_serial()

# 2. Configuration de l'interface graphique
fig, axes = plt.subplots(4, 1, sharex=True, figsize=(10, 8)) # 4 sous-graphiques, partageant l'axe X
fig.suptitle("Acquisition de Données STM32 (Valeurs ADC Brutes 0-4095)", fontsize=16)

# Liste pour stocker les objets Line2D (les courbes)
lines = []

# Configuration des 4 sous-graphiques
titles = ["LDR (Lumière - PA0/IN0)", "OPENME110 (Humidité - PA1/IN1)", 
          "Diode (Température - PA4/IN4)", "MPX2200DP (Pression - PC0/IN10)"]
colors = ['blue', 'green', 'red', 'purple']

for i, ax in enumerate(axes):
    line, = ax.plot([], [], colors[i])
    lines.append(line)
    ax.set_title(titles[i], fontsize=10)
    ax.grid(True)
    ax.tick_params(axis='y', labelsize=8)

# Définition de l'axe des temps pour le graphique du bas
axes[-1].set_xlabel("Temps (secondes)")

# 3. Création de l'animation
# interval=1000/60 -> 60 rafraîchissements par seconde pour le graphique
ani = animation.FuncAnimation(fig, animate, fargs=(lines, axes), interval=1000/60, blit=False)

# 4. Affichage du graphique
try:
    plt.show()
finally:
    # Fermeture propre du port série si l'utilisateur ferme la fenêtre Matplotlib
    if ser and ser.is_open:
        ser.close()
        print("\nApplication fermée. Port série relâché.")