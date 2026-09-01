/** @type {import('next').NextConfig} */
// 정적 내보내기 — Vercel 이 빌드하고, 서버 함수는 하나도 만들지 않는다.
export default { output: "export", images: { unoptimized: true } };
