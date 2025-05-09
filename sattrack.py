import tkinter as tk
from tkinter import messagebox, ttk
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
canvas = None

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
    fig, ax = plt.subplots(subplot_kw={'projection': 'polar'}, figsize=(4, 4))
    ax.set_theta_direction(-1)
    ax.set_theta_offset(3.14159 / 2)
    ax.set_title(f"NOAA {sat_name} Pass Path", fontsize=12)
    for p in pass_data:
        az = [p.get('startAz', 0), p.get('maxAz', 0), p.get('endAz', 0)]
        el = [p.get('startEl', 0), p.get('maxEl', 0), p.get('endEl', 0)]
        az_rad = [a * (3.14159 / 180) for a in az]
        el_inv = [90 - e for e in el]
        ax.plot(az_rad, el_inv, marker='o')
        ax.annotate(f"Start: {p.get('startAzCompass', '')}", (az_rad[0], el_inv[0]), fontsize=8)
        ax.annotate(f"End: {p.get('endAzCompass', '')}", (az_rad[2], el_inv[2]), fontsize=8)
    ax.set_ylim(0, 90)
    ax.set_yticks(range(0, 91, 10))
    ax.set_yticklabels(reversed(range(0, 91, 10)))
    return fig

def refresh_data():
    for row in table.get_children():
        table.delete(row)
    all_pass_data.clear()
    for short_id, norad_id in NORAD_IDS.items():
        data = get_satellite_passes(norad_id)
        if data and 'passes' in data:
            for p in data['passes']:
                start_time_utc = datetime.datetime.fromtimestamp(p['startUTC'], tz=datetime.timezone.utc)
                start_time_et = start_time_utc.astimezone(eastern_tz)
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

                start_time = start_time_et.strftime('%b %d %I:%M %p')
                max_time = datetime.datetime.fromtimestamp(p['maxUTC'], tz=datetime.timezone.utc).astimezone(eastern_tz).strftime('%I:%M %p')
                end_time = datetime.datetime.fromtimestamp(p['endUTC'], tz=datetime.timezone.utc).astimezone(eastern_tz).strftime('%b %d %I:%M %p')

                table.insert("", tk.END, values=(
                    short_id, start_time,
                    f"{p.get('startAz', 0)}° ({p.get('startAzCompass', '')})",
                    f"{p.get('maxEl', 0)}° at {max_time}", end_time,
                    f"{p.get('endAz', 0)}° ({p.get('endAzCompass', '')})", best_pass
                ), tags=(tag,))

                key = (short_id, start_time)
                if key not in all_pass_data:
                    all_pass_data[key] = (short_id, [])
                all_pass_data[key][1].append(p)

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
            canvas = FigureCanvasTkAgg(fig, master=plot_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(padx=10, pady=10)

def sort_column(col):
    def extract_sort_key(value):
        try:
            if 'at' in value:
                time_str = value.split('at')[-1].strip()
                return datetime.datetime.strptime(time_str, '%I:%M %p')
            elif any(m in value for m in ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                                          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']):
                return datetime.datetime.strptime(value, '%b %d %I:%M %p')
            else:
                return float(value.split('°')[0])
        except:
            return value.lower() if isinstance(value, str) else value

    data = [(extract_sort_key(table.set(child, col)), child) for child in table.get_children('')]
    data.sort(reverse=sort_states.get(col, False))
    for index, (_, item) in enumerate(data):
        table.move(item, '', index)
    sort_states[col] = not sort_states.get(col, False)

# === GUI Setup ===
window = tk.Tk()
window.title("NOAA Satellite Pass Tracker")
window.geometry("1000x720")

# Title
tk.Label(window, text="NOAA Satellite Pass Tracker", font=("Arial", 16, "bold")).pack(pady=(10, 0))

# Frequencies
legend_frame = tk.Frame(window)
legend_frame.pack(pady=5)
tk.Label(legend_frame, text="Frequencies:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
for sat_id, freq in SAT_FREQUENCIES.items():
    tk.Label(legend_frame, text=f"NOAA {sat_id}: {freq}", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)

# Table
columns = ("NOAA", "Start Time", "Start Azimuth", "Max Elevation", "End Time", "End Azimuth", "Pass Quality")
table_frame = tk.Frame(window)
table_frame.pack()

table = ttk.Treeview(table_frame, columns=columns, show="headings", height=18)
col_widths = [50, 120, 140, 120, 120, 140, 80]
for col, width in zip(columns, col_widths):
    table.heading(col, text=col, command=lambda c=col: sort_column(c))
    table.column(col, anchor=tk.CENTER, width=width)

scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=table.yview)
table.configure(yscroll=scrollbar.set)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
table.pack(side=tk.LEFT, fill=tk.BOTH)

style = ttk.Style()
style.configure("Treeview", font=("Arial", 10))
style.configure("Treeview.Heading", font=("Arial", 11, "bold"))
table.tag_configure('high', foreground='green')
table.tag_configure('mid', foreground='orange')
table.tag_configure('low', foreground='red')

table.bind("<<TreeviewSelect>>", on_select)

# Refresh button
tk.Button(window, text="Refresh Data", command=refresh_data, font=("Arial", 12)).pack(pady=10)

# Polar Plot Frame
plot_frame = tk.LabelFrame(window, text="Pass Path Plot", padx=5, pady=5)
plot_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

window.mainloop()
