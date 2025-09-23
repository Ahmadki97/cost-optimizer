import aioboto3
import os 
import asyncio
from botocore.exceptions import ClientError
from logger import logger
from datetime import datetime, timedelta
from dotenv import load_dotenv
from utils.utils import get_aws_resource_price, save_to_csv


load_dotenv('.env')

REGION_NAME_MAP = {
    "us-east-1": "US East (N. Virginia)",
    "us-east-2": "US East (Ohio)",
    "us-west-1": "US West (N. California)",
    "us-west-2": "US West (Oregon)",
    "ap-south-1": "Asia Pacific (Mumbai)",
    "ap-northeast-1": "Asia Pacific (Tokyo)",
    "eu-central-1": "EU (Frankfurt)",
    "eu-west-1": "EU (Ireland)",
    # Add more if needed
}


os_map = {
    "Linux/UNIX": "Linux",
    "Red Hat Enterprise Linux": "RHEL",
    "SUSE Linux": "SUSE",
    "Windows": "Windows"
}

PROFILE_NAME = os.getenv('AWS_PROFILE')
session = aioboto3.Session(profile_name=PROFILE_NAME)


async def find_idle_ec2_instances(region, cpu_threshold=5):
    try:
        logger.info(f"######## Checking instances in region {region} with CPU threshold less than {cpu_threshold}% ########")
        async with session.client('ec2', region_name=region) as ec2:   # ✅
            async with session.client('cloudwatch', region_name=region) as cw:  # ✅
        
            # get all running EC2 instances
                response = await ec2.describe_instances(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
                idle_instances = []
                for reserv in response['Reservations']:
                    for instance in reserv['Instances']:
                        instance_id = instance['InstanceId']
                        # get CPU utilization for the last day
                        metrics = await cw.get_metric_statistics(
                            Namespace='AWS/EC2',
                            MetricName='CPUUtilization',
                            Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                            StartTime=datetime.utcnow() - timedelta(hours=24),
                            EndTime=datetime.utcnow(),
                            Period=3600,  # 1-hour intervals
                            Statistics=['Average']
                        )
                        os_type = instance.get('PlatformDetails', 'Linux/UNIX')
                        os_filter = os_map.get(os_type, "Linux")
                        datapoints = metrics.get('Datapoints', [])
                        if not datapoints:
                            # No data -> might be idle or new instance
                            idle_instances.append({
                                'id': instance_id,
                                'reason': 'No CPU data available'
                            })
                            continue
                        avg_cpu = sum(d['Average'] for d in datapoints) / len(datapoints)
                        if avg_cpu < cpu_threshold:
                            hourly_cost = await asyncio.to_thread(
                                get_aws_resource_price,
                                service_code='AmazonEC2',
                                filters=[
                                    {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance['InstanceType']},
                                    {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': REGION_NAME_MAP.get(region, region)},
                                    {'Type': 'TERM_MATCH', 'Field': 'operatingSystem', 'Value': os_filter},
                                    {'Type': 'TERM_MATCH', 'Field': 'preInstalledSw', 'Value': 'NA'},
                                    {'Type': 'TERM_MATCH', 'Field': 'tenancy', 'Value': 'Shared'},
                                    {'Type': 'TERM_MATCH', 'Field': 'capacitystatus', 'Value': 'Used'}
                                ],
                                region=region
                            )
                            monthly_savings = hourly_cost * 24 * 30  # Approximate monthly savings
                            idle_instances.append({
                                'id': instance_id,
                                'average_cpu': avg_cpu,
                                'region': region,
                                'hourly_cost': hourly_cost,
                                'monthly_savings': f"{monthly_savings}$",
                                'instance_type': instance['InstanceType'],
                                'os': os_type
                            })
                await save_to_csv(idle_instances, f"/mnt/BA82FDFB82FDBC47/Python_Devops/boto3/aws-cost-optimizer/reports/idle_ec2_report.csv")
                logger.info(f"find_idle_ec2_instances() Method: ✅ Idle EC2 report for region {region} generated.")
    except ClientError as err:
        logger.error(f"Error in find_idle_ec2_instances() Method: ❌ AWS ClientError: {err}")
    except Exception as err:
        logger.error(f"Error in find_idle_ec2_instances() Method: ❌ Unexpected error: {err}")  