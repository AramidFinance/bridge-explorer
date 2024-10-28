from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from datetime import datetime, timedelta
from config.addresses import BRIDGE_ADDRESSES
from config.settings import ALGORAND_INDEXER_URL, VOI_INDEXER_URL
from monitors.base_monitor import BaseMonitor
import base64
from typing import Dict, List

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

def organize_bridge_operations(algo_txns: list, voi_txns: list) -> list:
    """Organize transactions into bridge operations"""
    TIME_WINDOW = timedelta(minutes=30)
    bridge_ops = []

    # Sort all transactions by timestamp
    all_txns = sorted(algo_txns + voi_txns, key=lambda x: x['timestamp'])
    matched_txids = set()

    for tx in all_txns:
        if tx['txid'] in matched_txids:
            continue

        current_time = datetime.fromtimestamp(tx['timestamp'])
        
        # Look for matching transaction in opposite chain
        for potential_match in all_txns:
            if (potential_match['txid'] not in matched_txids and 
                tx['chain'] != potential_match['chain']):
                
                match_time = datetime.fromtimestamp(potential_match['timestamp'])
                time_diff = match_time - current_time

                if timedelta(0) <= time_diff <= TIME_WINDOW:
                    bridge_op = {
                        'source_tx': tx,
                        'dest_tx': potential_match,
                        'status': 'Complete',
                        'time_taken': {
                            'minutes': int(time_diff.total_seconds() // 60),
                            'seconds': int(time_diff.total_seconds() % 60)
                        }
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
                'time_taken': None
            }
            bridge_ops.append(bridge_op)
            matched_txids.add(tx['txid'])

    return sorted(bridge_ops, key=lambda x: x['source_tx']['timestamp'], reverse=True)

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
            "datetime": datetime
        }
    )
