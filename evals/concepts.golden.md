# evals/concepts.golden.md — 개념 정답셋

파서 품질의 기준선. **손으로 채운다.** 파서나 점수식을 고칠 때마다 `python3 evals/run.py` 로 대조한다.

## 1. 파서가 뽑은 개념 (자동 갱신)
`[x]` 맞음 · `[~]` 이름이 어색함 · `[ ]` 개념이 아님(오탐)

- [ ] all-reduce
- [ ] allgather
- [ ] anchor
- [ ] anchor amortization
- [ ] Attention
- [ ] back-pressure
- [ ] barrier
- [ ] barrier (배리어)
- [ ] baseline 위생
- [ ] byte-for-byte 동일
- [ ] causal mask
- [ ] chunked prefill
- [ ] compute-bound
- [ ] continuous batching
- [ ] CP
- [ ] D disaggregation
- [ ] decode
- [ ] dense
- [ ] dense (조밀) 적합
- [ ] dotprod
- [ ] drainPrefillLogits
- [ ] E. 방법론·기반
- [ ] FFN
- [ ] FFN 와 SwiGLU
- [ ] GEMM
- [ ] GEMV
- [ ] GQA
- [ ] holdout
- [ ] KV affinity
- [ ] KV 캐시
- [ ] KV migration
- [ ] lmhead
- [ ] LongBench
- [ ] LSE (log-sum-exp) merge
- [ ] machine balance
- [ ] matched-accuracy 비교
- [ ] measurement study
- [ ] memory-bound
- [ ] needle-in-haystack
- [ ] online softmax
- [ ] P
- [ ] P2P
- [ ] phase diagram
- [ ] poll 대기
- [ ] PP
- [ ] prefill
- [ ] Q40 과 Q80
- [ ] repack
- [ ] residual stream
- [ ] ridge
- [ ] ring
- [ ] RMSNorm
- [ ] roofline
- [ ] RoPE
- [ ] RULER
- [ ] SP
- [ ] straggler
- [ ] SVD
- [ ] SVD 와 에너지
- [ ] SwiGLU
- [ ] TP
- [ ] TTFT
- [ ] turbo mode
- [ ] wave
- [ ] 공유 기저
- [ ] 과적합
- [ ] 과적합과 holdout
- [ ] 기호표
- [ ] 깊이 분해 절감
- [ ] 동기
- [ ] 랭크
- [ ] 로짓
- [ ] 로짓과 lmhead
- [ ] 리스크
- [ ] 메모리 계층
- [ ] 메모리 레이아웃과 repack
- [ ] 모델
- [ ] 모델·워크로드
- [ ] 배리어와 straggler
- [ ] 버블은 정량화된다
- [ ] 분산 softmax
- [ ] 분산 축 실측
- [ ] 블록 로컬 attention
- [ ] 블록 양자화
- [ ] 산술 강도
- [ ] 상대 오차
- [ ] 선형 사상
- [ ] 성능
- [ ] 시스템·측정 용어
- [ ] 알고리즘
- [ ] 알고리즘 용어
- [ ] 양자화
- [ ] 에너지
- [ ] 예외도 삼각형이다
- [ ] 용어 가이드
- [ ] 운영 규칙
- [ ] 위치 인코딩과 RoPE
- [ ] 일반화
- [ ] 재구성 오차
- [ ] 저랭크 근사
- [ ] 정규화
- [ ] 정확도 벤치마크
- [ ] 중복 계산 문제
- [ ] 지연 대 대역폭
- [ ] 진행 순서
- [ ] 집합 통신
- [ ] 청크 (chunk)
- [ ] 체제
- [ ] 최소제곱 적합
- [ ] 최소제곱과 정규방정식
- [ ] 캘리브레이션 덤프
- [ ] 타일링
- [ ] 토큰과 임베딩
- [ ] 통신·배리어
- [ ] 특이값
- [ ] 평가·논문 용어
- [ ] 하드웨어

## 2. 빠진 개념 (손으로 추가)
내가 아는데 위 목록에 없는 개념을 적는다. 재현율의 기준.

- [ ] (예: chunked prefill)

## 3. G3 상위 10개 판정
`[x]` 실제로 내가 설명 못 함(진짜 갭) · `[ ]` 사실 알고 있음(오탐)

- [ ] 1. distributed-llama  (문서 17개, 강조 1회)
- [ ] 2. FlashAttention  (문서 11개, 강조 3회)
- [ ] 3. syncWait  (문서 7개, 강조 7회)
- [ ] 4. multiheadAttBatchF32  (문서 6개, 강조 6회)
- [ ] 5. SDOT  (문서 9개, 강조 2회)
- [ ] 6. SwiftKV  (문서 7개, 강조 4회)
- [ ] 7. EAGAIN  (문서 5개, 강조 5회)
- [ ] 8. nnCpuOpsSetDecodePhase  (문서 3개, 강조 3회)
- [ ] 9. NnExecutor  (문서 5개, 강조 3회)
- [ ] 10. PipeEdge  (문서 9개, 강조 1회)

> **완료 기준**: 3절에서 `[x]`가 7개 이상이면 M1 통과.
