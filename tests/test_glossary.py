"""glossary.py 의 계약 박제.

**v0.3.0 작업 1-2.** `load_glossary` 의 repo_id 매핑/fallback 과
`merge_lookups` 의 권위 우선 정책을 고정한다. 목적은 커버리지가 아니라
**계약 고정** — 향후 어댑터 추상화 (v1.1+) 가 도입되거나 추출 방침이
조정될 때 기존 계약이 깨지면 테스트가 즉시 드러내도록 하는 안전망.

범위:
- `load_glossary`: 정상 매핑 / case-insensitive / 알 수 없는 repo_id
  fallback / 엔트리 스팟 (번역안함, 분할, 명사형 축약) / 태그 일관성
- `merge_lookups`: 충돌 시 repo 완전 대체 / 비충돌 양쪽 보존 + 태깅 /
  원본 dict 비변이 / len 내림차순 정렬 (#8 회귀 가드)
"""
from term_consistency.glossary import load_glossary, merge_lookups


# ---------------------------------------------------------------------------
# load_glossary: repo_id 매핑 + fallback
# ---------------------------------------------------------------------------


def test_load_glossary_known_repo_returns_78_keys():
    """정상 repo_id → 78 키 dict 반환. 키 수는 추출 방침 드리프트 감지
    가드 — 원본 표가 바뀌어 재추출되거나 포함/제외 규칙이 조정되면 이
    숫자가 바뀌면서 방침 재검토를 강제한다.
    """
    d = load_glossary("PyTorchKorea/tutorials-kr")
    assert len(d) == 78


def test_load_glossary_is_case_insensitive():
    """repo_id 대소문자 변형은 매핑 조회에 무관. GitHub 은 저장소 slug
    의 대소문자 변형을 같은 저장소로 인식하므로 도구도 동일 정책.
    """
    lower = load_glossary("pytorchkorea/tutorials-kr")
    mixed = load_glossary("PyTorchKorea/tutorials-kr")
    upper = load_glossary("PYTORCHKOREA/TUTORIALS-KR")
    assert lower == mixed == upper
    assert len(lower) == 78


def test_load_glossary_unknown_repo_returns_empty():
    """알 수 없는 repo_id → 빈 dict. 파이프라인이 override 없이
    terms.kr 만으로 동작하는 fallback 계약 (main.py 의 wiring 이
    이 반환값에 의존).
    """
    assert load_glossary("foo/bar") == {}
    assert load_glossary("") == {}


# ---------------------------------------------------------------------------
# load_glossary: 엔트리 스팟 (추출 방침 샘플 박제)
# ---------------------------------------------------------------------------


def test_load_glossary_untranslated_entries_are_en_to_en():
    """번역안함 엔트리 (SCOPE 제외 7 의 핵심 케이스) — en 소문자 키에
    en 원형 KR 값이 매핑된다. find_terms 의 substring 매칭이 '영문이
    kr 본문에 그대로 박힘' 을 matched 로 해석해 [ERR] leak 분기를
    자연스럽게 우회하는 설계의 근거.
    """
    d = load_glossary("pytorchkorea/tutorials-kr")
    assert d["cuda"][0]["korean"] == "CUDA"
    assert d["numpy"][0]["korean"] == "NumPy"
    assert d["tensor"][0]["korean"] == "Tensor"
    # Tensor / Tensors 분할 — 두 키가 같은 KR 값에 매핑
    assert d["tensors"][0]["korean"] == "Tensor"


def test_load_glossary_split_multi_form_entries():
    """다중 폼 EN 엔트리가 개별 키로 분할. 'learning rate, lr' →
    2 키, 'Getting Started tutorial' → 'getting started' + 'tutorial'
    2 키 (후자는 원 표가 콤마 없는 두 단어 나열임을 확인 후 분할).
    분할 방침이 바뀌면 이 테스트가 재검토를 강제.
    """
    d = load_glossary("pytorchkorea/tutorials-kr")
    assert d["learning rate"][0]["korean"] == "학습률"
    assert d["lr"][0]["korean"] == "학습률"
    assert d["getting started"][0]["korean"] == "시작하기"
    assert d["tutorial"][0]["korean"] == "튜토리얼"
    # 분할 결과 'getting started tutorial' 키는 존재 안 함
    assert "getting started tutorial" not in d


def test_load_glossary_noun_form_shortening():
    """~하다/~하기 로 끝나는 긴 동사구 번역은 명사형으로 축약. 하-보조
    용언 결합이 아닌 단어 (가지치기, 읽을거리) 는 유지 — 기/히 로 끝나는
    모든 단어를 일괄 축약하지 않는다는 세부 규칙의 박제.
    """
    d = load_glossary("pytorchkorea/tutorials-kr")
    assert d["instantiate"][0]["korean"] == "생성"  # NOT "생성하다"
    assert d["warmstart"][0]["korean"] == "빠르게 시작"  # NOT "빠르게 시작하기"
    assert d["pruning"][0]["korean"] == "가지치기"  # 유지
    assert d["read later"][0]["korean"] == "더 읽을거리"  # 유지


def test_load_glossary_all_entries_tagged_repo():
    """load_glossary 가 반환하는 모든 meaning 에 _authority='repo'
    태그가 존재. find_terms 의 authority propagation 이 이 계약에
    의존하며, merge_lookups 도 repo 측 meaning 은 태그 재부여 없이
    그대로 사용한다.
    """
    d = load_glossary("pytorchkorea/tutorials-kr")
    for key, meanings in d.items():
        for m in meanings:
            assert m.get("_authority") == "repo", f"missing/wrong tag on {key}"


# ---------------------------------------------------------------------------
# merge_lookups: 권위 우선 + 태깅 + 정렬
# ---------------------------------------------------------------------------


def test_merge_conflict_repo_fully_replaces_terms_kr():
    """충돌 시 repo 가 terms.kr 의 meaning list 를 **완전 대체**.
    병합이 아니므로 terms.kr 의 다중 허용 형태는 전부 소실되고 repo 의
    단일 형태만 허용된다. '레포 권위 상위 원칙' 의 구현 — 이 정책이
    바뀌면 스냅샷 회귀 + 이 유닛 모두 깨진다.
    """
    repo = {"gradient": [{"korean": "변화도", "_authority": "repo"}]}
    terms_kr = {
        "gradient": [{"korean": "그라디언트"}, {"korean": "기울기"}],
    }
    merged = merge_lookups(repo, terms_kr)
    assert len(merged["gradient"]) == 1
    assert merged["gradient"][0]["korean"] == "변화도"
    assert merged["gradient"][0]["_authority"] == "repo"


def test_merge_non_conflict_preserves_both_with_tags():
    """비충돌 키는 양쪽 다 보존. terms.kr 측 meaning 에는 새로
    _authority='terms.kr' 태그가 copy 로 부여되며, repo 측 태그는
    그대로 유지.
    """
    repo = {"cuda": [{"korean": "CUDA", "_authority": "repo"}]}
    terms_kr = {"attention": [{"korean": "어텐션"}]}
    merged = merge_lookups(repo, terms_kr)
    assert "cuda" in merged and "attention" in merged
    assert merged["cuda"][0]["_authority"] == "repo"
    assert merged["attention"][0]["_authority"] == "terms.kr"


def test_merge_does_not_mutate_inputs():
    """원본 dict 의 meaning 에 in-place 변이 금지. terms.kr 측 원본에
    _authority 가 주입되면 추후 재직렬화 시 오염 발생 가능 — copy 경로
    가 필수. 이 계약이 깨지면 terms_all.json 이 런타임에 오염된다.
    """
    repo = {"cuda": [{"korean": "CUDA", "_authority": "repo"}]}
    terms_kr_meaning = {"korean": "어텐션"}
    terms_kr = {"attention": [terms_kr_meaning]}
    merge_lookups(repo, terms_kr)
    assert "_authority" not in terms_kr_meaning, (
        "merge_lookups 가 terms.kr 원본 meaning 에 in-place 태그를 주입했음"
    )


def test_merge_result_sorted_by_key_length_desc():
    """머지 결과는 len(key) 내림차순. find_terms 의 #8 중복 탐지 로직
    이 '긴 용어 먼저 처리' 순서에 의존 (이슈 #8: 'gradient accumulation'
    안의 'gradient' 중복 탐지 방지). 정렬 계약이 깨지면 #8 회귀 즉시.
    """
    repo = {"a": [{"korean": "a", "_authority": "repo"}]}
    terms_kr = {
        "bbbbb": [{"korean": "b"}],
        "ccc": [{"korean": "c"}],
    }
    merged = merge_lookups(repo, terms_kr)
    keys = list(merged.keys())
    lens = [len(k) for k in keys]
    assert lens == sorted(lens, reverse=True)
    assert keys == ["bbbbb", "ccc", "a"]
