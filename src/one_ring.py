import os
import json
import asyncio
import pandas as pd
from scraper import rbi_webscraper
from utils.error_store import error_store
from utils.week_file_save import current_week_file
from datetime import datetime, timezone, timedelta



script_dir = os.path.dirname(os.path.realpath(__file__))
out_dir_error_logs = os.path.abspath(os.path.join(script_dir,"..","data","error_logs"))
os.makedirs(out_dir_error_logs,exist_ok = True)

in_dir_config_file = os.path.abspath(os.path.join(script_dir,"..","config.json"))



async def ring():
    count = 0
    while True:
        try:
            with open(in_dir_config_file) as file:
                data = json.load(file)
            time = datetime.now().strftime("%H")
            time_scraper = data["time_scraper"]
            if time_scraper == time:
                flag = rbi_webscraper()
                if flag == True:
                    continue
                
            
        except Exception as e:
            print(f"Error {e}")
            error_message = str(e)
            count +=1
            time = str(datetime.now(timezone.utc))
            
            Error_Message = error_message
            Time = time
            Error_Count = count
            Error_File = "Ring_file"
            error_store(Error_Message,Time,Error_Count,Error_File)
            
        
        config = json.load(in_dir_config_file)
        sleep_count = 86400
        n = config["run_count"]
        await asyncio.sleep(sleep_count/n)
        
    