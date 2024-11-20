from dotenv import load_dotenv
import os
from couchbase.cluster import Cluster
from couchbase.auth import PasswordAuthenticator
from couchbase.options import ClusterOptions
from openai import OpenAI 
from datetime import timedelta
from tqdm import tqdm
import uuid
import pandas as pd

# Load environment variables
load_dotenv()
DB_CONN_STR = os.getenv("DB_CONN_STR")
DB_USERNAME = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_BUCKET = os.getenv("DB_BUCKET")
DB_SCOPE = os.getenv("DB_SCOPE")
DB_COLLECTION = os.getenv("DB_COLLECTION")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MOVIES_DATASET = "imdb_top_1000.csv"

# Use text-embedding-3-small as the embedding model if not set
if not EMBEDDING_MODEL:
    EMBEDDING_MODEL = "text-embedding-3-small"


def check_environment_variable(variable_name):
    """Check if environment variable is set"""
    if variable_name not in os.environ:
        raise ValueError(
            f"{variable_name} environment variable is not set. Please add it to the environment"
        )

# Ensure that all environment variables are set
check_environment_variable("OPENAI_API_KEY")
check_environment_variable("DB_CONN_STR")
check_environment_variable("DB_USERNAME")
check_environment_variable("DB_PASSWORD")
check_environment_variable("DB_BUCKET")
check_environment_variable("DB_SCOPE")
check_environment_variable("DB_COLLECTION")
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),  # This is the default and can be omitted
)


def connect_to_couchbase(connection_string, db_username, db_password):
    """Connect to couchbase"""
    print("Connecting to couchbase...")
    auth = PasswordAuthenticator(db_username, db_password)
    options = ClusterOptions(auth)
    connect_string = connection_string
    cluster = Cluster(connect_string, options)

    # Wait until the cluster is ready for use.
    cluster.wait_until_ready(timedelta(seconds=5))

    return cluster


def generate_embeddings(client, input_data):
    """Generate OpenAI embeddings for the input data"""
    response = client.embeddings.create(input=input_data, model=EMBEDDING_MODEL)
    return response.data[0].embedding

def translate_to_korean(english_text):
    """
    영문 문장을 한글로 번역하는 함수.
    """
    try:
        # OpenAI API 요청
        response = client.chat.completions.create(
            model="gpt-4",  # 또는 "gpt-3.5-turbo"
            messages=[
                {"role": "system", "content": "You are a professional translator specialized in English to Korean translation."},
                {"role": "user", "content": f"Translate the following English text to Korean: {english_text}"}
            ],
            temperature=0.2,  # 번역의 일관성을 유지하기 위한 낮은 온도 설정
        )

        # 응답에서 번역된 텍스트 추출
        korean_translation = response.choices[0].message.content
        return korean_translation

    except Exception as e:
        return f"Error: {e}"

try:
    cluster = connect_to_couchbase(DB_CONN_STR, DB_USERNAME, DB_PASSWORD)
    bucket = cluster.bucket(DB_BUCKET)
    scope = bucket.scope(DB_SCOPE)
    collection = scope.collection(DB_COLLECTION)
    data = pd.read_csv(MOVIES_DATASET)

    # Convert columns to numeric types
    data["Gross"] = data["Gross"].str.replace(",", "").astype(float)

    # Fill empty values
    data["Gross"] = data["Gross"].fillna(0)
    data["Certificate"] = data["Certificate"].fillna("NA")
    data["Meta_score"] = data["Meta_score"].fillna(-1)

    data_in_dict = data.to_dict(orient="records")
    print("Ingesting Data...")
    for row in tqdm(data_in_dict):
        #byKR row["Overview_embedding"] = generate_embeddings(client, row["Overview"])
        row["Overview_embedding"] = generate_embeddings(client, row["Series_Title"]+row["Overview"])
        row["Overview_ko"] = translate_to_korean(row["Overview"])
        doc_id = uuid.uuid4().hex
        collection.upsert(doc_id, row)

except Exception as e:
    print("Error while ingesting data", e)
