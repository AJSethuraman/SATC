"""Hand one command to the open window and print what came back.   python3 send.py 'shot("x")'  or  send.py -f file"""
import sys
import time
from pathlib import Path

DRV = Path(__file__).resolve().parent
src = Path(sys.argv[2]).read_text() if sys.argv[1] == "-f" else sys.argv[1]
(DRV / "done").unlink(missing_ok=True)
(DRV / "cmd.py").write_text(src)
wait = float(sys.argv[-1]) if sys.argv[-1].replace(".", "").isdigit() and len(sys.argv) > 2 and sys.argv[1] != "-f" else 3000
t = time.time()
while not (DRV / "done").exists():
    if time.time() - t > wait:
        print("no answer yet")
        sys.exit(1)
    time.sleep(0.2)
print((DRV / "out.txt").read_text())
