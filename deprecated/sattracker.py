# NOAA Polar Operational Environmental Satellites (POES) Pass Tracker
# Powered by N2YO API

import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import requests
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import datetime
import pytz

API_KEY = 'NWCGC9-LK2RRA-VJAU5R-3GM5'
BASE_URL = 'https://api.n2yo.com/rest/v1/satellite/radiopasses'
NORAD_IDS = {'15': 25338, '18': 28654, '19': 33591}
SAT_FREQUENCIES = {'15': '137.620 MHz', '18': '137.9125 MHz', '19': '137.100 MHz'}
LAT, LNG, ALT = 39.9216, -75.1812, 12

sort_states = {}
eastern_tz = pytz.timezone('America/New_York')
all_pass_data = {}
canvas = None  # Canvas holder for polar plot

def get_satellite_passes(norad_id):
    url = f"{BASE_URL}/{norad_id}/{LAT}/{LNG}/{ALT}/2/10/&apiKey={API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if 'passes' in data:
            return data
        else:
            messagebox.showwarning("Warning", f"No passes data found: {data.get('info', 'No additional info')}")
    else:
        messagebox.showerror("Error", f"Failed to retrieve data: {response.status_code}")
    return None

def plot_horizon(pass_data, sat_name):
    plt.clf()
    fig, ax = plt.subplots(subplot_kw={'projection': 'polar'}, figsize=(4, 4))
    ax.set_theta_direction(-1)
    ax.set_theta_offset(3.14159 / 2)
    ax.set_title(f"NOAA {sat_name} Pass Path", fontsize=14)
    for p in pass_data:
        start_az = p['startAz'] * (3.14159 / 180)
        max_az = p['maxAz'] * (3.14159 / 180)
        end_az = p['endAz'] * (3.14159 / 180)
        start_el = 90 - p.get('startEl', 0)
        max_el = 90 - p.get('maxEl', 0)
        end_el = 90 - p.get('endEl', 0)
        ax.plot([start_az, max_az, end_az], [start_el, max_el, end_el], marker='o')
        ax.annotate(f"Start: {p.get('startAzCompass', 'N/A')}", (start_az, start_el), fontsize=8)
        ax.annotate(f"End: {p.get('endAzCompass', 'N/A')}", (end_az, end_el), fontsize=8)
    ax.set_ylim(0, 90)
    ax.set_yticks(range(0, 91, 10))
    ax.set_yticklabels(range(0, 91, 10))
    return fig

def refresh_data():
    for row in table.get_children():
        table.delete(row)
    all_pass_data.clear()
    for short_id, norad_id in NORAD_IDS.items():
        data = get_satellite_passes(norad_id)
        if data and 'passes' in data:
            for p in data['passes']:
                start_time_utc = datetime.datetime.utcfromtimestamp(p['startUTC'])
                start_time_et = start_time_utc.replace(tzinfo=pytz.utc).astimezone(eastern_tz)
                start_hour = start_time_et.hour
                max_el = p.get('maxEl', 0)

                if max_el > 60:
                    tag = 'high'
                    best_pass = "HIGH"
                elif max_el > 30:
                    tag = 'mid'
                    best_pass = "MID"
                else:
                    tag = 'low'
                    best_pass = "LOW"

                if not (8 <= start_hour < 20 and max_el > 40):
                    best_pass = ""

                # Format times
                start_time = start_time_et.strftime('%b %d %I:%M %p')
                max_time = datetime.datetime.utcfromtimestamp(p['maxUTC']).replace(tzinfo=pytz.utc).astimezone(eastern_tz).strftime('%I:%M %p')
                end_time = datetime.datetime.utcfromtimestamp(p['endUTC']).replace(tzinfo=pytz.utc).astimezone(eastern_tz).strftime('%b %d %I:%M %p')

                table.insert("", tk.END, values=(
                    short_id, start_time,
                    f"{p['startAz']}° ({p['startAzCompass']})",
                    f"{p['maxEl']}° at {max_time}", end_time,
                    f"{p['endAz']}° ({p['endAzCompass']})", best_pass
                ), tags=(tag,))

                all_pass_data[(short_id, start_time)] = (short_id, [p])

def on_select(event):
    global canvas
    selected_item = table.selection()
    if selected_item:
        values = table.item(selected_item, "values")
        sat_id, start_time = values[0], values[1]
        if (sat_id, start_time) in all_pass_data:
            short_id, pass_data = all_pass_data[(sat_id, start_time)]
            fig = plot_horizon(pass_data, short_id)
            if canvas:
                canvas.get_tk_widget().destroy()
            canvas = FigureCanvasTkAgg(fig, master=window)
            canvas.get_tk_widget().grid(row=3, column=1, padx=10, pady=10)

def sort_column(col):
    data = [(table.set(child, col), child) for child in table.get_children('')]
    data.sort(reverse=sort_states.get(col, False))
    for index, (_, item) in enumerate(data):
        table.move(item, '', index)
    sort_states[col] = not sort_states.get(col, False)

# Add this function
def toggle_theme():
    current_theme = style.theme_use()
    if current_theme == "default":
        style.theme_use("clam")  # Example dark theme
        window.configure(bg="black")
        table.configure(style="Dark.Treeview")
    else:
        style.theme_use("default")
        window.configure(bg="white")
        table.configure(style="Treeview")

# GUI setup
window = tk.Tk()
window.title("NOAA Satellite Pass Tracker")
window.geometry("1200x800")

# Add this before the table definition
title_label = tk.Label(window, text="NOAA Satellite Pass Tracker", font=("Arial", 16, "bold"))
title_label.grid(row=0, column=1, pady=(10, 5))

columns = ("NOAA", "Start Time", "Start Azimuth", "Max Elevation", "End Time", "End Azimuth", "Pass Quality")
table = ttk.Treeview(window, columns=columns, show="headings", height=20)

# Modify the column definition loop
for col in columns:
    table.heading(col, text=col, command=lambda c=col: sort_column(c))
    table.column(col, anchor=tk.CENTER)  # Let the column size adjust automatically

scrollbar = ttk.Scrollbar(window, orient="vertical", command=table.yview)
table.configure(yscroll=scrollbar.set)
scrollbar.grid(row=0, column=2, sticky="ns")

style = ttk.Style()
style.configure("Treeview", font=("Arial", 10))
style.configure("Treeview.Heading", font=("Arial", 11, "bold"))
table.tag_configure('high', foreground='green')
table.tag_configure('mid', foreground='orange')
table.tag_configure('low', foreground='red')

table.grid(row=0, column=1, padx=10, pady=10)
table.bind("<<TreeviewSelect>>", on_select)

refresh_button = tk.Button(window, text="Refresh Data", command=refresh_data, font=("Arial", 12))
refresh_button.grid(row=1, column=1, pady=(10, 5))

# Add a button for toggling theme
theme_button = tk.Button(window, text="Toggle Theme", command=toggle_theme, font=("Arial", 12))
theme_button.grid(row=1, column=1, pady=(5, 10), sticky="e")

# Replace the legend definition with this
legend_frame = tk.Frame(window)
legend_frame.grid(row=2, column=1, pady=(0, 10))

legend_label = tk.Label(legend_frame, text="Frequencies:", font=("Arial", 10, "bold"))
legend_label.pack(side=tk.LEFT, padx=5)

for sat_id, freq in SAT_FREQUENCIES.items():
    tk.Label(legend_frame, text=f"NOAA {sat_id}: {freq}", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)

window.mainloop()
