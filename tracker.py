import os
import csv
import json
import folium
import asyncio
import websockets
from datetime import datetime, timezone
from pyproj import Transformer

API_KEY = "18b68f6810277aef82705d77fde940c9e5f3567b"
CACHE_FILE = "last_known.json"
JS_DATA_FILE = "vessels_data.js"

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
                
                if epsg == "EPSG:4326":
                    lat, lon = northing, easting
                else:
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

SUBSEA_ASSETS = load_assets()

# ---------------------------------------------------------
# The Fleet Dictionary & Persistent Cache
# ---------------------------------------------------------
vessels = {
    "235103286": {"name": "Seven Kestrel", "lat": None, "lon": None, "sog": 0.0, "cog": 0.0, "updated": "Never"},
    "235071342": {"name": "Seven Atlantic", "lat": None, "lon": None, "sog": 0.0, "cog": 0.0, "updated": "Never"},
    "235084424": {"name": "Seven Falcon", "lat": None, "lon": None, "sog": 0.0, "cog": 0.0, "updated": "Never"}
}

def load_vessel_cache():
    """Loads last known vessel positions from disk on startup."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                for mmsi, data in saved.items():
                    if mmsi in vessels:
                        vessels[mmsi].update(data)
            print("Loaded last known vessel positions from cache.")
        except Exception as e:
            print(f"Could not read cache file: {e}")

def save_vessel_cache():
    """Saves current vessel positions to disk (JSON for Python, JS for smooth browser updates)."""
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(vessels, f, indent=2)
        with open(JS_DATA_FILE, "w", encoding="utf-8") as f:
            f.write(f"window.LATEST_VESSELS = {json.dumps(vessels)};")
    except Exception as e:
        print(f"Could not save cache file: {e}")

# ---------------------------------------------------------
# Map Generator (Antique Chart Style + Flash-Free Updates)
# ---------------------------------------------------------
def generate_map():
    map_center = [57.15, 0.5]
    m = folium.Map(location=map_center, zoom_start=7, tiles=None)
    map_id = m.get_name()

    # Antique Parchment CSS (No full-page meta refresh needed)
    custom_head = """
    <style>
        .leaflet-container {
            background-color: #e6dcc8 !important;
            font-family: Georgia, 'Times New Roman', serif;
        }
        .leaflet-tile-pane {
            filter: sepia(70%) contrast(105%) brightness(92%) hue-rotate(-5deg);
        }
        .antique-label {
            background-color: rgba(244, 236, 216, 0.9) !important;
            border: 1px solid #4a3525 !important;
            border-radius: 2px !important;
            color: #2b1d12 !important;
            font-family: Georgia, 'Times New Roman', serif !important;
            font-size: 11px !important;
            padding: 2px 6px !important;
            box-shadow: 1px 1px 3px rgba(0,0,0,0.3) !important;
        }
        .leaflet-tooltip-left.antique-label::before { border-left-color: #4a3525 !important; }
        .leaflet-tooltip-right.antique-label::before { border-right-color: #4a3525 !important; }
    </style>
    """
    m.get_root().header.add_child(folium.Element(custom_head))

    # 1. Base Layer: Esri Light Gray (Minimalist Antique Engraving Look)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles &copy; Esri",
        name="Antique Ink (Minimal)"
    ).add_to(m)

    # 2. Base Layer: Esri NatGeo (Vintage Explorer Atlas Look)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/NatGeo_World_Map/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles &copy; Esri &mdash; National Geographic",
        name="Vintage Atlas (Detailed)"
    ).add_to(m)

    # 3. Optional Overlay: OpenSeaMap Nautical Marks
    folium.TileLayer(
        tiles="https://tiles.openseamap.org/seamark/{z}/{x}/{y}.png",
        attr="Map data: &copy; OpenSeaMap contributors",
        name="Nautical Seamarks",
        overlay=True,
        control=True,
        show=False
    ).add_to(m)

    # --- Plot the Subsea Assets ---
    for asset in SUBSEA_ASSETS:
        folium.CircleMarker(
            location=[asset["lat"], asset["lon"]],
            radius=3, 
            color="#6e553e",
            fill=True,
            fill_color="#8c6d4f",
            fill_opacity=0.6,
            tooltip=f"{asset['field']} - {asset['name']}"
        ).add_to(m)

    folium.LayerControl().add_to(m)

    # Dynamic JS: Polls vessels_data.js every 5 seconds and moves markers without reloading the page
    dynamic_vessels_js = f"""
    <script>
        window.addEventListener('load', function() {{
            var map = {map_id};
            var vesselMarkers = {{}};

            function buildIcon(cog) {{
                var html = '<div style="transform: rotate(' + cog + 'deg); width: 24px; height: 24px; display: flex; align-items: center; justify-content: center;">' +
                           '<svg width="22" height="22" viewBox="0 0 24 24">' +
                           '<polygon points="12,2 19,21 12,17 5,21" fill="#1f140e" stroke="#f4ecd8" stroke-width="1.5"/>' +
                           '</svg></div>';
                return L.divIcon({{
                    html: html,
                    className: '',
                    iconSize: [24, 24],
                    iconAnchor: [12, 12]
                }});
            }}

            function updateVesselsOnMap(vessels) {{
                for (var mmsi in vessels) {{
                    var d = vessels[mmsi];
                    if (d.lat === null || d.lon === null) continue;

                    var cog = d.cog || 0.0;
                    var sog = d.sog || 0.0;
                    var popupHtml = "<div style='font-family: Georgia, serif; color: #2b1d12;'>" +
                                    "<b>" + d.name + "</b><br>MMSI: " + mmsi +
                                    "<br>Speed: " + sog + " kn<br>Course: " + cog + "&deg;" +
                                    "<br>Last Ping: " + d.updated + "</div>";
                    var tooltipHtml = "<b>" + d.name + "</b> (" + sog + " kn)";

                    if (vesselMarkers[mmsi]) {{
                        vesselMarkers[mmsi].setLatLng([d.lat, d.lon]);
                        vesselMarkers[mmsi].setIcon(buildIcon(cog));
                        vesselMarkers[mmsi].setPopupContent(popupHtml);
                        vesselMarkers[mmsi].setTooltipContent(tooltipHtml);
                    }} else {{
                        var marker = L.marker([d.lat, d.lon], {{ icon: buildIcon(cog) }}).addTo(map);
                        marker.bindPopup(popupHtml, {{ maxWidth: 200 }});
                        marker.bindTooltip(tooltipHtml, {{
                            permanent: true,
                            direction: 'right',
                            offset: [10, 0],
                            className: 'antique-label'
                        }});
                        vesselMarkers[mmsi] = marker;
                    }}
                }}
            }}

            function pollVesselData() {{
                var oldScript = document.getElementById('vessel-data-poller');
                if (oldScript) oldScript.remove();

                var s = document.createElement('script');
                s.id = 'vessel-data-poller';
                s.src = '{JS_DATA_FILE}?t=' + new Date().getTime();
                s.onload = function() {{
                    if (window.LATEST_VESSELS) {{
                        updateVesselsOnMap(window.LATEST_VESSELS);
                    }}
                }};
                document.body.appendChild(s);
            }}

            pollVesselData();
            setInterval(pollVesselData, 5000);
        }});
    </script>
    """
    m.get_root().html.add_child(folium.Element(dynamic_vessels_js))
    m.save("epaper_preview.html")

# ---------------------------------------------------------
# Live AISStream WebSocket Loop
# ---------------------------------------------------------
async def live_ais_feed():
    url = "wss://stream.aisstream.io/v0/stream"
    print(f"Loaded {len(SUBSEA_ASSETS)} subsea assets.")
    
    # Load previous positions, write initial JS data file, and build map once
    load_vessel_cache()
    save_vessel_cache()
    generate_map()

    while True:
        try:
            print("Connecting to AISStream...")
            async with websockets.connect(url, compression="deflate", ping_interval=20, ping_timeout=20) as ws:
                subscribe_message = {
                    "APIKey": API_KEY,
                    "BoundingBoxes": [[[-90, -180], [90, 180]]],
                    "FiltersShipMMSI": list(vessels.keys()),
                    "FilterMessageTypes": ["PositionReport"]
                }
                
                await ws.send(json.dumps(subscribe_message))
                
                async for raw_data in ws:
                    if isinstance(raw_data, bytes):
                        raw_data = raw_data.decode('utf-8')
                        
                    message = json.loads(raw_data)
                    msg_type = message.get("MessageType")
                    
                    if msg_type == "SubscriptionConfirmation":
                        print("--> Live feed active! Listening for fleet updates...")
                        continue
                        
                    if msg_type == "PositionReport":
                        meta = message.get("MetaData", {})
                        pos = message.get("Message", {}).get("PositionReport", {})
                        
                        mmsi = str(meta.get("MMSI") or pos.get("UserID"))
                        lat = meta.get("latitude") or pos.get("Latitude")
                        lon = meta.get("longitude") or pos.get("Longitude")
                        sog = pos.get("Sog", 0.0)
                        cog = pos.get("Cog", 0.0)
                        
                        if mmsi in vessels and lat is not None and lon is not None:
                            now_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
                            
                            vessels[mmsi]["lat"] = lat
                            vessels[mmsi]["lon"] = lon
                            vessels[mmsi]["sog"] = round(sog, 1)
                            vessels[mmsi]["cog"] = round(cog, 1)
                            vessels[mmsi]["updated"] = now_str
                            
                            print(f"[{now_str}] Updated {vessels[mmsi]['name']} -> Lat: {lat:.4f}, Lon: {lon:.4f} ({sog} kn, {cog}°)")
                            save_vessel_cache()

        except Exception as e:
            print(f"Connection interrupted ({type(e).__name__}: {e}). Reconnecting in 10 seconds...")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(live_ais_feed())