import re
import os
import json
import pandas as pd
from collections import defaultdict
from difflib import SequenceMatcher


file_path = os.path.dirname(os.path.realpath(__file__))

in_dir_config_file = os.path.abspath(os.path.join(file_path,"..","config.json"))

with open(in_dir_config_file) as config_file:
    config = json.load(config_file)

clean_notifications_path = config["data_check"]["clean_ref_file"] 

in_dir_master_direction   = os.path.abspath(os.path.join(file_path,"..", "Data", "master_directory", "master_directory.jsonl"))
master_dir = pd.read_json(in_dir_master_direction, lines = True)

notifications = pd.read_csv(clean_notifications_path)


def norm(s):
    cleaned = s.replace("–", "-").replace("—", "-") #replace en-dahses with normal dashes
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip(" ,-").lower()



def extract_names(text):
    DOC_TYPE = r"(?:Directions?|Guidelines?|Regulations?|Rules?|Circulars?|Framework|Scheme)"
        
    p1 = re.compile(
        r"Reserve Bank of India\s*[-–—]?\s*\(([^)]+)\)"
        r"(?:\s*\([^)]*\))*"
        r"\s*(?:[A-Za-z]+\s+){0,3}" + DOC_TYPE,
        re.IGNORECASE
        )
        
    p2 = re.compile(r"Reserve Bank of India\s*[-–—]\s*([A-Za-z ,]+?),?\s*Directions", re.IGNORECASE)
    
    if not isinstance(text,str): #check if the input is string or not
        return []
    else:
        return [norm(x) for x in (p1.findall(text) + p2.findall(text))]
        


def match_data():
        
    notifications["extracted_title"] = notifications["title"].apply(extract_names)