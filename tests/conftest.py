import sysfrom pathlib import PathROOT = Path(__file__).resolve().parents[1]sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
