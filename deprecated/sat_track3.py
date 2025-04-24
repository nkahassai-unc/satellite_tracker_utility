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
NORAD_IDS = {'NOAA 15': 25338, 'NOAA 18': 28654, 'NOAA 19': 33591}
SAT_FREQUENCIES = {'NOAA 15': '137.620 MHz', 'NOAA 18': '137.9125 MHz', 'NOAA 19': '137.100 MHz'}
LAT, LNG, ALT = 39.9216, -75.1812, 12

sort_states = {}
eastern_tz = pytz.timezone('America/New_York')
all_pass_data = {}

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
    ax.set_title(f"{sat_name} Pass Path", fontsize=14)
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
    for sat_name, norad_id in NORAD_IDS.items():
        data = get_satellite_passes(norad_id)
        if data and 'passes' in data:
            for p in data['passes']:
                start_time_utc = datetime.datetime.utcfromtimestamp(p['startUTC'])
                start_time_et = start_time_utc.replace(tzinfo=pytz.utc).astimezone(eastern_tz)
                start_hour = start_time_et.hour
                max_el = p.get('maxEl', 0)
                best_pass = "🔴"
                if max_el > 60:
                    best_pass = "🟢"
                elif max_el > 30:
                    best_pass = "🟡"

                if not (8 <= start_hour < 20 and max_el > 40):
                    best_pass = ""  # Only show dot if it's really best-ish

                start_time = start_time_et.strftime('%Y-%m-%d %I:%M:%S %p')
                max_time = datetime.datetime.utcfromtimestamp(p['maxUTC']).replace(tzinfo=pytz.utc).astimezone(eastern_tz).strftime('%Y-%m-%d %I:%M:%S %p')
                end_time = datetime.datetime.utcfromtimestamp(p['endUTC']).replace(tzinfo=pytz.utc).astimezone(eastern_tz).strftime('%Y-%m-%d %I:%M:%S %p')

                table.insert("", tk.END, values=(
                    sat_name, SAT_FREQUENCIES[sat_name], start_time,
                    f"{p['startAz']}° ({p['startAzCompass']})",
                    f"{p['maxEl']}° at {max_time}", end_time,
                    f"{p['endAz']}° ({p['endAzCompass']})", best_pass
                ), tags=('green_text',))

                all_pass_data[(sat_name, start_time)] = (sat_name, [p])

def on_select(event):
    selected_item = table.selection()
    if selected_item:
        values = table.item(selected_item, "values")
        sat_name, start_time = values[0], values[2]
        if (sat_name, start_time) in all_pass_data:
            sat_name, pass_data = all_pass_data[(sat_name, start_time)]
            fig = plot_horizon(pass_data, sat_name)
            canvas = FigureCanvasTkAgg(fig, master=window)
            canvas.get_tk_widget().grid(row=0, column=0, padx=10, pady=10)

def sort_column(col):
    data = [(table.set(child, col), child) for child in table.get_children('')]
    data.sort(reverse=sort_states.get(col, False))
    for index, (_, item) in enumerate(data):
        table.move(item, '', index)
    sort_states[col] = not sort_states.get(col, False)

# GUI setup
window = tk.Tk()
window.title("NOAA Satellite Pass Tracker")
window.geometry("1200x600")
window.configure(bg='lightgrey')

columns = ("Satellite", "Frequency", "Start Time", "Start Azimuth", "Max Elevation", "End Time", "End Azimuth", "Best Pass")
table = ttk.Treeview(window, columns=columns, show="headings", height=20)
for col in columns:
    table.heading(col, text=col, command=lambda c=col: sort_column(c))
    table.column(col, anchor=tk.CENTER, width=140)

scrollbar = ttk.Scrollbar(window, orient="vertical", command=table.yview)
table.configure(yscroll=scrollbar.set)
scrollbar.grid(row=0, column=2, sticky="ns")

style = ttk.Style()
style.configure("Treeview", background="black", foreground="green", fieldbackground="black", font=("Courier", 10))
style.configure("Treeview.Heading", font=("Courier", 11, "bold"))
table.tag_configure('green_text', foreground='green')

table.grid(row=0, column=1, padx=10, pady=10)
table.column("Best Pass", anchor=tk.CENTER, width=90)

table.bind("<<TreeviewSelect>>", on_select)

refresh_button = tk.Button(window, text="Refresh Data", command=refresh_data, font=("Courier", 12), bg='lightgrey')
refresh_button.grid(row=1, column=1, padx=10, pady=10)

window.mainloop()
