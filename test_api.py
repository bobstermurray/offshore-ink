import asyncio
import websockets
import json
from datetime import datetime, timezone

API_KEY = "18b68f6810277aef82705d77fde940c9e5f3567b"

async def test_stream():
    url = "wss://stream.aisstream.io/v0/stream"
    print("Connecting to AISStream...")
    
    try:
        async with websockets.connect(url) as ws:
            subscribe_message = {
                "APIKey": API_KEY,
                "BoundingBoxes": [[[50.0, -2.0], [58.0, 4.0]]], # North Sea & Channel
                "FilterMessageTypes": ["PositionReport"]
            }
            
            await ws.send(json.dumps(subscribe_message))
            print("Subscription sent! Waiting for frames...\n")
            
            ships_received = 0
            while ships_received < 5:
                raw_data = await asyncio.wait_for(ws.recv(), timeout=20.0)
                
                if isinstance(raw_data, bytes):
                    raw_data = raw_data.decode('utf-8')
                    
                message = json.loads(raw_data)
                msg_type = message.get("MessageType")
                
                # 1. Catch the new initial confirmation frame
                if msg_type == "SubscriptionConfirmation":
                    comp = message.get("Message", {}).get("CompressionEnabled")
                    print(f"--> Connected! Server confirmed subscription (Compression: {comp})\n")
                    continue
                
                # 2. Process actual ship position reports
                if msg_type == "PositionReport":
                    meta = message.get("MetaData", {})
                    pos = message.get("Message", {}).get("PositionReport", {})
                    
                    ship_name = meta.get("ShipName", "Unknown").strip()
                    mmsi = meta.get("MMSI") or pos.get("UserID")
                    lat = meta.get("latitude") or pos.get("Latitude")
                    lon = meta.get("longitude") or pos.get("Longitude")
                    
                    if lat is not None and lon is not None:
                        print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] "
                              f"Vessel: {ship_name:20} (MMSI: {mmsi}) -> Lat: {lat:.4f}, Lon: {lon:.4f}")
                        ships_received += 1
                    else:
                        print(f"Received frame without coordinates: {message}")
                else:
                    print(f"Received {msg_type}: {message}")
                
            print("\nSUCCESS! The AISStream pipeline is officially alive and working.")

    except asyncio.TimeoutError:
        print("\nTIMEOUT: Connected, but no vessel reports arrived within 20 seconds.")
    except websockets.exceptions.ConnectionClosed as e:
        print(f"\nCONNECTION CLOSED BY SERVER: Code {e.code} - Reason: {e.reason}")
    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_stream())