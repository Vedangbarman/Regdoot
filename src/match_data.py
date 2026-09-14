import re
import os
import json
import pandas as pd
from collections import defaultdict
from difflib import SequenceMatcher


file_path = os.path.abspath(os.getcwd())

in_dir_config_file = os.path.abspath(os.path.join(file_path,"..","config.json"))

with open(in_dir_config_file) as config_file:
    config = json.load(config_file)

clean_notifications_path = config["data_check"]["clean_ref_file"] 

in_dir_master_direction   = os.path.abspath(os.path.join(file_path,"..", "Data", "master_directory", "master_directory.jsonl"))
master_dir = pd.read_json(in_dir_master_direction, lines = True)
    