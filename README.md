# RepoScholar (가칭)

내가 연구 중인 레포(`inpyu/prefill-opt`)를 등록하면
**연구 노트와 코드를 대조해 내가 모르는 개념을 짚어주고**, 레포를 파싱해 얻은 정보로 **위키를 만들고**,
학습 자료·퀴즈를 만들고,
**관련 연구를 매일 브리핑**해 주는 웹 + 네이티브 앱. 1인용.

**이 서버의 cron 루틴이 Claude Code 헤드리스(구독)로 콘텐츠를 미리 만들어 git push하고,
Vercel이 정적 사이트로 무중단 자동 배포한다. 배포된 사이트는 LLM을 호출하지 않는다 — 추가 과금 0.**

배포: **https://paper-research-study.vercel.app**

현재 상태: **M1~M3 완료** — 파싱·갭·정적사이트·일일 논문 브리핑이 자동으로 돈다.

```bash
python3 routine/parse_notes.py && python3 routine/index_code.py && python3 routine/gaps.py --top 10
```

## 문서
- [제품 기획서](docs/01-product-plan.md) — 전제, 갭(G1/G2/G3) 정의, 시나리오, 범위, 리스크
- [아키텍처](docs/02-architecture.md) — 로컬 루틴 · 헤드리스 호출 규약 · 정적 배포 · 실패 모드
- [파이프라인](docs/03-pipeline.md) — 스텝 0~8: 파싱 · 갭 산출 · 생성 · 브리핑 · 배포 · 품질 검증
- [레포 위키](docs/05-wiki.md) — 파싱 부산물(파일·플래그·실험·로그·수치)을 학습 자료로
- [로드맵](docs/04-roadmap.md) — M0~M7

## 핵심 설계 원칙
1. **노트 우선** — 개념 그래프는 `research/*.md`에서 결정론적으로 뽑는다. LLM으로 지어내지 않는다.
2. **생성은 로컬, 배포는 정적** — LLM 작업은 전부 이 서버의 루틴에서 끝난다. 사이트에는 런타임 LLM이 없다.
3. **과금 지점 0** — API 키를 다루지 않으므로 초과 청구가 구조적으로 불가능하다.
4. **깨진 데이터는 배포하지 않는다** — 검증 실패 시 직전 산출물을 유지한다(회귀 금지).
5. **근거 없는 산출물은 버린다** — 개념은 노트/코드 인용을 물고, 논문은 API 응답에서만 온다.

## 루틴 (`routine/`) — 의존성 없음
이 서버에는 pip·node 가 없다. 파서는 **Python 표준 라이브러리만** 쓴다.

| 스크립트 | 하는 일 | LLM |
|---|---|---|
| `parse_notes.py` | `research/*.md` → 개념·링크·코드근거·논문시드·학습경로·가설 | 미사용 |
| `index_code.py` | 심볼·CLI 플래그·주석 용어·파일 변경빈도 | 미사용 |
| `gaps.py` | G1~G5 갭 산출 + 사람이 읽는 리포트 | 미사용 |
| `arxiv.py` | 시드 정규화 + arXiv 신규 수집 + BM25 랭킹 | 미사용 |
| `generate.py` | 브리핑 생성 (Claude Code 헤드리스, 구독) + 스키마 검증 | **사용** |
| `build.py` | `site/public/data/*.json` 생성 | 미사용 |
| `publish.py` | 검증 후 변경 시에만 commit & push | 미사용 |
| `notify.py` | ntfy.sh 푸시 발송 | 미사용 |
| `routine.sh` | cron 진입점 (flock · 타임아웃 · 로깅), **매일 06:10** | — |

산출물은 `out/*.json` (gitignore).

## 사이트 (`site/`) — Next.js 정적 내보내기
서버 함수를 하나도 만들지 않는다(`output: "export"`). 화면은 `public/data/*.json` 만 읽는다.

```bash
cd site && npm install && npm run build     # out/ 에 정적 파일
```

Vercel 프로젝트 설정에서 **Root Directory 를 `site` 로** 지정하면 push 마다 자동 배포된다.
