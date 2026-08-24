import os
import lxml
import json 
import asyncio
import requests
import pandas as pd
from bs4 import BeautifulSoup
from utils.week_file_save import current_week_file
from datetime import datetime, timezone, timedelta

script_dir = os.path.dirname(os.path.realpath(__file__))
out_dir_notifications = os.path.abspath(os.path.join(script_dir,"..","data","notifications"))

in_dir_config_file = os.path.abspath(os.path.join(script_dir,"..","..","config.json"))


def check_data():
    with open (in_dir_config_file) as file:
        data = json.load(file)
    
    date_format = "%a, %d %b %Y %H:%M:%S"
    ref_date = data["data_check"]["ref_date"]
    delta_ref_date = data["data_check"]["delta_ref_date"]
    
    ref_date_formatted = datetime.strptime(ref_date,date_format)
    delta_ref_date_formatted = datetime.strptime(delta_ref_date,date_format)
    
    format = "csv"
    raw_data_file = current_week_file(out_dir_notifications,format)
    
    if ref_date_formatted == delta_ref_date_formatted:
        print("")
    elif ref_date_formatted > delta_ref_date_formatted:
        print("")
        
    return True