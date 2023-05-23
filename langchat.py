from datetime import datetime
import numpy as np
import openai
from elasticsearch import Elasticsearch

# 实例化 Elasticsearch 客户端
es = Elasticsearch(hosts=["http://localhost:9200"])


#  查询相关的文本内容
def query_vector_to_string(query_vector, content_owner):
    # 定义查询
    query_body = {
        "size": 5,
        "query": {
            "function_score": {
                "query": {
                    "match": {
                        "content_owner": content_owner
                    }
                },
                "score_mode": "sum",
                "boost_mode": "replace",
                "functions": [
                    {
                        "filter": {"match_all": {}},
                        "exp": {
                            "content_last_access_time": {
                                "scale": "10m",
                                "decay": 0.99
                            }
                        }
                    },
                    {
                        "filter": {"match_all": {}},
                        "field_value_factor": {
                            "field": "content_importance",
                            "missing": 0
                        }
                    },
                    {
                        "filter": {"match_all": {}},
                        "script_score": {
                            "script": {
                                "source": "cosineSimilarity(params.query_vector, 'content_vector') + 1.0",
                                "params": {
                                    "query_vector": query_vector
                                }
                            }
                        }
                    }
                ]
            }
        }
    }
    # 执行查询
    return es.search(index="lang_chat_content", body=query_body)


# 插入文档
def insert_document(content_node_id, parent_id, creator_ip, content_owner, creator, content, importance):
    # 使用OpenAI的embedding生成向量
    print("insert_document start")
    try:
        embedding = openai.Embedding.create(input=content, model="text-embedding-ada-002")
        content_vector = np.array(embedding.result).tolist()

        # 获取当前时间
        current_time = datetime.now()

        # 创建文档
        doc = {
            "content_node_id": content_node_id,
            "content_leaf_depth": 0,  # 这里假设叶子深度为0，你可以根据需要进行修改
            "content_creator": creator,  # 这里假设内容创建者为"creator"，你可以根据需要进行修改
            "content_creation_time": current_time,
            "content_last_access_time": current_time,
            "generated_content": content,
            "content_importance": importance,
            "content_type": 1,
            "content_vector": content_vector,
            "content_owner": content_owner,
            "creator_ip": creator_ip,
            "parent_id": parent_id
        }
        docId = content_owner + "_" + content_node_id
        # 插入文档
        res = es.index(index="lang_chat_content", body=doc, id=docId)

        return res
    except Exception as e:
        print(e)
    finally:
        print("insert_document finished")
