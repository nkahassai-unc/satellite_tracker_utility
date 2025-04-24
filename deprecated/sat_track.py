import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import requests
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import datetime

# Replace with your actual N2YO API key
API_KEY = 'NWCGC9-LK2RRA-VJAU5R-3GM5'
BASE_URL = 'https://api.n2yo.com/rest/v1/satellite/radiopasses'
NORAD_IDS = {'NOAA 15': 25338, 'NOAA 18': 28654, 'NOAA 19': 33591}
SAT_FREQUENCIES = {'NOAA 15': '137.620 MHz', 'NOAA 18': '137.9125 MHz', 'NOAA 19': '137.100 MHz'}
LAT, LNG, ALT = 39.9216, -75.1812, 12  # Coordinates for ZIP 19145, Altitude ~12m

# Track sort state for each column
sort_states = {}

def get_satellite_passes(norad_id):
    """Fetch the satellite passes for a given NORAD ID."""
    url = f"{BASE_URL}/{norad_id}/{LAT}/{LNG}/{ALT}/2/10/&apiKey={API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if 'passes' in data:
            return data
        else:
            messagebox.showwarning("Warning", f"No passes data found: {data.get('info', 'No additional info')}")
            return None
    else:
        messagebox.showerror("Error", f"Failed to retrieve data: {response.status_code}")
        return None

def plot_horizon(pass_data, sat_name):
    """Plot the pass path on a polar plot representing the horizon."""
    plt.clf()  # Clear the current figure
    fig, ax = plt.subplots(subplot_kw={'projection': 'polar'}, figsize=(4, 4))
    ax.set_theta_direction(-1)
    ax.set_theta_offset(3.14159 / 2)
    ax.set_title(f"{sat_name} Pass Path", fontsize=14)

    for p in pass_data:
        start_az = p['startAz'] * (3.14159 / 180)
        max_az = p['maxAz'] * (3.14159 / 180)
        end_az = p['endAz'] * (3.14159 / 180)
        
        # Debugging output to inspect available keys in p
        print(f"Satellite pass data: {p}")

        # Use .get() to avoid KeyError and provide a default value
        start_el = 90 - p.get('startEl', 0)
        max_el = 90 - p.get('maxEl', 0)
        end_el = 90 - p.get('endEl', 0)  # Ensure this key exists or provide default

        ax.plot([start_az, max_az, end_az], [start_el, max_el, end_el], marker='o')
        ax.annotate(f"Start: {p.get('startAzCompass', 'N/A')}", (start_az, start_el), fontsize=8)
        ax.annotate(f"End: {p.get('endAzCompass', 'N/A')}", (end_az, end_el), fontsize=8)

    ax.set_ylim(0, 90)  # Set limits to represent elevation in degrees
    ax.set_yticks(range(0, 91, 10))  # Set y-ticks for elevation in degrees
    ax.set_yticklabels(range(0, 91, 10))  # Set y-tick labels to degrees

    return fig

def refresh_data():
    """Refresh and display pass data for each satellite."""
    for row in table.get_children():
        table.delete(row)  # Clear the table before adding new data
    all_pass_data.clear()
    for sat_name, norad_id in NORAD_IDS.items():
        data = get_satellite_passes(norad_id)
        if data and 'passes' in data:
            passes = data['passes']
            for p in passes:
                start_time = datetime.datetime.utcfromtimestamp(p['startUTC']).strftime('%Y-%m-%d %H:%M:%S')
                max_time = datetime.datetime.utcfromtimestamp(p['maxUTC']).strftime('%Y-%m-%d %H:%M:%S')
                end_time = datetime.datetime.utcfromtimestamp(p['endUTC']).strftime('%Y-%m-%d %H:%M:%S')
                table.insert("", tk.END, values=(
                    sat_name, SAT_FREQUENCIES[sat_name], start_time, f"{p['startAz']}° ({p['startAzCompass']})",
                    f"{p['maxEl']}° at {max_time}", end_time, f"{p['endAz']}° ({p['endAzCompass']})"
                ), tags=('green_text',))
                all_pass_data[(sat_name, start_time)] = (sat_name, [p])

def on_select(event):
    """Update the diagram based on selected pass."""
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
    """Sort the column data in ascending or descending order."""
    data = [(table.set(child, col), child) for child in table.get_children('')]
    data.sort(reverse=sort_states.get(col, False))
    for index, (_, item) in enumerate(data):
        table.move(item, '', index)
    sort_states[col] = not sort_states.get(col, False)

# GUI setup
window = tk.Tk()
window.title("NOAA Satellite Pass Tracker")
window.geometry("1200x600")

# Data storage for passes
all_pass_data = {}

# Treeview for table-like display with styled text
columns = ("Satellite", "Frequency", "Start Time", "Start Azimuth", "Max Elevation", "End Time", "End Azimuth")
table = ttk.Treeview(window, columns=columns, show="headings", height=20)
for col in columns:
    table.heading(col, text=col, command=lambda c=col: sort_column(c))
    table.column(col, anchor=tk.CENTER, width=120)

# Add a scrollbar to the table
scrollbar = ttk.Scrollbar(window, orient="vertical", command=table.yview)
table.configure(yscroll=scrollbar.set)
scrollbar.grid(row=0, column=2, sticky="ns")

# Style the Treeview with green text on a black background
style = ttk.Style()
style.configure("Treeview", background="black", foreground="green", fieldbackground="black", font=("Arial", 10))
style.configure("Treeview.Heading", font=("Arial", 11, "bold"))

# Apply the style to the table rows
table.tag_configure('green_text', foreground='green')

# Place the table in the window
table.grid(row=0, column=1, padx=10, pady=10)

# Bind selection to updating the plot
table.bind("<<TreeviewSelect>>", on_select)

# Refresh button to trigger data fetch
refresh_button = tk.Button(window, text="Refresh Data", command=refresh_data, font=("Arial", 12))
refresh_button.grid(row=1, column=1, padx=10, pady=10)

# Start the GUI loop
window.mainloop()
