import os
import json
import asyncio
import pandas as pd
from scraper import rbi_webscraper
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
                
            else:
                pass
            
        except Exception as e:
            print(f"Error {e}")
            error_message = str(e)
            count +=1
            time = str(datetime.now(timezone.utc))
            errors_ds = {}
            errors_ds['Error_Message'] = error_message
            errors_ds['Time'] = time
            errors_ds['Error Count'] = count
            errors_ds['Error_File'] = "Scraper"
                        
            format_errors = "json"
            current_path_error_log = current_week_file(out_dir_error_logs,format_errors)
            data = json.dumps(errors_ds)
            with open (current_path_error_log, "a") as file:
                file.write(data + "\n")
                print(f"Data saved to {current_path_error_log}")
        
        config = json.load(in_dir_config_file)
        sleep_count = 86400
        n = config["run_count"]
        await asyncio.sleep(sleep_count/n)
        
    