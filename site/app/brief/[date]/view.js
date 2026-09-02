"use client";
import { Link, useJson, Section, Loading, Failed, Back, Chips } from "../../ui";

const V = { "must-read": ["필독", "chip warn"], skim: ["훑기", "chip"], skip: ["넘김", "chip"] };

export default function BriefView({ date }) {
  const { data, error } = useJson(`briefing/${date}.json`);
  if (error) return <Failed e={error} />;
  if (!data) return <Loading />;
  return (
    <>
      <Back href="/brief" label="브리핑" />
      <h1 className="page">{data.date}</h1>
      <p className="lead">후보 {data.all?.length ?? "?"}편 중 {data.items.length}편</p>
      {data.items.map((b, i) => {
        const [label, cls] = V[b.verdict] || [b.verdict, "chip"];
        return (
          <div className="card" key={i} style={{ padding: "16px 18px" }}>
            <div className="t">
              <span className="n">
                <span className={cls} style={{ marginRight: 7 }}>{label}</span>
                <a href={b.url} target="_blank" rel="noreferrer">{b.title}</a>
              </span>
              <span className="s">{b.published}</span>
            </div>
            <Section title="무엇을 했나">{b.what}</Section>
            <Section title="우리 연구와의 관계">{b.relation}</Section>
            <Section title="우리 체제와의 간극">{b.gap}</Section>
            <div style={{ marginTop: 8 }}><Chips items={b.topics} brand /></div>
            {(b.hypothesis_notes || []).map((h, j) => (
              <div className="d" key={j}>· {h}</div>
            ))}
            <button className="btn" style={{ marginTop: 10 }}
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
