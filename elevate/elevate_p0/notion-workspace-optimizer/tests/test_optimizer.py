import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from optimizer import Page, optimize, score_page, ANSWER

def test_ranks_stale():
    pages = [Page("a","fresh",1,1,1,0), Page("b","stale",2,0,200,0)]
    r = optimize(pages, top_k=2)
    assert r["answer"]==ANSWER
    assert r["actions"][0]["id"]=="b"
    assert r["actions"][0]["action"]=="ARCHIVE_CANDIDATE"

def test_score_bounds():
    s = score_page(Page("x","t",0,0,0,0))
    assert s >= 0.3

if __name__=="__main__":
    test_ranks_stale(); test_score_bounds(); print("ok")
