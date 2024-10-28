from datetime import datetime
from algosdk.v2client import indexer
import base64
import requests
from functools import lru_cache
from services.cache import CacheService

class BaseMonitor:
    def __init__(self, indexer_url, address, chain_name):
        self.indexer_url = indexer_url
        self.address = address
        self.chain_name = chain_name
        self.cache = CacheService()
        
    def get_transactions(self, limit=50):
        # Try to get from cache first
        cached_txns = self.cache.get_transactions(self.chain_name)
        if cached_txns and self.cache.is_cache_fresh(self.chain_name):
            print(f"Using cached {self.chain_name} transactions")
            return cached_txns

        # If not in cache, fetch from indexer
        print(f"Fetching {self.chain_name} transactions")
        try:
            response = requests.get(
                f"{self.indexer_url}/v2/transactions",
                params={
                    "address": self.address,
                    "limit": limit
                }
            )
            if response.status_code == 200:
                transactions = [
                    self.format_transaction(tx)
                    for tx in response.json().get("transactions", [])
                ]
                # Store in cache
                self.cache.set_transactions(self.chain_name, transactions)
                return transactions
            return []
        except Exception as e:
            print(f"Error fetching {self.chain_name} transactions: {str(e)}")
            return []

    @lru_cache(maxsize=100)
    def get_asset_info(self, asset_id):
        """Cache asset info to avoid repeated API calls"""
        try:
            response = requests.get(
                f"{self.indexer_url}/v2/assets/{asset_id}"
            )
            if response.status_code == 200:
                asset_info = response.json()['asset']
                decimals = asset_info.get('params', {}).get('decimals', 0)
                name = asset_info.get('params', {}).get('name', f'ASA #{asset_id}')
                unit_name = asset_info.get('params', {}).get('unit-name', '')
                return {
                    'decimals': decimals,
                    'name': name,
                    'unit_name': unit_name
                }
        except Exception as e:
            print(f"Error fetching asset info: {e}")
        return None

    def format_transaction(self, txn):
        amount = 0
        asset_id = None
        asset_name = None

        # Handle regular payment transactions (ALGO/VOI)
        if 'payment-transaction' in txn:
            amount = txn['payment-transaction']['amount'] / 1_000_000
            asset_name = 'ALGO' if self.chain_name == 'Algorand' else 'VOI'

        # Handle ASA transfers
        elif 'asset-transfer-transaction' in txn:
            asset_transfer = txn['asset-transfer-transaction']
            asset_id = asset_transfer['asset-id']
            
            asset_info = self.get_asset_info(asset_id)
            if asset_info:
                amount = asset_transfer['amount'] / (10 ** asset_info['decimals'])
                asset_name = asset_info['unit_name'] or asset_info['name']
            else:
                amount = asset_transfer['amount']
                asset_name = f'ASA #{asset_id}'

        # Check for failed transaction
        failed = False
        note = ''
        if 'note' in txn:
            try:
                note = base64.b64decode(txn['note']).decode('utf-8')
            except:
                note = ''
            
        # Add failed and note fields
        # Add debug print
        print(f"Raw transaction rounds: {txn.get('confirmed-round')}, {txn.get('last-valid')}")
        
        formatted_txn = {
            'txid': txn['id'],
            'timestamp': txn['round-time'],
            'datetime': datetime.fromtimestamp(txn['round-time']),
            'chain': self.chain_name,
            'amount': amount,
            'asset_id': asset_id,
            'asset_name': asset_name,
            'note': note,
            # Make sure we're getting these values correctly
            'confirmed-round': txn.get('confirmed-round'),
            'last-valid': txn.get('last-valid')
        }
        return formatted_txn
