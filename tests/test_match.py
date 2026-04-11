"""find_terms 의 중복 탐지 skip 로직 단위 테스트 (#8).

이 파일은 스냅샷 회귀 테스트가 잡지 못하는 영역 — 짧은 용어가 긴 용어의
매칭 구간에 완전히 포함될 때 레코드가 실제로 제거되는지 — 를 직접 검증한다.

`tests/snapshots/pr_945.json` 의 유일한 substring-containment 케이스 (gradient
∈ gradient accumulation) 는 "Gradient penalty" 덕에 부분 커버라 스냅샷 diff
가 발생하지 않는다. 즉 스냅샷은 이 fix 의 축소 효과를 증명하지 못한다.
단위 테스트가 그 간극을 메운다.
"""
from term_consistency.match import find_terms


def _lookup(*pairs: tuple[str, str]) -> dict:
    """(term, korean) 쌍을 받아 term_lookup 형태로 변환. 긴 용어가 먼저
    insert 되도록 호출 측에서 순서를 맞춘다 — 실제 로더도 len 내림차순
    정렬 후 dict 를 구성하므로 동일 규약."""
    return {term.lower(): [{"korean": korean}] for term, korean in pairs}


def _segment(en: str, kr: str, file: str = "f.py") -> dict:
    return {"file": file, "en": en, "kr": kr}


def test_short_term_fully_covered_is_dropped():
    """긴 용어의 매칭 구간에 완전히 포함되는 짧은 용어는 unmatched 에서 제거."""
    lookup = _lookup(("training loop", "학습 루프"), ("training", "학습"))
    segments = [_segment("The training loop runs here.", "여기서 무언가 실행됨.")]

    matched, unmatched = find_terms(segments, lookup)

    origins = {u["origin"] for u in unmatched}
    assert "training loop" in origins
    assert "training" not in origins, (
        "'training' 의 유일한 occurrence 가 'training loop' 구간 안에 포함 → 제거돼야 함"
    )
    assert matched == []


def test_partial_cover_keeps_short_term():
    """짧은 용어의 occurrence 중 하나라도 구간 밖에 있으면 보고 유지."""
    lookup = _lookup(("gradient accumulation", "그래디언트 누적"), ("gradient", "그래디언트"))
    segments = [_segment("Gradient accumulation and gradient penalty.", "변화도 축적과 변화도 페널티.")]

    matched, unmatched = find_terms(segments, lookup)

    origins = [u["origin"] for u in unmatched]
    assert origins.count("gradient accumulation") == 1
    assert origins.count("gradient") == 1, (
        "'Gradient penalty' 의 gradient occurrence 는 구간 밖 → 유지돼야 함"
    )


def test_consume_applies_even_when_long_term_matched():
    """긴 용어가 matched 로 분류돼도 consume 효과는 유효."""
    lookup = _lookup(("training loop", "학습 루프"), ("training", "학습"))
    segments = [_segment("The training loop is stable.", "학습 루프는 안정적입니다.")]

    matched, unmatched = find_terms(segments, lookup)

    matched_origins = {m["origin"] for m in matched}
    unmatched_origins = {u["origin"] for u in unmatched}
    assert "training loop" in matched_origins
    assert "training" not in matched_origins
    assert "training" not in unmatched_origins, (
        "긴 용어가 matched 로 빠져도 consume 는 적용되어야 함"
    )


def test_brace_annotated_short_term_is_suppressed_when_fully_covered():
    """결정 박제: 짧은 용어가 긴 용어 구간에 완전히 포함되면 kr 가 brace
    형태로 그 짧은 용어를 주석하고 있더라도 suppress 된다.

    근거: 원 en 토큰은 복합어 형태이므로 복합어 쪽이 진정한 매칭 대상.
    이 테스트는 그 결정을 박제한다 — 향후 정책을 바꾸면 이 테스트가 깨지면서
    재검토를 강제한다.
    """
    lookup = _lookup(("training loop", "학습 루프"), ("training", "학습"))
    segments = [_segment("The training loop starts.", "학습 루프(training loop)가 시작됩니다.")]

    matched, unmatched = find_terms(segments, lookup)

    matched_origins = {m["origin"] for m in matched}
    unmatched_origins = {u["origin"] for u in unmatched}
    assert "training" not in matched_origins
    assert "training" not in unmatched_origins
