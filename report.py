"""Local, escaped, dependency-free reports. Never loads remote assets."""
import html
import json
from pathlib import Path


def write_report(result, output, title):
    base = Path(output)
    base.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False)
    base.with_suffix('.json').write_text(data + '\n', encoding='utf-8')
    rows = result.get('findings', [])
    body = ''.join('<tr><td>' + '</td><td>'.join(html.escape(str(row.get(k, ''))) for k in ('status', 'item', 'evidence', 'next_step')) + '</td></tr>' for row in rows)
    page = '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>
body{{font:16px/1.6 system-ui,sans-serif;background:#f5f7fb;color:#16283c;margin:0}}
main{{max-width:1100px;margin:40px auto;padding:28px;background:white;border-radius:12px}}
h1{{line-height:1.2}}.summary{{padding:16px;background:#e9f0fa;border-left:4px solid #2865b0}}
table{{border-collapse:collapse;width:100%;margin-top:24px}}th,td{{padding:12px;text-align:left;vertical-align:top;border-bottom:1px solid #d9e2ec;overflow-wrap:anywhere}}
pre{{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}}details{{margin-top:24px}}
@media(max-width:700px){{main{{margin:0;padding:16px}}table{{display:block;overflow-x:auto}}}}
</style><main><p>LOCAL OPERATIONS REPORT · {timestamp}</p><h1>{title}</h1>
<p class="summary"><strong>{status}</strong> — {summary}</p>
<table><thead><tr><th>Status</th><th>Item</th><th>Evidence</th><th>Next step</th></tr></thead><tbody>{body}</tbody></table>
<details><summary>Full evidence (JSON)</summary><pre>{data}</pre></details>
<p>Generated locally. Review evidence before making changes.</p></main></html>'''.format(title=html.escape(title), timestamp=html.escape(result['timestamp']), status=html.escape(result['status']), summary=html.escape(result['summary']), body=body, data=html.escape(data))
    base.with_suffix('.html').write_text(page, encoding='utf-8')
    return base.with_suffix('.html')
