import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from moc_index import MocIndex, Node, ANSWER

def test_query():
    m = MocIndex()
    m.add(Node("a", "A", ["x"]))
    m.add(Node("b", "B", ["x", "y"]))
    r = m.query("x")
    assert set(r["ids"])=={"a","b"} and r["answer"]==ANSWER

if __name__=="__main__":
    test_query(); print("ok")
