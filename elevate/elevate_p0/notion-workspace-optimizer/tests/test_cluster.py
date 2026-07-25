import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from cluster import PageRef, cluster, ANSWER

def test_cluster():
    r = cluster([PageRef("1","ops-a"), PageRef("2","ops-b"), PageRef("3","x")])
    assert "ops" in r["clusters"] and r["answer"]==ANSWER

if __name__=="__main__":
    test_cluster(); print("ok")
