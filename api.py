from fastapi import FastAPI, Request, Query, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from datetime import datetime, timedelta
from config.addresses import BRIDGE_ADDRESSES
from config.settings import ALGORAND_INDEXER_URL, VOI_INDEXER_URL
from monitors.base_monitor import BaseMonitor
import base64
from typing import Dict, List
import pytz

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Define explorer URLs
EXPLORERS = {
    "algorand": "https://explorer.perawallet.app/tx/",  # Changed to Pera Wallet explorer
    "voi": "https://explorer.voi.network/explorer/transaction/"
}

algo_monitor = BaseMonitor(
    ALGORAND_INDEXER_URL,
    BRIDGE_ADDRESSES["algorand"]["main"],
    "Algorand"
)

voi_monitor = BaseMonitor(
    VOI_INDEXER_URL,
    BRIDGE_ADDRESSES["voi"]["main"],
    "VOI"
)

def decode_note(note: str) -> str:
    """Decode base64 note field"""
    try:
        return base64.b64decode(note).decode('utf-8')
    except:
        return ""

# Set your default timezone
DEFAULT_TIMEZONE = pytz.timezone('UTC')  # Change 'UTC' to your desired timezone

@app.post("/set-timezone")
async def set_timezone(timezone: str = Form(...)):
    global DEFAULT_TIMEZONE
    try:
        DEFAULT_TIMEZONE = pytz.timezone(timezone)
        return JSONResponse(content={"message": "Timezone updated"}, status_code=200)
    except pytz.UnknownTimeZoneError:
        return JSONResponse(content={"message": "Invalid timezone"}, status_code=400)

def format_timestamp(timestamp: str, timezone: pytz.timezone) -> str:
    """Format the timestamp to the specified timezone"""
    try:
        dt = datetime.fromisoformat(timestamp).astimezone(timezone)
        return dt.strftime('%Y-%m-%d %H:%M:%S %Z')
    except Exception as e:
        print(f"Error formatting timestamp: {e}")
        return "Invalid timestamp"

def organize_bridge_operations(algo_txns: list, voi_txns: list) -> list:
    """Organize transactions into bridge operations"""
    TIME_WINDOW = timedelta(minutes=30)
    bridge_ops = []

    # Sort all transactions by timestamp
    all_txns = sorted(algo_txns + voi_txns, key=lambda x: datetime.fromisoformat(x['timestamp']).astimezone(DEFAULT_TIMEZONE))
    matched_txids = set()

    for tx in all_txns:
        try:
            current_time = datetime.fromisoformat(tx['timestamp']).astimezone(DEFAULT_TIMEZONE)
        except (KeyError, TypeError, ValueError) as e:
            current_time = None
            print(f"Error processing timestamp: {e}")
        
        # Look for matching transaction in opposite chain
        for potential_match in all_txns:
            if (potential_match['txid'] not in matched_txids and 
                tx['chain'] != potential_match['chain']):
                
                match_time = datetime.fromisoformat(potential_match['timestamp']).astimezone(DEFAULT_TIMEZONE)
                time_diff = match_time - current_time

                if timedelta(0) <= time_diff <= TIME_WINDOW:
                    bridge_op = {
                        'source_tx': tx,
                        'dest_tx': potential_match,
                        'status': 'Complete',
                        'time_taken': {
                            'minutes': int(time_diff.total_seconds() // 60),
                            'seconds': int(time_diff.total_seconds() % 60)
                        },
                        'formatted_time': format_timestamp(tx['timestamp'], DEFAULT_TIMEZONE)
                    }
                    bridge_ops.append(bridge_op)
                    matched_txids.add(tx['txid'])
                    matched_txids.add(potential_match['txid'])
                    break
        
        # If no match found
        if tx['txid'] not in matched_txids:
            bridge_op = {
                'source_tx': tx,
                'dest_tx': None,
                'status': 'Pending',
                'time_taken': None,
                'formatted_time': format_timestamp(tx['timestamp'], DEFAULT_TIMEZONE)
            }
            bridge_ops.append(bridge_op)
            matched_txids.add(tx['txid'])

    return sorted(bridge_ops, key=lambda x: datetime.fromisoformat(x['source_tx']['timestamp']).astimezone(DEFAULT_TIMEZONE), reverse=True)

@app.get("/", response_class=HTMLResponse)
async def get_transactions(request: Request):
    algo_txns = algo_monitor.get_transactions(limit=50)
    voi_txns = voi_monitor.get_transactions(limit=50)
    
    bridge_ops = organize_bridge_operations(algo_txns, voi_txns)
    
    return templates.TemplateResponse(
        "transactions.html", 
        {
            "request": request, 
            "bridge_ops": bridge_ops,
            "explorers": EXPLORERS,
            "datetime": datetime,
            "default_timezone": DEFAULT_TIMEZONE.zone  # Pass the timezone name
        }
    )
