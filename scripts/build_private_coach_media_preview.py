#!/usr/bin/env python3
"""Build a private, lazy-loaded browser for coach clips and staged frames."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


COACH_LABELS = {
    "liu_hui": "刘辉",
    "li_yuxuan": "李宇轩",
    "zheng_siwei": "郑思维",
}


def project_url(path: str) -> str:
    return "../../../" + path.lstrip("/")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    summary = json.loads((args.inventory / "summary.json").read_text(encoding="utf-8"))
    validation = json.loads((args.inventory / "validation.json").read_text(encoding="utf-8"))
    warning_ids = {row["asset_id"] for row in validation.get("warnings", [])}
    assets = [
        json.loads(line)
        for line in (args.inventory / "assets.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assets = [row for row in assets if not row.get("duplicate_of")]

    compact_assets: list[dict[str, Any]] = []
    by_source: dict[tuple[str, str], list[str]] = {}
    for row in assets:
        compact = {
            "id": row["asset_id"],
            "coach": row["coach"],
            "coachLabel": COACH_LABELS[row["coach"]],
            "sourceId": row["source_id"],
            "title": row["title"],
            "url": row["url"],
            "state": "ready" if row["state"] == "ready_existing" else "candidate",
            "pass": row["pass"],
            "actions": row["actions"],
            "labels": row["labels_zh"],
            "summaries": row.get("teaching_summaries_zh", []),
            "classification": row["classification"],
            "confidence": row["confidence"],
            "start": row["action_start_seconds"],
            "end": row["action_end_seconds"],
            "clipStart": row["clip_start_seconds"],
            "clipEnd": row["clip_end_seconds"],
            "clip": project_url(row["clip"]),
            "frames": [project_url(path) for path in row["frames"]],
            "frameLabels": row.get("frame_labels_zh", []),
            "frameTimes": row.get("frame_anchor_seconds", []),
            "frameNotes": row.get("frame_teaching_points_zh", []),
            "scope": row.get("scope_limitations", []),
            "warning": row["asset_id"] in warning_ids,
        }
        compact_assets.append(compact)
        by_source.setdefault((row["coach"], row["source_id"]), []).append(row["asset_id"])

    empty_sources = []
    for source in summary["sources"]:
        if source["state"] != "no_reliable_episode":
            continue
        empty_sources.append(
            {
                "id": f"empty:{source['coach']}:{source['source_id']}",
                "coach": source["coach"],
                "coachLabel": COACH_LABELS[source["coach"]],
                "sourceId": source["source_id"],
                "title": source["title"],
                "url": source["url"],
                "state": "none",
                "actions": [],
                "labels": [],
            }
        )

    payload = {
        "stats": {
            "sources": summary["source_count"],
            "assets": summary["canonical_asset_count"],
            "frames": summary["existing_canonical_frame_count"],
            "ready": summary["teaching_approved_canonical_asset_count"],
            "coveredSources": summary["source_count"]
            - summary["source_state_counts"].get("no_reliable_episode", 0),
            "emptySources": summary["source_state_counts"].get("no_reliable_episode", 0),
        },
        "assets": compact_assets,
        "emptySources": empty_sources,
    }
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

    html = TEMPLATE.replace("__CATALOG_DATA__", data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html, encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "source_count": payload["stats"]["sources"],
                "media_asset_count": len(compact_assets),
                "empty_source_count": len(empty_sources),
                "output_bytes": args.output.stat().st_size,
            },
            ensure_ascii=False,
        )
    )


TEMPLATE = r'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>教练动作素材 · 私有审阅</title>
  <style>
    :root{--ink:#0b2131;--muted:#557080;--paper:#f4f7f6;--card:#fff;--court:#147a62;--court-dark:#0d5648;--line:#d9e6e2;--orange:#e46f47;--blue:#2f637d;--shadow:0 16px 45px rgba(12,45,56,.10)}
    *{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink);font-family:"Noto Sans CJK SC","Microsoft YaHei",system-ui,sans-serif;line-height:1.5}
    button,input,select{font:inherit}.shell{max-width:1540px;margin:auto;padding:24px 28px 64px}
    .mast{position:relative;overflow:hidden;background:var(--ink);color:white;border-radius:3px;padding:32px 36px 28px;box-shadow:var(--shadow)}
    .mast:after{content:"";position:absolute;right:-7%;top:-95%;width:43%;height:250%;border:1px solid rgba(255,255,255,.23);transform:rotate(21deg);box-shadow:inset 0 0 0 46px rgba(20,122,98,.18),inset 0 0 0 47px rgba(255,255,255,.15)}
    .eyebrow{font:700 12px/1 "Arial Narrow","Roboto Condensed",sans-serif;letter-spacing:.18em;text-transform:uppercase;color:#8fe1ca}.mast h1{position:relative;z-index:1;margin:12px 0 8px;font:800 clamp(30px,5vw,68px)/.98 "Arial Narrow","Roboto Condensed","Noto Sans CJK SC",sans-serif;letter-spacing:-.045em;max-width:920px}.mast p{position:relative;z-index:1;margin:0;color:#c4d4dc;max-width:760px}.privacy{display:inline-flex;align-items:center;gap:8px;margin-top:20px;padding:7px 10px;border:1px solid rgba(143,225,202,.35);font-size:12px;color:#b7eada;background:rgba(20,122,98,.16)}.privacy:before{content:"";width:7px;height:7px;border-radius:50%;background:#8fe1ca}
    .scoreboard{display:grid;grid-template-columns:repeat(5,1fr);border:1px solid var(--line);border-top:0;background:var(--card);box-shadow:var(--shadow)}.score{padding:17px 20px;border-right:1px solid var(--line)}.score:last-child{border:0}.score strong{display:block;font:800 27px/1 "Arial Narrow","Roboto Condensed",sans-serif}.score span{font-size:12px;color:var(--muted)}
    .controls{position:sticky;top:0;z-index:20;display:grid;grid-template-columns:minmax(230px,1.7fr) repeat(3,minmax(135px,.7fr));gap:10px;margin:22px 0;padding:13px;background:rgba(244,247,246,.94);backdrop-filter:blur(16px);border:1px solid var(--line)}.control{width:100%;height:44px;border:1px solid #bfd0ca;background:white;color:var(--ink);padding:0 13px;border-radius:0;outline:none}.control:focus{border-color:var(--court);box-shadow:0 0 0 3px rgba(20,122,98,.13)}
    .resultbar{display:flex;justify-content:space-between;align-items:end;gap:20px;margin:22px 0 12px}.resultbar h2{margin:0;font-size:17px}.resultbar p{margin:2px 0 0;color:var(--muted);font-size:13px}.legend{display:flex;gap:13px;font-size:12px;color:var(--muted)}.legend span:before{content:"";display:inline-block;width:8px;height:8px;margin-right:6px;background:var(--court)}.legend span:last-child:before{background:var(--orange)}
    .grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}.card{min-width:0;background:var(--card);border:1px solid var(--line);box-shadow:0 8px 24px rgba(20,55,65,.06)}.cardhead{display:grid;grid-template-columns:1fr auto;gap:12px;padding:18px 18px 13px;border-bottom:1px solid var(--line)}.coach{font:800 11px/1 "Arial Narrow",sans-serif;letter-spacing:.16em;text-transform:uppercase;color:var(--court)}.card h3{margin:7px 0 0;font-size:17px;line-height:1.35}.card h3 a{color:inherit;text-decoration:none}.card h3 a:hover{text-decoration:underline;text-decoration-color:var(--court);text-underline-offset:3px}.badge{align-self:start;padding:6px 8px;font-size:11px;font-weight:800;color:white;background:var(--court);white-space:nowrap}.badge.review{background:var(--orange)}.badge.none{background:#7b8c95}
    .meta{display:flex;flex-wrap:wrap;gap:7px;margin-top:11px}.chip{padding:4px 7px;background:#eaf4f0;color:var(--court-dark);font-size:11px}.chip.neutral{background:#eef2f3;color:#506975}.media{display:grid;grid-template-columns:minmax(220px,.72fr) minmax(0,1.28fr);gap:0}.clipbox{background:#07141c;min-height:270px;display:flex;align-items:center}.clipbox video{display:block;width:100%;max-height:430px;background:#07141c}.stages{display:grid;grid-template-columns:repeat(7,minmax(92px,1fr));overflow-x:auto;border-left:1px solid var(--line)}.stage{min-width:92px;margin:0;border-right:1px solid var(--line);background:#f9fbfa}.stage:last-child{border:0}.stage img{display:block;width:100%;aspect-ratio:9/16;object-fit:cover;background:#dce6e2}.stagecopy{padding:8px}.stage b{display:block;font-size:11px;line-height:1.25}.stage time{display:block;margin-top:3px;color:var(--muted);font:700 10px/1 "Arial Narrow",sans-serif}.stage p{margin:7px 0 0;color:#5a707a;font-size:10px;line-height:1.35}
    .note{padding:13px 18px;border-top:1px solid var(--line);font-size:12px;color:var(--muted)}.note strong{color:var(--ink)}.warning{color:#a94b2d}.empty{padding:23px 18px}.empty p{margin:8px 0 0;color:var(--muted);font-size:13px}.pager{display:flex;justify-content:center;align-items:center;gap:10px;margin-top:25px}.pager button{border:1px solid var(--line);background:white;color:var(--ink);padding:9px 14px;cursor:pointer}.pager button:disabled{opacity:.35;cursor:not-allowed}.pager span{font:700 12px/1 "Arial Narrow",sans-serif;color:var(--muted)}.nothing{grid-column:1/-1;padding:60px 20px;text-align:center;border:1px dashed #aebfba;color:var(--muted)}
    @media(max-width:1040px){.grid{grid-template-columns:1fr}.scoreboard{grid-template-columns:repeat(3,1fr)}.score:nth-child(3){border-right:0}.score:nth-child(n+4){border-top:1px solid var(--line)}.controls{grid-template-columns:1fr 1fr}.media{grid-template-columns:minmax(250px,.8fr) minmax(0,1.2fr)}}
    @media(max-width:700px){.shell{padding:12px 12px 44px}.mast{padding:25px 20px}.scoreboard{grid-template-columns:1fr 1fr}.score{border-top:1px solid var(--line)}.score:nth-child(2n){border-right:0}.controls{position:relative;grid-template-columns:1fr}.resultbar{align-items:start;flex-direction:column}.media{grid-template-columns:1fr}.clipbox{min-height:0}.stages{border-left:0;border-top:1px solid var(--line)}.legend{display:none}}
    @media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
  </style>
</head>
<body>
<main class="shell">
  <header class="mast">
    <div class="eyebrow">Coach motion review / private workspace</div>
    <h1>教练动作素材，按原视频逐拍审阅</h1>
    <p>连续短片和七阶段关键帧放在同一条动作线上。绿色可进入教学，橙色只用于复核，不会混入学员侧。</p>
    <div class="privacy">私有目录 · 不进入 Git 或 GitHub Pages</div>
  </header>
  <section class="scoreboard" aria-label="素材统计">
    <div class="score"><strong id="statSources">—</strong><span>来源视频</span></div>
    <div class="score"><strong id="statCovered">—</strong><span>已有动作素材的视频</span></div>
    <div class="score"><strong id="statAssets">—</strong><span>连续动作短片</span></div>
    <div class="score"><strong id="statFrames">—</strong><span>阶段关键帧</span></div>
    <div class="score"><strong id="statReady">—</strong><span>已确认正确示范</span></div>
  </section>
  <section class="controls" aria-label="筛选素材">
    <input id="search" class="control" type="search" placeholder="搜索 B 站原始标题或来源 ID">
    <select id="coach" class="control" aria-label="教练"><option value="all">全部教练</option><option value="liu_hui">刘辉</option><option value="li_yuxuan">李宇轩</option><option value="zheng_siwei">郑思维</option></select>
    <select id="status" class="control" aria-label="审核状态"><option value="all">全部状态</option><option value="ready">可用于教学</option><option value="candidate">待上下文审核</option><option value="none">未找到可靠动作</option></select>
    <select id="action" class="control" aria-label="技术类型"><option value="all">全部技术</option></select>
  </section>
  <div class="resultbar"><div><h2 id="resultTitle">素材目录</h2><p id="resultMeta"></p></div><div class="legend"><span>可用于教学</span><span>只用于复核</span></div></div>
  <section id="grid" class="grid" aria-live="polite"></section>
  <nav class="pager" aria-label="分页"><button id="prev">上一页</button><span id="page"></span><button id="next">下一页</button></nav>
</main>
<script id="catalog" type="application/json">__CATALOG_DATA__</script>
<script>
  const data=JSON.parse(document.getElementById('catalog').textContent);const PAGE=12;
  const els={grid:document.getElementById('grid'),search:document.getElementById('search'),coach:document.getElementById('coach'),status:document.getElementById('status'),action:document.getElementById('action'),meta:document.getElementById('resultMeta'),page:document.getElementById('page'),prev:document.getElementById('prev'),next:document.getElementById('next')};let page=1;
  const escape=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const seconds=n=>`${Number(n).toFixed(2)}s`;
  document.getElementById('statSources').textContent=data.stats.sources.toLocaleString();document.getElementById('statCovered').textContent=data.stats.coveredSources.toLocaleString();document.getElementById('statAssets').textContent=data.stats.assets.toLocaleString();document.getElementById('statFrames').textContent=data.stats.frames.toLocaleString();document.getElementById('statReady').textContent=data.stats.ready.toLocaleString();
  [...new Set(data.assets.flatMap(x=>x.actions))].sort().forEach(action=>els.action.insertAdjacentHTML('beforeend',`<option value="${escape(action)}">${escape(action)}</option>`));
  function filtered(){const q=els.search.value.trim().toLowerCase(),coach=els.coach.value,status=els.status.value,action=els.action.value;return [...data.assets,...data.emptySources].filter(x=>(coach==='all'||x.coach===coach)&&(status==='all'||x.state===status)&&(action==='all'||x.actions.includes(action))&&(!q||`${x.title} ${x.sourceId} ${x.labels.join(' ')} ${x.actions.join(' ')}`.toLowerCase().includes(q)));}
  function card(x){if(x.state==='none')return `<article class="card"><div class="cardhead"><div><div class="coach">${escape(x.coachLabel)} · ${escape(x.sourceId)}</div><h3><a href="${escape(x.url)}" target="_blank" rel="noreferrer">${escape(x.title)}</a></h3></div><span class="badge none">无可靠动作</span></div><div class="empty"><strong>当前没有可安全抽取的连续示范</strong><p>已有候选未通过完整性、动作纯度或语义门控。保留原视频索引，不用说话画面或错误示范凑数。</p></div></article>`;
    const ready=x.state==='ready',labels=x.labels.length?x.labels:x.actions;const stages=x.frames.map((src,i)=>`<figure class="stage"><img src="${escape(src)}" loading="lazy" alt="${escape(x.frameLabels[i]||`阶段 ${i+1}`)}"><figcaption class="stagecopy"><b>${String(i+1).padStart(2,'0')} · ${escape(x.frameLabels[i]||`阶段 ${i+1}`)}</b><time>${seconds(x.frameTimes[i]||0)}</time><p>${escape(x.frameNotes[i]||'观察这一时刻可见的二维动作路线。')}</p></figcaption></figure>`).join('');return `<article class="card"><div class="cardhead"><div><div class="coach">${escape(x.coachLabel)} · ${escape(x.sourceId)}</div><h3><a href="${escape(x.url)}" target="_blank" rel="noreferrer">${escape(x.title)}</a></h3><div class="meta">${labels.map(v=>`<span class="chip">${escape(v)}</span>`).join('')}<span class="chip neutral">${seconds(x.start)}–${seconds(x.end)}</span><span class="chip neutral">${escape(x.pass==='continuity'?'连续性复核':'首轮')}</span></div></div><span class="badge ${ready?'':'review'}">${ready?'可用于教学':'待上下文审核'}</span></div><div class="media"><div class="clipbox"><video controls playsinline preload="metadata" src="${escape(x.clip)}"></video></div><div class="stages">${stages}</div></div><div class="note"><strong>${ready?'已确认：教练本人、正确示范、单次连续动作。':'边界：这里只是私有复核素材，尚未确认示范者角色与正反例。'}</strong>${x.warning?` <span class="warning">固定机位下有相邻帧视觉变化较小，需结合短片判断。</span>`:''}</div></article>`}
  function render(){document.querySelectorAll('video').forEach(v=>v.pause());const rows=filtered(),pages=Math.max(1,Math.ceil(rows.length/PAGE));page=Math.min(page,pages);const slice=rows.slice((page-1)*PAGE,page*PAGE);els.grid.innerHTML=slice.length?slice.map(card).join(''):'<div class="nothing">没有符合当前筛选条件的素材。</div>';els.meta.textContent=`${rows.length.toLocaleString()} 条结果 · 每页 ${PAGE} 条`;els.page.textContent=`${page} / ${pages}`;els.prev.disabled=page<=1;els.next.disabled=page>=pages;}
  [els.search,els.coach,els.status,els.action].forEach(el=>el.addEventListener('input',()=>{page=1;render()}));els.prev.addEventListener('click',()=>{page--;render();scrollTo({top:document.querySelector('.resultbar').offsetTop-20,behavior:'smooth'})});els.next.addEventListener('click',()=>{page++;render();scrollTo({top:document.querySelector('.resultbar').offsetTop-20,behavior:'smooth'})});render();
</script>
</body>
</html>
'''


if __name__ == "__main__":
    main()
