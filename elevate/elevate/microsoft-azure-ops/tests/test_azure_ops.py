import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from azure_ops_health import RegionSample, fleet, ANSWER

def test_fleet():
    r = fleet([
        RegionSample("a", 70, 0.001, 10, 10),
        RegionSample("b", 600, 0.1, 30, 10),
    ])
    assert r["answer"] == ANSWER
    assert r["worst"]["region"] == "b"
    assert r["fleet_score"] < 1.0

if __name__ == "__main__":
    test_fleet(); print("ok")
