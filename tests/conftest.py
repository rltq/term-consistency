"""공통 pytest fixture.

tests/fixtures/ 의 `.diff` 와 `terms_v0.1.0.json` 을 로드해서 테스트에 주입한다.
`main` 모듈은 단계 2+3 에서 모듈 레벨 import 가능 상태로 리팩토링된 전제.
"""
import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SNAPSHOTS_DIR = Path(__file__).parent / "snapshots"


@pytest.fixture(scope="session")
def terms_lookup():
    """`tests/fixtures/terms_v0.1.0.json` 을 로드해 `main.create_lookup` 에 통과시킨 결과."""
    import main  # 단계 2+3 후에 import 가 side-effect-free 가 된다

    with (FIXTURES_DIR / "terms_v0.1.0.json").open(encoding="utf-8") as f:
        all_terms = json.load(f)
    all_terms.sort(key=lambda x: len(x["term"]), reverse=True)
    return main.create_lookup(all_terms)


@pytest.fixture
def load_diff():
    """`pr_id` → `.diff` 텍스트 로더."""

    def _load(pr_id: int) -> str:
        return (FIXTURES_DIR / f"pr_{pr_id}.diff").read_text(encoding="utf-8")

    return _load


@pytest.fixture
def snapshot_path():
    """`pr_id` → 스냅샷 JSON 파일 경로."""

    def _path(pr_id: int) -> Path:
        return SNAPSHOTS_DIR / f"pr_{pr_id}.json"

    return _path
