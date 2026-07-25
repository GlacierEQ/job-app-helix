import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from thermal_spec import Envelope, within_spec, ANSWER, TARGET_C

def test_ok():
    r = within_spec(Envelope(25, 10, 40), 32)
    assert r["ok"] and r["answer"]==ANSWER and r["target_c"]==TARGET_C

def test_hot():
    r = within_spec(Envelope(25, 10, 40), 90)
    assert r["ok"] is False

if __name__=="__main__":
    test_ok(); test_hot(); print("ok")
