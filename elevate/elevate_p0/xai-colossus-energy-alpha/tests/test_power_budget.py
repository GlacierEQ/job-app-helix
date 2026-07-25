import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from power_budget import Load, budget, ANSWER

def test_ok():
    r = budget([Load("a", 10)], 20)
    assert r["status"]=="OK" and r["answer"]==ANSWER and r["strand"]=="alpha"

def test_over():
    r = budget([Load("a", 30)], 20)
    assert r["status"]=="OVERSUBSCRIBED"

if __name__=="__main__":
    test_ok(); test_over(); print("ok")
