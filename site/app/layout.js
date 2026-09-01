import "./globals.css";

export const metadata = {
  title: "RepoScholar — prefill-opt",
  description: "연구 노트와 코드를 대조해 갭을 짚어주는 학습 대시보드",
};

export default function RootLayout({ children }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
