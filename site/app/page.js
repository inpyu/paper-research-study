"use client";
import { useEffect, useMemo, useState } from "react";

const TABS = [["learn", "학습"], ["brief", "브리핑"], ["concept", "개념"],
              ["code", "코드"], ["paper", "논문"]];

const hhmm = (m) => {
  if (!m) return "";
  const h = Math.floor(m / 60), r = m % 60;
  return h ? `${h}시간 ${r}분` : `${r}분`;
};

// 즐겨찾기는 이 기기에만 남는다(정적 사이트라 서버가 없다).
const useStar = () => {
  const [set, setSet] = useState(() => new Set());
  useEffect(() => {
    try {
      setSet(new Set(JSON.parse(localStorage.getItem("stars") || "[]")));
    } catch { /* 저장소를 막아둔 브라우저 */ }
  }, []);
  const toggle = (id) => setSet((prev) => {
    const n = new Set(prev);
    n.has(id) ? n.delete(id) : n.add(id);
    try { localStorage.setItem("stars", JSON.stringify([...n])); } catch { }
    return n;
  });
  return [set, toggle];
};
const REPO_URL = "https://github.com/inpyu/prefill-opt/blob/main/";

// 탭을 바꾸면 path 는 즉시 바뀌지만 데이터는 한 박자 늦게 온다.
// 그 사이 새 탭이 옛 데이터 모양으로 그려져 터졌다. 경로가 일치할 때만 렌더한다.
const useJson = (path) => {
  const [st, setSt] = useState({ path: null, data: null, error: null });
  useEffect(() => {
    let alive = true;
    fetch(`./data/${path}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((j) => alive && setSt({ path, data: j, error: null }))
      .catch((e) => alive && setSt({ path, data: null, error: String(e.message || e) }));
    return () => { alive = false; };
  }, [path]);
  return st.path === path ? st : { path, data: null, error: null };
};

const ago = (iso) => {
  if (!iso) return "";
  const h = (Date.now() - new Date(iso)) / 36e5;
  if (h < 1) return "방금";
  if (h < 24) return `${Math.floor(h)}시간 전`;
  return `${Math.floor(h / 24)}일 전`;
};

const Loading = () => <div className="empty">불러오는 중…</div>;
const Failed = ({ e }) => <div className="empty">데이터를 불러오지 못했습니다 ({e})</div>;
const Tags = ({ items }) => (items || []).map((t) => <span className="pill" key={t}>{t}</span>);

function Section({ title, children }) {
  if (!children) return null;
  return (
    <>
      <div className="sec">{title}</div>
      <p className="body">{children}</p>
    </>
  );
}

/* ================= 적응형 진단 ================= */
function Diagnose({ course, title, onBack }) {
  const { data, error } = useJson(`quiz/${course}.json`);
  const [asked, setAsked] = useState([]);      // {item, picked} picked=null 은 모르겠어요
  const [theta, setTheta] = useState(2.5);
  const MAX = 8;

  const next = useMemo(() => {
    if (!data) return null;
    const seen = new Set(asked.map((a) => a.item.id));
    const pool = data.items.filter((i) => !seen.has(i.id));
    if (!pool.length || asked.length >= MAX) return null;
    // 지금 추정 실력에 가장 가까운 난이도를 낸다
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
        <button className="pill" onClick={onBack}>← 뒤로</button>
        <h2 className="title">진단 결과</h2>
        <div className="stats">
          <div className="stat"><b>{graded.length ? Math.round(right.length / graded.length * 100) : 0}%</b>
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
            <div className="card" key={i}
              style={{ borderLeft: `3px solid ${picked === null ? "var(--line)" : ok ? "var(--ok)" : "var(--warn)"}` }}>
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
            </div>
          );
        })}
        <button className="pill big" onClick={() => { setAsked([]); setTheta(2.5); }}>
          다시 풀기
        </button>
      </>
    );
  }

  return (
    <>
      <button className="pill" onClick={onBack}>← 뒤로</button>
      <div className="banner">
        <b>📊 적응형 진단 · 몇 문제만 풀면 내 수준이 나와요</b>
        <span>틀려도 괜찮아요 — 실력에 맞춰 문제가 조정돼요</span>
      </div>
      <div className="qhead">
        <span className="qtag">{title}</span>
        <span className="meta">객관식 · {asked.length + 1}문제째</span>
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
      <p className="meta center">
        고르면 바로 다음 문제로 넘어가요 · 정답과 해설은 마지막에 정리해서 보여드려요
      </p>
    </>
  );
}

/* ================= 학습 카탈로그 ================= */
function Learn({ openConcept }) {
  const { data, error } = useJson("catalog.json");
  const [course, setCourse] = useState(null);
  const [quiz, setQuiz] = useState(null);
  const [stars, toggleStar] = useStar();

  if (quiz) return <Diagnose course={quiz.id} title={quiz.title}
                             onBack={() => setQuiz(null)} />;
  if (error) return <Failed e={error} />;
  if (!data) return <Loading />;

  if (course) {
    const c = data.tracks.flatMap((t) => t.courses).find((x) => x.id === course);
    if (!c) return <Failed e="과목 없음" />;
    return (
      <>
        <button className="pill" onClick={() => setCourse(null)}>← 과목 목록</button>
        <h2 className="title">{c.title}</h2>
        {c.summary && <p className="lead">{c.summary}</p>}
        <p className="meta">{c.lessons.length} 레슨 · {hhmm(c.minutes)}</p>
        {c.has_quiz && (
          <button className="cta" onClick={() => setQuiz({ id: c.id, title: c.title })}>
            📊 적응형 진단 시작
          </button>
        )}
        <div className="sec">레슨</div>
        {c.lessons.map((l, i) => (
          <div className="card" key={l.id}>
            <div className="t">
              <span className="n"><span className="dim">{i + 1}.</span> {l.title}</span>
              <span className="s">{l.minutes}분</span>
            </div>
            <div className="d">{l.one_liner}</div>
            {l.concepts?.length > 0 && (
              <div className="d">
                {l.concepts.map((k) => (
                  <button className="pill" key={k} onClick={() => openConcept(k)}>{k}</button>
                ))}
              </div>
            )}
          </div>
        ))}
      </>
    );
  }

  return (
    <>
      <p className="meta">
        {data.lesson_count} 레슨 · 총 {hhmm(data.minutes)}
      </p>
      {data.tracks.map((t) => (
        <div key={t.id}>
          <div className="sec">
            {t.title}
            <span className="meta"> · {t.course_count} 과목 · {hhmm(t.minutes)}</span>
          </div>
          {t.courses.map((c) => (
            <div className="card" key={c.id}>
              <div className="t">
                <span className="n" style={{ cursor: c.lessons?.length ? "pointer" : "default" }}
                  onClick={() => c.lessons?.length && setCourse(c.id)}>
                  <span className="star" onClick={(e) => { e.stopPropagation(); toggleStar(c.id); }}>
                    {stars.has(c.id) ? "★" : "☆"}
                  </span>
                  {c.title}
                </span>
                <span className="s">
                  {c.lessons?.length
                    ? `${c.lessons.length} 레슨 · ${hhmm(c.minutes)}`
                    : "준비 중"}
                </span>
              </div>
              {c.has_quiz && (
                <button className="pill" style={{ marginTop: 6 }}
                  onClick={() => setQuiz({ id: c.id, title: c.title })}>
                  📊 진단 풀기
                </button>
              )}
            </div>
          ))}
        </div>
      ))}
    </>
  );
}

/* ================= 브리핑 ================= */
const VERDICT = { "must-read": ["필독", "warn"], skim: ["훑기", ""], skip: ["넘김", ""] };

function Briefings() {
  const [day, setDay] = useState(null);
  const idx = useJson("briefings.json");
  const one = useJson(day ? `briefing/${day}.json` : "briefings.json");

  if (day) {
    if (one.error) return <Failed e={one.error} />;
    if (!one.data || one.data.date !== day) return <Loading />;
    return (
      <>
        <button className="pill" onClick={() => setDay(null)}>← 날짜 목록</button>
        <div className="sec">{one.data.date}</div>
        {one.data.items.map((b, i) => {
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
              <Section title="무엇을 했나">{b.what}</Section>
              <Section title="우리 연구와의 관계">{b.relation}</Section>
              <Section title="우리 체제와의 간극">{b.gap}</Section>
              {b.abstract && <details><summary className="meta">초록 원문</summary>
                <p className="body" style={{ color: "var(--dim)" }}>{b.abstract}</p></details>}
              <div style={{ marginTop: 8 }}>
                <Tags items={b.topics} />
                {(b.hypothesis_notes || []).map((h, j) => (
                  <div className="d" key={j}>· {h}</div>
                ))}
              </div>
              <button className="pill" style={{ marginTop: 8 }}
                onClick={() => navigator.clipboard?.writeText(
                  `| **${b.title}** [arXiv](${b.url}) | ${b.what} | ${b.gap || ""} |`)}>
                refs.md 한 줄 복사
              </button>
            </div>
          );
        })}
      </>
    );
  }
  if (idx.error) return <Failed e={idx.error} />;
  if (!idx.data) return <Loading />;
  if (!idx.data.count) return <div className="empty">아직 브리핑이 없습니다.</div>;
  return (
    <>
      <p className="meta">매일 아침 arXiv 신규 논문을 이 연구의 선행연구와 대조해 추립니다.</p>
      {idx.data.items.map((b) => (
        <div key={b.date} onClick={() => setDay(b.date)} style={{ cursor: "pointer" }}>
          <div className="card">
            <div className="t">
              <span className="n">{b.date}</span>
              <span className="s">{b.must ? `필독 ${b.must}편` : `${b.count}편`}</span>
            </div>
            <div className="d">{b.titles.join(" · ")}</div>
          </div>
        </div>
      ))}
    </>
  );
}

/* ================= 개념 ================= */
function ConceptDetail({ k, onOpen, onBack, index }) {
  const { data: c, error } = useJson(`concept/${k.replace(/ /g, "_")}.json`);
  const nameOf = (key) => index?.find((x) => x.key === key)?.name || key;
  if (error) return <Failed e={error} />;
  if (!c) return <Loading />;
  return (
    <>
      <button className="pill" onClick={onBack}>← 목록</button>
      <h2 className="title">
        {c.name}
        {c.track === "foundation" && <span className="pill" style={{ marginLeft: 8, fontSize: 11 }}>기초</span>}
      </h2>
      {c.one_liner && <p className="lead">{c.one_liner}</p>}
      <div style={{ margin: "6px 0 4px" }}>
        {c.difficulty > 0 && <span className="pill">난이도 {c.difficulty}/5</span>}
        <Tags items={c.tags} />
        {c.aliases?.length > 0 && <span className="meta"> {c.aliases.join(" · ")}</span>}
      </div>

      {!c.what && (
        <div className="notice">아직 설명이 생성되지 않았습니다. 매일 루틴이 순서대로 채웁니다.</div>
      )}
      <Section title="무엇인가">{c.what}</Section>
      <Section title="왜 필요한가">{c.why}</Section>
      <Section title="어떻게 동작하는가">{c.how}</Section>
      <Section title="예시">{c.example}</Section>
      <Section title="이 연구에서는">{c.in_this_repo || c.for_this_research}</Section>

      {c.leads_to?.length > 0 && (
        <>
          <div className="sec">이걸 알면 읽을 수 있게 되는 것</div>
          {c.leads_to.map((p) => (
            <button className="pill big" key={p} onClick={() => onOpen(p)}>{nameOf(p)}</button>
          ))}
        </>
      )}

      {c.prerequisites?.length > 0 && (
        <>
          <div className="sec">먼저 알아야 할 개념</div>
          {c.prerequisites.map((p) => (
            <button className="pill big" key={p} onClick={() => onOpen(p)}>{nameOf(p)}</button>
          ))}
        </>
      )}
      {(c.related_keys?.length > 0 || c.links?.length > 0) && (
        <>
          <div className="sec">함께 보면 좋은 개념</div>
          {(c.related_keys || []).map((p) => (
            <button className="pill big" key={p} onClick={() => onOpen(p)}>{nameOf(p)}</button>
          ))}
          {(c.links || []).map((l, i) => (
            <button className="pill big" key={`l${i}`} onClick={() => onOpen(l.to_key)}>
              {l.to_text}
            </button>
          ))}
        </>
      )}

      {c.defs.length > 0 && <div className="sec">노트에서 읽기</div>}
      {c.defs.map((d, i) => (
        <a className="row" key={i} href={d.url} target="_blank" rel="noreferrer">
          <span className="mono">{d.doc.replace("research/", "")}</span>
          <span className="s">:{d.line}</span>
        </a>
      ))}
      {c.track !== "foundation" && <div className="sec">코드에서 보기</div>}
      {c.track === "foundation" ? null : c.evidence.length === 0
        ? <div className="empty">이 개념에 대응하는 코드를 찾지 못했습니다.</div>
        : c.evidence.map((e, i) => (
          <a className="row" key={i} href={e.url} target="_blank" rel="noreferrer">
            <span className="mono">{e.file}</span>
            <span className="s">{e.line_start ? `:${e.line_start}` : ""}</span>
          </a>
        ))}
    </>
  );
}

function Concepts({ jump, clearJump }) {
  const { data: idx, error } = useJson("concepts.json");
  const [q, setQ] = useState("");
  const [sel, setSel] = useState(null);
  const [mode, setMode] = useState("order");
  useEffect(() => { if (jump) { setSel(jump); clearJump?.(); } }, [jump]);

  const byKey = useMemo(
    () => Object.fromEntries((idx?.items || []).map((c) => [c.key, c])), [idx]);

  if (sel) return <ConceptDetail k={sel} index={idx?.items} onOpen={setSel}
                                 onBack={() => setSel(null)} />;
  if (error) return <Failed e={error} />;
  if (!idx) return <Loading />;

  const s = q.trim().toLowerCase();
  const match = (c) => !s || c.name.toLowerCase().includes(s) ||
    (c.one_liner || "").toLowerCase().includes(s) ||
    (c.tags || []).some((t) => t.toLowerCase().includes(s));

  const Item = ({ c }) => (
    <div onClick={() => setSel(c.key)} style={{ cursor: "pointer" }}>
      <div className="card">
        <div className="t">
          <span className="n">
            {c.name}
            {c.track === "foundation" && <span className="pill" style={{ marginLeft: 6, fontSize: 10.5 }}>기초</span>}
          </span>
          <span className="s">{c.difficulty ? `난이도 ${c.difficulty}` : ""}</span>
        </div>
        {c.one_liner
          ? <div className="d">{c.one_liner}</div>
          : <div className="d" style={{ color: "var(--dim)" }}>설명 생성 대기</div>}
      </div>
    </div>
  );

  return (
    <>
      <div className="switch">
        {[["order", "학습 순서"], ["all", "전체 목록"]].map(([k, label]) => (
          <button key={k} className="pill" data-on={mode === k}
            onClick={() => setMode(k)}>{label}</button>
        ))}
        <span className="meta">설명 {idx.explained}/{idx.count}</span>
      </div>
      <input type="search" placeholder="개념·태그 검색" value={q}
        onChange={(e) => setQ(e.target.value)} />
      {mode === "order" && !s && (
        <p className="meta">
          딥러닝 기초부터 시작해 이 연구의 용어까지 순서대로 이어집니다.
        </p>
      )}
      {mode === "order" && !s
        ? <>
          {(idx.foundation_stages || []).map((st) => (
            <div key={`f${st.stage}`}>
              <div className="sec">
                기초 {st.stage} · {st.title}
                <span className="meta"> · {st.keys.length}개</span>
              </div>
              {st.goal && <p className="meta" style={{ margin: "0 0 8px" }}>{st.goal}</p>}
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
        : (idx.order || idx.items.map((c) => c.key))
          .map((k) => byKey[k]).filter((c) => c && match(c))
          .map((c) => <Item c={c} key={c.key} />)}
    </>
  );
}

/* ================= 코드 ================= */
function CodeDetail({ path, onBack }) {
  const { data: d, error } = useJson(`code/${path.replace(/\//g, "_")}.json`);
  if (error) return <Failed e={error} />;
  if (!d) return <Loading />;
  return (
    <>
      <button className="pill" onClick={onBack}>← 파일 목록</button>
      <h2 className="title mono">{d.file}</h2>
      <div style={{ margin: "6px 0" }}>
        <Tags items={d.tags} />
        <span className="meta">{d.loc}줄 · 함수 {d.symbol_count}개 · 변경 {d.churn}회</span>
      </div>
      <Section title="이 파일이 하는 일">{d.role}</Section>
      <Section title="이 연구에서 왜 중요한가">{d.why_it_matters}</Section>
      <Section title="어디부터 읽을까">{d.read_order}</Section>
      <div className="sec">함수 {d.functions.length}개</div>
      {d.functions.map((f, i) => (
        <div className="card" key={i}>
          <div className="t">
            <a className="n mono" href={f.url} target="_blank" rel="noreferrer">{f.name}</a>
            <span className="s">:{f.line}</span>
          </div>
          <div className="d" style={{ color: "var(--fg)" }}>{f.what}</div>
          {f.note && <div className="d">{f.note}</div>}
        </div>
      ))}
      <a className="row" href={d.url} target="_blank" rel="noreferrer">GitHub 에서 전체 보기</a>
    </>
  );
}

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
        {d.traces.map((x, j) => (
          <button key={j} className="pill" data-on={i === j} onClick={() => setI(j)}>
            {x.label}
          </button>
        ))}
      </div>
      <p className="meta">프롬프트 하나가 들어왔을 때 호출되는 순서입니다.</p>
      {rows.map(({ k, n, depth }, j) => (
        <a key={j} href={n.url} target="_blank" rel="noreferrer"
           style={{ textDecoration: "none", display: "block",
                    marginLeft: Math.min(depth, 4) * 14 }}>
          <div className="card tight">
            <div className="t">
              <span className="n mono" style={{ fontSize: 13 }}>{k.split("#")[1]}</span>
            </div>
            <div className="d mono">{n.file.replace("src/", "")}:{n.line}</div>
          </div>
        </a>
      ))}
    </>
  );
}

function Code() {
  const { data: d, error } = useJson("wiki/files.json");
  const [sel, setSel] = useState(null);
  const [view, setView] = useState("files");
  const [q, setQ] = useState("");
  if (sel) return <CodeDetail path={sel} onBack={() => setSel(null)} />;
  return (
    <>
      <div className="switch">
        {[["files", "파일별 설명"], ["trace", "실행 경로"]].map(([k, label]) => (
          <button key={k} className="pill" data-on={view === k}
            onClick={() => setView(k)}>{label}</button>
        ))}
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
            .map((f) => (
              <div key={f.path} onClick={() => f.doc && setSel(f.path)}
                style={{ cursor: f.doc ? "pointer" : "default" }}>
                <div className="card">
                  <div className="t">
                    <span className="n mono">{f.path.replace("src/", "")}</span>
                    <span className="s">{f.loc}줄</span>
                  </div>
                  {f.role
                    ? <><div className="d" style={{ color: "var(--fg)" }}>{f.role}</div>
                        <div className="d"><Tags items={f.tags} />
                          <span className="meta">함수 {f.functions}개 설명</span></div></>
                    : <div className="d" style={{ color: "var(--dim)" }}>설명 생성 대기</div>}
                </div>
              </div>
            ))}
        </>
      )}
    </>
  );
}

/* ================= 논문 ================= */
function Papers() {
  const { data: d, error } = useJson("papers.json");
  if (error) return <Failed e={error} />;
  if (!d) return <Loading />;
  return (
    <>
      <p className="meta">research/refs.md 에서 추출한 선행연구. 매일 브리핑의 기준점입니다.</p>
      {d.items.map((p, i) => (
        <a className="card block" key={i} href={p.url} target="_blank" rel="noreferrer">
          <div className="t">
            <span className="n">{p.title || p.id}</span>
            <span className="s">{p.id}</span>
          </div>
          {p.gap && <div className="d">간극: {p.gap}</div>}
          <div className="d">{p.cited_in.map((s) => s.replace("research/", "")).join(", ")}</div>
        </a>
      ))}
    </>
  );
}

/* ================= 껍데기 ================= */
export default function Page() {
  const { data: m } = useJson("manifest.json");
  const [tab, setTab] = useState("learn");
  const [jump, setJump] = useState(null);
  return (
    <>
      <header>
        <div className="hrow">
          <h1>RepoScholar <span className="dim">· inpyu/prefill-opt</span></h1>
          <span className="meta">{m ? `${ago(m.generated_at)} 갱신` : ""}</span>
        </div>
        <nav>
          {TABS.map(([k, label]) => (
            <button key={k} data-on={tab === k} onClick={() => setTab(k)}>{label}</button>
          ))}
        </nav>
      </header>
      <main className="wrap">
        {tab === "learn" && <Learn openConcept={(k) => { setJump(k); setTab("concept"); }} />}
        {tab === "brief" && <Briefings />}
        {tab === "concept" && <Concepts jump={jump} clearJump={() => setJump(null)} />}
        {tab === "code" && <Code />}
        {tab === "paper" && <Papers />}
      </main>
    </>
  );
}
