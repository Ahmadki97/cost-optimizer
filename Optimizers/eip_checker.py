import aioboto3
from botocore.exceptions import ClientError
from utils.utils import get_instance_state, save_to_csv, get_aws_resource_price
from dotenv import load_dotenv
from fastapi import status
from fastapi.responses import JSONResponse
from logger import logger
import os 

load_dotenv('.env')


PROFILE_NAME = os.getenv('AWS_PROFILE')


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



async def list_unattached_eips(region: str) -> None:
    try:
        eip_data = []
        async with aioboto3.Session(profile_name=PROFILE_NAME).client('ec2', region_name=region) as ec2:
            addresses = (await ec2.describe_addresses()).get('Addresses', [])
            instances = await get_instance_state(ec2)
            nat_gateways = (await ec2.describe_nat_gateways()).get('NatGateways', [])
            nat_map = {
                gw_addr['AllocationId']: gw['NatGatewayId']
                for gw in nat_gateways
                for gw_addr in gw.get('NatGatewayAddresses', [])
                if 'AllocationId' in gw_addr
            }
            eip_hourly_price = 0.005 
            eip_monthly_price = round(eip_hourly_price * 720, 4)  # Assuming 720 hours in a month
            # Process each EIP
            for addr in addresses:
                allocation_id = addr.get('AllocationId', 'N/A')
                public_ip = addr.get('PublicIp', 'N/A')
                instance_id = addr.get('InstanceId', 'N/A')
                network_interface_id = addr.get('NetworkInterfaceId', 'N/A')
                domain = addr.get('Domain', 'N/A') # vpc or standard
                if allocation_id in nat_map:
                    # EIP is associated with a NAT Gateway
                    attachment_type = 'NAT Gateway'
                    attachment_id = nat_map[allocation_id]
                    state = 'Managed by AWS'
                elif instance_id != 'N/A':
                    attachment_type = 'EC2 Instance'
                    attachment_id = instance_id
                    state = next((inst['state'] for inst in instances if inst['id'] == instance_id), 'Unknown')
                elif network_interface_id != 'N/A':
                    # Standard EIP attached to a network interface (not directly to an instance)
                    attachment_type = 'Network Interface'
                    attachment_id = network_interface_id
                    state = 'N/A'
                else:
                    # Completly unattached EIP
                    attachment_type = 'Unattached'
                    attachment_id = 'N/A'
                    state = 'Available/Not attached'
                
                eip_data.append({
                    'PublicIp': public_ip,
                    'AllocationId': allocation_id,
                    'AttachmentType': attachment_type,
                    'AttachmentId': attachment_id,
                    'InstanceState': state,
                    'Domain': domain,
                    'IsIdle': attachment_type == 'Unattached',
                    'MonthlyCost($)': f"${eip_monthly_price}" if attachment_type == 'Unattached' else "$0.00"
                })
        await save_to_csv((eip_data), f"/mnt/BA82FDFB82FDBC47/Python_Devops/boto3/aws-cost-optimizer/reports/eip_report_{region}.csv")
        logger.info(f"eip_optimizer() Method: ✅ EIP report for region {region} generated.")
        return JSONResponse(content={"Message": f"EIP report for region {region} generated."}, status_code=status.HTTP_200_OK)
    except ClientError as err:
        logger.error(f"eip_optimizer() Method: ❌ Error fetching EIP data in region {region}: {err}")
        return JSONResponse(content={"Error": f"AWS ClientError: {err}"}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as err:
        logger.error(f"eip_optimizer() Method: ❌ Unexpected error: {err}")
        return JSONResponse(content={"Error": f"Unexpected error: {err}"}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)