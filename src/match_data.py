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
        

def get_lead(text):
    lead_break = re.compile(r"\n\s*2\.\s") #extract text from the first para 
    
    if not isinstance(text,str):
        return []
    
    else:
        m = lead_break.search(text)
        return text[:m.start()] if m else text[:600] #return first 600 characters 
                                                     #if the text 2nd section is not found before 600 characters
                                                     # used bucketing only! 
                                                     # gatorade
        

def match_data():
        
    notifications["extracted_title"] = notifications["title"].apply(extract_names)
    notifications["extracted_text"] = notifications["text"].apply(extract_names)
        
    notifications["extracted_text_lead"] = [extract_names(get_lead(t)) for t in notifications["text"]] 
    #used for loop instead of lambda for performance gains 
    
    master_dir["extracted_title"] = master_dir["title"].apply(extract_names)
    
    name_to_ids = defaultdict(set)
    
    for _, r in master_dir.iterrows():
        for name in r["extracted_title"]:
            name_to_ids[name].add(r["id"])
    
    
    master_lookup = {name: next(iter(ids)) for name, ids in name_to_ids.items() if len(ids) == 1}
    master_keys = list(master_lookup.keys())
    
    nbfc_pattern = re.compile(
    r"non[\s-]?banking financial compan|nbfc"
    r"|core investment compan(?:y|ies)"          # dropped bare \bcic\b — collides with Credit Information Company
    r"|standalone primary dealer|\bspd\b"
    r"|mortgage guarantee compan(?:y|ies)|\bmgc\b"
    r"|non-?operative financial holding compan(?:y|ies)|\bnofhc\b"
    r"|housing finance compan(?:y|ies)|\bhfc\b",
    re.IGNORECASE
    )
    notifications["is_nbfc_relevant"] = (
    notifications["text"].str.contains(nbfc_pattern, na=False) |
    notifications["title"].str.contains(nbfc_pattern, na=False)
    )

    other_entity_pattern = re.compile(
    r"regional rural bank"
    r"|urban co-?operative bank"
    r"|rural co-?operative bank"
    r"|state co-?operative bank"
    r"|district central co-?operative bank"
    r"|scheduled commercial bank"
    r"|commercial bank"
    r"|payments? bank"
    r"|small finance bank"
    r"|local area bank"
    r"|co-?operative bank"
    r"|banker and debt manager to government"
    r"|banker to governments? and banks"
    r"|consumer education and protection"
    r"|all india financial institutions?"
    r"|asset reconstruction compan(?:y|ies)"
    r"|credit information compan(?:y|ies)"
    r"|financial inclusion and development"
    r"|financial market"
    r"|issuer of currency"
    r"|payments? and settlement systems?",
    re.IGNORECASE
    )
    
    notifications["is_nbfc_in_title"] = notifications["title"].str.contains(nbfc_pattern, na = False)
    notifications["is_nbfc_relevant"] = (
        notifications["text"].str.contains(nbfc_pattern, na = False) | 
        notifications["is_nbfc_in_title"]
    )