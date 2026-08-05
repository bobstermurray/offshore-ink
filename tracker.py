import folium
import asyncio
import random
import csv
from pyproj import Transformer

transformers = {}

def load_assets():
    """Reads a cleanly formatted CSV file and transforms coordinates."""
    assets = []
    try:
        with open('assets.csv', mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                epsg = row["EPSG"].strip()
                easting = float(row["Easting"])
                northing = float(row["Northing"])
                
                # If it's already Lat/Lon (EPSG:4326), no transformation needed.
                # Easting = Longitude, Northing = Latitude
                if epsg == "EPSG:4326":
                    lat, lon = northing, easting
                else:
                    # Create the transformer only if we haven't used this EPSG yet
                    if epsg not in transformers:
                        transformers[epsg] = Transformer.from_crs(epsg, "EPSG:4326", always_xy=True)
                    
                    lon, lat = transformers[epsg].transform(easting, northing)
                
                assets.append({
                    "field": row["Field"],
                    "name": row["Asset"],
                    "lat": lat,
                    "lon": lon
                })
    except FileNotFoundError:
        print("Warning: assets.csv not found.")
    
    return assets

# ---------------------------------------------------------
# The Fleet Dictionary (Simulator)
# ---------------------------------------------------------
vessels = {
    "235103286": {"name": "Seven Kestrel", "lat": 57.143, "lon": -2.095, "status": "Simulated Transit"},
    "235071342": {"name": "Seven Atlantic", "lat": 56.780, "lon": 2.110, "status": "Simulated DP Ops"},
    "235084424": {"name": "Seven Falcon", "lat": 58.450, "lon": 1.020, "status": "Simulated Transit"}
}

def generate_map():
    map_center = [57.15, 0.5] 
    m = folium.Map(location=map_center, zoom_start=7, tiles="CartoDB positron")

    # --- Plot the Assets from the Cleaned CSV ---
    assets = load_assets()
    for asset in assets:
        folium.CircleMarker(
            location=[asset["lat"], asset["lon"]],
            radius=3, 
            color="grey",
            fill=True,
            fill_color="grey",
            fill_opacity=0.7,
            tooltip=f"{asset['field']} - {asset['name']}"
        ).add_to(m)

    # --- Plot the Vessels ---
    for mmsi, data in vessels.items():
        folium.Marker(
            location=[data["lat"], data["lon"]],
            tooltip=data["name"],
            popup=f"<b>{data['name']}</b><br>Status: {data['status']}",
            icon=folium.Icon(color="black", icon="ship", prefix="fa")
        ).add_to(m)

    m.save("epaper_preview.html")

# ---------------------------------------------------------
# Simulator Loop
# ---------------------------------------------------------
async def simulate_live_feed():
    print("Starting Offshore Ink Simulator...")
    generate_map()
    
    while True:
        await asyncio.sleep(5)
        mmsi = random.choice(list(vessels.keys()))
        v = vessels[mmsi]
        v["lat"] += random.uniform(-0.05, 0.05)
        v["lon"] += random.uniform(-0.05, 0.05)
        generate_map()

asyncio.run(simulate_live_feed())