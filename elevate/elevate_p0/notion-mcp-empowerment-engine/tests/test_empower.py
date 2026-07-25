import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from empower import Intent, plan, ANSWER

def test_search():
    r = plan(Intent("search", {"q": "x"}))
    assert r["ok"] and "notion.search" in r["chain"] and r["answer"]==ANSWER

def test_unknown():
    assert plan(Intent("nope", {}))["ok"] is False

if __name__=="__main__":
    test_search(); test_unknown(); print("ok")
