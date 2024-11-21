**이 소스는 https://github.com/couchbase-examples/hybrid-search-demo 에서 가져와서 수정한 것입니다.**
**시납시스를 한글로 변경한 부분은 https://github.com/kairess/hybrid-search-movie 를 참고하였습니다.**

## Hybrid Movie Search using Couchbase

This is a demo app built to perform hybrid search using the Vector Search capabilities of Couchbase. The demo allows users to search for movies based on the synopsis or overview of the movie using both the native [Couchbase Python SDK](https://docs.couchbase.com/python-sdk/current/howtos/full-text-searching-with-sdk.html) and using the [LangChain Vector Store integration](https://python.langchain.com/docs/integrations/vectorstores/couchbase/).

> Note that you need Couchbase Server 7.6 or higher for Vector Search.

### How does it work?

You can perform semantic searches for movies based on the plot synopsis. Additionally, you can filter the results based on the year of release and the IMDB rating for the movie. Optionally, you can also search for the keyword in the movie title.

![hybrid search demo](result/result.png)

The hybrid search can be performed using both the Couchbase Python SDK & the LangChain Vector Store integration for Couchbase. We use OpenAI for generating the embeddings.

### How to Run

- #### Install dependencies

  `pip install -r requirements.txt`

- #### Set the environment secrets

  Copy the `secrets.example.toml` file and rename it to `secrets.toml` and replace the placeholders with the actual values for your environment.

  > For the ingestion script, the same environment variables need to be set in the environment (using `.env` file from `.env.example`) as it runs outside the Streamlit environment.

  ```
  OPENAI_API_KEY = "<open_ai_api_key>"
  DB_CONN_STR = "<connection_string_for_couchbase_cluster>"
  DB_USERNAME = "<username_for_couchbase_cluster>"
  DB_PASSWORD = "<password_for_couchbase_cluster>"
  DB_BUCKET = "<name_of_bucket_to_store_documents>"
  DB_SCOPE = "<name_of_scope_to_store_documents>"
  DB_COLLECTION = "<name_of_collection_to_store_documents>"
  INDEX_NAME = "<name_of_search_index_with_vector_support>"
  EMBEDDING_MODEL = "text-embedding-3-small" # OpenAI embedding model to use to encode the documents
  ```

- #### Create the Search Index on Full Text Service

  We need to create the Search Index on the Full Text Service in Couchbase. For this demo, you can import the following index using the instructions.

  - [Couchbase Capella](https://docs.couchbase.com/cloud/search/import-search-index.html)

    - Copy the index definition to a new file index.json
    - Import the file in Capella using the instructions in the documentation.
    - Click on Create Index to create the index.

  - [Couchbase Server](https://docs.couchbase.com/server/current/search/import-search-index.html)

    - Click on Search -> Add Index -> Import
    - Copy the following Index definition in the Import screen
    - Click on Create Index to create the index.

  #### Index Definition

  Here, we are creating the index `movies-search-demo` on the documents in the `_default` collection within the `_default` scope in the bucket `movies`. The Vector field is set to `Overview_embedding` with 1536 dimensions and the text field set to `Overview`. We are also indexing and storing some of the other fields in the document for the hybrid search. The similarity metric is set to `dot_product`. If there is a change in these parameters, please adapt the index accordingly.

  ```json
  {
 "name": "idx_movie_openai",
 "type": "fulltext-index",
 "params": {
  "doc_config": {
   "docid_prefix_delim": "",
   "docid_regexp": "",
   "mode": "scope.collection.type_field",
   "type_field": "type"
  },
  "mapping": {
   "default_analyzer": "standard",
   "default_datetime_parser": "dateTimeOptional",
   "default_field": "_all",
   "default_mapping": {
    "dynamic": false,
    "enabled": false
   },
   "default_type": "_default",
   "docvalues_dynamic": false,
   "index_dynamic": false,
   "store_dynamic": false,
   "type_field": "_type",
   "types": {
    "semantic.movie_openai": {
     "dynamic": true,
     "enabled": true,
     "properties": {
      "IMDB_Rating": {
       "enabled": true,
       "dynamic": false,
       "fields": [
        {
         "index": true,
         "name": "IMDB_Rating",
         "store": true,
         "type": "number"
        }
       ]
      },
      "Overview": {
       "enabled": true,
       "dynamic": false,
       "fields": [
        {
         "analyzer": "en",
         "index": true,
         "name": "Overview",
         "store": true,
         "type": "text"
        }
       ]
      },
      "Overview_embedding": {
       "enabled": true,
       "dynamic": false,
       "fields": [
        {
         "dims": 1536,
         "index": true,
         "name": "Overview_embedding",
         "similarity": "dot_product",
         "type": "vector",
         "vector_index_optimized_for": "recall"
        }
       ]
      },
      "Overview_ko": {
       "enabled": true,
       "dynamic": false,
       "fields": [
        {
         "analyzer": "cjk",
         "index": true,
         "name": "Overview_ko",
         "store": true,
         "type": "text"
        }
       ]
      },
      "Poster_Link": {
       "enabled": true,
       "dynamic": false,
       "fields": [
        {
         "analyzer": "en",
         "index": true,
         "name": "Poster_Link",
         "store": true,
         "type": "text"
        }
       ]
      },
      "Released_Year": {
       "enabled": true,
       "dynamic": false,
       "fields": [
        {
         "index": true,
         "name": "Released_Year",
         "store": true,
         "type": "number"
        }
       ]
      },
      "Runtime": {
       "enabled": true,
       "dynamic": false,
       "fields": [
        {
         "analyzer": "en",
         "index": true,
         "name": "Runtime",
         "store": true,
         "type": "text"
        }
       ]
      },
      "Series_Title": {
       "enabled": true,
       "dynamic": false,
       "fields": [
        {
         "analyzer": "keyword",
         "index": true,
         "name": "Series_Title",
         "store": true,
         "type": "text"
        }
       ]
      }
     }
    }
   }
  },
  "store": {
   "indexType": "scorch",
   "segmentVersion": 16
  }
 },
 "sourceType": "gocbcore",
 "sourceName": "travel-sample",
 "sourceParams": {},
 "planParams": {
  "maxPartitionsPerPIndex": 4,
  "indexPartitions": 16,
  "numReplicas": 0
 }
}
```

- #### Ingest the Documents

  For this demo, we are using the [IMDB dataset from Kaggle](https://www.kaggle.com/datasets/harshitshankhdhar/imdb-dataset-of-top-1000-movies-and-tv-shows). You can download the CSV file, `imdb_top_1000.csv` to the source folder or use the one provided in the repo.

  To ingest the documents including generating the embeddings for the Overview field, you can run the script, `ingest.py`

  `python ingest.py`

- #### Run the application

  `streamlit run hybrid_search.py`
