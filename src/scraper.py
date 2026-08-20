import os
import lxml
import json 
import asyncio
import requests
import pandas as pd
from week_file_save import current_week_file
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta


script_dir = os.path.dirname(os.path.realpath(__file__))

out_dir_notifications = os.path.abspath(os.path.join(script_dir,"..","data","notifications"))
os.makedirs(out_dir_notifications,exist_ok = True)

out_dir_error_logs = os.path.abspath(os.path.join(script_dir,"..","data","error_logs"))
os.makedirs(out_dir_error_logs,exist_ok = True)

        
def isFileEmpty(filename): 
    try:
        if os.stat(filename).st_size > 0:
               return False
        else:
            return True
    except OSError:
        print ("No file")



async def rbi_webscraper():
    
    count = 0
    while count < 5:
        try: 
            url = "https://rbi.org.in/notifications_rss.xml"
            resp.raise_for_status()
            resp = requests.get(url)

            soup = BeautifulSoup(resp.content, features="xml")

            items = soup.find_all('item')

            pr_items = []
            
            format_notifications = "csv"
            current_path_notifications = current_week_file(out_dir_notifications,format_notifications)
            for item in items:
                pr_item = {}
                pr_item['title'] = item.title.text
                pr_item['description'] = item.description.text
                pr_item['link'] = item.link.text
                pr_item['pubDate'] = item.pubDate.text
                pr_items.append(pr_item)
        
                   
            pr_dataframe = pd.DataFrame(pr_items,columns=['title','description','link','pubDate'])
            if pr_items:
                path_check = os.path.exists(current_path_notifications)
                if path_check == True:
                    if isFileEmpty(current_path_notifications) == True:
                        pr_dataframe.to_csv(current_path_notifications,mode = 'a',header = True,index = False, encoding = 'utf-8')
                    else:
                        pr_dataframe.to_csv(current_path_notifications,mode = 'a',header = False,index = False, encoding = 'utf-8')
                            
                    print(f"Data saved to {current_path_notifications}")
                    break
                else:
                    pr_dataframe.to_csv(current_path_notifications,mode = 'a',header = True,index = False, encoding = 'utf-8')
                    break
            else:
                break
            
            
        
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
        
                  
        
        sleep_count = count*5
        print(f"Retrying in {sleep_count} seconds.......")
        await asyncio.sleep(sleep_count)
        if count == 5:
            return False
        else :
            return True
        
if __name__ == "__main__":
    asyncio.run(rbi_webscraper())
        
        
    
    
