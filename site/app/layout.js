import "./globals.css";
import { TopBar } from "./ui";

export const metadata = {
  title: "RepoScholar — prefill-opt",
  description: "연구 노트와 코드를 학습 자료로. 커리큘럼 · 개념 · 코드 · 논문 브리핑",
};

export default function RootLayout({ children }) {
  return (
    <html lang="ko">
      <body>
        <TopBar />
        <main className="wrap">{children}</main>
      </body>
    </html>
  );
}
