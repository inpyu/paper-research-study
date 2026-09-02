import Link from "next/link";
import { readData } from "./lib";

export default function Home() {
  const m = readData("manifest.json") || {};
  const cat = readData("catalog.json") || { tracks: [] };
  const cons = readData("concepts.json") || {};
  const files = readData("wiki/files.json") || {};
  const briefs = readData("briefings.json") || {};
  const papers = readData("papers.json") || {};
  const quizzes = cat.tracks?.flatMap((t) => t.courses).filter((c) => c.has_quiz).length || 0;

  const cards = [
    { href: "/learn", title: "학습", desc: "영역 → 과목 → 레슨. 과목마다 적응형 진단.",
      stat: `${cat.lesson_count || 0} 레슨 · 진단 ${quizzes} 과목` },
    { href: "/brief", title: "브리핑", desc: "매일 아침 arXiv 신규 논문을 선행연구와 대조합니다.",
      stat: briefs.latest ? `최신 ${briefs.latest}` : "준비 중" },
    { href: "/concept", title: "개념", desc: "딥러닝 기초부터 이 연구의 용어까지 순서대로.",
      stat: `${cons.count || 0} 개념 · 설명 ${cons.explained || 0}` },
    { href: "/code", title: "코드", desc: "파일 역할과 함수별 설명, 그리고 실행 경로.",
      stat: `${files.count || 0} 파일 · 설명 ${files.documented || 0}` },
    { href: "/paper", title: "논문", desc: "research/refs.md 에서 추출한 선행연구.",
      stat: `${papers.count || 0} 편` },
    { href: "/sitemap", title: "사이트맵", desc: "전체 구조를 한 화면에서.", stat: "" },
  ];

  return (
    <>
      <h1 className="page">무엇을 공부할까요</h1>
      <p className="lead">
        연구 노트와 코드를 대조해 만든 학습 자료입니다. 매일 아침 자동으로 갱신됩니다.
      </p>
      <div className="grid two">
        {cards.map((c) => (
          <Link className="card" href={c.href} key={c.href}>
            <div className="t">
              <span className="n">{c.title}</span>
              <span className="s">{c.stat}</span>
            </div>
            <div className="d">{c.desc}</div>
          </Link>
        ))}
      </div>
      {m.head_sha && (
        <p className="meta" style={{ marginTop: 18 }}>
          기준 커밋 <span className="mono">{m.head_sha.slice(0, 8)}</span>
        </p>
      )}
    </>
  );
}
