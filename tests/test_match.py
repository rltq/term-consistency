"""match.py 의 분기 계약 박제.

**v0.2.0 seed.** find_terms 의 중복 탐지 skip 로직 (#8). 스냅샷 회귀
테스트가 잡지 못하는 축소 효과 — 짧은 용어가 긴 용어의 매칭 구간에 완전히
포함될 때 레코드가 실제로 제거되는지 — 를 직접 검증한다. `pr_945.json` 의
유일한 substring-containment 케이스 (gradient ∈ gradient accumulation) 는
"Gradient penalty" 덕에 부분 커버라 스냅샷 diff 가 0 이므로 스냅샷으로는
fix 의 축소 효과를 증명할 수 없다.

**v0.3.0 작업 0 확장.** match.py 전체 계약을 박제한다. 목적은 커버리지가
아니라 **계약 고정** — v0.3.0 작업 1-2 (레포별 용어집 override + 권위 머지)
가 매칭 결정 로직을 건드릴 때 기존 분기가 동일하게 작동함을 박제한다.
범위: find_terms 의 모든 분기 (matched / brace-matched / unmatched /
[ERR] leak / kr 빈 문자열 / word boundary / case-insensitive) + 헬퍼
(normalize_ko, strip_text) 경계 + INCLUDE_SYNONYMS 훅 (SCOPE 제외 6). 두
레이어의 분담은 docs/TESTING.md 의 "검증 레이어 — 유닛" 섹션 참조.
"""
from term_consistency import match
from term_consistency.match import find_terms, normalize_ko, strip_text


def _lookup(*pairs: tuple[str, str]) -> dict:
    """(term, korean) 쌍을 받아 term_lookup 형태로 변환. 긴 용어가 먼저
    insert 되도록 호출 측에서 순서를 맞춘다 — 실제 로더도 len 내림차순
    정렬 후 dict 를 구성하므로 동일 규약."""
    return {term.lower(): [{"korean": korean}] for term, korean in pairs}


def _segment(en: str, kr: str, file: str = "f.py") -> dict:
    return {"file": file, "en": en, "kr": kr}


# ---------------------------------------------------------------------------
# find_terms: 중복 탐지 skip (#8 seed)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# normalize_ko: 공백 제거 경계
# ---------------------------------------------------------------------------
#
# normalize_ko 는 한국어 본문과 allowed 리스트를 대칭으로 공백 제거해서
# 비교하기 위한 함수다 (PR #19 에서 비대칭 버그 수정). 여기서 박제하는
# 계약은 "공백 ' ' 만 제거" 이며, 탭/개행 등 다른 whitespace 는 건드리지
# 않는다. 이 선택의 근거는 PR #19 의 결정 — "multi-word 번역어가 단일
# ' ' 로만 구성되는 게 실제 관찰 패턴" 이므로 그 이상의 normalize 는
# false negative 리스크.


def test_normalize_ko_strips_single_spaces():
    assert normalize_ko("혼합 정밀도") == "혼합정밀도"


def test_normalize_ko_strips_multiple_spaces():
    assert normalize_ko("활성화  함수") == "활성화함수"


def test_normalize_ko_empty_string_passthrough():
    assert normalize_ko("") == ""


def test_normalize_ko_no_space_passthrough():
    assert normalize_ko("혼합정밀도") == "혼합정밀도"


def test_normalize_ko_preserves_tab_and_newline():
    """탭/개행은 공백 취급하지 않는다 — 현재 행동 박제.

    근거: 실제 multi-word 번역어의 공백 패턴은 단일 ' ' 이며, 탭/개행이
    섞이는 경우는 관찰되지 않았다. 이 계약이 바뀌려면 실제 PR 에서 반례
    수집이 선행돼야 한다.
    """
    assert normalize_ko("혼합\t정밀도") == "혼합\t정밀도"
    assert normalize_ko("혼합\n정밀도") == "혼합\n정밀도"


# ---------------------------------------------------------------------------
# strip_text: 백틱 스트립 경계
# ---------------------------------------------------------------------------
#
# strip_text 는 code span / code block 의 내용을 매칭 전에 제거하는
# 사전 컷이다 (SCOPE 제외 3). 코드 안의 영어 식별자가 용어 매칭에
# 들어오면 거의 전부가 false positive 가 되므로 매칭 전에 제거.


def test_strip_text_removes_inline_backtick():
    assert strip_text("use `model` here") == "use  here"


def test_strip_text_removes_triple_backtick():
    assert strip_text("before ```code``` after") == "before  after"


def test_strip_text_plain_text_passthrough():
    assert strip_text("no backticks here") == "no backticks here"


def test_strip_text_multiple_blocks():
    assert strip_text("a `x` b `y` c") == "a  b  c"


def test_strip_text_empty_string_passthrough():
    assert strip_text("") == ""


# ---------------------------------------------------------------------------
# find_terms: 주요 분기 계약
# ---------------------------------------------------------------------------
#
# find_terms 는 if (brace) / elif (normalize_ko 포함) / elif (kr 비어있지
# 않음, [ERR] 또는 일반 unmatched) 의 3-way 분기를 갖는다. 각 분기는 출력
# 딕셔너리의 키가 다르다 ("matched" vs "matched(brace)") 거나 review_kr 의
# 프리픽스가 다르다 ("[ERR] ..." vs "..."). 이 섹션은 각 분기가 어느 입력
# 에서 선택되는지를 박제한다.


def test_matched_plain():
    """allowed 의 원문이 kr 에 그대로 있으면 일반 matched 분기 — 출력 키는 'matched'."""
    lookup = _lookup(("training", "학습"))
    segments = [_segment("Training is important.", "학습은 중요합니다.")]

    matched, unmatched = find_terms(segments, lookup)

    assert len(matched) == 1
    assert matched[0]["origin"] == "training"
    assert matched[0]["expected"] == ["학습"]
    assert "matched" in matched[0]
    assert "matched(brace)" not in matched[0]
    assert unmatched == []


def test_matched_via_normalize_ko_space_asymmetry():
    """allowed 에 공백이 있고 kr 은 공백 없이 쓴 경우 matched — #16 / PR #19 회귀 가드.

    normalize_ko 는 allowed 와 kr 양쪽에 대칭으로 적용돼야 multi-word
    번역어가 매칭된다. 이 대칭이 깨졌던 게 #16 이었다. 이 테스트가 깨지면
    대칭이 다시 무너진 것.
    """
    lookup = {"mixed precision": [{"korean": "혼합 정밀도"}]}
    segments = [_segment("Mixed precision training.", "혼합정밀도 학습을 적용합니다.")]

    matched, unmatched = find_terms(segments, lookup)

    assert len(matched) == 1
    assert matched[0]["origin"] == "mixed precision"
    # expected 는 사람 읽기용 — 원문 공백 형태 유지 (normalize_ko 적용 X).
    assert matched[0]["expected"] == ["혼합 정밀도"]
    assert "matched" in matched[0]
    assert unmatched == []


def test_brace_matched_precedence_over_plain():
    """kr 에 `한국어(english)` 패턴이 있으면 brace 분기가 일반 matched 보다 우선.

    두 조건을 동시에 만족할 수 있는 입력 — "학습(training) 은 중요합니다."
    는 "학습" 포함 검사도 통과하지만, if/elif 순서상 brace 분기가 먼저
    잡는다. 출력 키가 'matched(brace)' 로 달라지는 것이 분기 식별점.
    """
    lookup = _lookup(("training", "학습"))
    segments = [_segment("Training is important.", "학습(training) 은 중요합니다.")]

    matched, unmatched = find_terms(segments, lookup)

    assert len(matched) == 1
    assert matched[0]["origin"] == "training"
    assert "matched(brace)" in matched[0]
    assert "matched" not in matched[0]
    assert unmatched == []


def test_unmatched_plain_no_err_label():
    """en 에 토큰이 있고 kr 에 번역어도 leak 도 없으면 일반 unmatched — review_kr 에 [ERR] 없음."""
    lookup = _lookup(("training", "학습"))
    segments = [_segment("Training is important.", "매우 중요한 내용입니다.")]

    matched, unmatched = find_terms(segments, lookup)

    assert matched == []
    assert len(unmatched) == 1
    assert unmatched[0]["origin"] == "training"
    assert unmatched[0]["expected"] == ["학습"]
    assert not unmatched[0]["review_kr"].startswith("[ERR]")


def test_err_leak_standalone_english_token_in_kr():
    """영문 토큰이 kr 에 공백 경계로 박혀 있으면 review_kr 가 [ERR] 로 프리픽스."""
    lookup = _lookup(("softmax", "소프트맥스"))
    segments = [_segment("Use softmax here.", "여기서 softmax 를 사용합니다.")]

    matched, unmatched = find_terms(segments, lookup)

    assert matched == []
    assert len(unmatched) == 1
    assert unmatched[0]["review_kr"].startswith("[ERR] ")


def test_err_leak_korean_adjacent():
    """한글이 영문 토큰 직후에 붙어도 leak 로 탐지.

    re `\\b` 는 "Softmax와" 같이 한글 인접 시 경계를 인식하지 못한다.
    match.py 는 이를 우회하기 위해 ASCII-only 경계 `(?<![a-zA-Z]) / (?![a-zA-Z])`
    로 leak_pattern 을 별도 구성한다. 이 테스트는 그 우회가 실제로 한글
    인접 케이스를 잡는지 박제한다.
    """
    lookup = _lookup(("softmax", "소프트맥스"))
    segments = [_segment("Use softmax here.", "Softmax와 ReLU 를 비교합니다.")]

    matched, unmatched = find_terms(segments, lookup)

    assert matched == []
    assert len(unmatched) == 1
    assert unmatched[0]["review_kr"].startswith("[ERR] ")


def test_err_leak_case_insensitive():
    """leak 탐지는 case-insensitive — #10 회귀 가드.

    #10 이전에는 pattern.search (IGNORECASE) 로 en 매칭 후 `term in en_text`
    (case-sensitive) 로 분기 → 대문자 토큰에서 분기 실패가 [ERR] 로 잘못
    표기되는 비대칭이 있었다. 현재는 leak_pattern 도 IGNORECASE 이며
    대문자 토큰이 kr 에 박혀도 [ERR] 로 정상 분류된다.
    """
    lookup = _lookup(("softmax", "소프트맥스"))
    segments = [_segment("Use softmax function.", "Softmax 함수를 사용합니다.")]

    matched, unmatched = find_terms(segments, lookup)

    assert matched == []
    assert len(unmatched) == 1
    assert unmatched[0]["review_kr"].startswith("[ERR] ")


# ---------------------------------------------------------------------------
# find_terms: 경계 케이스
# ---------------------------------------------------------------------------


def test_kr_empty_string_produces_no_output():
    """kr_text 가 빈 문자열이면 matched / unmatched 어느 쪽에도 들어가지 않는다.

    현재 match.py L69 의 `elif len(kr_text) > 0:` 가드가 이 동작을 만든다.
    en 에 토큰이 있어도 kr 이 비어있으면 완전히 조용히 skip. 계약을 박제
    하는 이유: 이 가드가 없어지면 빈 kr 에서도 unmatched 레코드가 생성되어
    output 이 노이즈로 도배된다.
    """
    lookup = _lookup(("training", "학습"))
    segments = [_segment("Training is important.", "")]

    matched, unmatched = find_terms(segments, lookup)

    assert matched == []
    assert unmatched == []


def test_en_match_is_case_insensitive():
    """en 측 pattern 은 IGNORECASE — 대문자 토큰도 동일하게 매칭."""
    lookup = _lookup(("training", "학습"))
    segments = [_segment("TRAINING is important.", "학습이 중요합니다.")]

    matched, unmatched = find_terms(segments, lookup)

    assert len(matched) == 1
    assert matched[0]["origin"] == "training"
    assert unmatched == []


def test_word_boundary_blocks_substring():
    """`\\b` 경계가 더 긴 영어 단어의 일부를 매칭하지 않는다 — "retraining" 안의 "training" 차단."""
    lookup = _lookup(("training", "학습"))
    segments = [_segment("The retraining step is added.", "재학습 단계가 추가됩니다.")]

    matched, unmatched = find_terms(segments, lookup)

    # "training" 이 pattern.finditer 에서 매칭되지 않으므로 record 자체가 생성 안 됨.
    assert matched == []
    assert unmatched == []


def test_multiple_meanings_match_on_any():
    """meanings 리스트에 여러 korean 이 있을 때 하나라도 kr 에 있으면 matched.

    expected 필드에는 meanings 의 모든 korean 이 나열됨 (사람 리뷰용).
    """
    lookup = {"model": [{"korean": "모델"}, {"korean": "모형"}]}
    segments = [_segment("The model is complex.", "이 모형은 복잡합니다.")]

    matched, unmatched = find_terms(segments, lookup)

    assert len(matched) == 1
    assert matched[0]["origin"] == "model"
    assert matched[0]["expected"] == ["모델", "모형"]
    assert unmatched == []


def test_consumed_buffer_isolated_per_segment():
    """consumed 버퍼는 세그먼트 단위로 격리된다.

    한 세그먼트에서 긴 용어가 짧은 용어의 인터벌을 consume 했더라도 다음
    세그먼트에는 이월되지 않는다. 이슈 #8 의 consume 로직은 "세그먼트 안
    에서의 중복 보고 방지" 가 목적이지 "세그먼트 간 suppress" 가 아니다.
    """
    lookup = _lookup(("training loop", "학습 루프"), ("training", "학습"))
    segments = [
        # seg A: training loop 이 matched → training 의 span 을 consume
        _segment("The training loop runs.", "학습 루프가 실행됩니다."),
        # seg B: training 단독 등장 → seg A 의 consume 와 무관하게 처리돼야 함
        _segment("Training starts here.", "여기서 시작됩니다."),
    ]

    matched, unmatched = find_terms(segments, lookup)

    matched_origins = [m["origin"] for m in matched]
    unmatched_origins = [u["origin"] for u in unmatched]

    assert "training loop" in matched_origins
    # seg A 에서는 training 이 consume 되어 skip
    # seg B 에서는 consume 버퍼 초기화 → 정상적으로 unmatched 로 분류됨
    assert "training" in unmatched_origins


# ---------------------------------------------------------------------------
# find_terms: INCLUDE_SYNONYMS 훅 계약 (SCOPE 제외 6)
# ---------------------------------------------------------------------------
#
# INCLUDE_SYNONYMS 는 terms.kr 의 `meanings[].synonyms` 를 allowed 에
# 포함할지 제어하는 모듈 상수. PR #19 에서 추가된 훅이며 현재 기본값
# False. 운영자 답변이 확정되면 이 상수 토글 한 줄로 제외 6 을 닫을 수
# 있어야 하는데, 그 전제를 유지하려면 False/True 양쪽의 계약이 박제돼
# 있어야 한다. 그래야 토글 PR 의 안전성이 이 테스트로 즉시 검증된다.


def test_include_synonyms_false_treats_synonyms_only_match_as_unmatched():
    """기본 INCLUDE_SYNONYMS=False: synonyms 에만 있는 번역어는 allowed 에 포함되지 않음."""
    lookup = {
        "activation function": [
            {"korean": "활성화 함수", "synonyms": ["활성 함수"]},
        ],
    }
    segments = [_segment("Use activation function here.", "활성 함수를 사용합니다.")]

    matched, unmatched = find_terms(segments, lookup)

    assert matched == []
    assert len(unmatched) == 1
    # expected 는 synonyms 를 포함하지 않음 — korean 만.
    assert unmatched[0]["expected"] == ["활성화 함수"]


def test_include_synonyms_true_promotes_synonyms_to_allowed(monkeypatch):
    """INCLUDE_SYNONYMS=True: synonyms 가 allowed 에 동등 권위로 포함 → matched.

    terms.kr 운영자 답변이 확정되면 이 상수 토글 한 줄로 제외 6 을 닫을
    수 있도록 훅 계약을 박제. 이 테스트가 깨지면 토글 PR 의 안전성이
    재검토 필요.
    """
    monkeypatch.setattr(match, "INCLUDE_SYNONYMS", True)

    lookup = {
        "activation function": [
            {"korean": "활성화 함수", "synonyms": ["활성 함수"]},
        ],
    }
    segments = [_segment("Use activation function here.", "활성 함수를 사용합니다.")]

    matched, unmatched = find_terms(segments, lookup)

    assert len(matched) == 1
    # expected 에 korean + synonyms 둘 다 나열.
    assert matched[0]["expected"] == ["활성화 함수", "활성 함수"]
    assert unmatched == []


# ---------------------------------------------------------------------------
# find_terms: authority propagation (v0.3.0 작업 1-2)
# ---------------------------------------------------------------------------
#
# glossary.merge_lookups 가 각 meaning 에 _authority 태그를 부여하고,
# find_terms 가 이를 matched/unmatched 레코드의 "authority" 필드로
# propagate 한다. 권위 출처가 출력에 드러나야 리뷰 시점에 "이 엔트리가
# 어느 권위에 의해 판정됐는가" 를 즉시 구분할 수 있다. 아래 두 테스트는
# 태그된/태그 없는 양쪽 경로의 계약을 고정.


def test_authority_repo_tag_propagates_to_matched():
    """meaning 에 _authority='repo' 가 있으면 matched 레코드의
    authority 필드가 'repo' 로 출력된다. merge_lookups 의 태그가
    파이프라인 끝까지 propagate 됨을 박제.
    """
    lookup = {"training": [{"korean": "학습", "_authority": "repo"}]}
    segments = [_segment("Training is important.", "학습이 중요합니다.")]

    matched, _ = find_terms(segments, lookup)

    assert len(matched) == 1
    assert matched[0]["authority"] == "repo"


def test_authority_default_terms_kr_for_untagged_meanings():
    """태그 없는 meanings 는 기본값 'terms.kr' 로 해석. merge_lookups
    를 거치지 않은 레거시 경로 (terms_all.json 만 로드한 직통 호출)
    에 대한 하위 호환 계약 — find_terms 는 항상 authority 필드를
    출력해야 한다.
    """
    lookup = {"training": [{"korean": "학습"}]}  # no _authority key
    segments = [_segment("Training is important.", "학습이 중요합니다.")]

    matched, _ = find_terms(segments, lookup)

    assert len(matched) == 1
    assert matched[0]["authority"] == "terms.kr"


def test_authority_propagates_to_unmatched():
    """matched 뿐 아니라 unmatched 레코드에도 authority 필드가 달린다.
    unmatched 분기 (기대 번역이 kr 본문에 없음) 도 권위 출처를 드러내야
    리뷰 시 '어떤 권위가 이걸 기대했는가' 를 구분 가능.
    """
    lookup = {"training": [{"korean": "학습", "_authority": "repo"}]}
    segments = [_segment("Training is important.", "공부가 중요합니다.")]

    _, unmatched = find_terms(segments, lookup)

    assert len(unmatched) == 1
    assert unmatched[0]["authority"] == "repo"
