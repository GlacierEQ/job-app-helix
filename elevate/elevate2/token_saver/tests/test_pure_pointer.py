import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from pure_pointer import externalize, measure, ANSWER

def test_savings():
    d = Path(tempfile.mkdtemp())
    p = externalize("hello world " * 500, d)
    m = measure(p)
    assert m["bytes_out"] < m["bytes_in"]
    assert m["answer"]==ANSWER

if __name__=="__main__":
    test_savings(); print("ok")
