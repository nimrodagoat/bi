"""Render one entry from a drafts file (not the queue), e.g. for a preview:
python tools/render_draft.py content/drafts/explainer-bunker.yaml explainer-bunker output/preview.mp4"""
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from shorts import store  # noqa: E402
from shorts.stick import episode  # noqa: E402

path, wanted, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
items = {i["id"]: i for i in yaml.safe_load(open(path))}
episode.render(items[wanted], out, Path("output/work") / wanted, store.load_config())
print(f"rendered {out}")
