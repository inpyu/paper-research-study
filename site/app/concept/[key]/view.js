"use client";
import { Link, useJson, Section, Loading, Failed, Back, Chips } from "../../ui";

const slug = (k) => k.replace(/ /g, "_");

export default function ConceptView({ file }) {
  const { data: c, error } = useJson(`concept/${file}.json`);
  const { data: idx } = useJson("concepts.json");
  const nameOf = (k) => idx?.items?.find((x) => x.key === k)?.name || k;
  if (error) return <Failed e={error} />;
  if (!c) return <Loading />;

  const Links = ({ title, keys, texts }) => {
    const all = [...(keys || []).map((k) => [k, nameOf(k)]),
                 ...(texts || []).map((l) => [l.to_key, l.to_text])];
    if (!all.length) return null;
    return (
      <>
        <div className="sec">{title}</div>
        <div>{all.map(([k, label], i) => (
          <Link className="chip brand" key={`${k}-${i}`} href={`/concept/${slug(k)}`}>{label}</Link>
        ))}</div>
      </>
    );
  };

  return (
    <>
      <Back href="/concept" label="개념" />
      <h1 className="page">
        {c.name}
        {c.track === "foundation" && <span className="chip brand" style={{ marginLeft: 9, verticalAlign: "middle" }}>기초</span>}
      </h1>
      {c.one_liner && <p className="lead">{c.one_liner}</p>}
      <div style={{ marginBottom: 4 }}>
        {c.difficulty > 0 && <span className="chip">난이도 {c.difficulty}/5</span>}
        <Chips items={c.tags} />
        {c.aliases?.length > 0 && <span className="meta"> {c.aliases.join(" · ")}</span>}
      </div>

      {!c.what && <div className="notice">아직 설명이 생성되지 않았습니다. 매일 루틴이 순서대로 채웁니다.</div>}
      <Section title="무엇인가">{c.what}</Section>
      <Section title="왜 필요한가">{c.why}</Section>
      <Section title="어떻게 동작하는가">{c.how}</Section>
      <Section title="예시">{c.example}</Section>
      <Section title="이 연구에서는">{c.in_this_repo || c.for_this_research}</Section>

      <Links title="먼저 알아야 할 개념" keys={c.prerequisites} />
      <Links title="이걸 알면 읽을 수 있게 되는 것" keys={c.leads_to} />
      <Links title="함께 보면 좋은 개념" keys={c.related_keys} texts={c.links} />

      {c.defs?.length > 0 && (
        <>
          <div className="sec">노트에서 읽기</div>
          {c.defs.map((d, i) => (
            <a className="row" key={i} href={d.url} target="_blank" rel="noreferrer">
              <span className="mono">{d.doc.replace("research/", "")}</span>
              <span className="s">:{d.line}</span>
            </a>
          ))}
        </>
      )}
      {c.track !== "foundation" && (
        <>
          <div className="sec">코드에서 보기</div>
          {!c.evidence?.length
            ? <div className="empty">이 개념에 대응하는 코드를 찾지 못했습니다.</div>
            : c.evidence.map((e, i) => (
              <a className="row" key={i} href={e.url} target="_blank" rel="noreferrer">
                <span className="mono">{e.file}</span>
                <span className="s">{e.line_start ? `:${e.line_start}` : ""}</span>
              </a>
            ))}
        </>
      )}
    </>
  );
}
