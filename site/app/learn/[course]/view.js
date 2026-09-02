"use client";
import { Link, useJson, hhmm, Loading, Failed, Back } from "../../ui";

export default function CourseView({ id }) {
  const { data, error } = useJson("catalog.json");
  if (error) return <Failed e={error} />;
  if (!data) return <Loading />;
  const track = data.tracks.find((t) => t.courses.some((c) => c.id === id));
  const c = track?.courses.find((x) => x.id === id);
  if (!c) return <Failed e="과목을 찾지 못했습니다" />;
  return (
    <>
      <Back href="/learn" label="학습" />
      <div className="meta">{track.title}</div>
      <h1 className="page">{c.title}</h1>
      {c.summary && <p className="lead">{c.summary}</p>}
      <p className="meta">{c.lessons.length} 레슨 · {hhmm(c.minutes)}</p>
      {c.has_quiz && (
        <Link className="btn primary block" href={`/learn/${c.id}/quiz`}
          style={{ margin: "16px 0" }}>
          📊 적응형 진단 시작
        </Link>
      )}
      <div className="sec">레슨</div>
      {c.lessons.map((l, i) => (
        <div className="card" key={l.id}>
          <div className="t">
            <span className="n"><span className="meta">{i + 1}.</span> {l.title}</span>
            <span className="s">{l.minutes}분</span>
          </div>
          <div className="d">{l.one_liner}</div>
          {l.concepts?.length > 0 && (
            <div className="d">
              {l.concepts.map((k) => (
                <Link className="chip brand" key={k}
                  href={`/concept/${k.replace(/ /g, "_")}`}>{k}</Link>
              ))}
            </div>
          )}
        </div>
      ))}
    </>
  );
}
