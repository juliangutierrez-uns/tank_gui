import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk

import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import simcentralconnect

from tkinter import filedialog
import os

__version__ = "4.3"
__author__ = "UNS-UFCG-UFBA"

root = tk.Tk()
root.withdraw()  # ocultar ventana mientras selecciona carpeta

# Pedir carpeta
root_path = filedialog.askdirectory(title="Select the folder containing the project files")
if not root_path:
    messagebox.showerror("Error", "No folder was selected. The programme will close.")
    root.destroy()
    exit()

root.deiconify()  # mostrar la ventana luego de seleccionar carpeta


# Construcción de rutas dinámicas
simPath = os.path.join(root_path, "MW2-Tank_python.simx")
simName = "MW2-Tank_python"

logo_paths = {
    "uns": os.path.join(root_path, "logo_UNS.png"),
    "ufcg": os.path.join(root_path, "logo_UFCG.png"),
    "ufba": os.path.join(root_path, "logo_UFBA.png")
}

model_image_path = os.path.join(root_path, "model.png")


# Connect to SimCentral
sc = simcentralconnect.connect().Result
sc.SetOptions(repr({'EnableApiLogging': 'false'}))

sm  = sc.GetService("ISimulationManager")
vm  = sc.GetService("IVariableManager")
snm = sc.GetService("ISnapshotManager")
osm = sc.GetService("IOptimizationSetManager")
scm = sc.GetService("IScenarioManager")


sm.DeleteSim(simName).Result
sm.ImportSim(simPath).Result
sm.UpdateSimulationMode(simName,"Process").Result
snm.RevertSnapshot(simName,"Pro 3").Result
sm.UpdateSimulationMode(simName,"FluidFlow").Result
sm.UpdateSimulationMode(simName,"Dynamics").Result
snm.RevertSnapshot(simName,"Dyn 2").Result

# Global variables and data lists
simulacion_activa = False
sp_data = []
nivel_tanque_data = []
tiempo_data = []
erroplot = []
PIDplot = []
OPcplot = []
tiempo_iter = 0

# Initial control parameters
erro_integral = 0
iae_total = 0
kc = 100
ti = 0.5
tp = 0.1
sp_actual = 0.5

# Interface control
def iniciar_simulacion():
    global simulacion_activa, iae_total, erro_integral
    simulacion_activa = True
    iae_total = 0
    erro_integral = 0
    iae_var.set("0.00")

def detener_simulacion():
    global simulacion_activa
    simulacion_activa = False

def salir():
    detener_simulacion()
    root.quit()
    root.destroy()

def actualizar_parametros():
    global sp_actual, kc, ti, tp
    try:
        sp = float(entry_sp.get())
        if not 0.0 <= sp <= 1.0:
            raise ValueError("SP must be between 0 and 1")
        sp_actual = sp
        kc = float(entry_kc.get())
        ti = float(entry_ti.get())
        tp = float(entry_tp.get())
    except ValueError as e:
        messagebox.showerror("Input Error", str(e))

# PI control logic and plot update
def actualizar_grafico(_):
    global erro_integral, tiempo_iter
    if simulacion_activa:
        sm.RunSingleStep(simName)

        PV = vm.GetVariableValue(simName,"Tank1.Level","fraction").Result
        SP = sp_actual
        Fe = vm.GetVariableValue(simName,"S2.Q","m3/h").Result
        tiempo = vm.GetVariableValue(simName,"t","s").Result

        erro = SP - PV
        global iae_total
        iae_total += abs(erro) * tp
        PID = kc * erro + (kc / ti) * erro_integral

        D = vm.GetVariableValue(simName,"Tank1.D","m").Result
        A = 3.14159 * D * D * 0.25
        Fsc = Fe - A * PID
        Fs = max(0.0, min(Fsc, 108.6))
        OPc = Fs / 108.6
        OPc = max(0.0, min(OPc, 1.0))

        if Fs == Fsc:
            erro_integral += erro * tp

        vm.SetVariableValue(simName,"XV2.ManPos", OPc, "fraction").Result
        vm.SetVariableValue(simName,"PythonSet", SP, "fraction").Result

        sp_data.append(SP)
        nivel_tanque_data.append(PV)
        PIDplot.append(PID)
        erroplot.append(erro)
        OPcplot.append(OPc)
        tiempo_data.append(tiempo)

        nivel_var.set(f"{PV:.2f}")
        iae_var.set(f"{iae_total:.2f}")

        ax.clear()
        ax.plot(tiempo_data, sp_data, label="Set Point (SP)", color='tab:blue')
        ax.plot(tiempo_data, nivel_tanque_data, label="Tank Level", color='tab:orange')
        ax.fill_between(tiempo_data, sp_data, nivel_tanque_data, color='lightcoral', alpha=0.3, label="IAE Area")
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Level")
        ax.set_title("SP and Tank Level over Time")
        ax.legend()

        window = 3600  # segundos visibles en el gráfico
        if tiempo_data:
            t_max = tiempo_data[-1]
            t_min = max(0, t_max - window)
            ax.set_xlim(t_min, t_max)

        tiempo_iter += 1

def about():
    messagebox.showinfo("About", f"Version: {__version__}\nAuthor: {__author__}")


def on_resize(event):
    print(f"Ventana redimensionada: {event.width}x{event.height}")
    # Podés escalar fuentes, redibujar, etc.

def resize_image(path, width, height):
    img = Image.open(path)
    return ImageTk.PhotoImage(img.resize((width, height), Image.Resampling.LANCZOS))

def quit_me():
    root.quit()
    root.destroy()


''' GUI '''
root.title("Tank Control Simulation")
root.configure(bg='white')

screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
app_width = int(screen_width * 1)
app_height = int(screen_height * 1)
x_offset = int((screen_width - app_width) / 2)
y_offset = int((screen_height - app_height) / 2)
root.geometry(f"{app_width}x{app_height}+{x_offset}+{y_offset}")


### MENU
menubar = tk.Menu(root)
menu_about = tk.Menu(menubar, tearoff=0)
menu_about.add_command(label="About", command=about)
menubar.add_cascade(label="About", menu=menu_about)
root.config(menu=menubar)


### TOP FRAME
frame_top = tk.Frame(root, height=100, bg='white')
frame_top.pack(side="top", fill="x")

frame_logos = tk.Frame(frame_top, bg='white')
frame_logos.place(relx=0.5, rely=0.5, anchor="center")

logos = [
    {"path": logo_paths["uns"], "label": None, "base_size": (80, 80)},
    {"path": logo_paths["ufcg"], "label": None, "base_size": (80, 80)},
    {"path": logo_paths["ufba"], "label": None, "base_size": (60, 80)}
]


image_refs = []  # lista para evitar que se borren las imágenes

for logo in logos:
    img_tk = resize_image(logo["path"], *logo["base_size"])
    label = tk.Label(frame_logos, image=img_tk, bg='white')
    label.pack(side="left", padx=10, pady=10)
    logo["label"] = label
    image_refs.append(img_tk)  # guardar la referencia



### LEFT FRAME
frame_left = tk.Frame(root, bg='white')
frame_left.pack(side=tk.LEFT, fill="both", expand=True, padx=10, pady=10)

tk.Button(frame_left, text="Start Simulation", font=('Arial', 10, 'bold'), bg="#3e1152", fg="white", command=iniciar_simulacion, width=20).pack(pady=2)
tk.Button(frame_left, text="Stop Simulation", font=('Arial', 10, 'bold'), bg="#3e1152", fg="white", command=detener_simulacion, width=20).pack(pady=2)

tk.Label(frame_left, text="Set Point (SP):", font=('Arial', 10, 'bold'), bg="#3e1152", fg="white", width=20).pack(pady=(20,0))
entry_sp = tk.Entry(frame_left)
entry_sp.insert(0, "0.5")
entry_sp.pack(pady=2)

tk.Label(frame_left, text="Tank Level:", font=('Arial', 10, 'bold'), bg="#3e1152", fg="white", width=20).pack(pady=2)
nivel_var = tk.StringVar()
tk.Label(frame_left, textvariable=nivel_var, font=('Arial', 10, 'bold'), bg="white", width=20).pack(pady=2)
tk.Label(frame_left, text="IAE:", font=('Arial', 10, 'bold'), bg="#3e1152", fg="white", width=20).pack(pady=2)
iae_var = tk.StringVar()
tk.Label(frame_left, textvariable=iae_var, font=('Arial', 10, 'bold'), bg="white", width=20).pack(pady=2)


tk.Label(frame_left, text="kc:", font=('Arial', 10, 'bold'), bg="#3e1152", fg="white", width=20).pack(pady=2)
entry_kc = tk.Entry(frame_left)
entry_kc.insert(0, "100")
entry_kc.pack(pady=2)

tk.Label(frame_left, text="ti:", font=('Arial', 10, 'bold'), bg="#3e1152", fg="white", width=20).pack(pady=2)
entry_ti = tk.Entry(frame_left)
entry_ti.insert(0, "0.5")
entry_ti.pack(pady=2)

tk.Label(frame_left, text="tp:", font=('Arial', 10, 'bold'), bg="#3e1152", fg="white", width=20).pack(pady=2)
entry_tp = tk.Entry(frame_left)
entry_tp.insert(0, "0.1")
entry_tp.pack(pady=2)

tk.Button(frame_left, text="Update Parameters", font=('Arial', 10, 'bold'), bg="#3e1152", fg="white", command=actualizar_parametros, width=20).pack(pady=10)
tk.Button(frame_left, text="Exit", font=('Arial', 10, 'bold'), bg="red", fg="white", command=salir).pack(pady=10)

#image model
model_info = {"path": model_image_path, "label": None, "base_size": (400, 150)}
model_tk = resize_image(model_info["path"], *model_info["base_size"])
model_label = tk.Label(frame_left, image=model_tk, bg='white')
model_label.image_ref = model_tk
model_label.pack()
model_info["label"] = model_label

### RIGHT FRAME
frame_right = tk.Frame(root)
frame_right.pack(side=tk.RIGHT, fill="both", expand=True, padx=10, pady=10)

fig, ax = plt.subplots(figsize=(6, 4))
canvas = FigureCanvasTkAgg(fig, master=frame_right)
canvas.get_tk_widget().pack(fill="both", expand=True)

ani = animation.FuncAnimation(fig, actualizar_grafico, interval=100)

def on_resize(event):
    new_width = event.width
    new_height = event.height

    # Update the canvas size
    root.geometry(f"{new_width}x{new_height}+{x_offset}+{y_offset}")

root.bind("<Configure>", on_resize)
root.protocol("WM_DELETE_WINDOW", quit_me)
root.mainloop()