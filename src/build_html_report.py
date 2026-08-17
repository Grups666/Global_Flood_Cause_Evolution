from __future__ import annotations

import argparse
import base64
import html
import re
from pathlib import Path

import markdown


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "reports" / "global_flood_cause_evolution.md"
DESTINATION = ROOT / "reports" / "global_flood_cause_evolution.html"


def _embed_images(source: str, source_dir: Path) -> str:
    pattern = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")

    def replace(match: re.Match[str]) -> str:
        alt, target = match.groups()
        path = (source_dir / target).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Report image not found: {path}")
        mime = "image/svg+xml" if path.suffix.lower() == ".svg" else "image/png"
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return f'![{alt}](data:{mime};base64,{encoded})'

    return pattern.sub(replace, source)


def _neutralize_local_links(source: str) -> str:
    pattern = re.compile(r"(?<!!)\[([^\]]+)\]\((?!https?://|mailto:)([^)]+)\)")

    def replace(match: re.Match[str]) -> str:
        label, target = match.groups()
        return f'<span class="local-reference" title="Project path: {html.escape(target)}">{label}</span>'

    return pattern.sub(replace, source)


def build_html_report(source: Path = SOURCE, destination: Path = DESTINATION) -> dict[str, object]:
    markdown_source = source.read_text(encoding="utf-8")
    expected_image_count = len(re.findall(r"!\[[^\]]*\]\([^)]+\)", markdown_source))
    markdown_source = _embed_images(markdown_source, source.parent)
    markdown_source = _neutralize_local_links(markdown_source)

    converter = markdown.Markdown(
        extensions=["extra", "sane_lists", "toc"],
        extension_configs={"toc": {"toc_depth": "2-3", "permalink": False}},
        output_format="html5",
    )
    article = converter.convert(markdown_source)
    toc = converter.toc
    image_count = article.count("data:image/")
    if image_count != expected_image_count:
        raise RuntimeError(
            f"Expected {expected_image_count} embedded figures, found {image_count}"
        )

    document = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>降雨型大洪水成因变化的局地水文区格局（1982–2019）</title>
  <style>
    :root {{
      --ink: #243142;
      --muted: #657181;
      --line: #dce3ea;
      --paper: #ffffff;
      --canvas: #f3f6f8;
      --blue: #33658a;
      --orange: #d97745;
      --pale-blue: #e8f0f5;
      --pale-orange: #f8eee8;
      --shadow: 0 18px 54px rgba(36, 49, 66, .10);
      --radius: 18px;
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      margin: 0;
      color: var(--ink);
      background: var(--canvas);
      font-family: Inter, "Noto Sans SC", "Microsoft YaHei", system-ui, sans-serif;
      font-size: 16px;
      line-height: 1.78;
      text-rendering: optimizeLegibility;
    }}
    #progress {{
      position: fixed; inset: 0 auto auto 0; z-index: 20;
      width: 0; height: 3px; background: linear-gradient(90deg, var(--blue), var(--orange));
    }}
    .shell {{ max-width: 1440px; margin: 0 auto; padding: 24px; display: grid; grid-template-columns: 270px minmax(0, 1fr); gap: 28px; }}
    aside {{ position: sticky; top: 24px; align-self: start; max-height: calc(100vh - 48px); overflow: auto; }}
    .brand {{ margin-bottom: 18px; padding: 6px 6px 15px; border-bottom: 1px solid var(--line); }}
    .brand strong {{ display: block; font-size: 13px; letter-spacing: .08em; text-transform: uppercase; }}
    .brand span {{ color: var(--muted); font-size: 12px; }}
    .toc ul {{ list-style: none; padding-left: 0; margin: 0; }}
    .toc ul ul {{ padding-left: 13px; margin: 4px 0 8px; border-left: 1px solid var(--line); }}
    .toc a {{ display: block; padding: 6px 9px; color: var(--muted); text-decoration: none; border-radius: 8px; font-size: 13px; line-height: 1.4; }}
    .toc a:hover, .toc a.active {{ color: var(--blue); background: var(--pale-blue); }}
    .aside-actions {{ display: flex; gap: 8px; margin-top: 16px; }}
    button {{ border: 1px solid var(--line); background: white; color: var(--ink); border-radius: 9px; padding: 8px 11px; cursor: pointer; font: inherit; font-size: 12px; }}
    button:hover {{ border-color: var(--blue); color: var(--blue); }}
    article {{ background: var(--paper); border-radius: var(--radius); box-shadow: var(--shadow); padding: 64px clamp(28px, 5.5vw, 84px) 80px; min-width: 0; }}
    h1 {{ margin: 0 0 8px; font-size: clamp(34px, 5vw, 58px); line-height: 1.13; letter-spacing: -.035em; max-width: 1000px; }}
    h1 + p {{ margin-top: 0; color: var(--muted); font-size: 14px; letter-spacing: .04em; }}
    h2 {{ margin: 72px 0 22px; padding-top: 8px; font-size: 30px; line-height: 1.28; letter-spacing: -.02em; border-top: 1px solid var(--line); }}
    h3 {{ margin: 42px 0 16px; font-size: 23px; line-height: 1.35; }}
    p {{ margin: 14px 0; }}
    ul, ol {{ padding-left: 1.35em; }}
    li {{ margin: 7px 0; }}
    strong {{ color: #182535; }}
    blockquote {{ margin: 28px 0; padding: 18px 22px; border-left: 4px solid var(--orange); background: var(--pale-orange); border-radius: 0 12px 12px 0; font-size: 18px; }}
    code {{ padding: 2px 6px; border-radius: 5px; background: #eef2f5; color: #9b4a2d; font-family: "Cascadia Code", Consolas, monospace; font-size: .88em; }}
    pre {{ overflow: auto; padding: 18px; background: #1f2b3a; color: #eef3f7; border-radius: 12px; }}
    pre code {{ padding: 0; background: transparent; color: inherit; }}
    a {{ color: var(--blue); text-decoration-thickness: 1px; text-underline-offset: 3px; }}
    .local-reference {{ color: var(--muted); border-bottom: 1px dotted #9ca8b4; cursor: help; }}
    article img {{ display: block; width: 100%; height: auto; margin: 28px auto 38px; border: 1px solid var(--line); border-radius: 14px; background: #fff; box-shadow: 0 12px 34px rgba(36, 49, 66, .08); cursor: zoom-in; }}
    article img:focus-visible {{ outline: 3px solid rgba(51, 101, 138, .42); outline-offset: 4px; }}
    body.lightbox-open {{ overflow: hidden; }}
    .lightbox {{
      position: fixed; inset: 0; z-index: 100; display: none;
      align-items: center; justify-content: center; padding: 28px;
      background: rgba(18, 27, 38, .88); backdrop-filter: blur(8px);
    }}
    .lightbox.open {{ display: flex; }}
    .lightbox-figure {{ margin: 0; max-width: 96vw; max-height: 94vh; display: flex; flex-direction: column; align-items: center; gap: 10px; }}
    .lightbox-image {{ display: block; width: auto; height: auto; max-width: 96vw; max-height: calc(94vh - 38px); object-fit: contain; background: white; border-radius: 10px; box-shadow: 0 22px 70px rgba(0,0,0,.35); }}
    .lightbox-caption {{ color: #eef3f7; font-size: 13px; text-align: center; }}
    .lightbox-close {{
      position: fixed; top: 18px; right: 20px; width: 42px; height: 42px;
      padding: 0; border-radius: 50%; border-color: rgba(255,255,255,.35);
      background: rgba(18,27,38,.72); color: white; font-size: 25px; line-height: 1;
    }}
    .lightbox-close:hover {{ border-color: white; color: white; }}
    table {{ width: 100%; border-collapse: collapse; margin: 24px 0; font-size: 14px; }}
    th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--line); }}
    th {{ color: var(--muted); background: #f7f9fa; }}
    .facts {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 28px 0 44px; }}
    .fact {{ padding: 16px 18px; background: linear-gradient(145deg, var(--pale-blue), #fff); border: 1px solid var(--line); border-radius: 12px; }}
    .fact b {{ display: block; font-size: 24px; line-height: 1.1; color: var(--blue); }}
    .fact span {{ color: var(--muted); font-size: 12px; }}
    .mobile-bar {{ display: none; }}
    @media (max-width: 900px) {{
      .shell {{ display: block; padding: 0; }}
      aside {{ display: none; }}
      article {{ border-radius: 0; padding: 72px 20px 56px; }}
      .mobile-bar {{ display: flex; position: fixed; z-index: 15; top: 0; left: 0; right: 0; height: 50px; padding: 8px 12px; align-items: center; justify-content: space-between; background: rgba(255,255,255,.94); border-bottom: 1px solid var(--line); backdrop-filter: blur(10px); }}
      h2 {{ margin-top: 56px; font-size: 25px; }}
      .facts {{ grid-template-columns: 1fr; }}
    }}
    @media print {{
      body {{ background: white; font-size: 10.5pt; }}
      #progress, aside, .mobile-bar {{ display: none !important; }}
      .shell {{ display: block; max-width: none; padding: 0; }}
      article {{ box-shadow: none; padding: 0; }}
      h2 {{ break-before: page; margin-top: 0; }}
      h3, img, table, blockquote {{ break-inside: avoid; }}
      img {{ box-shadow: none; max-height: 225mm; object-fit: contain; }}
      a {{ color: inherit; text-decoration: none; }}
    }}
  </style>
</head>
<body>
  <div id="progress"></div>
  <div class="lightbox" id="figure-lightbox" role="dialog" aria-modal="true" aria-label="图表大图" aria-hidden="true">
    <button class="lightbox-close" type="button" aria-label="关闭大图">×</button>
    <figure class="lightbox-figure">
      <img class="lightbox-image" alt="">
      <figcaption class="lightbox-caption"></figcaption>
    </figure>
  </div>
  <div class="mobile-bar"><strong>Global Flood Cause Evolution</strong><button onclick="window.print()">打印 / PDF</button></div>
  <div class="shell">
    <aside>
      <div class="brand"><strong>Research Report</strong><span>完整实验 · 2026-08-17</span></div>
      <nav class="toc" aria-label="目录">{toc}</nav>
      <div class="aside-actions"><button onclick="window.print()">打印 / PDF</button><button onclick="window.scrollTo(0,0)">回到顶部</button></div>
    </aside>
    <article>
      <div class="facts">
        <div class="fact"><b>1,407,121</b><span>重建雨洪事件</span></div>
        <div class="fact"><b>2,839</b><span>主分析流域</span></div>
        <div class="fact"><b>17</b><span>高置信度局地信号</span></div>
        <div class="fact"><b>1982–2019</b><span>研究时段</span></div>
      </div>
      {article}
    </article>
  </div>
  <script>
    const progress = document.getElementById('progress');
    const links = [...document.querySelectorAll('.toc a')];
    const sections = links.map(a => document.getElementById(a.getAttribute('href').slice(1))).filter(Boolean);
    function update() {{
      const height = document.documentElement.scrollHeight - innerHeight;
      progress.style.width = (height > 0 ? scrollY / height * 100 : 0) + '%';
      let current = sections[0];
      for (const section of sections) if (section.getBoundingClientRect().top < 140) current = section;
      links.forEach(a => a.classList.toggle('active', current && a.getAttribute('href') === '#' + current.id));
    }}
    addEventListener('scroll', update, {{passive: true}}); update();

    const lightbox = document.getElementById('figure-lightbox');
    const lightboxImage = lightbox.querySelector('.lightbox-image');
    const lightboxCaption = lightbox.querySelector('.lightbox-caption');
    const lightboxClose = lightbox.querySelector('.lightbox-close');
    let figureTrigger = null;
    function openFigure(image) {{
      figureTrigger = image;
      lightboxImage.src = image.src;
      lightboxImage.alt = image.alt || '报告图表';
      lightboxCaption.textContent = image.alt || '';
      lightbox.classList.add('open');
      lightbox.setAttribute('aria-hidden', 'false');
      document.body.classList.add('lightbox-open');
      lightboxClose.focus();
    }}
    function closeFigure() {{
      lightbox.classList.remove('open');
      lightbox.setAttribute('aria-hidden', 'true');
      document.body.classList.remove('lightbox-open');
      lightboxImage.removeAttribute('src');
      if (figureTrigger) figureTrigger.focus();
    }}
    document.querySelectorAll('article img').forEach(image => {{
      image.tabIndex = 0;
      image.setAttribute('role', 'button');
      image.setAttribute('aria-label', '点击查看大图：' + (image.alt || '报告图表'));
      image.addEventListener('click', () => openFigure(image));
      image.addEventListener('keydown', event => {{
        if (event.key === 'Enter' || event.key === ' ') {{
          event.preventDefault();
          openFigure(image);
        }}
      }});
    }});
    lightboxClose.addEventListener('click', closeFigure);
    lightbox.addEventListener('click', event => {{ if (event.target === lightbox) closeFigure(); }});
    addEventListener('keydown', event => {{ if (event.key === 'Escape' && lightbox.classList.contains('open')) closeFigure(); }});
  </script>
</body>
</html>"""

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(document, encoding="utf-8")
    return {
        "status": "complete",
        "source": str(source),
        "destination": str(destination),
        "embedded_figures": image_count,
        "bytes": destination.stat().st_size,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a self-contained HTML research report.")
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path, default=DESTINATION)
    args = parser.parse_args()
    print(build_html_report(args.source.resolve(), args.output.resolve()))


if __name__ == "__main__":
    main()
