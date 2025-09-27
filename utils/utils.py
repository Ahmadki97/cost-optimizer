import csv
import aiofiles
import json
import boto3
import datetime
import pandas as pd
from io import StringIO
from logger import logger
from botocore.exceptions import ClientError
from botocore.config import Config
from mypy_boto3_ec2.client import EC2Client
from pathlib import Path


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


REPORTS_DIR = Path('reports')




async def get_report_summary():
    try:
        summary = {
            "ec2": 0,
            "eip": 0,
            "ebs": 0
        }
        if (REPORTS_DIR / "idle_ec2_report.csv").exists():
            df = pd.read_csv(REPORTS_DIR / "idle_ec2_report.csv")
            summary['ec2'] = len(df)
        if (REPORTS_DIR / "eip_report.csv").exists():
            df = pd.read_csv(REPORTS_DIR / "eip_report.csv")
            summary['eip'] = len(df)
        if (REPORTS_DIR / "unused_ebs.csv").exists():
            df = pd.read_csv(REPORTS_DIR / "unused_ebs.csv")
            summary['ebs'] = len(df)
        return summary
    except Exception as err:
        logger.error(f"❌ Unexpected error in get_report_summary() Method: {err}")
        raise


async def get_instance_state(ec2: EC2Client) -> list[dict]:
    try:
        paginator = ec2.get_paginator('describe_instances')
        result = []
        async for page in paginator.paginate():
            for reserv in page['Reservations']:
                for instance in reserv['Instances']:
                    result.append({
                        'id': instance['InstanceId'],
                        'state': instance['State']['Name'],
                        'type': instance['InstanceType'],
                        'region': ec2.meta.region_name
                    })
        return result
    except ClientError as err:
        print(f"❌ AWS ClientError: {err}")
        raise 

    except Exception as err:
        print(f"❌ Unexpected error: {err}")
        raise 



def get_aws_resource_price(service_code: str, filters: list, region: str) -> float:
    try:
        client = boto3.client('pricing', region_name='us-east-1', config=Config(retries={'max_attempts': 10, 'mode': 'standard'}))
        location = REGION_NAME_MAP.get(region, region)
        pricing_filters = [{'Type': 'TERM_MATCH', 'Field': 'location', 'Value': location}]
        for f in filters:
            pricing_filters.append({'Type': 'TERM_MATCH', 'Field': f['Field'], 'Value': f['Value']})
        resp = client.get_products(ServiceCode=service_code, Filters=pricing_filters, MaxResults=1)
        if not resp['PriceList']:
            logger.info(f"❌ No pricing data found for {service_code} in {region} with filters {filters}")
            raise ValueError(f"No pricing data found for service {service_code} in {region} with filters {filters}")
        price_item = json.loads(resp['PriceList'][0])
        terms = price_item['terms']['OnDemand']
        price_dimensions = next(iter(next(iter(terms.values()))['priceDimensions'].values()))
        return float(price_dimensions['pricePerUnit']['USD'])
    except ClientError as err:
        logger.error(f"Error in utils.get_aws_resource_price() Method: ❌ AWS ClientError: {err}")
        raise
    except Exception as err:
        logger.error(f"❌ Unexpected error: {err}")
        raise
        



async def save_to_csv(data: list[dict], fil_path: str):
    if not data:
        logger.info("utils.save_to_csv() Method: No data to save.")
        return
    path = Path(fil_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    buffer = StringIO() # In-memory text stream
    writer = csv.DictWriter(buffer, fieldnames=data[0].keys()) # Use keys from the first dict as headers
    writer.writeheader()
    writer.writerows(data)
    async with aiofiles.open(path, mode='w') as f:
        await f.write(buffer.getvalue())
    logger.info(f"utils.save_to_csv() Method: ✅ Async report saved to {path}")





async def gat_daily_cost(region: str):
    try:
        client = boto3.client('ce', region_name='us-east-1')
        end_date = datetime.datetime.utcnow().date()
        start_date = end_date - datetime.timedelta(days=7)
        response = client.get_cost_and_usage(
            TimePeriod={
                "start": start_date.strftime('%Y-%m-%d'),
                "end": end_date.strftime('%Y-%m-%d')
            },
            Granularity='DAILY',
            Metrics=['UnblendedCost'],
        )
        data = [
            {
                "date": item['TimePeriod']['Start'],
                "amount": float(item['Total']['UnblendedCost']['Amount']),
                "region": region,
                "currency": item['Total']['UnblendedCost']['Unit']
            }
            for item in response['ResultsByTime']
        ]
        logger.info(f"utils.gat_daily_cost() Method: ✅ Daily cost data fetched for region {region}")
        return data
    except Exception as err:
        logger.error(f"❌ Unexpected error in gat_daily_cost() Method: {err}")
        raise