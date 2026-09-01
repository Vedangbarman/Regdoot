import os 
import json
import requests
from bs4 import BeautifulSoup
from utils.week_file_save import current_week_file

script_dir = os.path.dirname(os.path.realpath(__file__))

out_dir_master_directory = os.path.abspath(os.path.join(script_dir,"..","data","master_directory"))
os.makedirs(out_dir_master_directory,exist_ok = True)


def scrape_master_directory():
    intial_id = 12931
    
    for i in range(0,35):
        id = intial_id + i
        url = f"https://rbi.org.in/scripts/BS_ViewMasDirections.aspx?id={id}"
        resp = requests.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, features="html.parser")
        
        title = soup.find('b').get_text(strip=True)
        
        
        content = soup.find('tr', class_='tablecontent2')
        for junk in content.find_all(["script", "style", "input"]):
            junk.decompose()
        clean_text = content.get_text(separator="\n", strip=True).replace("\r", "")
        
        clean_data = {"id": id, "title": title, "category": "NBFC", "url": url, "text": clean_text}
        
        file_path = os.path.abspath(os.path.join(out_dir_master_directory,f"{id}.json"))
        with open(file_path,"w",encoding = "utf-8") as f:
            json.dump(clean_data,f)
        
        
        
scrape_master_directory()
        