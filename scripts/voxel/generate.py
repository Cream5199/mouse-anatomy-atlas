"""Reconstruct the original Digimouse labels into the validated web assets."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys

source = Path(__file__).resolve().parent
root = source.parent.parent
manifest = json.loads((source / 'assets.json').read_text(encoding='utf-8'))
assert hashlib.sha256((source / 'atlas.zip').read_bytes()).hexdigest() == manifest['source']['sha256']
for script in ['reconstruct_voxel.py', 'split_and_validate.py', 'optimize_normals.py']:
    subprocess.run([sys.executable, str(source / script)], cwd=source, check=True)

subprocess.run([sys.executable, str(source / 'refine_components.py'),
    '--input', str(source / '.cache/core-web.glb.gz'),
    '--metadata', str(source / '.cache/metadata.json'),
    '--output', str(source / '.cache/paired'),
    '--expected-sha', manifest['models'][0]['decompressedSHA256']], check=True)

target = root / 'public/models/digimouse-voxel'
target.mkdir(parents=True, exist_ok=True)
for generated, published in [
    ('paired/core.glb.gz', 'core.glb.gz'),
    ('skin-web.glb.gz.part1', 'skin.glb.gz.part1'),
    ('skin-web.glb.gz.part2', 'skin.glb.gz.part2'),
]:
    shutil.copyfile(source / '.cache' / generated, target / published)
print('Generated web geometry. Run npm run build to verify checksums and build the site.')
