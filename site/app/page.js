"use client";
import { useEffect, useMemo, useState } from "react";

const TABS = [
  ["brief", "브리핑"],
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
        {[["trace", "실행 경로"], ["artifacts", "실험"], ["numbers", "수치"], ["files", "파일"], ["flags", "플래그"], ["history", "연대기"], ["plan", "계획"]].map(([k, label]) => (
          <button key={k} className="pill" onClick={() => setView(k)}
            style={{ cursor: "pointer", background: view === k ? "var(--accent)" : "transparent",
                     color: view === k ? "#fff" : "var(--dim)",
                     borderColor: view === k ? "var(--accent)" : "var(--line)" }}>{label}</button>
        ))}
      </div>
      {!d ? <div className="empty">불러오는 중…</div> :
        view === "trace" ? <Trace d={d} /> :
        view === "artifacts" ? <Runs d={d} /> :
        view === "numbers" ? <Numbers d={d} /> :
        view === "files" ? d.items.map((f, i) => (
          <Card key={i} name={<span className="mono">{f.path.replace("src/", "")}</span>}
            side={`${f.loc}줄 · 변경 ${f.churn} · 참조 ${f.in_refs ?? 0}`} href={f.url}>
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

/* ---------- 브리핑 ---------- */
const VERDICT = {
  "must-read": ["필독", "warn"],
  skim: ["훑기", ""],
  skip: ["넘김", ""],
};

function Briefings() {
  const idx = useJson("briefings.json");
  const [day, setDay] = useState(null);
  const d = useJson(day ? `briefing/${day}.json` : "briefings.json");
  const cur = day && d && d.date === day ? d : null;

  if (!idx) return <div className="empty">불러오는 중…</div>;
  if (idx.count === 0) return <div className="empty">아직 브리핑이 없습니다.</div>;

  if (!day) {
    return (
      <>
        <p className="meta" style={{ marginTop: 4 }}>
          매일 아침 arXiv 신규 논문을 refs.md 시드와 대조해 3편으로 추립니다.
        </p>
        {idx.items.map((b) => (
          <div key={b.date} onClick={() => setDay(b.date)} style={{ cursor: "pointer" }}>
            <Card name={b.date}
              side={b.must ? `필독 ${b.must}편` : `${b.count}편`}>
              {b.titles.join(" · ")}
            </Card>
          </div>
        ))}
      </>
    );
  }
  if (!cur) return <div className="empty">불러오는 중…</div>;
  return (
    <>
      <button className="pill" style={{ cursor: "pointer" }} onClick={() => setDay(null)}>← 날짜</button>
      <div className="sec">{cur.date} · 후보 {cur.all?.length ?? "?"}편 중 {cur.items.length}편</div>
      {cur.items.map((b, i) => {
        const [label, cls] = VERDICT[b.verdict] || [b.verdict, ""];
        return (
          <div className="card" key={i}>
            <div className="t">
              <span className="n">
                <span className={`pill ${cls}`}>{label}</span>
                <a href={b.url} target="_blank" rel="noreferrer">{b.title}</a>
              </span>
              <span className="s">{b.published}</span>
            </div>
            <div className="d" style={{ color: "var(--fg)", marginTop: 8 }}>{b.what}</div>
            <div className="d" style={{ marginTop: 4 }}>{b.relation}</div>
            {b.gap && <div className="d" style={{ marginTop: 4 }}>간극: {b.gap}</div>}
            <div className="d" style={{ marginTop: 6 }}>
              {(b.hypotheses || []).map((h) => <span className="pill" key={h}>{h}</span>)}
              <span className="pill">{b.categories?.[0]}</span>
              <span className="pill">유사도 {b.score}</span>
            </div>
            <div style={{ marginTop: 8 }}>
              <button className="pill" style={{ cursor: "pointer" }}
                onClick={() => navigator.clipboard?.writeText(
                  `| **${b.title}** [arXiv](${b.url}) | ${b.what} | ${b.gap || ""} |`)}>
                refs.md 한 줄 복사
              </button>
            </div>
          </div>
        );
      })}
    </>
  );
}

/* ---------- 실행 경로 (위키 W2) ---------- */
function Trace({ d }) {
  const [i, setI] = useState(0);
  const t = d.traces?.[i];
  if (!t) return <div className="empty">경로 없음</div>;
  const children = {};
  t.edges.forEach((e) => (children[e.from] ||= []).push(e.to));
  const rows = [];
  const walk = (k, depth, seen) => {
    if (depth > 4 || seen.has(k)) return;
    const n = t.nodes[k];
    if (!n) return;
    rows.push({ k, n, depth });
    (children[k] || []).forEach((c) => walk(c, depth + 1, new Set([...seen, k])));
  };
  walk(t.entry, 0, new Set());
  return (
    <>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 10 }}>
        {d.traces.map((x, j) => (
          <button key={j} className="pill" onClick={() => setI(j)}
            style={{ cursor: "pointer", background: i === j ? "var(--accent)" : "transparent",
                     color: i === j ? "#fff" : "var(--dim)",
                     borderColor: i === j ? "var(--accent)" : "var(--line)" }}>
            {x.label}
          </button>
        ))}
      </div>
      <p className="meta" style={{ marginTop: 0 }}>
        호출 그래프를 tree-sitter 로 뽑아 편 것. 노트가 설명하는 단계는{" "}
        <b>{t.covered}/{Object.keys(t.nodes).length}</b> 뿐이다.
      </p>
      {rows.map(({ k, n, depth }, j) => (
        <a key={j} href={n.url} target="_blank" rel="noreferrer"
           style={{ textDecoration: "none", display: "block",
                    marginLeft: Math.min(depth, 4) * 14 }}>
          <div className="card" style={{ padding: "8px 11px", marginBottom: 5,
               borderLeft: `3px solid ${n.notes.length ? "var(--ok)" : "var(--line)"}` }}>
            <div className="t">
              <span className="n mono" style={{ fontSize: 13 }}>{k.split("#")[1]}</span>
              <span className="s">{n.refs ? `참조 ${n.refs}` : ""}</span>
            </div>
            <div className="d">
              <span className="mono">{n.file.replace("src/", "")}:{n.line}</span>
              {n.notes.length > 0
                ? <span style={{ color: "var(--ok)" }}> · {n.notes.join(", ")}</span>
                : <span style={{ color: "var(--dim)" }}> · 노트 설명 없음</span>}
            </div>
          </div>
        </a>
      ))}
    </>
  );
}

/* ---------- 실험 카드 (W4) ---------- */
function Runs({ d }) {
  return (
    <>
      <p className="meta" style={{ marginTop: 4 }}>
        artifacts/ 의 run-id {d.count}개. manifest·hosts.tsv·raw 로그를 파싱한 것.
        <b> 어떤 노트도 인용하지 않는 실험 {d.G6.length}개(G6)</b>.
      </p>
      {d.runs.map((r) => (
        <div className="card" key={r.run_id}>
          <div className="t">
            <span className="n mono">{r.run_id}</span>
            <span className="s">{(r.created_utc || "").slice(0, 10)}</span>
          </div>
          <div className="d">
            {r.node_count ? `노드 ${r.node_count}` : "노드 정보 없음"}
            {r.temp_range && ` · ${r.temp_range[0]}~${r.temp_range[1]}℃`}
            {r.governor?.length ? ` · ${r.governor.join("/")}` : ""}
            {` · 로그 ${r.raw_files}`}
            {r.git_sha && ` · ${r.git_sha.slice(0, 8)}`}
            {r.dirty && <span className="pill warn" style={{ marginLeft: 6 }}>dirty</span>}
          </div>
          {r.results && (
            <div className="d">
              결과 {r.results.rows}행 —{" "}
              {Object.entries(r.results.summary).slice(0, 3).map(([k, v]) =>
                `${k} ${v.min}~${v.max}(중앙 ${v.median})`).join(" · ")}
            </div>
          )}
          {r.flags?.length > 0 && (
            <div className="d mono">{r.flags.join(" ")}</div>
          )}
          <div className="d">
            {r.cited_in.length
              ? <span style={{ color: "var(--ok)" }}>인용: {r.cited_in.join(", ")}</span>
              : <span style={{ color: "var(--warn)" }}>인용 없음 (G6)</span>}
          </div>
          {r.warnings.map((w, i) => (
            <div className="d" key={i} style={{ color: "var(--warn)" }}>⚠ {w}</div>
          ))}
        </div>
      ))}
    </>
  );
}

/* ---------- 수치 대사전 (W6) ---------- */
function Numbers({ d }) {
  const [view, setView] = useState("dict");
  return (
    <>
      <div style={{ display: "flex", gap: 6, marginBottom: 10 }}>
        {[["dict", `자주 쓰는 수치`], ["g8", `불일치 ${d.G8_count}`],
          ["g7", `출처 없음 ${d.G7_count}`]].map(([k, label]) => (
          <button key={k} className="pill" onClick={() => setView(k)}
            style={{ cursor: "pointer", background: view === k ? "var(--accent)" : "transparent",
                     color: view === k ? "#fff" : "var(--dim)",
                     borderColor: view === k ? "var(--accent)" : "var(--line)" }}>{label}</button>
        ))}
      </div>
      {view === "dict" && d.dictionary.map((x, i) => (
        <Card key={i} name={<span className="mono">{x.value.toLocaleString()} {x.unit}</span>}
          side={`${x.count}회`}>
          {x.example}
          <div style={{ marginTop: 3 }}>{x.docs.join(", ")}</div>
        </Card>
      ))}
      {view === "g8" && (
        <>
          <p className="meta" style={{ marginTop: 0 }}>
            같은 맥락에서 값이 다른 수치. 논문 쓰기 전에 확인할 것 — 후보이지 확정이 아니다.
          </p>
          {d.G8.map((x, i) => (
            <div className="card" key={i}>
              <div className="t">
                <span className="n mono">{x.values.join(" / ")} {x.unit}</span>
              </div>
              <div className="d">{x.sig}</div>
              {x.where.map((w, j) => (
                <div className="d mono" key={j}>{w.doc}:{w.line} — {w.context}</div>
              ))}
            </div>
          ))}
        </>
      )}
      {view === "g7" && (
        <>
          <p className="meta" style={{ marginTop: 0 }}>
            artifacts/README.md 규칙: “논문의 모든 수치는 run-id 를 인용해야 한다”.
            run-id 를 인용하는 문서는 <b>{d.docs.filter((x) => x.run_ids.length).length}/{d.docs.length}</b> 뿐이다.
          </p>
          {d.docs.filter((x) => x.measured_unsourced > 0).map((x, i) => (
            <Card key={i} name={x.doc} side={`측정값 ${x.measured_unsourced}개`}>
              run-id 인용 없음
            </Card>
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
  const [tab, setTab] = useState("brief");
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
            <div className="stat"><b>{s.G6}/{s.runs}</b><span>G6 고아 실험</span></div>
            <div className="stat"><b>{s.G7}</b><span>G7 출처 없는 수치</span></div>
          </div>
        )}
        {tab === "brief" && <Briefings />}
        {tab === "gap" && <Gaps />}
        {tab === "concept" && <Concepts />}
        {tab === "wiki" && <Wiki />}
        {tab === "paper" && <Papers />}
      </main>
    </>
  );
}
