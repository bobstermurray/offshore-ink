import folium

# Center the map off the East Coast of Scotland / Aberdeen
map_center = [57.15, 0.5] 

# "CartoDB positron" provides a clean, black-and-white base map 
# to mimic the physical e-paper aesthetic.
m = folium.Map(location=map_center, zoom_start=7, tiles="CartoDB positron")

# We will swap these hardcoded coordinates for a live API feed later.
# I've included the actual MMSI numbers for your fleet.
vessels = [
    {"name": "Seven Kestrel", "mmsi": "235103286", "lat": 57.143, "lon": -2.095, "status": "Aberdeen Harbour"},
    {"name": "Seven Atlantic", "mmsi": "235071342", "lat": 56.780, "lon": 2.110, "status": "Central North Sea"},
    {"name": "Seven Falcon", "mmsi": "235084424", "lat": 58.450, "lon": 1.020, "status": "Northern North Sea"}
]

# Plot each vessel on the map
for v in vessels:
    folium.Marker(
        location=[v["lat"], v["lon"]],
        tooltip=v["name"],
        popup=f"<b>{v['name']}</b><br>MMSI: {v['mmsi']}<br>{v['status']}",
        icon=folium.Icon(color="black", icon="ship", prefix="fa")
    ).add_to(m)

# Generate the web page
m.save("epaper_preview.html")
print("Map generated! Look for epaper_preview.html in your folder.")