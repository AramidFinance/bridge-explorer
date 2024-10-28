import os
from dotenv import load_dotenv

load_dotenv()

# Redis settings
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
CACHE_TTL = int(os.getenv('CACHE_TTL', 300))  # 5 minutes

# Chain settings
ALGORAND_INDEXER_URL = os.getenv('ALGORAND_INDEXER_URL', 'https://mainnet-idx.algonode.cloud')
VOI_INDEXER_URL = os.getenv('VOI_INDEXER_URL', 'https://mainnet-idx.voi.nodely.dev')

# VOI endpoints - updated to use the correct mainnet indexer
VOI_NODE_URL = "https://mainnet-api.voi.nodely.dev"
