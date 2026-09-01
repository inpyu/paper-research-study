# 아키텍처 v0.3 — 로컬 루틴 생성 + 정적 무중단 배포

## 0. 무엇이 바뀌었나 (v0.2 → v0.3)

v0.2는 "사용자가 Anthropic API 키를 등록하면 서버가 그 키로 LLM을 호출"하는 BYOK 구조였다.
**과금 지점을 아예 없애기 위해** 구조를 뒤집는다.

```
v0.2  브라우저 → Vercel 함수 → Anthropic API(사용자 키, 토큰 과금)   ← 과금 지점 존재
v0.3  이 서버(cron) → Claude Code 헤드리스(구독) → 정적 파일 생성
                    → git push → Vercel 자동 배포
      브라우저/앱 → 정적 JSON만 읽음                                  ← 과금 지점 0
```

**배포된 사이트는 LLM을 단 한 번도 호출하지 않는다.** 이것이 v0.3의 정의다.

### 이 전환으로 사라지는 것들 (v0.2 설계의 절반이 불필요해짐)

| v0.2에서 필요했던 것 | v0.3에서 |
|---|---|
| API 키 AES 암호화 저장 | **불필요** — 키를 다루지 않음 |
| 토큰 예산 하드 캡 · 사용량 추적 | **불필요** — 구독 사용량만 로깅 |
| 함수 300초 제약 대응 스텝 큐 | **불필요** — 로컬에서 시간 제한 없이 실행 |
| GitHub tarball API 인메모리 해제 | **불필요** — `git pull`로 직접 읽음 |
| cron 1회/일 제약 우회 | **불필요** — 로컬 cron은 원하는 만큼 |
| Postgres + pgvector | **선택** — 정적 JSON으로 충분, 필요해지면 도입 |

남는 것은 파이프라인 본체와 UI뿐이다. **구현량이 절반 이하로 줄었다.**

---

## 1. 검증된 실행 환경 (2026-09-01 이 서버에서 직접 확인)

| 항목 | 확인 결과 |
|---|---|
| Claude Code 바이너리 | `~/.vscode-server/extensions/anthropic.claude-code-2.1.252-linux-x64/resources/native-binary/claude` (v2.1.252) |
| 헤드리스 실행 | `claude -p "..." --output-format json` → **exit 0, 정상 응답** |
| 과금 상태 | 구독 계정, `extra_usage_disabled` — 초과 과금 비활성 |
| cron | `systemctl is-active cron` → **active**, 사용자 crontab 비어 있음 |
| 가동 | uptime 3일 5시간, 디스크 여유 515G |
| 외부 접근 | api.github.com 200, export.arxiv.org 200 |
| Python | 3.10.12 |
| Node/npm | **없음** — 루틴은 Node 없이 동작하게 설계(앱 개발 시에만 nvm 설치) |
| GitHub push | **미설정** — `~/.ssh/id_rsa_cau.pub`는 있으나 GitHub에 미등록 (설정 필요) |

### 설정이 필요한 두 가지
1. **안정된 바이너리 경로** — VSCode 확장이 업데이트되면 위 경로가 바뀐다.
   `claude install stable`로 `~/.local/bin/claude`에 설치하고 cron은 그 경로만 쓴다.
2. **GitHub 인증** — `~/.ssh/id_rsa_cau.pub`를 GitHub에 등록하거나 PAT을 credential helper에 저장.

---

## 2. 전체 구조

```
┌─ 이 서버 (상시 가동) ────────────────────────────────────┐
│  cron  06:00 매일                                        │
│   └ routine.sh                                           │
│      1. git pull   prefill-opt (main, wcep)              │
│      2. parse.py   research/*.md 파싱 → 개념·링크·갭      │  LLM 0
│      3. arxiv.py   신규 논문 수집 → 후보 필터링           │  LLM 0
│      4. claude -p  갭 설명 · 퀴즈 · 브리핑 생성 → JSON     │  구독
│      5. build.py   site/public/data/*.json 갱신           │
│      6. git commit && git push  (변경 있을 때만)          │
│      7. notify.py  푸시 알림 발송 (ntfy / Expo Push)      │
└──────────────────────────────────────────────────────────┘
            │ push
            ▼
        [ GitHub: inpyu/paper-research-study ]
            │ webhook
            ▼
        [ Vercel Hobby ] 자동 빌드 → 원자적 배포(무중단) · 즉시 롤백
            │
      ┌─────┴─────┐
   [ 웹 ]      [ Expo 앱 ]        둘 다 정적 JSON만 fetch. LLM 호출 0
```

### 무중단 배포가 성립하는 이유
Vercel은 새 배포를 **먼저 빌드해 준비한 뒤 트래픽을 원자적으로 전환**한다.
빌드가 실패하면 기존 배포가 그대로 유지되고, 문제가 생기면 이전 배포로 즉시 롤백할 수 있다.
루틴이 실패하거나 서버가 꺼져도 **사이트는 마지막 상태로 계속 살아 있다** — 정적이기 때문이다.

---

## 3. Claude Code 헤드리스 호출 규약

```bash
CLAUDE=~/.local/bin/claude

$CLAUDE -p "$(cat prompts/gap-explain.md)" \
  --model claude-haiku-4-5-20251001 \
  --output-format json \
  --permission-mode acceptEdits \
  --allowedTools "Read,Write,Glob,Grep" \
  --add-dir /home/cau/work/prefill-opt \
  > out/gap-$slug.json
```

원칙:
- **작업당 하나의 프롬프트, 하나의 JSON 산출물.** 대화형 상태에 의존하지 않는다.
- 출력은 반드시 JSON 스키마 검증 후 채택. 실패 시 1회 재시도, 그래도 실패면 **직전 산출물 유지**(회귀 금지).
- 모델 분리: 브리핑 요약 = Haiku, 갭 설명·퀴즈 = Sonnet.
- 매 실행의 `usage`/`modelUsage`를 `logs/usage.jsonl`에 적재 → 구독 한도 소진 추이 관찰.
- 루틴 전체에 타임아웃(예: 20분)과 `flock`을 걸어 중복 실행을 막는다.

### 구독 사용량 한도에 대한 정직한 서술
구독에는 시간당·주간 사용 한도가 있다. 루틴이 한도에 걸리면 그날 생성이 건너뛰어진다.
따라서 **루틴은 가볍게** 설계한다 — 매일 전체 재생성이 아니라 **변경분만**:
- 노트/코드가 바뀐 개념의 설명만 재생성
- 새로 생긴 갭에 대해서만 설명 생성 (하루 최대 5건)
- 브리핑은 논문 3편 요약(짧은 호출)
실패 시에도 기존 사이트는 그대로다. 알림으로 실패를 알린다.

---

## 4. 데이터 — DB 없이 정적 JSON

```
site/public/data/
├── manifest.json        생성 시각, head_sha(main/wcep), 각 파일 해시
├── concepts.json        개념 노드 + 링크 + 노트 인용 + 코드 근거
├── gaps.json            G1/G2/G3 + 우선순위 점수
├── explain/<slug>.json  개념별 보충 설명 (생성된 것만)
├── quiz/<slug>.json     개념별 퀴즈
├── papers.json          refs.md 시드 논문 (정규화된 메타데이터)
└── briefings/YYYY-MM-DD.json   그날의 브리핑 3편
```

- 파일 단위 분할 → 앱이 필요한 것만 받는다. 개념 하나 열 때 전체를 받지 않는다.
- `manifest.json`의 해시로 클라이언트 캐시 무효화.
- **전부 git에 커밋된다** → 생성 이력이 곧 버전 관리. "지난주에는 이 개념 설명이 어땠나"를 `git log`로 본다.

### 진도·오답 같은 사용자 상태
정적 사이트에는 서버 상태가 없다. 1인용이므로:
- 웹은 `localStorage`, 앱은 `AsyncStorage`에 저장
- 설정 화면에서 **JSON 내보내기/가져오기** 제공 (기기 간 이동)
- 기기 간 자동 동기화가 정말 필요해지면 그때 Neon 무료 티어를 붙인다 (LLM과 무관하므로 과금 없음)

---

## 5. 프론트엔드

| | 선택 | 이유 |
|---|---|---|
| 웹 | **Next.js 15 정적 내보내기**(`output: 'export'`) 또는 Vite SPA | Vercel이 빌드하므로 로컬에 Node 불필요. 서버 함수 0개 |
| 앱 | **Expo (React Native)** | 같은 JSON을 fetch. 오프라인 캐시로 지하철에서도 열람 |
| 알림 | 로컬 루틴이 직접 발송 | 서버가 필요 없음. ntfy.sh(무계정, 무료) 또는 Expo Push API |

앱과 웹은 `packages/shared`의 타입과 fetch 클라이언트를 공유한다.

## 6. 저장소 레이아웃

```
paper-research-study/
├── docs/                기획 문서
├── routine/             ★ 이 서버에서 도는 것 (Python, Node 불필요)
│   ├── routine.sh       cron 진입점 (flock + 타임아웃 + 로깅)
│   ├── pull.py          대상 레포 갱신
│   ├── parse_notes.py   research/*.md 결정론적 파서
│   ├── index_code.py    코드 심볼 인덱싱
│   ├── gaps.py          G1/G2/G3 산출
│   ├── arxiv.py         신규 논문 수집·필터
│   ├── generate.py      claude -p 호출 + JSON 스키마 검증
│   ├── build.py         site/public/data/ 갱신
│   ├── publish.py       git commit && push (변경 시에만)
│   └── notify.py        푸시 발송
├── prompts/             헤드리스 프롬프트 (버전 관리 대상)
├── site/                Next.js 정적 사이트 (Vercel이 빌드)
├── mobile/              Expo 앱
├── packages/shared/     공용 타입
├── evals/               파서·갭 품질 정답셋
└── logs/                usage.jsonl, routine.log (gitignore)
```

## 7. 실패 모드와 대응

| 실패 | 증상 | 대응 |
|---|---|---|
| 서버 다운 | 데이터가 갱신 안 됨 | 사이트는 정상 동작. `manifest.json`의 생성 시각을 UI에 표시해 "며칠 전 데이터"임을 드러냄 |
| 구독 한도 소진 | 생성 스텝 실패 | LLM 없는 스텝(파싱·갭·논문 수집)만으로 배포 진행. 알림으로 통지 |
| 인증 만료 | `claude -p` 실패 | 루틴이 감지 후 알림 → 대화형에서 재로그인 |
| LLM 출력 스키마 위반 | 검증 실패 | 1회 재시도 후 **직전 산출물 유지**. 절대 깨진 데이터를 배포하지 않음 |
| Vercel 빌드 실패 | 배포 안 됨 | 기존 배포 유지(무중단). 알림 |
| 확장 업데이트로 경로 변경 | 바이너리 없음 | `~/.local/bin/claude` 고정 경로 사용 |
