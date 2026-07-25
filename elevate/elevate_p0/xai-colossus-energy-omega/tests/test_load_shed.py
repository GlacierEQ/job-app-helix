import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from load_shed import Circuit, shed, ANSWER

def test_shed_low_priority_first():
    r = shed([Circuit("crit", 10, 1), Circuit("batch", 5, 9)], 4)
    assert r["actions"][0]["shed"]=="batch"
    assert r["met"] and r["answer"]==ANSWER and r["strand"]=="omega"

if __name__=="__main__":
    test_shed_low_priority_first(); print("ok")
