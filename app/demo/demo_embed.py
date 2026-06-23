import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(
    api_key=os.environ["SILICONFLOW_API_KEY"],
    base_url="https://api.siliconflow.cn/v1"
)


def embed(text):
    r = client.embeddings.create(
        model="BAAI/bge-m3", input=text
    )
    return r.data[0].embedding


v1 = embed("Pod 内存泄漏导致 OOM")
v2 = embed("容器内存溢出被杀")
v3 = embed("数据库慢查询")

print("向量维度: ", len(v1))
print("前5个数:", v1[:5])


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


print("OOM vs 内存溢出 相似度 :", round(dot(v1, v2), 2))
print("OOM vs 慢查询 相似度 :", round(dot(v1, v3), 2))
