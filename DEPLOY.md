# Deployment Guide

## Local Development
1. Install Redis locally
2. Copy `.env.example` to `.env` and configure
3. Run `pip3 install -r requirements.txt`
4. Run `python3 -m uvicorn main:app --reload`

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

## Setting Up Redis on AWS
Create an ElastiCache Redis Instance:
Go to the AWS Management Console.
Navigate to ElastiCache.
Choose "Create" and select "Redis".
Configure the instance settings (e.g., node type, number of replicas).
Security Groups:
Ensure the security group allows inbound traffic from your ECS cluster.
Integrating with Your Application
Environment Variables:
Set REDIS_URL in your ECS task definition using the endpoint provided by ElastiCache.
Connecting from Your Application:
Ensure your application code uses REDIS_URL to connect to Redis.
Deploying Your Application
Create an ECS Cluster:
Go to the ECS section in the AWS Management Console.
Create a new cluster.
Task Definition:
Define a task using your Dockerfile.
Set the necessary environment variables (REDIS_URL, etc.).
Deploy the Task:
Run the task on your ECS cluster.
