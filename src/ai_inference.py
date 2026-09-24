import os
import json
import pandas as pd
import traceback
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from utils.error_store import error_store
from utils.week_file_save import current_week_file
from langchain_google_genai import ChatGoogleGenerativeAI


load_dotenv()
API_KEY = os.getenv('GEMINI')
os.environ["GOOGLE_API_KEY"] = API_KEY



class ComplianceEvaluation(BaseModel):
    title: str
    link: str
    pubdate : str = Field(
        description="The date string formatted exactly as 'ddd, DD MMM YYYY HH:MM:SS' (e.g. 'Mon, 21 Sep 2026 17:25:00')"
    )
    is_applicable : bool
    is_master_direction_matching : bool
    reason : str
    correct_master_dir : str
    diff : str
    explanation : str
    actions_required : str
    action_date : str
    effective_date: str = Field(
        description="The date string formatted exactly as 'ddd, DD MMM YYYY HH:MM:SS' (e.g. 'Mon, 21 Sep 2026 17:25:00')"
    )
    

def invoke_ai():
    script_dir = os.path.dirname(os.path.realpath(__file__))
    in_dir_config = os.path.abspath(os.path.join(script_dir,"..","config.json"))


    out_dir_output = os.path.abspath(os.path.join(script_dir,"..","data","notifications_output"))
    os.makedirs(out_dir_output,exist_ok = True)

    with open(in_dir_config) as f:
        data = json.load(f)

    debug = False
    if debug:
        in_dir_notifications = os.path.abspath(os.path.join(script_dir,"..","data","notifications_matched","test.jsonl"))

    if not debug:
        in_dir_notifications = data["data_check"]["matched_ref_file"]
        
    notifications = []
    with open(in_dir_notifications, "r", encoding="utf-8") as file_notifications:
        for line in file_notifications:
            notifications.append(json.loads(line))

    in_dir_profile = os.path.abspath(os.path.join(script_dir,"..","profile.json"))
    with open(in_dir_profile, "r", encoding="utf-8") as file_profile:
        profile = json.load(file_profile)
        try : 
            llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", temperature=0)
            structured_llm = llm.with_structured_output(ComplianceEvaluation)

            results = []

            for i, json_line in enumerate(notifications):
                promt = f"""Evaluate compliance applicability. 
                        "title"(title of notification), "link" (link of notification), "pubdate" (as mentioned in data),
                        "is_applicable" (boolean),"is_master_direction_matching" (boolean),"reason"(if master directory doesn't match to the given data return reason if no master directory to match return none),
                        "correct_master_dir"(return not applicable if no master dir needed, mention correct one if master directory mentioned is wrong with full title as mentioned in circular ,otherwise write correct), 
                        "diff","mention direct proposed ( if not return not applicable ) changes in the text 
                        example : Reserve Bank of India (Non-Banking Financial Companies – Concentration Risk Management) Fourth Amendment Directions, 2026

                The Reserve Bank has issued the Reserve Bank of India (Non-Banking Financial Companies – Concentration Risk Management) Directions, 2025 dated November 28, 2025 (hereinafter referred to as ‘Directions’). On a review, it has been decided to revise the large exposure framework for Infrastructure Debt Fund-Non-Banking Financial Company (IDF-NBFC) in the Upper Layer.

                2. Accordingly, in exercise of the powers conferred by Chapter III B of the Reserve Bank of India Act, 1934, and all other provisions / laws enabling the Reserve Bank of India (‘RBI’) in this regard, RBI being satisfied that it is necessary and expedient in the public interest so to do, hereby, issues the Amendment Directions hereinafter specified.

                3. These Amendment Directions shall be called the Reserve Bank of India (Non-Banking Financial Companies – Concentration Risk Management) Fourth Amendment Directions, 2026.

                4. These Amendment Directions shall come into force with immediate effect.

                5. These Amendment Directions shall modify the Directions as under:

                (1) After paragraph 39 in ‘Chapter IV - Guidelines Applicable to NBFC – Upper Layer’, a new paragraph 39A shall be inserted as under:

                39A. The large exposure limits applicable to NBFC-IFC shall also be applicable to IDF-NBFC that are subject to Upper Layer regulations in terms of paragraph 60A of the Reserve Bank of India (Non-Banking Financial Companies – Undertaking of Financial Services) Directions, 2025 read together with paragraph 18 (4) (i) of the Reserve Bank of India (Commercial Banks – Undertaking of Financial Services) Directions, 2025.

                mentions "applicable to Upper Layer" " After paragraph 39 in ‘Chapter IV - Guidelines Applicable to NBFC – Upper Layer’, a new paragraph 39A shall be inserted as under:

                39A. The large exposure limits applicable to NBFC-IFC shall also be applicable to IDF-NBFC that are subject to Upper Layer regulations in terms of paragraph 60A of the Reserve Bank of India (Non-Banking Financial Companies – Undertaking of Financial Services) Directions, 2025 read together with paragraph 18 (4) (i) of the Reserve Bank of India (Commercial Banks – Undertaking of Financial Services) Directions, 2025."
                return this with the old text
                        "explanation" (explane new changes and old changes and how it affect things in proper words as described in notification), "actions_required" (actions required by the company to make).
                        "action_date" ( when to take action mention date or return exact text when the changes is proposed)

                        Profile:
                        {json.dumps(profile,indent = 2 )}
                        
                        Data : 
                        {json.dumps(json_line,indent = 2 )}
                        """
                evaluation : ComplianceEvaluation = structured_llm.invoke(promt)
                
                results.append(evaluation.model_dump())

            output_path = current_week_file(out_dir_output,format = "json")
            
            df_results=pd.DataFrame(results)
            df_results.to_json(output_path,orient="records",lines=True)
            
            if results:
                return True
            else:
                return False
        
        except Exception as e:
            error_store(error_message=str(e),trace_back = traceback.format_exc(),time = str(datetime.now(timezone.utc)),error_count="Null",error_file="ai_inference")
        
if __name__ == "__main__":
    invoke_ai()