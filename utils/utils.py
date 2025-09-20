import csv
import aiofiles
import aioboto3
from io import StringIO
from botocore.exceptions import ClientError
from mypy_boto3_ec2.client import EC2Client
from pathlib import Path




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


async def save_to_csv(data: list[dict], fil_path: str):
    if not data:
        print("No data to save.")
        return
    path = Path(fil_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    buffer = StringIO() # In-memory text stream
    writer = csv.DictWriter(buffer, fieldnames=data[0].keys()) # Use keys from the first dict as headers
    writer.writeheader()
    writer.writerows(data)
    async with aiofiles.open(path, mode='w') as f:
        await f.write(buffer.getvalue())
    print(f"✅ Async report saved to {path}")