"use client";
import { useEffect, useMemo, useState } from "react";

const TABS = [
  ["gap", "갭"],
  ["concept", "개념"],
  ["wiki", "위키"],
  ["paper", "논문"],
];

const useJson = (path) => {
  const [d, setD] = useState(null);
  useEffect(() => {
    let alive = true;
    fetch(`./data/${path}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((j) => alive && setD(j))
      .catch(() => alive && setD(null));
    return () => { alive = false; };
  }, [path]);
  return d;
};

const ago = (iso) => {
  if (!iso) return "";
  const h = (Date.now() - new Date(iso)) / 36e5;
  if (h < 1) return "방금";
  if (h < 24) return `${Math.floor(h)}시간 전`;
  return `${Math.floor(h / 24)}일 전`;
};

function Card({ name, side, children, href }) {
  const body = (
    <div className="card">
      <div className="t">
        <span className="n">{name}</span>
        {side && <span className="s">{side}</span>}
      </div>
      {children && <div className="d">{children}</div>}
    </div>
  );
  return href ? <a href={href} target="_blank" rel="noreferrer" style={{ textDecoration: "none" }}>{body}</a> : body;
}

/* ---------- 갭 ---------- */
function Gaps() {
  const [kind, setKind] = useState("G3");
  const d = useJson(`gap/${kind}.json`);
  const desc = {
    G3: "노트에서 언급만 되고 정의된 적 없는 용어 — 안다고 착각하고 넘어간 것",
    G1: "코드에만 있고 노트에 전혀 없는 용어",
    G2: "노트에 있으나 코드 근거를 못 찾은 개념",
    G4: "어떤 노트도 언급하지 않는 소스 파일",
    G5: "노트에 설명이 없는 CLI 플래그",
  }[kind];
  return (
    <>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", margin: "4px 0 10px" }}>
        {["G3", "G1", "G4", "G5", "G2"].map((k) => (
          <button key={k} className="pill" onClick={() => setKind(k)}
            style={{ cursor: "pointer", background: kind === k ? "var(--accent)" : "transparent",
                     color: kind === k ? "#fff" : "var(--dim)",
                     borderColor: kind === k ? "var(--accent)" : "var(--line)" }}>
            {k}
          </button>
        ))}
      </div>
      <p className="meta" style={{ marginTop: 0 }}>{desc}</p>
      {!d ? <div className="empty">불러오는 중…</div> :
        d.items.length === 0 ? <div className="empty">없음</div> :
        d.items.slice(0, 120).map((x, i) => {
          if (kind === "G3")
            return (
              <Card key={i} name={x.term}
                side={`문서 ${x.doc_count} · 강조 ${x.emph} · ${x.in_code ? `코드 ${x.in_code}` : "노트만"}`}>
                {x.docs.map((s) => s.replace("research/", "")).join(", ")}
              </Card>
            );
          if (kind === "G1")
            return <Card key={i} name={x.term} side={`변경 ${x.churn}회`} href={x.url}>
              <span className="mono">{x.file}</span></Card>;
          if (kind === "G2")
            return <Card key={i} name={x.name} side={`정의 ${x.docs}곳`} />;
          if (kind === "G4")
            return <Card key={i} name={x.path.replace("src/", "")} side={`${x.loc}줄 · 변경 ${x.churn}회`} href={x.url} />;
          return <Card key={i} name={<span className="mono">{x.flag}</span>}
            side={`${x.sites}곳`} href={x.url}>
            <span className="mono">{x.file}:{x.line}</span></Card>;
        })}
    </>
  );
}

/* ---------- 개념 ---------- */
function Concepts() {
  const idx = useJson("concepts.json");
  const [q, setQ] = useState("");
  const [sel, setSel] = useState(null);
  const detail = useJson(sel ? `concept/${sel.replace(/ /g, "_")}.json` : "concepts.json");
  const items = useMemo(() => {
    if (!idx) return [];
    const s = q.trim().toLowerCase();
    return idx.items.filter((c) => !s || c.name.toLowerCase().includes(s) ||
      c.aliases.some((a) => a.toLowerCase().includes(s)));
  }, [idx, q]);

  if (sel && detail && detail.key === sel) {
    return (
      <>
        <button className="pill" style={{ cursor: "pointer" }} onClick={() => setSel(null)}>← 목록</button>
        <h2 style={{ margin: "14px 0 4px", fontSize: 20 }}>{detail.name}</h2>
        {detail.aliases.length > 0 && <p className="meta">{detail.aliases.join(" · ")}</p>}
        <div className="sec">노트 정의 {detail.defs.length}곳</div>
        {detail.defs.map((d, i) => (
          <Card key={i} name={d.doc.replace("research/", "")} side={`:${d.line}`} href={d.url} />
        ))}
        <div className="sec">코드 근거 {detail.evidence.length}곳</div>
        {detail.evidence.length === 0 ? <div className="empty">없음 — G2 갭</div> :
          detail.evidence.map((e, i) => (
            <Card key={i} name={<span className="mono">{e.file}</span>}
              side={e.line_start ? `:${e.line_start}` : e.via || ""} href={e.url}>{e.note}</Card>
          ))}
        {detail.links.length > 0 && (
          <>
            <div className="sec">이어지는 개념</div>
            {detail.links.map((l, i) => (
              <button key={i} className="pill" style={{ cursor: "pointer" }}
                onClick={() => setSel(l.to_key)}>{l.to_text}</button>
            ))}
          </>
        )}
      </>
    );
  }
  return (
    <>
      <input type="search" placeholder="개념 검색" value={q} onChange={(e) => setQ(e.target.value)} />
      {!idx ? <div className="empty">불러오는 중…</div> :
        <div className="grid2">
          {items.map((c) => (
            <div key={c.key} onClick={() => setSel(c.key)} style={{ cursor: "pointer" }}>
              <Card name={c.name} side={`문서 ${c.docs}${c.ev ? ` · 근거 ${c.ev}` : ""}`} />
            </div>
          ))}
        </div>}
    </>
  );
}

/* ---------- 위키 ---------- */
function Wiki() {
  const [view, setView] = useState("files");
  const d = useJson(`wiki/${view}.json`);
  return (
    <>
      <div style={{ display: "flex", gap: 6, margin: "4px 0 12px", flexWrap: "wrap" }}>
        {[["files", "파일"], ["flags", "플래그"], ["history", "연대기"], ["plan", "계획"]].map(([k, label]) => (
          <button key={k} className="pill" onClick={() => setView(k)}
            style={{ cursor: "pointer", background: view === k ? "var(--accent)" : "transparent",
                     color: view === k ? "#fff" : "var(--dim)",
                     borderColor: view === k ? "var(--accent)" : "var(--line)" }}>{label}</button>
        ))}
      </div>
      {!d ? <div className="empty">불러오는 중…</div> :
        view === "files" ? d.items.map((f, i) => (
          <Card key={i} name={<span className="mono">{f.path.replace("src/", "")}</span>}
            side={`${f.loc}줄 · 변경 ${f.churn}회`} href={f.url}>
            {f.notes.length ? `노트: ${f.notes.map((n) => n.replace("research/", "")).join(", ")}`
              : <span style={{ color: "var(--warn)" }}>노트 없음 (G4)</span>}
          </Card>
        )) :
        view === "flags" ? d.items.map((f, i) => (
          <Card key={i} name={<span className="mono">{f.flag}</span>}
            side={`${f.sites.length}곳`} href={f.url}>
            <span className="mono">{f.sites[0].file}:{f.sites[0].line}</span></Card>
        )) :
        view === "history" ? d.items.map((c, i) => (
          <Card key={i} name={c.subject} side={c.date}>
            <span className="mono">{c.sha}</span></Card>
        )) : (
          <>
            <div className="sec">학습 경로 {d.stages.length} Stage</div>
            {d.stages.map((s, i) => <Card key={i} name={`Stage ${s.stage}`} side="">{s.title}</Card>)}
            <div className="sec">가설</div>
            {Object.values(d.hypotheses).map((h, i) => (
              <Card key={i} name={h.id} side="">{h.context}</Card>
            ))}
            <div className="sec">노트 문서 {d.docs.length}개</div>
            {d.docs.map((x, i) => (
              <Card key={i} name={x.path.replace("research/", "")} side={`${x.lines}줄`} href={x.url}>
                {x.title}</Card>
            ))}
          </>
        )}
    </>
  );
}

/* ---------- 논문 ---------- */
function Papers() {
  const d = useJson("papers.json");
  if (!d) return <div className="empty">불러오는 중…</div>;
  return (
    <>
      <p className="meta" style={{ marginTop: 4 }}>
        research/refs.md 와 노트에서 추출한 시드 논문. 매일 브리핑의 기준점이 된다.
      </p>
      {d.items.map((p, i) => (
        <Card key={i} name={p.title || p.id} side={p.id} href={p.url}>
          {p.gap && <div style={{ marginBottom: 4 }}>간극: {p.gap}</div>}
          인용 {p.cited_in.length}곳 — {p.cited_in.map((s) => s.replace("research/", "")).join(", ")}
        </Card>
      ))}
    </>
  );
}

export default function Page() {
  const m = useJson("manifest.json");
  const [tab, setTab] = useState("gap");
  const s = m?.summary;
  return (
    <>
      <header>
        <div className="hrow">
          <h1>RepoScholar <span style={{ color: "var(--dim)", fontWeight: 400 }}>· inpyu/prefill-opt</span></h1>
          <span className="meta">
            {m ? `${ago(m.generated_at)} 갱신 · ${m.head_sha.slice(0, 8)}` : "…"}
          </span>
        </div>
        <nav>
          {TABS.map(([k, label]) => (
            <button key={k} data-on={tab === k} onClick={() => setTab(k)}>{label}</button>
          ))}
        </nav>
      </header>
      <main className="wrap">
        {s && (
          <div className="stats">
            <div className="stat"><b>{s.concepts_defined}</b><span>정의된 개념</span></div>
            <div className="stat"><b>{s.G3}</b><span>G3 미정의 용어</span></div>
            <div className="stat"><b>{s.G4}/{s.src_files}</b><span>G4 미문서 파일</span></div>
            <div className="stat"><b>{s.G5}/{s.flags}</b><span>G5 미문서 플래그</span></div>
            <div className="stat"><b>{s.G2}</b><span>G2 근거 없음</span></div>
          </div>
        )}
        {tab === "gap" && <Gaps />}
        {tab === "concept" && <Concepts />}
        {tab === "wiki" && <Wiki />}
        {tab === "paper" && <Papers />}
      </main>
    </>
  );
}
