/** @type {import('next').NextConfig} */
// 정적 내보내기 — 서버 함수는 하나도 만들지 않는다.
// trailingSlash 를 켜면 /learn/index.html 형태로 나와 어떤 정적 서버에서도 동작한다.
export default {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
};
