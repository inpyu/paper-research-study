"use client";
import { Link, useJson, useStar, hhmm, Loading, Failed } from "../ui";

export default function Learn() {
  const { data, error } = useJson("catalog.json");
  const [stars, toggleStar] = useStar();
  if (error) return <Failed e={error} />;
  if (!data) return <Loading />;
  return (
    <>
      <h1 className="page">학습</h1>
      <p className="lead">{data.lesson_count} 레슨 · 총 {hhmm(data.minutes)}</p>
      {data.tracks.map((t) => (
        <div key={t.id}>
          <div className="sec">
            {t.title} <span className="meta">· {t.course_count} 과목 · {hhmm(t.minutes)}</span>
          </div>
          {t.courses.map((c) => {
            const inner = (
              <div className="t">
                <span className="n">
                  <span className="star" onClick={(e) => {
                    e.preventDefault(); e.stopPropagation(); toggleStar(c.id);
                  }}>{stars.has(c.id) ? "★" : "☆"}</span>
                  {c.title}
                </span>
                <span className="s">
                  {c.lessons?.length ? `${c.lessons.length} 레슨 · ${hhmm(c.minutes)}` : "준비 중"}
                </span>
              </div>
            );
            return c.lessons?.length
              ? <Link className="card" href={`/learn/${c.id}`} key={c.id}>{inner}
                  {c.has_quiz && <div className="d"><span className="chip brand">📊 진단 있음</span></div>}
                </Link>
              : <div className="card" key={c.id}>{inner}</div>;
          })}
        </div>
      ))}
    </>
  );
}
