import os

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()
client = OpenAI(
    api_key=os.environ["SILICONFLOW_API_KEY"],
    base_url="https://api.siliconflow.cn/v1"
)


class RCAReport(BaseModel):
    root_cause: str
    confidence: float
    evidence: list[str]
    suggestion: str


system_prompt = """你是运维根因分析助手。规则：
1.遇到"频繁重启 / OOM"类问题，优先排查内存（不是CPU）
2.必须输出JSON，格式：{"root_cause":"","confidence":0.0,"evidence":[],"suggestion":""}
只输出JSON，不要任何解释或markdown。"""

r = client.chat.completions.create(
    model="deepseek-ai/DeepSeek-V3",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "order-service频繁重启，内存 510Mi/limit 512Mi，已重启 7 次"}
    ],
    response_format={"type": "json_object"}
)

print("【原始返回】")
print(r.choices[0].message.content)

report = RCAReport.model_validate_json(r.choices[0].message.content)
print("\n 【解析成python对象】")
print("根因：", report.root_cause)
print("置信度：", report.confidence)
print("证据：", report.evidence)
print("建议：", report.suggestion)
