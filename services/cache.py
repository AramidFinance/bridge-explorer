import redis
import json
from datetime import datetime, timedelta
from config.settings import REDIS_URL, CACHE_TTL

class CacheService:
    def __init__(self):
        self.redis = redis.from_url(REDIS_URL)
        self.ttl = CACHE_TTL

    def get_transactions(self, chain_name):
        """Get transactions from cache for given chain"""
        key = f"{chain_name.lower()}_transactions"
        data = self.redis.get(key)
        if data:
            return json.loads(data)
        return None

    def set_transactions(self, chain_name, transactions):
        """Store transactions in cache for given chain"""
        key = f"{chain_name.lower()}_transactions"
        
        # Convert datetime objects to strings
        for txn in transactions:
            if 'datetime' in txn and isinstance(txn['datetime'], datetime):
                txn['datetime'] = txn['datetime'].isoformat()
        
        self.redis.setex(
            key,
            self.ttl,
            json.dumps(transactions)
        )

    def is_cache_fresh(self, chain_name):
        """Check if cache is still fresh"""
        key = f"{chain_name.lower()}_transactions"
        ttl = self.redis.ttl(key)
        return ttl > 0

    def clear_cache(self, chain_name=None):
        """Clear cache for specific chain or all chains"""
        if chain_name:
            key = f"{chain_name.lower()}_transactions"
            self.redis.delete(key)
        else:
            # Clear all cached transactions
            for key in self.redis.keys("*_transactions"):
                self.redis.delete(key)
