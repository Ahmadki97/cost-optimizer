import boto3
import json
import os 
from datetime import datetime, timedelta
from dotenv import load_dotenv


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
session = boto3.Session(profile_name=PROFILE_NAME)


def find_idle_ec2_instances(region, cpu_threshold=5):
    print(f"Checking instances in region {region} with CPU threshold less than {cpu_threshold}%")
    ec2 = session.client('ec2', region_name=region)
    cw = session.client('cloudwatch', region_name=region)
    pricing = session.client('pricing', region_name=region)
    # get all running EC2 instances
    response = ec2.describe_instances(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
    idle_instances = []
    for reserv in response['Reservations']:
        for instance in reserv['Instances']:
            instance_id = instance['InstanceId']
            # get CPU utilization for the last day
            metrics = cw.get_metric_statistics(
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
                hourly_cost = None
                monthly_savings = None
                try:
                    region_name = REGION_NAME_MAP.get(region)
                    price_resp = pricing.get_products(
                        ServiceCode='AmazonEC2',
                        Filters=[
                            {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance['InstanceType']},
                            {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': region_name},
                            {'Type': 'TERM_MATCH', 'Field': 'operatingSystem', 'Value': os_filter},
                            {'Type': 'TERM_MATCH', 'Field': 'preInstalledSw', 'Value': 'NA'},
                            {'Type': 'TERM_MATCH', 'Field': 'tenancy', 'Value': 'Shared'},
                            {'Type': 'TERM_MATCH', 'Field': 'capacitystatus', 'Value': 'Used'}
                        ],
                        MaxResults=1
                    )
                    if price_resp['PriceList']:
                        price_item = json.loads(price_resp['PriceList'][0])
                        terms = price_item.get('terms', {}).get('OnDemand', {})
                        term_key = list(terms.keys())[0]
                        price_dimensions = terms[term_key]['priceDimensions']
                        dimension_key = list(price_dimensions.keys())[0]
                        hourly_cost = float(price_dimensions[dimension_key]['pricePerUnit']['USD'])
                        monthly_savings = hourly_cost * 24 * 30  # Approximate monthly savings
                except Exception as e:
                    print(f"Error fetching pricing for {instance_id}: {e}")
                idle_instances.append({
                    'id': instance_id,
                    'average_cpu': avg_cpu,
                    'region': region,
                    'hourly_cost': hourly_cost,
                    'monthly_savings': f"{monthly_savings}$",
                    'instance_type': instance['InstanceType'],
                    'os': os_type
                })
    return idle_instances