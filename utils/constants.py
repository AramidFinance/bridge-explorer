# API endpoints
ALGORAND_INDEXER_URL = "https://mainnet-idx.algonode.cloud"
VOI_INDEXER_URL = "https://explorer.voi.network/api/v1"  # Updated VOI indexer URL

# Polling intervals (in seconds)
POLL_INTERVAL = 5

# Explorer URLs
EXPLORERS = {
    "algorand": "https://algoexplorer.io/tx/",
    "voi": "https://explorer.voi.network/explorer/transaction/"  # Updated VOI explorer URL
}

# Transaction types
TXN_TYPE_PAYMENT = "payment"
TXN_TYPE_APP_CALL = "appl"
TXN_TYPE_ASSET_TRANSFER = "axfer"
