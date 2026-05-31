import sys
from pathlib import Path

# Ensure the project root is on sys.path so all pipelines.* imports resolve
# regardless of which directory pytest is invoked from.
sys.path.insert(0, str(Path(__file__).parent))
