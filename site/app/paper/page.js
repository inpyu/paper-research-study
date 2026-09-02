"use client";
import { useJson, Loading, Failed } from "../ui";

export default function Papers() {
  const { data, error } = useJson("papers.json");
  if (error) return <Failed e={error} />;
  if (!data) return <Loading />;
  return (
    <>
      <h1 className="page">논문</h1>
      <p className="lead">research/refs.md 에서 추출한 선행연구. 매일 브리핑의 기준점입니다.</p>
      {data.items.map((p, i) => (
        <a className="card" key={i} href={p.url} target="_blank" rel="noreferrer">
          <div className="t">
            <span className="n">{p.title || p.id}</span>
            <span className="s mono">{p.id}</span>
          </div>
          {p.gap && <div className="d">간극: {p.gap}</div>}
          <div className="d">{p.cited_in.map((s) => s.replace("research/", "")).join(", ")}</div>
        </a>
      ))}
    </>
  );
}
