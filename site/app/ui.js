"use client";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

export const REPO_URL = "https://github.com/inpyu/prefill-opt/blob/main/";

/** 정적 사이트라 데이터는 클라이언트가 받는다.
 *  경로가 바뀌면 옛 데이터로 새 화면을 그리지 않도록 출처를 함께 들고 다닌다.
 */
export function useJson(path) {
  const [st, setSt] = useState({ path: null, data: null, error: null });
  useEffect(() => {
    if (!path) return;
    let alive = true;
    fetch(`/data/${path}`)          // 도메인 루트에 배포되므로 절대경로가 안전하다
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((j) => alive && setSt({ path, data: j, error: null }))
      .catch((e) => alive && setSt({ path, data: null, error: String(e.message || e) }));
    return () => { alive = false; };
  }, [path]);
  return st.path === path ? st : { path, data: null, error: null };
}

export const hhmm = (m) => {
  if (!m) return "";
  const h = Math.floor(m / 60), r = m % 60;
  return h ? `${h}시간 ${r}분` : `${r}분`;
};
export const ago = (iso) => {
  if (!iso) return "";
  const h = (Date.now() - new Date(iso)) / 36e5;
  if (h < 1) return "방금";
  if (h < 24) return `${Math.floor(h)}시간 전`;
  return `${Math.floor(h / 24)}일 전`;
};

export const Loading = () => <div className="empty">불러오는 중…</div>;
export const Failed = ({ e }) => (
  <div className="empty">데이터를 불러오지 못했습니다 ({e})</div>
);
export const Chips = ({ items, brand }) =>
  (items || []).map((t) => (
    <span className={`chip${brand ? " brand" : ""}`} key={t}>{t}</span>
  ));

export function Section({ title, children }) {
  if (!children) return null;
  return (<><div className="sec">{title}</div><p className="body">{children}</p></>);
}

export function Back({ href, label }) {
  const router = useRouter();
  return (
    <div className="crumb">
      <button className="back" onClick={() => router.back()}>← 뒤로</button>
      {href && <><span>·</span><Link href={href}>{label}</Link></>}
    </div>
  );
}

const NAV = [
  ["/learn", "학습"], ["/brief", "브리핑"], ["/concept", "개념"],
  ["/code", "코드"], ["/paper", "논문"], ["/sitemap", "사이트맵"],
];

export function TopBar() {
  const path = usePathname() || "/";
  const { data: m } = useJson("manifest.json");
  return (
    <header className="topbar">
      <div className="topin">
        <div className="brandrow">
          <Link href="/" className="brand">
            <span className="logo">R</span>
            RepoScholar <small>· inpyu/prefill-opt</small>
          </Link>
          <span className="meta">{m ? `${ago(m.generated_at)} 갱신` : ""}</span>
        </div>
        <nav>
          {NAV.map(([href, label]) => {
            const on = path === href || path.startsWith(href + "/");
            return (
              <Link key={href} href={href} aria-current={on ? "page" : undefined}>
                {label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}

/** 즐겨찾기 — 정적 사이트라 서버가 없다. 이 기기에만 남는다. */
export function useStar() {
  const [set, setSet] = useState(() => new Set());
  useEffect(() => {
    try { setSet(new Set(JSON.parse(localStorage.getItem("stars") || "[]"))); }
    catch { /* 저장소를 막아둔 브라우저 */ }
  }, []);
  const toggle = (id) => setSet((prev) => {
    const n = new Set(prev);
    n.has(id) ? n.delete(id) : n.add(id);
    try { localStorage.setItem("stars", JSON.stringify([...n])); } catch { }
    return n;
  });
  return [set, toggle];
}

export { Link, useMemo, useState, useEffect };
