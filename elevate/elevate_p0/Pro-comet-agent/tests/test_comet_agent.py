import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from comet_agent import CometAgent, ANSWER

def test_run():
    r = CometAgent(budget=4).run("x")
    assert r["n"]==4 and r["steps"][0]["kind"]=="plan"
    assert r["steps"][-1]["kind"]=="reflect" and r["answer"]==ANSWER

if __name__=="__main__":
    test_run(); print("ok")
