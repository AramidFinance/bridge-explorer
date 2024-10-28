# Deployment Guide

## Local Development
1. Install Redis locally
2. Copy `.env.example` to `.env` and configure
3. Run `pip install -r requirements.txt`
4. Run `uvicorn main:app --reload`

## AWS Deployment
1. Create an ElastiCache Redis instance
2. Create an ECS cluster
3. Create a task definition using the Dockerfile
4. Set environment variables in task definition:
   - REDIS_URL
   - CACHE_TTL
   - ALGORAND_INDEXER_URL
   - VOI_INDEXER_URL
5. Deploy the task to ECS
