from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from datetime import datetime, timedelta, timezone
from config.addresses import BRIDGE_ADDRESSES
from config.settings import ALGORAND_INDEXER_URL, VOI_INDEXER_URL, ARAMID_INDEXER_URL
from monitors.base_monitor import BaseMonitor
from monitors.aramid_monitor import AramidMonitor
import base64
from typing import Dict, List
import json

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Define explorer URLs
EXPLORERS = {
    "algorand": "https://explorer.perawallet.app/tx/",  # Changed to Pera Wallet explorer
    "voi": "https://explorer.voi.network/explorer/transaction/",
    "aramid": None  # We'll handle this case in the template
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

aramid_monitor = AramidMonitor(
    ARAMID_INDEXER_URL,
    BRIDGE_ADDRESSES["aramid"]["main"],
    "Aramid"
)

def decode_note(note: str) -> str:
    """Decode base64 note field"""
    try:
        return base64.b64decode(note).decode('utf-8')
    except:
        return ""

# Set a fixed timezone (UTC)
DEFAULT_TIMEZONE = timezone.utc

def format_timestamp(timestamp: str) -> str:
    """Format the timestamp in UTC"""
    try:
        dt = datetime.fromisoformat(timestamp)
        return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
    except Exception as e:
        print(f"Error formatting timestamp: {e}")
        return "Invalid timestamp"

def organize_bridge_operations(algo_txns: list, voi_txns: list, aramid_txns: list) -> list:
    """
    Chain A -> Aramid Chain (consensus) -> Chain B
    """
    TIME_WINDOW = timedelta(minutes=30)
    bridge_ops = []
    matched_txids = set()
    matched_txids_resp = []
    matching_txs= []

    # Sort all transactions by timestamp
    all_txns = sorted(algo_txns + voi_txns, key=lambda x: datetime.fromisoformat(x['timestamp']))

    # Process each transaction
    for tx in all_txns:
        if tx['note'].startswith("aramid-confirm/v1:j"):
            bridgedResponse = json.loads(tx['note'].removeprefix("aramid-confirm/v1:j"))
            matched_txids_resp[bridgedResponse['sourceTxId']] = bridgedResponse
            matching_txs[bridgedResponse['sourceTxId']] = tx

        if not tx['note'].startswith("aramid-transfer/v1:j"):
            continue  # Skip to the next item in the loop
        trimmed_note = tx['note'].removeprefix("aramid-transfer/v1:j")

        bridgeOrder = json.loads(trimmed_note)

        tx_time = datetime.fromisoformat(tx['timestamp'])
        
        # Look for matching transaction in the other chain
        matching_tx = None
        aramid_tx = None

        # # Find matching transaction within time window
        # for other_tx in all_txns:
        #     if other_tx['txid'] in matched_txids:
        #         continue
        #     if other_tx['chain'] == tx['chain']:  # Must be from different chain
        #         continue
                
        #     other_time = datetime.fromisoformat(other_tx['timestamp'])
        #     time_diff = abs(other_time - tx_time)
            
        #     if time_diff <= TIME_WINDOW:
        #         matching_tx = other_tx
        #         matched_txids.add(other_tx['txid'])
                
        #         # Look for corresponding Aramid transaction
        #         for a_tx in aramid_txns:
        #             a_time = datetime.fromisoformat(a_tx['timestamp'])
        #             if min(tx_time, other_time) <= a_time <= max(tx_time, other_time):
        #                 aramid_tx = a_tx
        #                 break
        #         break
        matching_tx = matching_txs[tx['txid']]
        if matching_tx:
            # Determine source and destination based on timestamp
            if tx_time < datetime.fromisoformat(matching_tx['timestamp']):
                source_tx = tx
                dest_tx = matching_tx
            else:
                source_tx = matching_tx
                dest_tx = tx

            bridge_ops.append({
                "bridge_order": bridgeOrder,
                "bridged_info": matched_txids_resp[tx['txid']],
                'source_tx': source_tx,
                'bridged_tx': matching_tx,
                'note': tx['note'],
                'dest_tx': dest_tx,
                'aramid_tx': aramid_tx,
                'status': 'Complete',
                'time_taken': {
                    'minutes': int(abs((datetime.fromisoformat(dest_tx['timestamp']) - 
                                     datetime.fromisoformat(source_tx['timestamp'])).total_seconds()) // 60),
                    'seconds': int(abs((datetime.fromisoformat(dest_tx['timestamp']) - 
                                     datetime.fromisoformat(source_tx['timestamp'])).total_seconds()) % 60)
                },
                'formatted_time': format_timestamp(source_tx['timestamp'])
            })
        else:
            bridge_ops.append({
                "bridge_order": bridgeOrder,
                "bridged_info": None,
                'source_tx': tx,
                'bridged_tx': None,
                'note': tx['note'],
                'dest_tx': None,
                'aramid_tx': None,
                'status': 'Pending',
                'time_taken': None,
                'formatted_time': format_timestamp(tx['timestamp'])
            })

    return sorted(bridge_ops, key=lambda x: datetime.fromisoformat(x['source_tx']['timestamp']), reverse=True)

@app.get("/", response_class=HTMLResponse)
async def get_transactions(
    request: Request,
    page: int = Query(1, ge=1),
    size: int = Query(30, ge=1, le=1000)
):
    algo_txns = algo_monitor.get_transactions(limit=1000)
    voi_txns = voi_monitor.get_transactions(limit=1000)
    aramid_txns = aramid_monitor.get_transactions(limit=1000)
    
    bridge_ops = organize_bridge_operations(algo_txns, voi_txns, aramid_txns)
    
    # Manual pagination
    start_idx = (page - 1) * size
    end_idx = start_idx + size
    paginated_ops = bridge_ops[start_idx:end_idx]
    total = len(bridge_ops)
    total_pages = (total + size - 1) // size
    
    template_context = {
        "request": request,
        "bridge_ops": paginated_ops,
        "explorers": EXPLORERS,
        "get_relative_time": get_relative_time,
        "pagination": {
            "current_page": page,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
            "next_page": page + 1 if page < total_pages else None,
            "prev_page": page - 1 if page > 1 else None,
            "get_fee_from_note": get_fee_from_note
        }
    }
    
    return templates.TemplateResponse("transactions.html", template_context)

def get_relative_time(timestamp):
    """Convert timestamp to relative time (e.g., '2 minutes ago')"""
    try:
        # Ensure timestamp is in UTC
        if isinstance(timestamp, str):
            dt = datetime.fromisoformat(timestamp)
        else:
            dt = timestamp
            
        now = datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
            
        delta = now - dt
        
        if delta.days > 0:
            return f"{delta.days}d ago"
        elif delta.seconds >= 3600:
            hours = delta.seconds // 3600
            return f"{hours}h ago"
        elif delta.seconds >= 60:
            minutes = delta.seconds // 60
            return f"{minutes}m ago"
        else:
            return f"{delta.seconds}s ago"
    except Exception as e:
        print(f"Error calculating relative time: {e}")
        return "unknown time ago"

# Register the function as a template global
def get_fee_from_note(note):
    """Extract fee amount from transaction note"""
    try:
        if note and note.startswith('aramid-transfer/v1:j'):
            json_str = note.split('aramid-transfer/v1:j', 1)[1]
            data = json.loads(json_str)
            fee_amount = data.get('feeAmount', 0)
            return "{:.6f}".format(fee_amount / 1000000)
    except Exception as e:
        print(f"Error parsing fee from note: {e}")
        return "0.000000"

# Add the function to Jinja2 environment
templates.env.globals["get_fee_from_note"] = get_fee_from_note

def get_transaction_details(note):
    """Parse transaction note for detailed information"""
    try:
        if note.startswith('aramid-transfer/v1:j'):
            json_str = note.split('aramid-transfer/v1:j', 1)[1]
            data = json.loads(json_str)
            return {
                'source_amount': data.get('sourceAmount', 0),
                'destination_amount': data.get('destinationAmount', 0),
                'fee_amount': data.get('feeAmount', 0),
                'destination_network': data.get('destinationNetwork'),
                'destination_address': data.get('destinationAddress'),
                'destination_token': data.get('destinationToken')
            }
    except Exception as e:
        print(f"Error parsing transaction note: {e}")
        return None
