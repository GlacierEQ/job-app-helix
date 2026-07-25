import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from workflow_engine import Workflow, Stage, ANSWER

def test_flow():
    wf = Workflow("t", [Stage("a", lambda s: True, 1), Stage("b", lambda s: s.get("ok"), 1)])
    r1 = wf.advance()
    assert r1["advanced_to"]=="a"
    wf.state["ok"]=True
    r2 = wf.advance()
    assert r2["advanced_to"]=="b" and r2["answer"]==ANSWER

if __name__=="__main__":
    test_flow(); print("ok")
