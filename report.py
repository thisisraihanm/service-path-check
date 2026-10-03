"""Escaped, local reports with a plain-language overview and optional IT details."""
import html
import json
from pathlib import Path
from friendly import explain


def write_report(result, output, title):
    base = Path(output)
    base.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False)
    base.with_suffix('.json').write_text(data + '\n', encoding='utf-8')
    esc = lambda value: html.escape(str(value))
    headline, meaning, action = explain(result, title)
    rows = ''.join('<tr><td>' + '</td><td>'.join(esc(row.get(k, '')) for k in ('status', 'item', 'evidence', 'next_step')) + '</td></tr>' for row in result.get('findings', []))
    status = result.get('status', 'incomplete')
    color = 'good' if status in ('pass', 'verified', 'unchanged') else 'review'
    demo = '<p class="demo">EXAMPLE REPORT · Fictional data. This is not a check of your own computer or files.</p>' if result.get('demo') else ''
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>
body{{font:17px/1.6 system-ui,sans-serif;background:#f1f5f9;color:#173144;margin:0}}
main{{max-width:980px;margin:32px auto;padding:32px;background:white;border-radius:14px}}
.eyebrow{{font-size:13px;letter-spacing:.08em;color:#175e65}}h1{{line-height:1.15;font-size:32px;margin:12px 0}}h2{{font-size:19px;margin-bottom:4px}}
.result{{padding:22px;border-radius:10px;border-left:6px solid #bc7612;background:#fff7e8}}.good{{border-color:#218367;background:#ecf8f2}}
.result strong{{font-size:25px;line-height:1.25;display:block}}.demo{{background:#e7eefb;padding:12px;border-radius:8px;font-weight:600}}
.note{{color:#536675;font-size:14px}}details{{margin-top:26px;border-top:1px solid #dce3e8;padding-top:16px}}summary{{cursor:pointer;font-weight:600}}
table{{border-collapse:collapse;width:100%;margin-top:16px}}th,td{{padding:10px;text-align:left;vertical-align:top;border-bottom:1px solid #dce3e8;overflow-wrap:anywhere}}
pre{{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}}.table{{overflow:auto}}
@media(max-width:650px){{main{{margin:0;padding:20px}}h1{{font-size:27px}}.result strong{{font-size:22px}}}}
@media print{{body{{background:white}}main{{margin:0;padding:10px}}}}
</style><main><p class="eyebrow">RAIHAN TOOLS / LOCAL REPORT</p><h1>{title}</h1>{demo}
<section class="result {color}"><strong>{headline}</strong><p>{meaning}</p></section>
<h2>What you can do next</h2><p>{action}</p>
<p class="note">Checked at {timestamp}. Original files and settings were not changed.</p>
<p class="note">Reports may contain server or file names. Share with your IT support when needed.</p>
<details><summary>Details for IT support</summary><p><strong>{status}</strong> — {summary}</p><div class="table">
<table><thead><tr><th>Status</th><th>Item</th><th>Evidence</th><th>Next step</th></tr></thead><tbody>{rows}</tbody></table></div>
<details><summary>Full evidence</summary><pre>{data}</pre></details></details></main></html>'''.format(
        title=esc(title),demo=demo,color=color,headline=esc(headline),meaning=esc(meaning),action=esc(action),
        timestamp=esc(result['timestamp']),status=esc(status),summary=esc(result['summary']),rows=rows,data=esc(data))
    base.with_suffix('.html').write_text(page, encoding='utf-8')
    return base.with_suffix('.html')
