import os
import lxml
import json 
import asyncio
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta


script_dir = os.path.dirname(os.path.realpath(__file__))
in_dir_config_file = os.path.abspath(os.path.join(script_dir,"..","..","config.json"))


def check_data(article_list):
        try:
            with open (in_dir_config_file,) as file:
                data = json.load(file)
            valid_articles = []
            
            date_format = "%a, %d %b %Y %H:%M:%S"
            ref_date = data["data_check"]["ref_date"]
            ref_article = data["data_check"]["ref_article"]
            delta_ref_date = data["data_check"]["delta_ref_date"]
            
            
            for article in article_list :
                if ref_date == "null" and delta_ref_date == "null" and ref_article == "null":
                    valid_articles.append(article)
                
                elif ref_date != "null" and delta_ref_date != "null" and ref_article != "null":
                    pubDate = article["pubDate"]
                    pubDate_formatted = datetime.strptime(pubDate,date_format)
                    ref_date_formatted = datetime.strptime(ref_date,date_format)
                    if pubDate_formatted > ref_date_formatted:
                        valid_articles.append(article)
                    
                    elif pubDate_formatted == ref_date_formatted :
                        if ref_article != article["link"] :
                            valid_articles.append(article)
                
                else:
                    print("Reference Value are missing!")
            
            if article_list:
                if ref_date == "null" : 
                    data["data_check"]["ref_date"] = article_list[0]["pubDate"]
                    data["data_check"]["delta_ref_date"] = article_list[0]["pubDate"]
                    data["data_check"]["ref_article"] = article_list[0]["link"]
                    
                else:
                    data["data_check"]["ref_date"] = ref_date                
                    data["data_check"]["ref_date"] = article_list[0]["pubDate"]
                    data["data_check"]["ref_article"] = article_list[0]["link"]
                    
                with open(in_dir_config_file, "w") as file:
                    json.dump(data, file, indent=4)

            return valid_articles
            
        except Exception as e:
            print(f"Error: {e}")
            return []
