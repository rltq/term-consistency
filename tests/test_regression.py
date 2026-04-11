"""회귀 픽스처 테스트.

픽스처 `.diff` 와 `terms_v0.1.0.json` 을 `main.main()` 파이프라인에 통과시켜
stdout JSON 을 `tests/snapshots/` 의 기대값과 비교. 스냅샷 미존재 시 자동
생성 후 의도적으로 fail — 사람 눈 검토를 강제한다.
"""
import json
import os

import pytest

from tests.conftest import FIXTURES, SNAPSHOTS

PR_IDS = [922, 923, 945, 1059]
UPDATE_SNAPSHOTS = os.environ.get("TC_UPDATE_SNAPSHOTS") == "1"


def _produce_unmatched(pr_id: int, monkeypatch, capsys) -> list:
    """`pr_id` 픽스처를 `main.main()` 에 통과시켜 unmatched JSON 을 반환."""
    import main

    diff_text = (FIXTURES / f"pr_{pr_id}.diff").read_text(encoding="utf-8")
    monkeypatch.setattr(main, "load_diff_text", lambda pr_url: diff_text)

    with (FIXTURES / "terms_v0.1.0.json").open(encoding="utf-8") as f:
        fixture_terms = json.load(f)
    fixture_terms.sort(key=lambda x: len(x["term"]), reverse=True)
    monkeypatch.setattr(main, "load_terms", lambda *a, **kw: fixture_terms)

    # 실제 github.com/PyTorchKorea/tutorials-kr URL 사용 — extract_repo_id 가
    # 유효 repo_id 를 뽑아내 load_glossary 가 pytorch-kr override 를 반환.
    # load_diff_text 는 위에서 monkeypatch 로 고정되어 네트워크 호출 없음.
    monkeypatch.setattr(
        "sys.argv",
        ["main.py", "--pr", f"https://github.com/PyTorchKorea/tutorials-kr/pull/{pr_id}"],
    )

    main.main()
    captured = capsys.readouterr()
    return json.loads(captured.out)


@pytest.mark.parametrize("pr_id", PR_IDS)
def test_regression(pr_id, monkeypatch, capsys):
    result = _produce_unmatched(pr_id, monkeypatch, capsys)
    path = SNAPSHOTS / f"pr_{pr_id}.json"

    if UPDATE_SNAPSHOTS or not path.exists():
        path.write_text(
            json.dumps(result, sort_keys=True, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if not UPDATE_SNAPSHOTS:
            pytest.fail(f"스냅샷 생성: {path.name}. 내용 확인 후 pytest 재실행.")

    expected = json.loads(path.read_text(encoding="utf-8"))
    assert result == expected
