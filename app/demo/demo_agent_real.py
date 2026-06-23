import json
import os

import requests
import urllib3
from dotenv import load_dotenv
from openai import OpenAI

urllib3.disable_warnings()
load_dotenv()

client = OpenAI(
    api_key=os.environ["SILICONFLOW_API_KEY"],
    base_url="https://api.siliconflow.cn/v1"
)
PROM = os.environ["PROM_URL"].rstrip("/")
AUTH = (os.environ["PROM_USER"], os.environ["PROM_PASS"])


def query_prometheus(promql: str) -> str:
    r = requests.get(f"{PROM}/query", params={"query": promql}, auth=AUTH, verify=False, timeout=15)
    return json.dumps(r.json()["data"]["result"], ensure_ascii=False)[:500]


tools = [{
    "type": "function",
    "function": {
        "name": "query_prometheus",
        "description": "查询VictoriaMetrics指标，可用 instance 标签定位具体主机/服务",
        "parameters": {
            "type": "object",
            "properties": {
                "promql": {
                    "type": "string"
                }
            },
            "required": ["promql"]
        },
    }
}]

messages = [
    {"role": "system", "content": "你是运维RCA助手。需要指标时调用query_prometheus，拿到真实数据后给根因。"},
    {"role": "user", "content": "MySQL 实例 10.3.240.116:19211 慢查询异常多，业务反映下单慢，排查根因"}
]

for i in range(3):
    msg = client.chat.completions.create(
        model="deepseek-ai/DeepSeek-V3",
        messages=messages,
        tools=tools
    ).choices[0].message

    print(f'content: {msg.content}')
    print(f'tool_calls: {[tc.function.name for tc in (msg.tool_calls or [])]}')
    print('\n')
    messages.append(msg)
    if not msg.tool_calls:
        print(f'\n 【最终根因】\n{msg.content}')
        break
    for tc in msg.tool_calls:
        args = json.loads(tc.function.arguments)
        print(f"\n 【第{i + 1}轮】模型要查: {args}")
        result = query_prometheus(args["promql"])
        print(f" 真实返回：{result[:180]}")
        messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
