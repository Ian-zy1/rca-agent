"""
D1 验证脚本：一次性检查硅基流动三项能力。
用法：
  1. 在 app/.env 写入 SILICONFLOW_API_KEY=sk-xxx
  2. app/.venv/bin/python app/verify_d1.py
"""
import os
import sys
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
api_key = os.environ.get("SILICONFLOW_API_KEY")
if not api_key or api_key.startswith("sk-xxx"):
    print("❌ 未找到有效 SILICONFLOW_API_KEY")
    print("   请先创建 app/.env 并写入：SILICONFLOW_API_KEY=你的真实key")
    sys.exit(1)

client = OpenAI(api_key=api_key, base_url="https://api.siliconflow.cn/v1")
MODEL = "deepseek-ai/DeepSeek-V3"
results = {"chat": False, "fc": False, "emb": False}

print("\n=== ① Chat 测试（DeepSeek-V3）===")
try:
    r = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": "用一句话解释 PodOOMKilled"}],
    )
    print("✅ Chat OK：", r.choices[0].message.content[:100])
    results["chat"] = True
except Exception as e:
    print("❌ Chat 失败：", repr(e)[:200])

print("\n=== ② Function Calling 测试（D3 命门）===")
try:
    tools = [{
        "type": "function",
        "function": {
            "name": "query_prometheus",
            "description": "查询 Prometheus 指标，返回某个时间序列的值",
            "parameters": {
                "type": "object",
                "properties": {"promql": {"type": "string", "description": "PromQL 查询语句"}},
                "required": ["promql"],
            },
        },
    }]
    r = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": "帮我查一下 order-service 的内存使用情况"}],
        tools=tools,
        tool_choice="auto",
    )
    msg = r.choices[0].message
    if msg.tool_calls:
        tc = msg.tool_calls[0]
        print(f"✅ FC OK：模型调用了 {tc.function.name}，参数 {tc.function.arguments}")
        results["fc"] = True
    else:
        print("⚠️ FC 未触发 tool_call，模型直接回答：", (msg.content or "")[:100])
        print("   → 尝试在 prompt 里更明确要求调用工具，或换 deepseek-ai/DeepSeek-V2.5")
except Exception as e:
    print("❌ FC 失败：", repr(e)[:200])

print("\n=== ③ Embeddings 测试（bge-m3，D4 命门）===")
for emb_model in ["BAAI/bge-m3", "bge-m3"]:
    try:
        r = client.embeddings.create(model=emb_model, input="Pod 内存泄漏导致 OOM")
        dim = len(r.data[0].embedding)
        print(f"✅ Embeddings OK（model={emb_model}）：维度 {dim}")
        results["emb"] = True
        break
    except Exception as e:
        print(f"❌ Embeddings 失败（model={emb_model}）：", repr(e)[:200])

print("\n" + "=" * 40)
passed = sum(results.values())
print(f"结果：{passed}/3 通过")
for k, v in results.items():
    print(f"  {'✅' if v else '❌'} {k}")
if passed == 3:
    print("\n🎉 三盏全绿，D1 大胜，底座确认，明天按计划走 D2。")
elif results["chat"] and not (results["fc"] or results["emb"]):
    print("\n⚠️ chat 通但 FC/embeddings 有问题，把上面报错发我，换备选方案。")
else:
    print("\n⚠️ 有红灯，把报错原样发我。")
