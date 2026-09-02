"use client";
import { useJson, Section, Loading, Failed, Back, Chips } from "../../ui";

export default function FileView({ file }) {
  const { data: d, error } = useJson(`code/${file}.json`);
  if (error) return <Failed e={error} />;
  if (!d) return <Loading />;
  return (
    <>
      <Back href="/code" label="코드" />
      <h1 className="page mono" style={{ fontSize: 21 }}>{d.file}</h1>
      <div style={{ margin: "6px 0 2px" }}>
        <Chips items={d.tags} brand />
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
      <a className="row" href={d.url} target="_blank" rel="noreferrer">
        <span>GitHub 에서 전체 보기</span><span className="s">↗</span>
      </a>
    </>
  );
}
