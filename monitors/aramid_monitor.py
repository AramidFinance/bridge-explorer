from monitors.base_monitor import BaseMonitor
import requests

class AramidMonitor(BaseMonitor):
    def __init__(self, indexer_url, address, chain_name):
        super().__init__(indexer_url, address, chain_name)

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

    def format_transaction(self, txn):
        # Use the base monitor's format_transaction as it should handle
        # the same transaction format (Algorand-based chain)
        return super().format_transaction(txn)
