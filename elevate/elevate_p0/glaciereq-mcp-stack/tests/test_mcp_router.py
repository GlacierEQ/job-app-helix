import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from mcp_router import demo_router, ANSWER

def test_ping():
    r = demo_router()
    assert r.call("ping")["result"]=="pong" and r.call("ping")["answer"]==ANSWER

def test_deny():
    r = demo_router()
    assert r.call("evil")["ok"] is False

def test_add():
    assert demo_router().call("add", a=2, b=40)["result"]==42

if __name__=="__main__":
    test_ping(); test_deny(); test_add(); print("ok")
