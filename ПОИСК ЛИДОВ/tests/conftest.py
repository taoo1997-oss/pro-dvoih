import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIX = Path(__file__).resolve().parent / "fixtures"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from finder import store  # noqa: E402
from finder.config import load_config  # noqa: E402


@pytest.fixture
def cfg():
    return load_config(ROOT / "config.json")


@pytest.fixture
def db(tmp_path):
    conn = store.connect(tmp_path / "t.db")
    yield conn
    conn.close()


@pytest.fixture
def fixtures_dir():
    return FIX


class FakeResp:
    def __init__(self, path=None, text=None, status=200):
        if path is not None:
            self._bytes = Path(path).read_bytes()
            self.text = self._bytes.decode("utf-8", "replace")
        else:
            self.text = text or ""
            self._bytes = self.text.encode("utf-8")
        self.status_code = status
        self.encoding = "utf-8"
        self.headers = {"content-type": "text/html; charset=utf-8"}

    @property
    def content(self):
        return self._bytes
