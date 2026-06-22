#!/usr/bin/env python3
"""Markdown → HTML 转换器(深色主题,自包含)"""
import os, glob, re

try:
    import markdown
except ImportError:
    os.system(f"python3 -m pip install markdown pygments --quiet")
    import markdown

CSS = """
:root {
  --bg:#0b1220; --bg2:#0f172a; --card:#1e293b; --border:#334155;
  --text:#e2e8f0; --dim:#94a3b8; --blue:#3b82f6; --cyan:#06b6d4;
  --green:#10b981; --amber:#f59e0b; --red:#ef4444; --purple:#8b5cf6;
}
*{box-sizing:border-box;margin:0;padding:0}
body{
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
  background:var(--bg);color:var(--text);line-height:1.75;font-size:15px;
  max-width:920px;margin:0 auto;padding:32px 24px 80px;
}
h1{color:#60a5fa;font-size:28px;border-bottom:2px solid var(--border);padding-bottom:12px;margin:24px 0 20px}
h2{color:#7dd3fc;font-size:22px;margin:36px 0 16px;padding-bottom:8px;border-bottom:1px solid var(--border)}
h3{color:var(--text);font-size:18px;margin:28px 0 12px}
h4{color:var(--amber);font-size:16px;margin:24px 0 10px}
p{margin:10px 0}
code{
  background:var(--card);padding:2px 7px;border-radius:4px;
  font-family:"SF Mono",Consolas,Monaco,monospace;font-size:0.88em;color:#f0abfc;
  border:1px solid var(--border);
}
pre{
  background:var(--bg2);padding:16px 20px;border-radius:8px;
  border:1px solid var(--border);overflow-x:auto;margin:14px 0;
}
pre code{background:none;border:none;padding:0;color:var(--text);font-size:0.85em}
table{border-collapse:collapse;width:100%;margin:16px 0;font-size:14px;display:block;overflow-x:auto}
th,td{border:1px solid var(--border);padding:8px 14px;text-align:left}
th{background:var(--card);color:#7dd3fc;font-weight:600;white-space:nowrap}
tr:nth-child(even){background:rgba(30,41,59,0.4)}
blockquote{
  border-left:3px solid var(--blue);margin:16px 0;padding:10px 18px;
  background:rgba(59,130,246,0.06);border-radius:0 6px 6px 0;color:var(--dim);
}
blockquote p{margin:4px 0}
a{color:#60a5fa;text-decoration:none}
a:hover{text-decoration:underline}
ul,ol{padding-left:28px;margin:10px 0}
li{margin:5px 0}
hr{border:none;border-top:1px solid var(--border);margin:36px 0}
strong{color:#fcd34d;font-weight:600}
em{color:#a5f3fc}
del{color:var(--dim)}
/* Pygments code highlight (friendly dark) */
.codehilite{background:var(--bg2);border-radius:8px;border:1px solid var(--border);margin:14px 0;overflow-x:auto}
.codehilite pre{background:none;border:none;margin:0}
.codehilite .k{color:#c792ea}
.codehilite .s{color:#c3e88d}
.codehilite .n{color:#eeffff}
.codehilite .o{color:#89ddff}
.codehilite .c{color:#546e7a;font-style:italic}
.codehilite .nf{color:#82aaff}
.codehilite .nc{color:#ffcb6b}
.codehilite .nb{color:#f78c6c}
.codehilite .m{color:#f78c6c}
.codehilite .err{color:#ff5572}
/* Anchor links */
h1,h2,h3,h4{scroll-margin-top:20px}
/* Scrollbar */
::-webkit-scrollbar{width:8px;height:8px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:4px}
"""

TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>{css}</style>
</head>
<body>
{nav}
{content}
</body>
</html>"""

NAV = """
<div style="margin-bottom:24px;padding:10px 16px;background:var(--card);border:1px solid var(--border);border-radius:8px;font-size:13px">
  <a href="day0-ai-glossary.html">📖 术语表</a> · 
  <a href="day0-langchain-langgraph-overview.html">⚙️ LangChain/LangGraph</a> · 
  <a href="reference-alibaba-rca.html">🏢 阿里RCA参考</a> · 
  <a href="../../demo/index.html">🎮 Demo演示</a>
</div>
"""

def convert(base, filename):
    md_path = os.path.join(base, filename)
    with open(md_path, "r", encoding="utf-8") as f:
        text = f.read()
    
    title_match = re.search(r'^#\s+(.+)$', text, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else filename
    
    html_body = markdown.markdown(
        text,
        extensions=['tables', 'fenced_code', 'codehilite', 'toc', 'sane_lists'],
        extension_configs={'codehilite': {'css_class': 'codehilite'}}
    )
    
    full = TEMPLATE.format(
        title=title,
        css=CSS,
        nav=NAV,
        content=html_body
    )
    
    out_name = filename.replace('.md', '.html')
    out_path = os.path.join(base, out_name)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(full)
    
    return out_name

if __name__ == '__main__':
    base = '/Users/yongzhao/rca-agent/knowledge/001'
    md_files = sorted(glob.glob(os.path.join(base, '*.md')))
    
    print(f"Found {len(md_files)} markdown files")
    for md_file in md_files:
        fname = os.path.basename(md_file)
        out = convert(base, fname)
        print(f"  ✓ {fname} → {out}")
    
    print(f"\nDone! Open: file://{base}/day0-ai-glossary.html")
