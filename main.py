import boto3
from optimizer.ec2_checker import find_idle_ec2_instances
from optimizer.eip_checker import list_unattached_eips
from optimizer.ebs_checker import list_unused_ebs
import asyncio

session = boto3.Session(profile_name="devops-personal")  





if __name__ == "__main__":
    asyncio.run(find_idle_ec2_instances(region="us-east-1", cpu_threshold=5))