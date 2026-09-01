import os 
import json
import traceback
import asyncio
import requests
from bs4 import BeautifulSoup

script_dir = os.path.dirname(os.path.realpath(__file__))

out_dir_master_directory = os.path.abspath(os.path.join(script_dir,"..","data","notification_historical"))
os.makedirs(out_dir_master_directory,exist_ok = True)


async def scrape_historical_notification():
    intial_id = 12925
    count = 0
    i = 0
    while i < 766:
        for i in range(0,766):
            try : 
                id = intial_id + i
                url = f"https://rbi.org.in/scripts/NotificationUser.aspx?Id={id}"
                resp = requests.get(url)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.content, features="html.parser")
                
                title = soup.find('b').get_text(strip=True)
                
                
                content = soup.find('tr', class_='tablecontent2')
                for junk in content.find_all(["script", "style", "input"]):
                    junk.decompose()
                clean_text = content.get_text(separator="\n", strip=True).replace("\r", "")
                
                clean_data = {"id": id, "title": title, "category": "NBFC", "url": url, "text": clean_text}
                
                file_path = os.path.abspath(os.path.join(out_dir_master_directory,f"notification.jsonl"))
                with open(file_path,"a",encoding = "utf-8") as f:
                    f.write(json.dumps(clean_data) + "\n")
            
            except Exception as e:
                if count < 25:
                    traceback.print_exc()
                    count +=5
                    await asyncio.sleep(count)
                else:
                    break
                
                

if __name__ == "__main__":
    asyncio.run(scrape_historical_notification())
        