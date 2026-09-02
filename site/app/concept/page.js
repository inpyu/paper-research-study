"use client";
import { Link, useJson, useMemo, useState, Loading, Failed } from "../ui";

export default function Concepts() {
  const { data: idx, error } = useJson("concepts.json");
  const [q, setQ] = useState("");
  const [mode, setMode] = useState("order");
  const byKey = useMemo(
    () => Object.fromEntries((idx?.items || []).map((c) => [c.key, c])), [idx]);
  if (error) return <Failed e={error} />;
  if (!idx) return <Loading />;

  const s = q.trim().toLowerCase();
  const match = (c) => !s || c.name.toLowerCase().includes(s) ||
    (c.one_liner || "").toLowerCase().includes(s) ||
    (c.tags || []).some((t) => t.toLowerCase().includes(s));

  const Item = ({ c }) => (
    <Link className="card" href={`/concept/${c.key.replace(/ /g, "_")}`}>
      <div className="t">
        <span className="n">
          {c.name}
          {c.track === "foundation" && <span className="chip brand" style={{ marginLeft: 7 }}>기초</span>}
        </span>
        <span className="s">{c.difficulty ? `난이도 ${c.difficulty}` : ""}</span>
      </div>
      <div className="d">{c.one_liner || "설명 생성 대기"}</div>
    </Link>
  );

  return (
    <>
      <h1 className="page">개념</h1>
      <p className="lead">딥러닝 기초부터 이 연구의 용어까지 순서대로 이어집니다.</p>
      <div className="switch">
        <div className="seg">
          {[["order", "학습 순서"], ["all", "전체 목록"]].map(([k, label]) => (
            <button key={k} data-on={mode === k} onClick={() => setMode(k)}>{label}</button>
          ))}
        </div>
        <span className="meta">설명 {idx.explained}/{idx.count}</span>
      </div>
      <input type="search" placeholder="개념·태그 검색" value={q}
        onChange={(e) => setQ(e.target.value)} />
      {mode === "order" && !s ? (
        <>
          {(idx.foundation_stages || []).map((st) => (
            <div key={`f${st.stage}`}>
              <div className="sec">기초 {st.stage} · {st.title}
                <span className="meta"> · {st.keys.length}개</span></div>
              {st.goal && <p className="meta" style={{ margin: "0 0 9px" }}>{st.goal}</p>}
              {st.keys.map((k) => byKey[k] && <Item c={byKey[k]} key={k} />)}
            </div>
          ))}
          {idx.steps.map((st) => (
            <div key={st.level}>
              <div className="sec">
                {st.level === 0 ? "연구 용어 — 노트에 정의된 것" : `연구 용어 ${st.level}단계`}
                <span className="meta"> · {st.keys.length}개</span>
              </div>
              {st.keys.map((k) => byKey[k] && <Item c={byKey[k]} key={k} />)}
            </div>
          ))}
        </>
      ) : (
        (idx.order || idx.items.map((c) => c.key))
          .map((k) => byKey[k]).filter((c) => c && match(c))
          .map((c) => <Item c={c} key={c.key} />)
      )}
    </>
  );
}
