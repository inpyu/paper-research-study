# 로드맵 v0.3

**LLM 없이 되는 것 → 로컬 루틴 → 배포 → 앱** 순서. 각 단계가 끝날 때마다 실제로 쓸 수 있어야 한다.

## M0 — 실행 기반 다지기 (반나절)
- [ ] `claude install stable` → `~/.local/bin/claude` 고정 경로 확보
- [ ] GitHub 인증: `~/.ssh/id_rsa_cau.pub` 등록 (또는 PAT credential helper)
- [ ] `~/work/prefill-opt` clone, `main`/`wcep` worktree
- [ ] `routine/routine.sh` 뼈대: flock + 타임아웃 + `logs/routine.log`
- **완료 기준**: cron이 빈 루틴을 돌리고 로그가 남는다. `claude -p`가 cron 환경에서도 성공한다.

## M1 — 파서와 갭 (1주) ★ 가장 중요, LLM 미사용
- [ ] `parse_notes.py` — 개념 헤딩(`## 1-3. Attention`), `← 이어지는 개념`,
      `01-code-map.md` 표 → 코드 근거, `refs.md` 표 → 논문 시드,
      `04-reading-path.md` Stage, `00-RESEARCH-PLAN.md` H1~H5
- [ ] `index_code.py` — tree-sitter 심볼, 코드맵의 함수명 기준 재해석
- [ ] `gaps.py` — G1/G2/G3 + 우선순위 점수
- [ ] `evals/concepts.golden.md` 정답셋 50개 + 파서 회귀 테스트
- **완료 기준**: `python3 routine/gaps.py --top 10`이 stdout에 갭을 출력하고,
  그중 7개 이상이 "실제로 몰랐던 것"이다. **여기서 유용하지 않으면 중단한다.**

## M2 — 정적 사이트와 무중단 배포  ✅ 코드 완료 (Vercel 연결만 남음)
- [x] `build.py` → `site/public/data/*.json` + `manifest.json` (130파일 310KB)
- [x] `site/` Next.js 15 정적 내보내기: 갭 / 개념 / 위키 / 논문 4개 탭, 모바일 우선
- [x] `publish.py` → 검증 통과 시에만 commit & push (개념 50개 미만이면 회귀로 보고 중단)
- [x] 화면에 "마지막 갱신 시각 · head_sha" 표시
- [ ] Vercel 프로젝트 생성 (Root Directory = `site`) — 대시보드에서 import
- **완료 기준**: 폰 브라우저에서 갭 지도를 본다. 매일 아침 자동으로 갱신된다.

## M2.5 — 레포 위키 (4~5일) — 대부분 LLM 미사용
- [ ] `wiki.py` — 파일 페이지(22) · 플래그 사전(70) · 실험 카드(16) · 수치 대사전 · 열린 질문 · 용어 역인덱스
- [ ] `artifacts/*/manifest.json`·`hosts.tsv`·`raw/*.log` 파서
- [ ] G4~G8(문서화 갭) 산출
- [ ] 위키 화면 + 출처 배지(`노트 인용` / `파싱 사실` / `생성된 서술`)
- **완료 기준**: 미문서 플래그 48개와 미문서 파일 13개가 목록으로 뜬다. 서술 생성은 아직 없어도 된다.

## M3 — 논문 브리핑  ✅ 완료
- [x] `arxiv.py` 시드 37편 정규화(arXiv API) + 신규 수집 + **정규화 BM25** 랭킹
- [x] `generate.py` 브리핑 생성(헤드리스 Haiku) + jsonschema 검증 + 중복 제거 + 재시도
- [x] `notify.py` ntfy.sh 푸시 (계정·키 불필요, 서버가 직접 발송)
- [x] 브리핑 탭 + `refs.md` 한 줄 복사 버튼
- [x] cron 등록: 매일 06:10
- **완료 기준**: 매일 아침 폰 알림이 오고, 눌러서 3편을 읽는다.

## M4 — 학습 콘텐츠 (1주)
- [ ] 갭 설명 생성(하루 5건) + 퀴즈 생성 + 사후 근거 검증
- [ ] 퀴즈 UI + 복습 큐(localStorage) + 내보내기/가져오기
- **완료 기준**: 갭 → 학습 → 퀴즈 → 복습이 한 바퀴 돈다.

## M4.5 — 위키 서술 생성 (병행, 하루 5건)
- [ ] 미문서 플래그·파일 서술 생성 + 인용 `file:line` 사후 검증
- [ ] 실행 경로 페이지 · 로그 사전
- **완료 기준**: 10일이면 플래그 사전이 다 채워진다.

## M5 — 네이티브 앱 (1주)
- [ ] nvm으로 Node 설치(앱 개발용), Expo 프로젝트
- [ ] 같은 JSON을 소비하는 4개 화면 + 오프라인 캐시
- [ ] Expo Push로 알림 전환, EAS 개인 배포
- **완료 기준**: 지하철에서 오프라인으로 브리핑과 퀴즈를 본다.

## M7 — 그다음
- 브랜치 비교(`main` vs `wcep` 신규 개념), push 훅으로 즉시 재생성,
  브리핑 → `refs.md` PR 자동 제안, 노트 수식 ↔ 논문 수식 대응

---

## 지금 당장의 첫 3개
1. **`parse_notes.py` + `gaps.py`를 stdout 스크립트로 먼저 쓴다.** 사이트도 배포도 없이.
   G3 상위 10개를 보고 판단한다. (반나절)
2. `evals/concepts.golden.md` — 내가 아는 개념 50개를 손으로 적는다.
   같은 스크립트에서 **미문서 플래그 48개 목록**도 함께 뽑는다(3줄이면 나온다).
3. `claude install stable` + GitHub SSH 키 등록 (10분)
