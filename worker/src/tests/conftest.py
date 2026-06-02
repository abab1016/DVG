import sys
from pathlib import Path

# Erlaube Importe wie "from mapping.grpc_mapping import ..." in den Tests
_SRC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SRC))
