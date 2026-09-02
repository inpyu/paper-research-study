"use client";
import { Link, useJson, Loading, Failed } from "../ui";

export default function Briefs() {
  const { data, error } = useJson("briefings.json");
  if (error) return <Failed e={error} />;
  if (!data) return <Loading />;
  if (!data.count) return <div className="empty">아직 브리핑이 없습니다.</div>;
  return (
    <>
      <h1 className="page">브리핑</h1>
      <p className="lead">매일 아침 arXiv 신규 논문을 이 연구의 선행연구와 대조해 추립니다.</p>
      {data.items.map((b) => (
        <Link className="card" href={`/brief/${b.date}`} key={b.date}>
          <div className="t">
            <span className="n">{b.date}</span>
            <span className="s">
              {b.must ? <span className="chip warn">필독 {b.must}편</span> : `${b.count}편`}
            </span>
          </div>
          <div className="d">{b.titles.join(" · ")}</div>
        </Link>
      ))}
    </>
  );
}
