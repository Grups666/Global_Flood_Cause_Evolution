from __future__ import annotations

import argparse
import base64
import html
import json
import re
import shutil
from pathlib import Path

import markdown


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "reports" / "global_flood_cause_evolution.md"
DESTINATION = ROOT / "reports" / "global_flood_cause_evolution.html"
PUBLIC_REPORT = ROOT / "public" / "reports" / "global_flood_cause_evolution.html"
PUBLIC_ASSETS = ROOT / "public" / "reports" / "assets"


def _embed_images(source: str, source_dir: Path) -> str:
    pattern = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")

    def replace(match: re.Match[str]) -> str:
        alt, target = match.groups()
        path = (source_dir / target).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Report image not found: {path}")
        mime = "image/svg+xml" if path.suffix.lower() == ".svg" else "image/png"
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"![{alt}](data:{mime};base64,{encoded})"

    return pattern.sub(replace, source)


def _neutralize_local_links(source: str) -> str:
    pattern = re.compile(r"(?<!!)\[([^\]]+)\]\((?!https?://|mailto:)([^)]+)\)")

    def replace(match: re.Match[str]) -> str:
        label, target = match.groups()
        return (
            f'<span class="local-reference" title="Project path: '
            f'{html.escape(target)}">{label}</span>'
        )

    return pattern.sub(replace, source)


def build_html_report(
    source: Path = SOURCE, destination: Path = DESTINATION
) -> dict[str, object]:
    markdown_source = source.read_text(encoding="utf-8")
    analysis_summary = json.loads((ROOT / "outputs" / "logs" / "analysis_summary.json").read_text(encoding="utf-8"))
    local_summary = json.loads((ROOT / "outputs" / "logs" / "local_analysis_summary.json").read_text(encoding="utf-8"))
    primary = analysis_summary["sample_counts"]["pot_q95"]
    expected_images = len(re.findall(r"!\[[^\]]*\]\([^)]+\)", markdown_source))
    markdown_source = _embed_images(markdown_source, source.parent)
    markdown_source = _neutralize_local_links(markdown_source)
    converter = markdown.Markdown(
        extensions=["extra", "sane_lists", "toc"],
        extension_configs={"toc": {"toc_depth": "2-3", "permalink": False}},
        output_format="html5",
    )
    article = converter.convert(markdown_source)
    if article.count("data:image/") != expected_images:
        raise RuntimeError("Not all report figures were embedded")

    document = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>全球降雨型大洪水生成条件的局地演变（1982–2019）</title>
  <style>
    :root {{ --ink:#233143; --muted:#647487; --line:#dce4ea; --paper:#fff; --canvas:#f2f6f8; --blue:#2f6688; --cyan:#22d3ee; --orange:#cf673f; --shadow:0 18px 54px rgba(28,43,58,.10); }}
    * {{ box-sizing:border-box; }} html {{ scroll-behavior:smooth; }}
    body {{ margin:0; color:var(--ink); background:var(--canvas); font:16px/1.78 Inter,"Noto Sans SC","Microsoft YaHei",system-ui,sans-serif; text-rendering:optimizeLegibility; }}
    #progress {{ position:fixed; inset:0 auto auto 0; z-index:30; width:0; height:3px; background:linear-gradient(90deg,var(--blue),var(--cyan),var(--orange)); }}
    .shell {{ max-width:1480px; margin:auto; padding:24px; display:grid; grid-template-columns:275px minmax(0,1fr); gap:28px; }}
    aside {{ position:sticky; top:24px; align-self:start; max-height:calc(100vh - 48px); overflow:auto; padding:6px; }}
    .brand {{ padding:4px 4px 16px; margin-bottom:14px; border-bottom:1px solid var(--line); }} .brand strong,.brand span {{ display:block; }} .brand strong {{ font-size:13px; letter-spacing:.08em; text-transform:uppercase; }} .brand span {{ margin-top:3px; color:var(--muted); font-size:12px; }}
    .toc ul {{ list-style:none; margin:0; padding:0; }} .toc ul ul {{ margin:4px 0 8px 11px; padding-left:11px; border-left:1px solid var(--line); }} .toc a {{ display:block; padding:6px 9px; border-radius:8px; color:var(--muted); font-size:13px; line-height:1.4; text-decoration:none; }} .toc a:hover,.toc a.active {{ color:var(--blue); background:#e6f0f5; }}
    .actions {{ display:flex; gap:8px; margin-top:16px; }} button {{ padding:8px 11px; border:1px solid var(--line); border-radius:9px; background:#fff; color:var(--ink); font:12px Inter,system-ui; cursor:pointer; }} button:hover {{ color:var(--blue); border-color:var(--blue); }}
    article {{ min-width:0; padding:58px clamp(30px,5.5vw,86px) 80px; border-radius:18px; background:var(--paper); box-shadow:var(--shadow); }}
    .facts {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin:0 0 40px; }} .fact {{ padding:16px 18px; border:1px solid var(--line); border-radius:12px; background:linear-gradient(145deg,#e9f2f6,#fff); }} .fact b,.fact span {{ display:block; }} .fact b {{ color:var(--blue); font-size:24px; line-height:1.1; }} .fact span {{ margin-top:4px; color:var(--muted); font-size:12px; }}
    h1 {{ max-width:1020px; margin:0 0 8px; font-size:clamp(34px,5vw,57px); line-height:1.14; letter-spacing:-.035em; }} h1+p {{ margin-top:0; color:var(--muted); font-size:14px; }}
    h2 {{ margin:70px 0 22px; padding-top:9px; border-top:1px solid var(--line); font-size:29px; line-height:1.3; letter-spacing:-.02em; }} h3 {{ margin:40px 0 15px; font-size:22px; line-height:1.35; }} p {{ margin:14px 0; }} ul,ol {{ padding-left:1.35em; }} li {{ margin:7px 0; }} strong {{ color:#172536; }}
    blockquote {{ margin:28px 0; padding:18px 22px; border-left:4px solid var(--orange); border-radius:0 12px 12px 0; background:#f8eee8; font-size:18px; }}
    code {{ padding:2px 6px; border-radius:5px; background:#eef2f5; color:#984a30; font:.88em "Cascadia Code",Consolas,monospace; }} pre {{ overflow:auto; padding:18px; border-radius:12px; background:#1f2b3a; color:#eef3f7; }} pre code {{ padding:0; background:transparent; color:inherit; }}
    a {{ color:var(--blue); text-underline-offset:3px; }} .local-reference {{ color:var(--muted); border-bottom:1px dotted #97a6b3; cursor:help; }}
    article img {{ display:block; width:min(100%,1180px); height:auto; margin:28px auto 38px; border:1px solid var(--line); border-radius:14px; background:#fff; box-shadow:0 12px 34px rgba(36,49,66,.08); cursor:zoom-in; }} article img:focus-visible {{ outline:3px solid rgba(34,211,238,.6); outline-offset:4px; }}
    .lightbox {{ position:fixed; inset:0; z-index:100; display:none; align-items:center; justify-content:center; padding:28px; background:rgba(16,25,36,.9); backdrop-filter:blur(8px); }} .lightbox.open {{ display:flex; }} body.lightbox-open {{ overflow:hidden; }} .lightbox figure {{ display:flex; flex-direction:column; align-items:center; gap:10px; max-width:97vw; max-height:95vh; margin:0; }} .lightbox img {{ max-width:97vw; max-height:calc(95vh - 40px); object-fit:contain; border-radius:10px; background:white; box-shadow:0 22px 70px rgba(0,0,0,.4); }} .lightbox figcaption {{ color:#eef3f7; font-size:13px; }} .lightbox-close {{ position:fixed; top:18px; right:20px; width:42px; height:42px; padding:0; border-color:rgba(255,255,255,.4); border-radius:50%; background:rgba(18,27,38,.75); color:#fff; font-size:25px; }}
    table {{ width:100%; margin:24px 0; border-collapse:collapse; font-size:14px; }} th,td {{ padding:10px 12px; border-bottom:1px solid var(--line); text-align:left; }} th {{ color:var(--muted); background:#f7f9fa; }} .mobile-bar {{ display:none; }}
    @media(max-width:900px) {{ .shell {{ display:block; padding:0; }} aside {{ display:none; }} article {{ padding:70px 20px 56px; border-radius:0; }} .mobile-bar {{ position:fixed; inset:0 0 auto; z-index:20; display:flex; height:50px; padding:8px 12px; align-items:center; justify-content:space-between; border-bottom:1px solid var(--line); background:rgba(255,255,255,.95); backdrop-filter:blur(10px); }} .facts {{ grid-template-columns:1fr 1fr; }} h2 {{ margin-top:54px; font-size:25px; }} }}
    @media print {{ body {{ background:#fff; font-size:10.5pt; }} #progress,aside,.mobile-bar,.lightbox {{ display:none!important; }} .shell {{ display:block; max-width:none; padding:0; }} article {{ padding:0; box-shadow:none; }} h2 {{ break-before:page; margin-top:0; }} h3,img,table,blockquote {{ break-inside:avoid; }} article img {{ box-shadow:none; max-height:225mm; object-fit:contain; }} }}
  </style>
</head>
<body>
  <div id="progress"></div>
  <div class="mobile-bar"><strong>Global Flood Cause Evolution</strong><button onclick="window.print()">打印 / PDF</button></div>
  <div class="lightbox" id="lightbox" role="dialog" aria-modal="true" aria-label="图表大图" aria-hidden="true"><button class="lightbox-close" aria-label="关闭大图">×</button><figure><img alt=""><figcaption></figcaption></figure></div>
  <div class="shell">
    <aside><div class="brand"><strong>Research report</strong><span>完整实验 · 2026-09-01</span></div><nav class="toc" aria-label="目录">{converter.toc}</nav><div class="actions"><button onclick="window.print()">打印 / PDF</button><button onclick="scrollTo(0,0)">回到顶部</button></div></aside>
    <article><div class="facts"><div class="fact"><b>{primary['events']:,}</b><span>POT/Q95 极端事件</span></div><div class="fact"><b>{primary['catchments']:,}</b><span>合格长期观测流域</span></div><div class="fact"><b>{local_summary['strong_evidence_basins']}</b><span>具有强证据的水文区</span></div><div class="fact"><b>{local_summary['strong_evidence_signals']}</b><span>强证据机制信号</span></div></div>{article}</article>
  </div>
  <script>
    const progress=document.getElementById('progress'); const links=[...document.querySelectorAll('.toc a')]; const sections=links.map(a=>document.getElementById(a.getAttribute('href').slice(1))).filter(Boolean);
    function update(){{const h=document.documentElement.scrollHeight-innerHeight;progress.style.width=(h>0?scrollY/h*100:0)+'%';let current=sections[0];for(const section of sections)if(section.getBoundingClientRect().top<140)current=section;links.forEach(a=>a.classList.toggle('active',current&&a.getAttribute('href')==='#'+current.id));}} addEventListener('scroll',update,{{passive:true}});update();
    const box=document.getElementById('lightbox'),large=box.querySelector('img'),caption=box.querySelector('figcaption'),close=box.querySelector('.lightbox-close');let trigger=null;
    function openFigure(image){{trigger=image;large.src=image.src;large.alt=image.alt||'报告图表';caption.textContent=image.alt||'';box.classList.add('open');box.setAttribute('aria-hidden','false');document.body.classList.add('lightbox-open');close.focus();}}
    function closeFigure(){{box.classList.remove('open');box.setAttribute('aria-hidden','true');document.body.classList.remove('lightbox-open');large.removeAttribute('src');trigger?.focus();}}
    document.querySelectorAll('article img').forEach(image=>{{image.tabIndex=0;image.setAttribute('role','button');image.setAttribute('aria-label','点击查看大图：'+(image.alt||'报告图表'));image.addEventListener('click',()=>openFigure(image));image.addEventListener('keydown',event=>{{if(event.key==='Enter'||event.key===' '){{event.preventDefault();openFigure(image);}}}});}});close.addEventListener('click',closeFigure);box.addEventListener('click',event=>{{if(event.target===box)closeFigure();}});addEventListener('keydown',event=>{{if(event.key==='Escape'&&box.classList.contains('open'))closeFigure();}});
  </script>
</body>
</html>"""
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(document, encoding="utf-8")
    if source == SOURCE and destination == DESTINATION:
        PUBLIC_REPORT.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(destination, PUBLIC_REPORT)
        PUBLIC_ASSETS.mkdir(parents=True, exist_ok=True)
        for figure in sorted((ROOT / "reports" / "assets").glob("figure_*.png")):
            shutil.copy2(figure, PUBLIC_ASSETS / figure.name)
    return {
        "status": "complete",
        "source": str(source),
        "destination": str(destination),
        "embedded_figures": expected_images,
        "bytes": destination.stat().st_size,
        "public_report": str(PUBLIC_REPORT) if source == SOURCE and destination == DESTINATION else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a self-contained HTML report")
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path, default=DESTINATION)
    args = parser.parse_args()
    print(build_html_report(args.source.resolve(), args.output.resolve()))


if __name__ == "__main__":
    main()
