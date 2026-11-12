"""Reproduce the authored mouse teaching extension after generating Digimouse assets."""
from pathlib import Path
import subprocess,sys,shutil
root=Path(__file__).resolve().parents[2]
source=Path(__file__).resolve().parent
for name in ['digestive','vascular','muscles']:
    out=source/'.cache'/name
    command=[sys.executable,str(source/name/('generate_'+name+'.py')),'--output',str(out)]
    if name=='digestive':command+=['--metadata',str(root/'public/models/digimouse-voxel/metadata.json'),'--source-core',str(root/'public/models/digimouse-voxel/core.glb.gz'),'--skip-preview']
    subprocess.run(command,check=True)
    target=root/'public/models/mouse-teaching'/name
    target.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(out/'core.glb.gz',target/'core.glb.gz')
print('Generated teaching geometry; curated metadata is unchanged. npm run build verifies model checksums.')
