import os
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_google_genai import ChatGoogleGenerativeAI
load_dotenv()

API_KEY = os.getenv('GEMINI')

script_dir = os.path.dirname(os.path.realpath(__file__))
in_dir_config = os.path.abspath(os.path.join(script_dir,"..","config.json"))

os.environ["GOOGLE_API_KEY"] = API_KEY

model = ChatGoogleGenerativeAI(model = "gemini-3.7-flash")


response = model.invoke("Hello, Gemini!")
print(response.content)


