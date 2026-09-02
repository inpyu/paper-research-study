import Link from "next/link";
import { readData } from "../lib";

export const metadata = { title: "사이트맵 — RepoScholar" };

export default function Sitemap() {
  const cat = readData("catalog.json") || { tracks: [] };
  const cons = readData("concepts.json") || { items: [], foundation_stages: [] };
  const files = readData("wiki/files.json") || { items: [] };
  const briefs = readData("briefings.json") || { items: [] };

  return (
    <>
      <h1 className="page">사이트맵</h1>
      <p className="lead">전체 구조입니다. 어디서든 브라우저 뒤로가기로 돌아올 수 있습니다.</p>

      <div className="sec">학습</div>
      {cat.tracks.map((t) => (
        <div className="node has" key={t.id} style={{ marginBottom: 12 }}>
          <div className="meta" style={{ marginBottom: 6 }}>{t.title}</div>
          {t.courses.map((c) => (
            <div key={c.id}>
              {c.lessons?.length
                ? <Link className="chip brand" href={`/learn/${c.id}`}>{c.title}</Link>
                : <span className="chip">{c.title} (준비 중)</span>}
            </div>
          ))}
        </div>
      ))}

      <div className="sec">개념 {cons.count}</div>
      <div className="node">
        {(cons.foundation_stages || []).map((st) => (
          <div className="meta" key={st.stage}>기초 {st.stage} · {st.title} — {st.keys.length}개</div>
        ))}
        <div className="meta">연구 용어 — {(cons.items || []).filter((c) => c.track !== "foundation").length}개</div>
        <Link className="chip brand" href="/concept">개념 전체 보기</Link>
      </div>

      <div className="sec">코드 {files.count}</div>
      <div className="node">
        <Link className="chip brand" href="/code">파일 목록</Link>
        <Link className="chip" href="/code?view=trace">실행 경로</Link>
      </div>

      <div className="sec">브리핑</div>
      <div className="node">
        {(briefs.items || []).slice(0, 10).map((b) => (
          <Link className="chip" href={`/brief/${b.date}`} key={b.date}>{b.date}</Link>
        ))}
      </div>

      <div className="sec">논문</div>
      <div className="node"><Link className="chip brand" href="/paper">선행연구 목록</Link></div>
    </>
  );
}
