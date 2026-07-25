import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from weather_gate import Weather, evaluate, ANSWER

def test_go():
    r = evaluate(Weather(10, 5, 30, 10000, 10))
    assert r["decision"]=="GO" and r["answer"]==ANSWER

def test_nogo_lightning():
    r = evaluate(Weather(10, 5, 2, 10000, 10))
    assert r["decision"]=="NO-GO" and "lightning" in r["violations"]

if __name__=="__main__":
    test_go(); test_nogo_lightning(); print("ok")
