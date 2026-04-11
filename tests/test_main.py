"""main.py 의 CLI 인접 헬퍼 계약 박제.

**v0.3.0 작업 1-2.** `extract_repo_id` 는 PR URL 에서 'owner/name' 을
뽑아내는 URL 파싱 로직으로, `load_glossary` 의 repo_id fallback 정책과
결합해 파이프라인이 네트워크 호출 없이 override 가용 여부를 결정하는
첫 관문이다. 이 헬퍼가 잘못된 입력에 크래시하거나 기대 못 한 값을
반환하면 override 경로 전체가 무력화되거나 예기치 못한 동작으로 흐를
수 있어 엣지 케이스를 명시적으로 박제한다.
"""
from main import extract_repo_id


def test_extract_repo_id_github_pr_url():
    """정상 GitHub PR URL → 'owner/name' 형태. pull 번호는 결과에
    포함되지 않는다. 이 형식이 load_glossary 의 repo_id 매핑 키와
    정확히 일치해야 한다 (case-insensitive 는 load_glossary 측 정책).
    """
    url = "https://github.com/PyTorchKorea/tutorials-kr/pull/1056"
    assert extract_repo_id(url) == "PyTorchKorea/tutorials-kr"


def test_extract_repo_id_preserves_case():
    """repo_id 추출은 URL 의 대소문자를 보존한다. 대소문자 무시 매칭은
    load_glossary 가 책임지므로 이 헬퍼는 raw 입력 유지.
    """
    url = "https://github.com/pytorchkorea/tutorials-kr/pull/1"
    assert extract_repo_id(url) == "pytorchkorea/tutorials-kr"


def test_extract_repo_id_non_github_host():
    """github.com 이 아닌 호스트 → 빈 문자열. load_glossary 의
    fallback 경로 (빈 dict) 로 위임된다. gitlab, bitbucket 등의
    호스트 지원은 v1.1+ 의 별개 이슈.
    """
    assert extract_repo_id("https://gitlab.com/foo/bar/pull/1") == ""
    assert extract_repo_id("https://bitbucket.org/foo/bar/pull/1") == ""


def test_extract_repo_id_short_or_empty_path():
    """경로에 owner 만 있거나 비어있으면 빈 문자열. 'owner' 단독은
    PR URL 형태가 아니므로 override 매핑을 시도하지 않는다.
    """
    assert extract_repo_id("https://github.com/only-one") == ""
    assert extract_repo_id("https://github.com/") == ""
    assert extract_repo_id("https://github.com") == ""


def test_extract_repo_id_malformed_input():
    """URL 형태가 아닌 문자열 — 크래시 없이 빈 문자열 반환. 테스트
    픽스처나 잘못된 CLI 입력에서도 파이프라인이 fallback 경로로
    안전하게 흐르도록 하는 계약.
    """
    assert extract_repo_id("not a url") == ""
    assert extract_repo_id("") == ""
