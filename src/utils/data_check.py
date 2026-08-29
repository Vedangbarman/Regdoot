import os
import json 
from datetime import datetime,timezone
from utils.week_file_save import current_week_file

script_dir = os.path.dirname(os.path.realpath(__file__))
in_dir_config_file = os.path.abspath(os.path.join(script_dir,"..","..","config.json"))

out_dir_error_logs = os.path.abspath(os.path.join(script_dir,"..","data","error_logs"))
os.makedirs(out_dir_error_logs, exist_ok=True)



def check_data(article_list,file_path):
        try:
            with open (in_dir_config_file,) as file:
                data = json.load(file)
            valid_articles = []
            
            date_format = "%a, %d %b %Y %H:%M:%S"
            ref_date = data["data_check"]["ref_date"]
            ref_article = data["data_check"]["ref_article"]
            delta_ref_date = data["data_check"]["delta_ref_date"]
            
            
            for article in article_list :
                if ref_date == "zero" and delta_ref_date == "zero" and ref_article == "zero":
                    valid_articles.append(article)
                
                elif ref_date != "zero" and delta_ref_date != "zero" and ref_article != "zero":
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
                if ref_date == "zero" : 
                    data["data_check"]["ref_date"] = article_list[0]["pubDate"]
                    data["data_check"]["delta_ref_date"] = article_list[0]["pubDate"]
                    data["data_check"]["ref_article"] = article_list[0]["link"]
                    data["data_check"]["ref_file"] = str(file_path)  
                    
                else:
                    data["data_check"]["delta_ref_date"] = ref_date                
                    data["data_check"]["ref_date"] = article_list[0]["pubDate"]
                    data["data_check"]["ref_article"] = article_list[0]["link"]
                    data["data_check"]["ref_file"] = str(file_path) 
                    
                with open(in_dir_config_file, "w") as file:
                    json.dump(data, file, indent=4)

            return valid_articles
            
        except Exception as e:
            print(f"Error: {e}")
            print(f"Error {e}")
            error_message = str(e)
            time = str(datetime.now(timezone.utc))
            errors_ds = {}
            errors_ds['Error_Message'] = error_message
            errors_ds['Time'] = time
            errors_ds['Error Count'] = "not_applicable"
            errors_ds['Error_File'] = "Scraper"          
            format_errors = "json"
            current_path_error_log = current_week_file(out_dir_error_logs,format_errors)
            data = json.dumps(errors_ds)
            with open (current_path_error_log, "a") as file:
                file.write(data + "\n")
            print(f"Data saved to {current_path_error_log}")
            return []
