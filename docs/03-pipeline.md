# 파이프라인 v0.3 — 노트 우선(notes-first), 로컬 루틴 실행

`prefill-opt`의 실제 노트 형식을 열어보고 설계했다.
**이 서버의 cron 루틴(`routine/`)이 전 스텝을 실행**하고, 결과를 정적 JSON으로 배포한다.
각 스텝은 멱등이며, 실패해도 직전 산출물이 유지된다(회귀 금지).

---

## 스텝 0 — 수집 (LLM 미사용)

```bash
# ~/work/prefill-opt 에 clone 해두고 매일 갱신
git -C ~/work/prefill-opt fetch --all --prune
for br in main wcep; do git ... worktree/checkout $br; done
```
- 로컬 파일시스템이므로 API 제한·용량 제한·시간 제한이 없다. private 레포도 SSH 키로 동일.
- 이전 실행의 `head_sha`와 같으면 파싱·갱신을 건너뛴다(브랜치별).
- 대상: `research/**.md`(노트), `src/**`·`prefill_bench/**`·`scripts/**`(코드).
  `artifacts/`, `converter/` 등은 제외.

## 스텝 1 — 노트 파싱 (LLM 미사용) ★ 핵심

`prefill-opt` 노트의 실제 관습을 파싱 규칙으로 고정한다.

| 관습 | 실제 예 | 파서 규칙 |
|---|---|---|
| 번호 붙은 개념 헤딩 | `## 1-3. Attention` | `^#{2,3}\s*(\d+[-\w]*)\.\s+(.+)` → 개념명 = 캡처 2, 앵커 = 캡처 1 |
| 개념 간 링크 | 항목 끝의 `← 이어지는 개념` | 해당 줄 이후의 내부 링크 → `concept_links(kind='next')` |
| 문서 간 링크 | `[05-math-attention](05-math-attention.md)` | 문서 그래프 구성, 상대경로 정규화 |
| 용어집 | `08-glossary.md`, `understand/03-glossary-full.md` | 헤딩 = 용어, 본문 첫 문단 = 정의 |
| **코드 맵 표** | `01-code-map.md`의 `| 개념 | 위치 | 메모 |` | `` `파일:줄~줄` `` 파싱 → **concept_evidence 직행** (LLM 불필요) |
| 선행연구 표 | `refs.md`의 `| 논문 | 요지 | 우리와의 간극 |` | arXiv ID/DOI 링크 추출 → `papers(is_seed=true)` |
| 학습 경로 | `04-reading-path.md`의 `Stage N` + `★/○/△` | 개념·논문의 **읽는 순서와 우선순위** |
| 가설 | `00-RESEARCH-PLAN.md`의 `H1`~`H5` | 브리핑 태깅용 라벨 |

산출: 개념 노드 · 개념 링크 · 코드 근거 · 논문 시드 · 학습 순서 · 가설 목록. **전부 LLM 없이.**

루틴이 실패해도 이 스텝까지는 항상 성공한다 — 갭 지도는 LLM과 무관하게 늘 최신이다.

> 이 스텝이 잘 되면 나머지는 부수적이다. 파서는 `evals/`의 정답셋으로 회귀 테스트한다.

## 스텝 2 — 코드 심볼 인덱싱 (LLM 미사용)

- Python `tree_sitter` 바인딩으로 C/C++/Python 심볼 추출 (루틴이 Python이므로 Node 불필요): 함수·클래스·매크로·주요 전역.
- 주석에서 개념어 후보 수집(예: `// KV re-streaming`), 노트 용어와 문자열/별칭 매칭.
- `01-code-map.md`가 이미 지정한 위치는 **줄 번호가 밀렸을 수 있으므로 함수 이름으로 재해석**
  (노트 자체가 "줄 번호는 참고값, 함수 이름으로 찾을 것"이라고 명시하고 있다).

## 스텝 3 — 갭 산출 (LLM 미사용)

```
코드개념집합 C = 심볼명·주석 개념어 정규화
노트개념집합 N = 헤딩 정의가 있는 개념
노트언급집합 M = 노트 본문에 등장하지만 정의 헤딩이 없는 용어

G1 = C − (N ∪ M)         코드에 있는데 노트에 아예 없음
G2 = N − 코드근거있음      노트에 있는데 대응 구현 없음
G3 = M − N                언급만 되고 정의된 적 없음   ← 최우선
```

**G3 우선순위 점수** — "무엇부터 공부해야 하는가"의 답:
```
priority = 0.4 * 전제횟수(이 용어를 쓰는 서로 다른 문서 수)
         + 0.3 * 코드근접도(대응 심볼의 중요 파일 여부: llm.cpp, nn-cpu-ops.cpp …)
         + 0.2 * reading-path 상 이른 Stage일수록 가산
         + 0.1 * 최근성(최근 커밋에서 등장)
```

## 스텝 3.5 — 위키 뼈대 생성 (LLM 미사용)

`artifacts/*/manifest.json`·`hosts.tsv`·`raw/*.log`, CLI 플래그, 호출 관계, 노트 역인덱스를 파싱해
위키 페이지의 뼈대와 문서화 갭 G4~G8을 만든다. 상세는 [05-wiki.md](05-wiki.md).

## 스텝 4 — 보충 설명 생성 (Claude Code 헤드리스, **하루 최대 5건**)

사이트는 런타임에 LLM을 부르지 않으므로, 설명은 **미리 만들어 둔다**.
다만 구독 사용량을 아끼기 위해 하루에 처리하는 양을 제한한다.

우선순위 큐: ① 새로 생긴 G3 ② 우선순위 점수 상위 ③ 노트가 수정되어 재생성이 필요한 것.
이미 생성된 개념은 `explain/<slug>.json`에 남아 있으므로 다시 만들지 않는다.

입력(프롬프트 캐싱 적용):
```
[캐시] 노트에서 이 용어가 쓰인 문단들 (최대 6개)
[캐시] 관련 코드 스니펫 (최대 3개, file:line 포함)
[요청] 이 용어를 다음 형식으로 설명:
       ① 한 줄 정의  ② 왜 필요한가(문제 → 해결)  ③ 이 레포에서의 실체(file:line 인용)
       ④ 이미 아는 개념 중 무엇과 이어지는가(노트에 정의된 개념명으로만)
제약: 제공된 문단·스니펫에 없는 사실을 쓰지 말 것. 모르면 "노트에 근거 없음"으로 표시.
```
④가 노트에 없는 개념명을 만들면 폐기 후 1회 재시도. 그래도 실패하면 **직전 파일을 그대로 둔다.**

호출 형태:
```bash
claude -p "$(render prompts/gap-explain.md --slug $slug)" \
  --model claude-sonnet-5 --output-format json \
  --permission-mode acceptEdits --allowedTools "Read,Glob,Grep" \
  --add-dir ~/work/prefill-opt
```
LLM이 노트와 코드를 **직접 읽을 수 있으므로**(Read/Grep 허용), 프롬프트에 문단을 전부 넣지 않아도 된다.
필요한 곳을 스스로 찾아 인용하게 하고, 인용한 `file:line`이 실제로 존재하는지 루틴이 사후 검증한다.

## 스텝 5 — 퀴즈 생성 (헤드리스, 설명 생성과 함께)

- 출제 근거는 **노트 문단 또는 코드 스니펫 하나**로 고정, `evidence_ref`에 저장.
- 유형: 개념 이해 2 / 수치·측정값 1(노트가 실측값 중심이므로 유효) / 코드 읽기 2.
- 자체 검증 1패스: 정답 유일성, 근거만으로 답이 결정되는지, 선지 길이 편향.
- 복습: SM-2 축약(1→3→7→16→35일), 오답 시 리셋.


## 스텝 6 — 논문 시드 & 매칭

```
시드     refs.md 파싱으로 확보 (Galaxy, Prima.cpp, TPI-LLM, Star Attention, APE,
         SwiftKV, Context Parallelism, FlashAttention 1/2, Roofline, Pope et al. …)
         + 04-reading-path.md의 Stage별 ★ 논문
정규화   arXiv ID / DOI → arXiv API·OpenAlex로 메타데이터 확정 (제목·초록 생성 금지)
개념연결 개념 ↔ 논문: 노트 내 동시 등장(공동 출현 통계) + 제목·초록 TF-IDF 유사도
         LLM은 "왜 관련 있는지" 한 문장만 작성
```

## 스텝 7 — 일 1회 논문 브리핑 (로컬 cron)

```
1. arXiv API: cs.DC / cs.LG / cs.AR 최근 24~48시간 신규 + 키워드
   ("prefill", "TTFT", "context parallel", "edge inference", "CPU inference",
    "pipeline parallel", "KV cache", "chunked prefill" …  ← refs.md에서 자동 도출)
2. 후보 30편 → 시드 논문 말뭉치(refs.md 논문 초록)와의 TF-IDF/BM25 유사도 상위 8편
   ※ 임베딩 API는 쓰지 않는다(과금 발생). 순수 로컬 계산 — scikit-learn 또는 자체 BM25
3. LLM(Haiku)으로 편당 3문장:
   ① 무엇을 했나  ② H1~H5 중 무엇을 보강/위협하나  ③ must-read / skim / skip
   제약: 제목·저자·수치는 API 응답에서 그대로. 새로 만들지 말 것
4. 상위 3편을 `briefings/YYYY-MM-DD.json`으로 저장
   → 루틴이 직접 푸시 발송(ntfy.sh 또는 Expo Push API) "오늘의 논문 3편, must-read 1편"
5. 저장 버튼 → refs.md 표에 붙일 마크다운 한 줄 생성
   | **제목** [arXiv:xxxx](url) | 요지 | 우리와의 간극(초안) |
```
브리핑 1회 소모: 후보 8편 × (초록 1.5K토큰 + 출력 200토큰) — 구독 한도 대비 무시할 수준.
**추가 청구액은 0원이다.**

## 스텝 8 — 배포 (LLM 미사용)

```
build.py    산출물을 site/public/data/*.json 으로 직렬화, manifest.json 해시 갱신
검증        JSON 스키마 · 코드 근거 file:line 실재 여부 · 논문 URL 응답 확인
publish.py  변경이 있을 때만 git commit && push
            커밋 메시지: "data: 2026-09-02 (갭 +3, 설명 5, 브리핑 3)"
Vercel      webhook 수신 → 빌드 → 원자적 전환(무중단). 실패 시 기존 배포 유지
```
검증에 걸리면 **push하지 않는다.** 깨진 데이터가 배포되는 경로가 없다.

---

## 품질 검증 (evals/)

`prefill-opt`를 기준 레포로 삼아 정답셋을 만든다. 프롬프트나 파서를 고칠 때마다 돌린다.

| 항목 | 방법 | 목표 |
|---|---|---|
| 노트 파서 정확도 | 손으로 만든 개념 50개 정답 리스트와 대조 | 재현율 ≥ 0.95 (결정론적이므로 높아야 정상) |
| 코드맵 근거 유효성 | 파싱한 file:function이 실제 존재하는가 | ≥ 0.95 |
| G3 유용성 | 상위 10개를 보고 "실제로 내가 몰랐다" 판정 | ≥ 7/10 |
| 설명 근거성 | 노트/코드에 없는 주장 포함 여부 | 0건 |
| 브리핑 적합성 | 3편 중 실제로 읽을 만한 편수 | ≥ 1.5/3 |
| 비용 | 전체 분석 + 브리핑 30일 | ≤ 월 $3 |
