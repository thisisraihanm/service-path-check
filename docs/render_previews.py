"""Render real local demo HTML as documentation images, without a browser."""
from pathlib import Path
from weasyprint import HTML, CSS
import fitz

ROOT = Path(__file__).resolve().parent
if ROOT.name != 'docs':
    raise SystemExit('Place this script in the repository docs directory.')

def deny_external(url, *args, **kwargs):
    raise ValueError('External resources are not needed for this self-contained report.')

base = '''
@page { size: 1280px 1900px; margin: 0; }
body { margin: 0 !important; background: #f1f5f9 !important; font-family: DejaVu Sans, sans-serif !important; }
main { max-width: 1120px !important; margin: 26px auto !important; padding: 32px !important; }
details details { display: none; }
summary { list-style: none; }
table { table-layout: fixed; }
th, td { font-size: 15px !important; overflow-wrap: break-word !important; }
th:nth-child(1) { width: 90px; }
th:nth-child(2) { width: 170px; }
'''
for variant in ('overview','details'):
    css = base + ('details { display: none; }' if variant == 'overview' else 'details { display: block; }')
    document = HTML(filename=str(ROOT/'demo-report.html'), url_fetcher=deny_external).render(stylesheets=[CSS(string=css)])
    # Measure the rendered report so the image contains no unused page below it.
    main = next(b for b in document.pages[0]._page_box.descendants() if b.element_tag == 'main')
    height = int(main.position_y + main.margin_height() + 20)
    if len(document.pages) != 1 or height > 1900:
        raise RuntimeError('Report exceeds the preview canvas; review layout before publishing.')
    css += f'\n@page {{ size: 1280px {height}px; }}'
    pdf = HTML(filename=str(ROOT/'demo-report.html'), url_fetcher=deny_external).write_pdf(stylesheets=[CSS(string=css)])
    with fitz.open(stream=pdf, filetype='pdf') as rendered:
        page = rendered[0]
        page.get_pixmap(matrix=fitz.Matrix(4/3,4/3), alpha=False).save(ROOT/f'images/report-{variant}.png')
    print(f'Created images/report-{variant}.png')
