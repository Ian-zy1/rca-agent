import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(
    api_key=os.environ["SILICONFLOW_API_KEY"],
    base_url="https://api.siliconflow.cn/v1"
)

tools = [{
    "type": "function",
    "function": {
        "name": "query_prometheus",
        "description": "查询Prometeus监控指标",
        "parameters": {
            "type": "object",
            "properties": {
                "promql": {
                    "type": "string",
                    "description": "PromQL查询语句"
                }
            },
            "required": ["promql"]
        }
    }
}]

msg = client.chat.completions.create(
    model="deepseek-ai/DeepSeek-V3",
    messages=[
        {"role": "user", "content": "帮我查 order-service的内存使用情况"},
    ],
    tools=tools
).choices[0].message

if msg.tool_calls:
    tc = msg.tool_calls[0]
    print("模型决定调用:", tc.function.name)
    print("它自己生存的PromQL:", tc.function.arguments)

else:
    print("模型直接回答:", msg.content)
