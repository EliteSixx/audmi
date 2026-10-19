
import json
from pathlib import Path

folder = Path("data/synthetic/golden_dataset")

for file in sorted(folder.glob("*.json")):
    data = json.loads(file.read_text(encoding="utf-8"))

    if isinstance(data, list):
        count = len(data)
    elif isinstance(data, dict):
        count = len(data["data"]) if isinstance(
            data.get("data"), list) else "inspect structure"
    else:
        count = "inspect structure"

    print(f"{file.name}: {count}")
