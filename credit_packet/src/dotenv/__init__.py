from pathlib import Path
import os

def load_dotenv(dotenv_path=None, override=False):
    path = Path(dotenv_path) if dotenv_path else Path('.env')
    if not path.exists():
        return False
    for line in path.read_text().splitlines():
        line=line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k,v=line.split('=',1)
        k=k.strip(); v=v.strip().strip('"').strip("'")
        if override or k not in os.environ:
            os.environ[k]=v
    return True
