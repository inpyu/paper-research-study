"use client";
import { Link, useJson, useState, Loading, Failed, Chips } from "../ui";

function Trace() {
  const { data: d, error } = useJson("wiki/trace.json");
  const [i, setI] = useState(0);
  if (error) return <Failed e={error} />;
  if (!d) return <Loading />;
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
      <div className="switch">
        <div className="seg">
          {d.traces.map((x, j) => (
            <button key={j} data-on={i === j} onClick={() => setI(j)}>{x.label}</button>
          ))}
        </div>
      </div>
      <p className="meta">프롬프트 하나가 들어왔을 때 호출되는 순서입니다.</p>
      {rows.map(({ k, n, depth }, j) => (
        <a key={j} href={n.url} target="_blank" rel="noreferrer"
          style={{ display: "block", marginLeft: Math.min(depth, 4) * 16 }}>
          <div className="card" style={{ padding: "9px 13px", marginBottom: 6 }}>
            <div className="t">
              <span className="n mono" style={{ fontSize: 13.5 }}>{k.split("#")[1]}</span>
              <span className="s mono">{n.file.replace("src/", "")}:{n.line}</span>
            </div>
          </div>
        </a>
      ))}
    </>
  );
}

export default function Code() {
  const { data: d, error } = useJson("wiki/files.json");
  const [view, setView] = useState("files");
  const [q, setQ] = useState("");
  return (
    <>
      <h1 className="page">코드</h1>
      <p className="lead">파일이 하는 일과 함수별 설명, 그리고 실행 경로입니다.</p>
      <div className="switch">
        <div className="seg">
          {[["files", "파일별 설명"], ["trace", "실행 경로"]].map(([k, label]) => (
            <button key={k} data-on={view === k} onClick={() => setView(k)}>{label}</button>
          ))}
        </div>
      </div>
      {view === "trace" ? <Trace /> : error ? <Failed e={error} /> : !d ? <Loading /> : (
        <>
          <p className="meta">설명 {d.documented}/{d.count} · 참조와 변경이 잦은 파일부터</p>
          <input type="search" placeholder="파일 검색" value={q}
            onChange={(e) => setQ(e.target.value)} />
          {[...d.items]
            .filter((f) => !q || f.path.toLowerCase().includes(q.toLowerCase()))
            .sort((a, b) => (b.doc ? 1 : 0) - (a.doc ? 1 : 0) ||
              (b.churn * 3 + (b.in_refs || 0)) - (a.churn * 3 + (a.in_refs || 0)))
            .map((f) => {
              const inner = (
                <>
                  <div className="t">
                    <span className="n mono">{f.path.replace("src/", "")}</span>
                    <span className="s">{f.loc}줄</span>
                  </div>
                  {f.role
                    ? <><div className="d" style={{ color: "var(--fg)" }}>{f.role}</div>
                        <div className="d"><Chips items={f.tags} brand />
                          <span className="meta">함수 {f.functions}개 설명</span></div></>
                    : <div className="d">설명 생성 대기</div>}
                </>
              );
              return f.doc
                ? <Link className="card" key={f.path}
                    href={`/code/${f.path.replace(/\//g, "_")}`}>{inner}</Link>
                : <div className="card" key={f.path}>{inner}</div>;
            })}
        </>
      )}
    </>
  );
}
