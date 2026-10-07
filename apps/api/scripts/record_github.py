"""Record one public GitHub profile as an offline test fixture.

    uv run python scripts/record_github.py UtkarshTheWise

Needs GITHUB_TOKEN in apps/api/.env and network access to api.github.com (not every campus Wi-Fi).
Runs the real collector and detectors through a recording transport, so every request the pipeline
makes for this profile is saved under tests/fixtures/github/<login>/. Aborts and deletes the
recording if the token string appears in any saved file.
"""

import shutil
import sys
from pathlib import Path

import httpx
from sqlalchemy.orm import sessionmaker

API_DIR = Path(__file__).resolve().parent.parent
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from app.config import get_settings  # noqa: E402
from app.db import models  # noqa: E402,F401
from app.db.base import Base, make_engine  # noqa: E402
from app.services.detectors import analyse  # noqa: E402
from app.services.github import GitHubClient, collect  # noqa: E402
from scripts.github_fixtures import FIXTURE_ROOT, RecordingTransport  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    login = argv[1]
    settings = get_settings()
    if not settings.github_token:
        print("GITHUB_TOKEN is not set in apps/api/.env")
        return 1

    out_dir = FIXTURE_ROOT / login
    if out_dir.exists():
        shutil.rmtree(out_dir)

    engine = make_engine("sqlite:///:memory:")  # a fresh cache, so every request really goes out
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db:
        client = GitHubClient(db, settings, transport=RecordingTransport(httpx.HTTPTransport(), out_dir))
        snapshot = collect(login, db, client=client)
        analyses = analyse(snapshot)

    files = list(out_dir.glob("*.json"))
    leaked = [f.name for f in files if settings.github_token in f.read_text(encoding="utf-8")]
    if leaked:
        shutil.rmtree(out_dir)
        print(f"ABORTED: the token appeared in {leaked}; recording deleted")
        return 1

    size_kb = sum(f.stat().st_size for f in files) / 1024
    print(f"recorded {len(files)} responses ({size_kb:.0f} KB) for {snapshot.login} in {out_dir}")
    print(f"{len(snapshot.repos)} repos, {len(analyses)} analysed, {client.calls} http calls\n")
    for name, a in analyses.items():
        s = a.signals
        print(
            f"{name:<24} commits {s.authored_commits}/{s.total_commits:<4} tests={s.has_tests!s:<5} "
            f"ci={s.has_ci!s:<5} kb={s.code_kb:<7} skills={sorted(a.skills)} "
            f"flags={[f.code for f in a.flags]}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
