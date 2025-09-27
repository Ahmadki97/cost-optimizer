from utils.utils import get_report_summary, gat_daily_cost
from Models.pydantic_models import OptimizerRequest
from fastapi import status, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi import APIRouter
from dotenv import load_dotenv
from logger import logger
from pathlib import Path
import pandas as pd 
import os



load_dotenv('.env')
PROFILE = os.getenv('AWS_PROFILE', 'default')
get_router = APIRouter()
REPORTS_DIR = Path('reports')
templates = Jinja2Templates(directory="templates")


@get_router.get("/")
async def root(request: Request):
    try:
        summary = await get_report_summary()
        reports = [f.name for f in REPORTS_DIR.glob("*.csv")]
        return templates.TemplateResponse("home.html",
                                           {"request": request,
                                            "summary": summary,
                                            "reports": reports,
                                            "aws_profile": PROFILE})
    except Exception as err:
        logger.error(f"❌ Unexpected error in root controller {err}")
        return JSONResponse(content={"Error": "Error in root controller"}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)




@get_router.get("/cost")
async def daily_cost(request: OptimizerRequest):
    try:
        region = request.region
        data = await gat_daily_cost(region=region) 
    except Exception as err:
        logger.error(f"❌ Unexpected error in daily_cost controller {err}")
        return JSONResponse(content={"Error": "Error in daily_cost controller"}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)




@get_router.get("/all-reports")
async def all_reports():
    try:
        reports = [f for f in os.listdir(REPORTS_DIR) if f.endswith(".csv")]
        return JSONResponse(content={"reports": reports}, status_code=status.HTTP_200_OK)
    except Exception as err:
        logger.error(f"❌ Unexpected error in all_reports controller {err}")
        return JSONResponse(content={"Error": "Error in all_reports controller"}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

@get_router.get("/reports/{report_name}")
async def get_report(report_name: str, request: Request):
    try:
        file_path = os.path.join(REPORTS_DIR, report_name)
        if not os.path.isfile(file_path):
            return JSONResponse(content={"Error": "Report not found"}, status_code=status.HTTP_404_NOT_FOUND)
        df = pd.read_csv(file_path)
        html_table = df.to_html(classes='table table-hover table-striped align-middle', index=False)
        logger.info(f"get_report controller: ✅ Report {report_name} fetched successfully")
        return templates.TemplateResponse("rebort_view.html",
                                           {"request": request,
                                            "report_name": report_name,
                                            "table": html_table})
    except Exception as err:
        logger.error(f"❌ Unexpected error in get_report controller {err}")
        return JSONResponse(content={"Error": "Error in get_report controller"}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)