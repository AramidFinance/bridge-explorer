from monitors.base_monitor import BaseMonitor

class VoiMonitor(BaseMonitor):
    def get_transactions(self, limit=50):
        # Override with VOI-specific API calls
        # Implement according to VOI indexer API specs
        pass

    def format_transaction(self, txn):
        # Override with VOI-specific transaction formatting
        # Implement according to VOI transaction format
        pass

