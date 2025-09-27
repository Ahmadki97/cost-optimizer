from fastapi import APIRouter
from logger import logger
from Models.pydantic_models import OptimizerRequest, EC2Request
from fastapi.responses import JSONResponse
from fastapi import status
from Optimizers.ec2_checker import find_idle_ec2_instances
from Optimizers.ebs_checker import list_unused_ebs
from Optimizers.eip_checker import list_unattached_eips




optimizer_router = APIRouter()


@optimizer_router.post("/ec2")
async def check_ec2_instances(request: EC2Request):
    try:
        region = request.region
        cpu_threshold = request.cpu_threshold
        response = await find_idle_ec2_instances(region, cpu_threshold)
        return response
    except Exception as err:
        logger.error(f"❌ Unexpected error in check_ec2_instance controller {err}")
        return JSONResponse(content={"Error": "Error in check_ec2_instance controller"}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)



@optimizer_router.post("/ebs")
async def check_ebs(request: OptimizerRequest):
    try:
        region = request.region
        response = await list_unused_ebs(region=region)
        return response
    except Exception as err:
        logger.error(f"❌ Unexpected error in check_ebs controller {err}")
        return JSONResponse(content={"Error": "Error in check_ebs controller"}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@optimizer_router.post("/eip")
async def check_eip(request: OptimizerRequest):
    try:
        region = request.region
        response = await list_unattached_eips(region=region)
        return response
    except Exception as err:
        logger.error(f"❌ Unexpected error in check_eip controller {err}")
        return JSONResponse(content={"Error": "Error in check_eip controller"}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

@optimizer_router.post("/refresh")
async def refresh_reports(request: EC2Request):
    try:
        region = request.region
        cpu_threshold = request.cpu_threshold
        await list_unattached_eips(region=region)
        await list_unused_ebs(region=region)
        await find_idle_ec2_instances(region=region, cpu_threshold=cpu_threshold) 
        logger.info("refresh_reports controller: ✅ All reports refreshed successfully")
        return JSONResponse(content={"Message": "All reports refreshed successfully"}, status_code=status.HTTP_200_OK)
    except Exception as err:
        logger.error(f"❌ Unexpected error in refresh_reports controller {err}")
        return JSONResponse(content={"Error": "Error in refresh_reports controller"}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)