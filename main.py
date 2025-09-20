import boto3
from optimizer.ec2_checker import find_idle_ec2_instances
from optimizer.eip_checker import listEIPs
import asyncio

session = boto3.Session(profile_name="devops-personal")  





if __name__ == "__main__":
    asyncio.run(listEIPs("us-east-1"))