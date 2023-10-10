from typing import Union, Dict
from fastapi import FastAPI, Query
from sentinelhub import (
    SentinelHubCatalog,
    BBox,
    SentinelHubStatistical,
    Geometry,
    SHConfig,
    CRS,
    DataCollection,
    SentinelHubRequest,
    MimeType,
)
import base64
from datetime import datetime, date, timedelta
import json
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from PIL import Image
import io
from pathlib import Path
from uuid import uuid4
from enum import Enum

# Description for the FastAPI application
description = """
Sentinel API helps you do work with farm
"""
app = FastAPI(
    title="Sentinel API",
    docs_url="/",
    description=description,
    version="0.0.1",
)
app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Evaluation scripts for NDVI and SMI indices
eval_ndvi = """
//VERSION=3

let viz = ColorMapVisualizer.createDefaultColorMap();

function evaluatePixel(samples) {
    let val = index(samples.B08, samples.B04);
    val = viz.process(val);
    val.push(samples.dataMask);
    return val;
}

function setup() {
  return {
    input: [{
      bands: [
        "B04",
        "B08",
        "dataMask"
      ]
    }],
    output: {
      bands: 4
    }
  }
}
"""
eval_smi = """
//VERSION=3

let index = (B8A - B11)/(B8A + B11);

let val = colorBlend(index, [-0.8, -0.24, -0.032, 0.032, 0.24, 0.8], [[0.5,0,0], [1,0,0], [1,1,0], [0,1,1], [0,0,1], [0,0,0.5]]);
val.push(dataMask);
return val;
"""
# Configuration for Sentinel Hub
config = SHConfig()
config.sh_client_id = "2fde1530-a87e-4c46-b638-8dab2a2aa381"
config.sh_client_secret = "R-)FscoRc,/Yk2XP?NHyonu|sL3Cw2.WtW*A?rk:"
config.sh_base_url = "https://services.sentinel-hub.com"


class SupportedIndices(str, Enum):
    ndvi = "ndvi"
    smi = "smi"


# homepage
@app.get("/")
def read_root():
    """
    This is the homepage of the API.
    """
    return {"Hello": "World"}


# satellite dates
@app.get("/dates/")
def dates(
    polygon: str = """{"coordinates":[[[73.77544002083724,18.67297200337846],[73.77479411066756,18.672198614893645],[73.77535928206632,18.67195214969084],[73.77598725028642,18.672547065086846],[73.77544002083724,18.67297200337846]]],"type":"Polygon"}""",
):
    """
    This endpoint returns a list of dates for which satellite imagery is available.
    The polygon parameter is used to specify the area of interest.
    The polygon is specified as a JSON string.
    """
    catalog = catalog = SentinelHubCatalog(config=config)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    geometry = Geometry(geometry=json.loads(polygon), crs=CRS.WGS84)
    search_iterator = catalog.search(
        DataCollection.SENTINEL2_L2A,
        geometry=geometry,
        time=(start_date, end_date),
    )
    response = []
    results = list(search_iterator)

    for item in results:
        date_str = item["properties"]["datetime"].replace('Z', '')

        datetime_obj = datetime.fromisoformat(
            date_str
        )  # Remove the 'Z' at the end
        date_only = datetime_obj.date()

        response.append(
            {"date": date_only, "cloud cover": item["properties"]["eo:cloud_cover"]}
        )

    return response


# satellite Imagery
@app.get("/imagery/")
def imagery(
    geometry = """{"coordinates":[[[73.77544002083724,18.67297200337846],[73.77479411066756,18.672198614893645],[73.77535928206632,18.67195214969084],[73.77598725028642,18.672547065086846],[73.77544002083724,18.67297200337846]]],"type":"Polygon"}""",
    bbox: str = """[12,2,12,1]""", 
    index: Union[SupportedIndices, str] = "ndvi",
    date: date = Query(..., description="Imagery date"),
):
    """
    This endpoint returns satellite imagery for a given index.
    The index parameter is used to specify the index to be calculated.
    The index can be either 'ndvi' or 'smi'.
    The polygon is specified as a JSON string.
    
    """
    geom = Geometry(
        geometry=json.loads(geometry),
        crs=CRS.WGS84,
    )
    bbox = BBox(bbox=json.loads(bbox), crs=CRS.WGS84)
    data_folder = f"static/{index}/field-imagery-{uuid4()}/"
    # Path(data_folder).mkdir(parents=True, exist_ok=True)
    if index == "ndvi":
        evalscript = eval_ndvi
    elif index == "smi":
        evalscript = eval_smi
    request = SentinelHubRequest(
        data_folder=data_folder,
        evalscript=evalscript,
        input_data=[
            SentinelHubRequest.input_data(
                data_collection=DataCollection.SENTINEL2_L2A,
                time_interval=(date, date),
            ),
        ],
        responses=[
            SentinelHubRequest.output_response("default", MimeType.PNG),
        ],
        bbox=bbox,
        config=config,
    )

    request.get_data(save_data=True)
    img_path = f"{data_folder}{request.get_filename_list()[0]}"
    with open(img_path, "rb") as masked_image:
        encoded_image_string = base64.b64encode(masked_image.read())
    return {"path":img_path}


# NDVI stats
@app.get("/ndvi-stats/")
def stats(
    geometry = """{"coordinates":[[[73.77544002083724,18.67297200337846],[73.77479411066756,18.672198614893645],[73.77535928206632,18.67195214969084],[73.77598725028642,18.672547065086846],[73.77544002083724,18.67297200337846]]],"type":"Polygon"}""",
    start_date: date = Query(..., description="Start date"),
    end_date: date = Query(..., description="End date"),
):  
    """
    This endpoint returns NDVI statistics for a given time period.
    The polygon is specified as a JSON string.
    The start_date and end_date parameters are used to specify the time period.
    The response is a JSON object 
    """
    geom = Geometry(
        geometry=json.loads(geometry),
        crs=CRS.WGS84,
    )
    request = SentinelHubStatistical(
        aggregation=SentinelHubStatistical.aggregation(
            evalscript="""
            function setup() {
            return {
                input: [
                {
                    bands: ["B02", "B04", "B08", "dataMask"],
                },
                ],
                output: [
                {
                    id: "data",
                    bands: 1,
                },

                {
                    id: "dataMask",
                    bands: 1,
                },
                ],
            };
            }

            function evaluatePixel(samples) {
            let ndvi = (samples.B08 - samples.B04) / (samples.B08 + samples.B04);

            let validValue = 1;
            if (ndvi < -1 || ndvi > 1) {
                validValue = 0;
            }
            return {
                data: [ndvi],
                dataMask: [samples.dataMask * validValue ],
            };
            }
            """,
            time_interval=(start_date, end_date),
            aggregation_interval="P5D",
            size=[512, 461.953],
        ),
        input_data=[
            SentinelHubStatistical.input_data(
                DataCollection.SENTINEL2_L2A,
            ),
        ],
        geometry=geom,
        config=config,
    )

    response = request.get_data()

    return {"stats": response}
