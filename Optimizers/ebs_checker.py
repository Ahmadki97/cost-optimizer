import aioboto3
from botocore.exceptions import ClientError
from utils.utils import save_to_csv, get_aws_resource_price
from dotenv import load_dotenv
from fastapi import status
from fastapi.responses import JSONResponse
from logger import logger
import asyncio
import datetime
import os 

load_dotenv('.env')
PROFILE = os.getenv('AWS_PROFILE')


EBS_PRICING_TYPE_MAP = {
    "gp2": "General Purpose",
    "gp3": "General Purpose (gp3)",
    "io1": "Provisioned IOPS",
    "io2": "Provisioned IOPS io2",
    "st1": "Throughput Optimized HDD",
    "sc1": "Cold HDD",
    "standard": "Magnetic"
}



async def list_unused_ebs(region: str) -> bool:
    try:
        logger.info(f"############ Executing unused EBS checker at time {datetime.datetime.now()} ############")
        report = []
        async with aioboto3.Session(profile_name=PROFILE).client('ec2', region_name=region) as ec2:
            paginator = ec2.get_paginator('describe_volumes')
            async for page in paginator.paginate():
                for vol in page.get('Volumes', []):
                    if not vol.get('Attachments'):
                        vol_id = vol['VolumeId']
                        size = vol['Size']
                        vol_type = vol['VolumeType']
                        price = await asyncio.to_thread(get_aws_resource_price,
                            service_code='AmazonEC2',
                            filters = [
                                {"Field": "productFamily", "Value": "Storage"},
                                {"Field": "volumeType", "Value": EBS_PRICING_TYPE_MAP.get(vol_type, vol_type)},
                                {"Field": "volumeApiName", "Value": vol_type},
                            ],
                            region = region
                        )
                        logger.info(f"Volume price is {price}")
                        monthly_cost = round(price * size , 4)
                        report.append({
                            'VolumeId': vol_id,
                            'Size(GB)': size,
                            'VolumeType': vol_type,
                            'Region': region,
                            'MonthlyCost($)': f"${monthly_cost}"
                        })
                        await save_to_csv(data=report, fil_path=f"/mnt/BA82FDFB82FDBC47/Python_Devops/boto3/aws-cost-optimizer/reports/unused_ebs_{region}.csv")
        logger.info(f"✅ Unused EBS report generated and saved to reports/unused_ebs.csv")
        return JSONResponse(content={"Message": f"Unused EBS report for region {region} generated."}, status_code=status.HTTP_200_OK)
    except ClientError as err:
        logger.error(f"❌ AWS ClientError: {err}")
        return JSONResponse(content={"Error": f"AWS ClientError: {err}"}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as err:
        logger.error(f"❌ Unexpected error: {err}")
        return JSONResponse(content={"Error": f"Unexpected error: {err}"}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)