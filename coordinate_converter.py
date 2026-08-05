import csv
from pyproj import Transformer

def convert_for_google_maps(input_file="assets.csv", output_file="assets (wgs84).csv"):
    transformers = {}
    results = []

    try:
        # 1. Read the existing assets database
        with open(input_file, mode='r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                epsg = row["EPSG"].strip()
                easting = float(row["Easting"])
                northing = float(row["Northing"])
                
                # 2. Convert to WGS84 (Decimal Degrees)
                if epsg == "EPSG:4326":
                    # It's already WGS84. From our clean CSV: Easting = Longitude, Northing = Latitude
                    lat = northing
                    lon = easting
                else:
                    if epsg not in transformers:
                        transformers[epsg] = Transformer.from_crs(epsg, "EPSG:4326", always_xy=True)
                    
                    lon, lat = transformers[epsg].transform(easting, northing)
                
                # 3. Store the result, rounding to 6 decimal places for Google Maps
                results.append({
                    "Field": row["Field"],
                    "Asset": row["Asset"],
                    "Latitude": round(lat, 6),
                    "Longitude": round(lon, 6)
                })
                
    except FileNotFoundError:
        print(f"Error: Could not find {input_file}. Make sure you are in the right folder.")
        return

    # 4. Write the results to a brand new CSV file
    with open(output_file, mode='w', newline='', encoding='utf-8') as outfile:
        fieldnames = ["Field", "Asset", "Latitude", "Longitude"]
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        
        writer.writeheader()
        writer.writerows(results)
        
    print(f"Success! Converted {len(results)} assets and saved them to '{output_file}'.")

if __name__ == "__main__":
    convert_for_google_maps()