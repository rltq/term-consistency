"""레포별 용어집 override (repo glossary adapter).

SCOPE 제외 7 (v0.2.0 픽스처 한정 → 레포 글로서리 상위 권위) 을 닫는
모듈. 현재는 PyTorchKorea/tutorials-kr 의 TRANSLATION_GUIDE.md 표를
1회 추출한 정적 JSON (``data/glossary_pytorch_kr.json``) 을 읽어
``term_lookup`` 과 병합할 수 있는 형태로 반환한다.

아키텍처
--------
- ``load_glossary(repo_id) -> dict[str, list[dict]]`` — ``term_lookup``
  과 동일 shape. 각 meaning dict 에 ``_authority="repo"`` 필드가 붙어,
  find_terms 출력에서 권위 출처를 구분할 수 있다.
- 알 수 없는 ``repo_id`` → 빈 dict (fallback). 파이프라인이 override
  없이 기존 terms.kr 룩업만으로 동작.
- v1.1+ 의 adapter 추상화 (어댑터 패턴, 플러그인 레지스트리 등) 는
  별도 작업. 현재는 ``repo_id → 파일명`` 매핑 dict 하나만 유지한다.

데이터 추출 방침 (``glossary_pytorch_kr.json`` 생성 시 적용)
--------------------------------------------------------------
**1. 소스.**
    PyTorchKorea/tutorials-kr ``TRANSLATION_GUIDE.md`` 의 "용어 사용
    규칙" 섹션 아래 마크다운 테이블. 원본 행 76개.

**2. 1회성 추출.**
    업스트림 표가 변경되면 수동 재추출 필요. 파이프라인은 마크다운
    파서를 포함하지 않는다 — 1회 작업에 파서를 유지하는 비용 회피.
    추출 일자와 소스 커밋은 도입 PR 본문에 기록된다 (코드 옆 docstring
    과 PR 본문이 이중 진실 원천).

**3. 포함 규칙.**
    - **번역안함 엔트리** (CUDA, NumPy, Tensor 등 원본 9행) →
      ``{en_lower: [{"korean": en_as_given}]}`` 로 dict 내부에 동일
      취급. find_terms 의 substring 매칭이 "영문이 kr 본문에 그대로
      박혀 있음" 을 검증해 ``[ERR] leak`` 분기를 자연스럽게 우회.
    - **다중 폼 EN 분할**: ``Tensor / Tensors`` → 2개 키,
      ``learning rate, lr`` → 2개 키, ``Getting Started tutorial`` →
      ``getting started`` + ``tutorial`` 2개 키 (후자는 원 표가 콤마
      없는 두 단어 나열이었음을 재확인).
    - **괄호 한정어 strip**: ``Production (environment, use)`` →
      ``production``.
    - **명사형 축약**: ``~하다`` / ``~하기`` 로 끝나는 긴 동사구 번역은
      명사형으로 (``생성하다`` → ``생성``, ``빠르게 시작하기`` →
      ``빠르게 시작``). 단일 단어 ``가지치기``/``읽을거리`` 는 하-보조
      용언 결합이 아니므로 그대로 유지.

**4. 제외 (기계적 처리 불가).**
    - ``track (computation) history → 연산 기록을 추적하다`` — EN 측
      괄호가 "선택적 부분" 을 의미. ``re.escape`` 로 리터럴
      ``(computation)`` 을 요구하게 되어 실제 영문 본문과 매칭 불가.
      의미론적 해석이 필요해 이번 스코프 밖.

**5. 알려진 경계 (의도적 미처리).**
    - ``autograd → Autograd`` 의 KR 측 case 불일치. 현재 find_terms
      는 KR 측 substring 비교가 case-sensitive 라 kr 본문이 소문자
      ``autograd`` 이면 매칭 실패. v0.3 스코프 외 — 매칭 대소문자
      정책 변경은 별개 이슈로 분리.

**결과.** 원본 76행에서 1건 제외, 3건 분할 (``learning rate/lr``,
``Tensor/Tensors``, ``Getting Started/tutorial``) → **78개 키**.
키 수 계약은 P3 의 유닛 테스트로 박제한다.
"""

import json
from pathlib import Path


_DATA_DIR = Path(__file__).parent.parent / "data"

# repo_id → 데이터 파일명. v1.1+ 에 어댑터 추상화가 추가되면 이 매핑은
# 런타임 플러그인 레지스트리로 승격될 수 있다.
_GLOSSARY_FILES = {
    "pytorchkorea/tutorials-kr": "glossary_pytorch_kr.json",
}


def load_glossary(repo_id: str) -> dict[str, list[dict]]:
    """레포별 용어 override 를 term_lookup 과 동일 shape 로 반환.

    Args:
        repo_id: ``"owner/name"`` 형태 (case-insensitive).

    Returns:
        term 을 키로, meaning dict 의 리스트를 값으로 하는 dict. 각
        meaning 은 최소 ``"korean"`` 필드를 가지며, 이 모듈이 반환
        하는 엔트리는 ``"_authority": "repo"`` 로 태그된다. 알 수
        없는 ``repo_id`` 에 대해서는 빈 dict 를 반환하여 파이프라인이
        override 없이 기존 terms.kr 만으로 동작하게 한다.
    """
    filename = _GLOSSARY_FILES.get(repo_id.lower())
    if filename is None:
        return {}
    with open(_DATA_DIR / filename, encoding="utf-8") as f:
        return json.load(f)
