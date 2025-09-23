import boto3
client = boto3.Session(profile_name='devops-personal').client("pricing", region_name="us-east-1")
response = client.get_products(ServiceCode="AmazonEC2", MaxResults=100)
print(response['PriceList'][0])