import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import requests
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import datetime
import pytz  # Import pytz for timezone handling

# Replace with your actual N2YO API key
API_KEY = 'NWCGC9-LK2RRA-VJAU5R-3GM5'
BASE_URL = 'https://api.n2yo.com/rest/v1/satellite/radiopasses'
NORAD_IDS = {'NOAA 15': 25338, 'NOAA 18': 28654, 'NOAA 19': 33591}
SAT_FREQUENCIES = {'NOAA 15': '137.620 MHz', 'NOAA 18': '137.9125 MHz', 'NOAA 19': '137.100 MHz'}
LAT, LNG, ALT = 39.9216, -75.1812, 12  # Coordinates for ZIP 19145, Altitude ~12m

# Track sort state for each column
sort_states = {}

# Timezone for Eastern Time
eastern_tz = pytz.timezone('America/New_York')

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

        start_el = 90 - p.get('startEl', 0)
        max_el = 90 - p.get('maxEl', 0)
        end_el = 90 - p.get('endEl', 0)  # Provide default value

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
                start_time_utc = datetime.datetime.utcfromtimestamp(p['startUTC'])
                start_time_et = start_time_utc.replace(tzinfo=pytz.utc).astimezone(eastern_tz)  # Convert to ET
                start_hour = start_time_et.hour
                max_el = p.get('maxEl', 0)  # Default to 0 if missing

                # Determine if this is a "BEST" pass
                best_pass = "X" if (8 <= start_hour < 20 and max_el > 40) else ""

                # Format times for display
                start_time_display = start_time_et.strftime('%Y-%m-%d %I:%M:%S %p')  # Format to 12-hour with AM/PM
                max_time_display = datetime.datetime.utcfromtimestamp(p['maxUTC']).replace(tzinfo=pytz.utc).astimezone(eastern_tz).strftime('%Y-%m-%d %I:%M:%S %p')
                end_time_display = datetime.datetime.utcfromtimestamp(p['endUTC']).replace(tzinfo=pytz.utc).astimezone(eastern_tz).strftime('%Y-%m-%d %I:%M:%S %p')

                # Insert pass data into the table with BEST indicator
                table.insert("", tk.END, values=(
                    sat_name, SAT_FREQUENCIES[sat_name], start_time_display,
                    f"{p['startAz']}° ({p['startAzCompass']})",
                    start_time_et,  # Store the original datetime object for sorting
                    max_time_display, end_time_display, best_pass
                ))

    # Function to sort the table by the datetime object
    def sort_by_datetime(col_index):
        data = [(table.set(child, col_index), child) for child in table.get_children('')]
        data.sort(key=lambda x: datetime.datetime.strptime(x[0], '%Y-%m-%d %H:%M:%S%z'))
        for index, (val, child) in enumerate(data):
            table.move(child, '', index)

    # Sort by the start time column (index 4)
    sort_by_datetime(4)

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
window.configure(bg='lightgrey')  # Set the main window background to light grey

# Data storage for passes
all_pass_data = {}

# Treeview for table-like display with styled text
columns = ("Satellite", "Frequency", "Start Time", "Start Azimuth", "Max Elevation", "End Time", "End Azimuth", "Best Pass")  # Added "Best Pass"
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

# Adjust width for the new column
table.column("Best Pass", anchor=tk.CENTER, width=80)  # Set the width for the 'Best Pass' column

# Bind selection to updating the plot
table.bind("<<TreeviewSelect>>", on_select)

# Refresh button to trigger data fetch
refresh_button = tk.Button(window, text="Refresh Data", command=refresh_data, font=("Arial", 12), bg='lightgrey')
refresh_button.grid(row=1, column=1, padx=10, pady=10)

# Start the GUI loop
window.mainloop()
