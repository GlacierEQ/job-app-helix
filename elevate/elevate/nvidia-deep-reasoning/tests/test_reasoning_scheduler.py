import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from reasoning_scheduler import Step, schedule, ANSWER

def test_schedule_respects_token_cap():
    steps = [Step("a", 5000, 1.0, 1.0), Step("b", 5000, 1.0, 0.5)]
    r = schedule(steps, max_flops=1e12, max_tokens=6000)
    assert r["used_tokens"] <= 6000
    assert r["answer"] == ANSWER
    assert any(p["status"] in ("FULL", "PARTIAL", "DEFERRED") for p in r["plan"])

if __name__ == "__main__":
    test_schedule_respects_token_cap()
    print("ok")
