"use client";
import { useJson, useMemo, useState, Loading, Failed, Back, Link } from "../../../ui";

const MAX = 8;

export default function QuizView({ id }) {
  const { data, error } = useJson(`quiz/${id}.json`);
  const [asked, setAsked] = useState([]);
  const [theta, setTheta] = useState(2.5);

  const next = useMemo(() => {
    if (!data) return null;
    const seen = new Set(asked.map((a) => a.item.id));
    const pool = data.items.filter((i) => !seen.has(i.id));
    if (!pool.length || asked.length >= MAX) return null;
    let best = pool[0], bd = 99;
    for (const it of pool) {
      const d = Math.abs(it.difficulty - theta);
      if (d < bd) { bd = d; best = it; }
    }
    return best;
  }, [data, asked, theta]);

  if (error) return <Failed e={error} />;
  if (!data) return <Loading />;

  const answer = (idx) => {
    const it = next;
    const ok = idx === it.answer;
    setAsked((a) => [...a, { item: it, picked: idx }]);
    // 맞히면 더 어려운 쪽으로, 틀리면 쉬운 쪽으로. 모르겠어요는 절반만 내린다.
    setTheta((t) => Math.max(1, Math.min(5,
      idx === null ? t - 0.35 : ok ? t + 0.55 : t - 0.6)));
  };

  if (!next) {
    const graded = asked.filter((a) => a.picked !== null);
    const right = graded.filter((a) => a.picked === a.item.answer);
    const level = Math.max(1, Math.min(5, Math.round(theta)));
    const bank = data.items.length;
    const solvable = data.items.filter((i) => i.difficulty <= level).length;
    return (
      <>
        <Back href={`/learn/${id}`} label={data.title} />
        <h1 className="page">진단 결과</h1>
        <div className="stats">
          <div className="stat">
            <b>{graded.length ? Math.round(right.length / graded.length * 100) : 0}%</b>
            <span>정답률 {right.length}/{graded.length}</span></div>
          <div className="stat"><b>{level}/5</b><span>도달 난이도</span></div>
          <div className="stat"><b>{Math.round(solvable / bank * 100)}%</b>
            <span>이 과목 문항 소화</span></div>
        </div>
        <p className="meta">
          “이 과목 문항 소화”는 이 문제은행({bank}문항) 중 도달 난이도 이하의 비율입니다.
          다른 사람과 비교한 값이 아닙니다.
        </p>
        <div className="sec">문제별 정리</div>
        {asked.map(({ item, picked }, i) => {
          const ok = picked === item.answer;
          return (
            <div className="card" key={i} style={{
              borderLeftWidth: 3,
              borderLeftColor: picked === null ? "var(--line)"
                : ok ? "var(--ok)" : "var(--danger)" }}>
              <div className="t">
                <span className="n">{item.question}</span>
                <span className="s">난이도 {item.difficulty}</span>
              </div>
              <div className="d">
                {picked === null ? "건너뜀" : ok ? "정답" : `내 답: ${item.choices[picked]}`}
              </div>
              <div className="d" style={{ color: "var(--fg)" }}>
                정답: {item.choices[item.answer]}
              </div>
              <div className="d">{item.explanation}</div>
              {item.concepts?.length > 0 && (
                <div className="d">
                  {item.concepts.map((k) => (
                    <Link className="chip brand" key={k}
                      href={`/concept/${k.replace(/ /g, "_")}`}>{k}</Link>
                  ))}
                </div>
              )}
            </div>
          );
        })}
        <button className="btn" style={{ marginTop: 12 }}
          onClick={() => { setAsked([]); setTheta(2.5); }}>다시 풀기</button>
      </>
    );
  }

  return (
    <>
      <Back href={`/learn/${id}`} label={data.title} />
      <div className="banner">
        <b>📊 적응형 진단 · 몇 문제만 풀면 내 수준이 나와요</b>
        <span>틀려도 괜찮아요 — 실력에 맞춰 문제가 조정돼요</span>
      </div>
      <div className="progress"><i style={{ width: `${asked.length / MAX * 100}%` }} /></div>
      <div className="qhead">
        <span className="qtag">{data.title}</span>
        <span className="meta">객관식 · {asked.length + 1} / {MAX}</span>
      </div>
      <div className="qcard">
        <div className="qtext">{next.question}</div>
        {next.choices.map((c, i) => (
          <button className="choice" key={i} onClick={() => answer(i)}>{c}</button>
        ))}
        <button className="choice skip" onClick={() => answer(null)}>
          🤔 모르겠어요 · 다음 문제 →
        </button>
      </div>
      <p className="meta center" style={{ marginTop: 12 }}>
        고르면 바로 다음 문제로 넘어가요 · 정답과 해설은 마지막에 정리해서 보여드려요
      </p>
    </>
  );
}
