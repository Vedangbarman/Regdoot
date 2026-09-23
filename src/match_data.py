import re
import os
import json
import pandas as pd
from collections import defaultdict
from difflib import SequenceMatcher
from datetime import datetime, timezone
from utils.error_store import error_store
from utils.week_file_save import current_week_file


file_path = os.path.dirname(os.path.realpath(__file__))

in_dir_config_file = os.path.abspath(os.path.join(file_path,"..","config.json"))
out_dir_error_logs = os.path.abspath(os.path.join(file_path,"..","data","error_logs"))

with open(in_dir_config_file) as config_file:
    config = json.load(config_file)


clean_notifications_path = config["data_check"]["clean_ref_file"] 

in_dir_master_direction   = os.path.abspath(os.path.join(file_path,"..", "Data", "master_directory", "master_directory.jsonl"))
master_dir = pd.read_json(in_dir_master_direction, lines = True)

notifications = pd.read_csv(clean_notifications_path)



def isFileEmpty(filename): 
    try:
        if os.stat(filename).st_size > 0:
               return False
        else:
            return True
    except OSError:
        flag = "os_error"
        return flag

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
        

def char_diff(a, b):
    diff = 0
    for tag, i1, i2, j1, j2 in SequenceMatcher(None, a, b).get_opcodes():
        if tag != "equal":
            diff += max(i2 - i1, j2 - j1)
    return diff


def match_row(row,master_lookup):
    if row["discard_pre_match"]:
        return None, "discarded"
    for n in row["found_title"]:
        if n in master_lookup:
            return master_lookup[n], "title_match"
    for n in row["found_text"]:          # full text, not lead
        if n in master_lookup:
            return master_lookup[n], "text_match"
    return None, "no_match"

def bucket(row):
    if row["match_method"] == "discarded":
        return "discard"
    if row["match_method"] != "no_match":
        return "linked"
    if row["is_nbfc_relevant"]:
        has_citation = len(row["found_title"]) > 0 or len(row["found_text_lead"]) > 0
        return "nbfc_citation_unmatched" if has_citation else "nbfc_standalone"
    return "general" 

def match_data():
        
    notifications["extracted_title"] = notifications["title"].apply(extract_names)
    notifications["extracted_text"] = notifications["clean_description"].apply(extract_names)
        
    notifications["extracted_text_lead"] = [extract_names(get_lead(t)) for t in notifications["clean_description"]] 
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
    notifications["clean_description"].str.contains(nbfc_pattern, na=False) |
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
        notifications["clean_description"].str.contains(nbfc_pattern, na = False) | 
        notifications["is_nbfc_in_title"]
    )
    
    notifications["names_other_entity"] = notifications["title"].str.contains(other_entity_pattern, na=False)
    notifications["discard_pre_match"] = notifications["names_other_entity"] & ~notifications["is_nbfc_relevant"]
    
    notifications[["matched_id", "match_method"]] = list(
    notifications.apply(match_row, axis=1, args=(master_lookup,))
    )
    
    fuzzy_candidates = []
    for idx, row in notifications[notifications["match_method"] == "no_match"].iterrows():
        for n in(row["found_title"] + row["found_text_lead"]):
            for key in master_keys:
                if char_diff(n,key)<=5:
                    fuzzy_candidates.append((idx,row["id"],n,key))
                    break
                
                
    fuzzy_df = pd.DataFrame(fuzzy_candidates, columns=["row_idx", "circular_id", "extracted_name", "closest_master_name"])
    print(f"{len(fuzzy_df)} candidates")
    
    fuzzy_df["master_id"] = fuzzy_df["closest_master_name"].map(master_lookup)

    dupe_check = fuzzy_df.groupby("row_idx")["master_id"].nunique()
    
    ambiguous_rows = dupe_check[dupe_check > 1].index
    
    
    safe_fuzzy = fuzzy_df[~fuzzy_df["row_idx"].isin(ambiguous_rows)].drop_duplicates("row_idx")
    for _, r in safe_fuzzy.iterrows():
        notifications.loc[r["row_idx"], "matched_id"]   = master_lookup[r["closest_master_name"]]
        notifications.loc[r["row_idx"], "match_method"] = "fuzzy_match"
        
    notifications["bucket"] = notifications.apply(bucket, axis=1)
    ref_pattern = re.compile(r"([A-Z]+(?:\.[A-Z]+)+\.\d+)/([\d-]+)/(\d{4}-\d{2})")
    
    notifications["subject_code"] = notifications["clean_description"].str.extract(ref_pattern)[1]
    
    master_dir["subject_code"] = master_dir["text"].str.extract(ref_pattern)[1]
    
    code_counts = master_dir.dropna(subset=["subject_code"]).groupby("subject_code")["id"].nunique()
    generic_codes = code_counts[code_counts > 1].index.tolist()
    clean_master = master_dir[~master_dir["subject_code"].isin(generic_codes)]

    code_matches = notifications.merge(
    clean_master.dropna(subset=["subject_code"])[["id", "subject_code"]],
    on="subject_code", how="left", suffixes=("", "_master")
    )
    
   
    
    out_path = os.path.join(file_path,"..","Data","notifications_matched")
    out_path_json = current_week_file(out_path,format = "json")
    
    kept = notifications[notifications["bucket"] != "discard"].copy()
    
    if ( len(fuzzy_df)>0 ):
        file_empty_status = isFileEmpty(out_path_json)
        if file_empty_status == True:
            kept.to_json(out_path_json,mode = "a",header = True,index=False, encoding="utf-8-sig")
            print(f"{len(fuzzy_df)} : Candidates Saved")
            
        elif file_empty_status == False:
            kept.to_json(out_path_json,mode = "a",header = False,index=False, encoding="utf-8-sig")
            print(f"{len(fuzzy_df)} : Candidates Saved")
        
        elif  file_empty_status == "os_error":
            time = str(datetime.now(timezone.utc))
            Error_Message = "Unknow Error in match_data.py while checking for file empty status"
            error_count =  "Not Applicable"
            Error_File = "Match_data"
            error_store(Error_Message,time,error_count,Error_File)   
            return False
          
        config["data_check"]["matched_ref_file"] = out_path_json
        with open(in_dir_config_file, "w") as config_file:
            json.dump(config, config_file, indent=4)
            return True
        
        
    else:
        print("None Saved")
        return False
        
        
if __name__ == "__main__":
    match_data()