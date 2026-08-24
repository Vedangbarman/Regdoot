import os
import lxml
import json 
import asyncio
import requests
import pandas as pd
from bs4 import BeautifulSoup
from utils.data_check import check_data
from utils.week_file_save import current_week_file
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
        flag = 1
        return flag



async def rbi_webscraper():
    
    count = 0
    while count < 5:
        try: 
            url = "https://rbi.org.in/notifications_rss.xml"
            resp = requests.get(url)
            resp.raise_for_status()
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
            
            if pr_items:
                checked_pr_items = check_data(pr_items)
                    
                if checked_pr_items:
                    pr_dataframe = pd.DataFrame(checked_pr_items,columns=['title','description','link','pubDate'])
                    path_check = os.path.exists(current_path_notifications)
                        
                    if path_check == True:
                        file_empty_status = isFileEmpty(current_path_notifications)
                        if file_empty_status == True:
                                    pr_dataframe.to_csv(current_path_notifications,mode = 'a',header = True,index = False, encoding = 'utf-8')
                                    return True
                                
                        elif file_empty_status == False:
                            pr_dataframe.to_csv(current_path_notifications,mode = 'a',header = False,index = False, encoding = 'utf-8')            
                            print(f"Data saved to {current_path_notifications}")
                            return True
                        
                        elif  file_empty_status == 1:
                            return False
                           
                        else:
                            return False                          
                            
                    else:
                        pr_dataframe.to_csv(current_path_notifications,mode = 'a',header = True,index = False, encoding = 'utf-8')
                        return True 
                    
                else:
                    print("nothing Found")
                    return False
            else:
                print("nothing Found")
                return False
                       
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
                
if __name__ == "__main__":
    asyncio.run(rbi_webscraper())
        
        
    
    
