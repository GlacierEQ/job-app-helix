import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from flow_controller import PID, control_loop, ANSWER, TARGET_C

def test_hot_increases_flow():
    pid = PID()
    cool = pid.step(40)
    hot = pid.step(80)
    assert hot > cool
    r = control_loop([40, 90])
    assert r["answer"]==ANSWER and r["target_c"]==TARGET_C

if __name__=="__main__":
    test_hot_increases_flow(); print("ok")
