"""회귀 픽스처 테스트.

단계 4 에서 4건의 골든 케이스 스냅샷을 박제한 후 실제 비교 로직이 활성화된다.
그 전까지는 스켈레톤만 존재하며 pytest 실행 시 `skip` 된다.
"""
import pytest

# v0.2 시작 시점의 골든 케이스 4건 (docs/ROADMAP.md v0.2.0 작업 2)
PR_IDS = [922, 923, 945, 1059]


@pytest.mark.skip(reason="단계 4 에서 구현 예정")
@pytest.mark.parametrize("pr_id", PR_IDS)
def test_regression(pr_id, load_diff, terms_lookup, snapshot_path, capsys, monkeypatch):
    """`pr_id` 의 픽스처 `.diff` 를 `main.main()` 에 통과시켜 stdout JSON 을 스냅샷과 비교."""
    pass
