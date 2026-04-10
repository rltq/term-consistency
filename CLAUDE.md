# CLAUDE.md

term-consistency 프로젝트의 세션 시작 오리엔테이션. 매 세션마다 자동 로드된다.

이 문서는 인덱스이며 본문은 거의 없다. 본문은 [docs/](./docs/) 하위 4개 문서에 있다.

---

## 이 프로젝트가 무엇인가

term-consistency 는 한국어 번역 PR 의 용어를 terms.kr 의 권장 번역어로 정렬하되 각 레포의 자체 용어집을 상위 원칙으로 존중하는 룰베이스 **스크리너** 이다. v0.1.0 은 PyTorchKorea/tutorials-kr 만 대상으로 한다.

자세한 정의: [docs/SCOPE.md](./docs/SCOPE.md) 의 "도구 한 줄 정의" 섹션.

---

## 지금 어디에 있는가

[docs/ROADMAP.md](./docs/ROADMAP.md) 의 **"현재 위치"** 섹션 참조. 이 줄은 ROADMAP 한 곳에서만 갱신되며 여기서 복제하지 않는다.

---

## 코드/문서를 손대기 전에 읽을 것

| 무엇을 하려는가 | 먼저 읽을 것 |
|---|---|
| 새 기능 추가, 의존성 도입 | [docs/PRINCIPLES.md](./docs/PRINCIPLES.md) — 3원칙 위반하지 않는지 확인 |
| 버그 수정 / 동작 변경 | [docs/SCOPE.md](./docs/SCOPE.md) — 의도된 비탐지인지 확인 (특히 제외 7) |
| 다음 마일스톤 작업 시작 | [docs/ROADMAP.md](./docs/ROADMAP.md) — 현재 마일스톤의 DoD 와 위험 |
| 테스트/픽스처 작업 | [docs/TESTING.md](./docs/TESTING.md) — 회귀 픽스처 패턴, 스냅샷 갱신 의사결정 트리 |
| #9 raw queue 의 새 케이스 분석 | [docs/TESTING.md](./docs/TESTING.md) 의 "픽스처 승격 절차" 섹션 |

---

## 매 세션 시작 프로토콜

### 1. 드리프트 체크

세션 시작 시 git log (마지막 `docs:` 커밋 이후) vs 다음 항목들 비교:
- ROADMAP 의 "현재 위치" 줄
- ROADMAP 의 현재 마일스톤 DoD 체크박스
- SCOPE 의 버전 스탬프 + 제외 항목 상태

드리프트 0개 → 침묵. 1개 이상 → 한 문단으로 보고 (사용자 작업 응답 *전*).

### 2. 제안-승인-실행

모든 mutation (Edit/Write/git commit/branch ops/패키지 설치/외부 API 의 POST/PUT/DELETE 등) 은 **사용자 명시 승인 필요**. 제안은 Y/N 또는 짧은 수정으로 끝낼 수 있게 구체적이어야 한다.

read/inspect (Read/Glob/Grep/git status·log·diff/read-only API) 는 자유.

메모리 갱신은 알리되 승인 게이트 없음.

### 3. 톤 룰

이 레포의 모든 공개 문서 (`docs/`, `CLAUDE.md`, `README.md`, GitHub 이슈/PR 본문) 는 **객관적 톤**. 개인 대명사 ("본인", "사용자") 가급적 회피. 한국어 주어 생략 활용. 위험은 일반 패턴으로 표현.

### 4. 브랜치 정책

- 일상 드리프트 sync: `claude/sync` 장수명 브랜치, 매 commit 전 main 에 rebase, PR 안 만듦.
- Feature 작업 (초기 docs 셋업, 기능 추가, 큰 리팩토링): 별도 단명 feature branch (`docs/...`, `feat/...`).
- main 에 직접 commit 안 함.

---

## 어떻게 돌리는가

```bash
# 도구 실행
uv run main.py --pr https://github.com/PyTorchKorea/tutorials-kr/pull/<N>

# 회귀 픽스처 테스트 (v0.2.0 이후)
uv run pytest tests/
```

`terms_all.json` 이 레포 루트에 없으면 첫 실행 시 poc.terms.kr 에서 받아서 캐싱한다.

---

## 이 문서 갱신 시점

이 문서 자체는 거의 안 바뀐다. 갱신해야 할 경우:

- 다른 docs 의 구조가 바뀌어 cross-ref 가 깨질 때
- 새 docs 가 추가될 때
- 세션 프로토콜이 변경될 때 (드리프트 체크, 제안-승인-실행, 톤 룰, 브랜치 정책 중 하나라도)
- 도구 실행 명령어가 바뀔 때

"지금 어디에 있는가" 는 **여기서 갱신하지 않는다** — ROADMAP 한 곳에서만.
