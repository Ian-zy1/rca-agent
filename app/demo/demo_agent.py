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

messages = [
    {"role": "system", "content": "你是运维根因分析助手。需要指标数据时调用 query_prometheus，拿到数据后给出根因。"},
    {"role": "user", "content": "order-service 频繁重启，帮我排查根因"},
]

r1 = client.chat.completions.create(
    model="deepseek-ai/DeepSeek-V3",
    messages=messages,
    tools=tools,
).choices[0].message

messages.append(r1)

if r1.tool_calls:
    tc = r1.tool_calls[0]
    print("【第一轮】模型要查：", tc.function.arguments)

    mock_result = 'container_memory_usage_bytes{container="order-service"} = 510Mi / limit 512Mi, restart_count=7'
    messages.append({"role": "tool", "tool_call_id": tc.id, "content": mock_result})

    r2 = client.chat.completions.create(
        model="deepseek-ai/DeepSeek-V3",
        messages=messages,
        tools=tools,
    ).choices[0].message
    print("\n 【第二轮】模型拿到数据后的根因: \n", r2.content)

else:
    print("模型直接回答:", r1.content)
