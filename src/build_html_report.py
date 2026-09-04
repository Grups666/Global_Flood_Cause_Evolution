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


def _embed_images(source: str, source_dir: Path) -> tuple[str, int]:
    pattern = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
    count = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal count
        alt, target = match.groups()
        path = (source_dir / target).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Report image not found: {path}")
        mime = "image/svg+xml" if path.suffix.lower() == ".svg" else "image/png"
        count += 1
        return f"![{alt}](data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')})"

    return pattern.sub(replace, source), count


def _neutralize_local_links(source: str) -> str:
    pattern = re.compile(r"(?<!!)\[([^\]]+)\]\((?!https?://|mailto:)([^)]+)\)")
    return pattern.sub(
        lambda match: (
            f'<span class="local-reference" title="Project path: '
            f'{html.escape(match.group(2))}">{match.group(1)}</span>'
        ),
        source,
    )


def build_html_report(source: Path = SOURCE, destination: Path = DESTINATION) -> dict[str, object]:
    content, image_count = _embed_images(source.read_text(encoding="utf-8"), source.parent)
    content = _neutralize_local_links(content)
    converter = markdown.Markdown(
        extensions=["extra", "sane_lists", "toc"],
        extension_configs={"toc": {"toc_depth": "2-3"}},
        output_format="html5",
    )
    article = converter.convert(content)
    if article.count("data:image/") != image_count:
        raise RuntimeError("Not all report figures were embedded")

    summary = json.loads((ROOT / "outputs" / "logs" / "analysis_summary.json").read_text(encoding="utf-8"))
    primary = summary["sample_counts"]["pot_q95"]
    facts = [
        (f"{primary['events']:,}", "Q95 大洪水事件"),
        (f"{primary['catchments']:,}", "有长期记录的观测流域"),
        (f"{summary['supported_overall_trends']:,}", "大洪水本身的稳健变化"),
        (f"{summary['supported_mechanism_trends']:,}", "机制特异的稳健变化"),
    ]
    fact_html = "".join(f'<div class="fact"><b>{value}</b><span>{label}</span></div>' for value, label in facts)

    document = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light"><title>降雨驱动型大洪水生成机制的长期变化</title>
<style>
:root{{--ink:#213043;--muted:#65768a;--line:#dce5ea;--paper:#fff;--canvas:#f2f6f8;--blue:#2f6688;--cyan:#19c9de;--orange:#d96b3f}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--canvas);color:var(--ink);font:16px/1.78 Inter,"Noto Sans SC","Microsoft YaHei",system-ui,sans-serif}}
#progress{{position:fixed;z-index:40;inset:0 auto auto 0;height:3px;width:0;background:linear-gradient(90deg,var(--blue),var(--cyan),var(--orange))}}
.shell{{max-width:1500px;margin:auto;padding:24px;display:grid;grid-template-columns:280px minmax(0,1fr);gap:28px}}aside{{position:sticky;top:24px;align-self:start;max-height:calc(100vh - 48px);overflow:auto;padding:8px}}
.brand{{padding:4px 5px 16px;border-bottom:1px solid var(--line);margin-bottom:12px}}.brand strong,.brand span{{display:block}}.brand strong{{font-size:13px;letter-spacing:.08em;text-transform:uppercase}}.brand span{{font-size:12px;color:var(--muted);margin-top:4px}}
.toc ul{{list-style:none;margin:0;padding:0}}.toc ul ul{{margin-left:11px;padding-left:11px;border-left:1px solid var(--line)}}.toc a{{display:block;padding:6px 9px;border-radius:8px;color:var(--muted);font-size:13px;line-height:1.4;text-decoration:none}}.toc a:hover,.toc a.active{{color:#185b75;background:#e5f3f6}}
.actions{{display:flex;gap:8px;margin-top:16px}}button{{padding:8px 11px;border:1px solid var(--line);border-radius:9px;background:#fff;color:var(--ink);cursor:pointer}}
article{{min-width:0;padding:58px clamp(30px,5.2vw,84px) 80px;background:var(--paper);border-radius:18px;box-shadow:0 18px 54px rgba(28,43,58,.1)}}.facts{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:42px}}.fact{{padding:17px 18px;border:1px solid var(--line);border-radius:13px;background:linear-gradient(145deg,#eaf3f6,#fff)}}.fact b,.fact span{{display:block}}.fact b{{font-size:24px;color:var(--blue)}}.fact span{{font-size:12px;color:var(--muted);margin-top:3px}}
h1{{font-size:clamp(35px,5vw,58px);line-height:1.13;letter-spacing:-.035em;margin:0 0 10px}}h1+p{{color:var(--muted)}}h2{{font-size:29px;line-height:1.3;margin:68px 0 22px;padding-top:10px;border-top:1px solid var(--line)}}h3{{font-size:21px;margin:38px 0 13px}}p{{margin:14px 0}}li{{margin:7px 0}}blockquote{{margin:28px 0;padding:18px 22px;border-left:4px solid var(--orange);border-radius:0 12px 12px 0;background:#f9eee8;font-size:18px}}
code{{padding:2px 6px;border-radius:5px;background:#eef2f5;color:#944c33}}pre{{overflow:auto;padding:18px;border-radius:12px;background:#1f2b3a;color:#eef3f7}}pre code{{padding:0;background:none;color:inherit}}a{{color:var(--blue);text-underline-offset:3px}}.local-reference{{color:var(--muted);border-bottom:1px dotted #9ba9b5}}
article img{{display:block;width:min(100%,1180px);height:auto;margin:28px auto 40px;border:1px solid var(--line);border-radius:14px;background:#fff;box-shadow:0 12px 34px rgba(36,49,66,.08);cursor:zoom-in}}table{{width:100%;border-collapse:collapse;margin:24px 0;font-size:14px}}th,td{{padding:10px 12px;border-bottom:1px solid var(--line);text-align:left}}th{{background:#f6f9fa;color:var(--muted)}}
.lightbox{{display:none;position:fixed;z-index:100;inset:0;align-items:center;justify-content:center;padding:28px;background:rgba(14,24,35,.94)}}.lightbox.open{{display:flex}}.lightbox img{{max-width:97vw;max-height:93vh;object-fit:contain;background:#fff;border-radius:10px}}.close{{position:fixed;top:18px;right:20px;width:44px;height:44px;border-color:#71808e;border-radius:50%;background:#172334;color:#fff;font-size:25px}}
@media(max-width:900px){{.shell{{display:block;padding:0}}aside{{display:none}}article{{border-radius:0;padding:55px 20px}}.facts{{grid-template-columns:1fr 1fr}}}}
@media print{{body{{background:#fff}}#progress,aside,.lightbox{{display:none!important}}.shell{{display:block;padding:0}}article{{padding:0;box-shadow:none}}article img{{box-shadow:none}}}}
</style></head><body><div id="progress"></div><div class="lightbox" id="figure-lightbox" aria-hidden="true"><button class="close" aria-label="关闭">×</button><img alt="放大图表"></div>
<div class="shell"><aside><div class="brand"><strong>Research report</strong><span>1982–2019 · gauged catchments</span></div><nav class="toc report-nav">{converter.toc}</nav><div class="actions"><button onclick="window.print()">打印 / PDF</button><button onclick="scrollTo(0,0)">回到顶部</button></div></aside><article><div class="facts">{fact_html}</div>{article}</article></div>
<script>
const progress=document.getElementById('progress'),links=[...document.querySelectorAll('.toc a')],sections=links.map(a=>document.getElementById(a.hash.slice(1))).filter(Boolean);function update(){{const h=document.documentElement.scrollHeight-innerHeight;progress.style.width=(h?scrollY/h*100:0)+'%';let c=sections[0];for(const s of sections)if(s.getBoundingClientRect().top<140)c=s;links.forEach(a=>a.classList.toggle('active',c&&a.hash==='#'+c.id))}}addEventListener('scroll',update,{{passive:true}});update();
const box=document.getElementById('figure-lightbox'),large=box.querySelector('img');function closeBox(){{box.classList.remove('open');box.setAttribute('aria-hidden','true')}}document.querySelectorAll('article img').forEach(img=>{{img.tabIndex=0;const open=()=>{{large.src=img.src;large.alt=img.alt;box.classList.add('open');box.setAttribute('aria-hidden','false')}};img.onclick=open;img.onkeydown=e=>{{if(e.key==='Enter'||e.key===' ')open()}}}});box.querySelector('.close').onclick=closeBox;box.onclick=e=>{{if(e.target===box)closeBox()}};addEventListener('keydown',e=>{{if(e.key==='Escape')closeBox()}});
</script></body></html>"""
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(document, encoding="utf-8")
    if source == SOURCE and destination == DESTINATION:
        PUBLIC_REPORT.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(destination, PUBLIC_REPORT)
        PUBLIC_ASSETS.mkdir(parents=True, exist_ok=True)
        for figure in sorted((ROOT / "reports" / "assets").glob("figure_0[1-6]_*.png")):
            shutil.copy2(figure, PUBLIC_ASSETS / figure.name)
    return {"status": "complete", "embedded_figures": image_count, "bytes": destination.stat().st_size}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path, default=DESTINATION)
    args = parser.parse_args()
    print(build_html_report(args.source.resolve(), args.output.resolve()))


if __name__ == "__main__":
    main()
