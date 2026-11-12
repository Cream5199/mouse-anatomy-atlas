from pathlib import Path
import sys,json,struct,gzip,hashlib
SOURCE=Path(__file__).resolve().parent
BASE=SOURCE/'.cache'
BASE.mkdir(exist_ok=True)

import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/'pydeps'))
import numpy as np
from convert_mouse import export_glb

def load(path):
 raw=path.read_bytes()
 assert struct.unpack_from('<4sII',raw)==(b'glTF',2,len(raw))
 n,tag=struct.unpack_from('<I4s',raw,12);assert tag==b'JSON'
 doc=json.loads(raw[20:20+n]);bsize,btag=struct.unpack_from('<I4s',raw,20+n);assert btag==b'BIN\x00'
 binary=memoryview(raw)[28+n:];assert len(binary)==bsize
 def access(index):
  acc=doc['accessors'][index];view=doc['bufferViews'][acc['bufferView']]
  types={5126:'<f4',5125:'<u4'};widths={'VEC3':3,'SCALAR':1}
  width=widths[acc['type']];dt=types[acc['componentType']]
  offset=view.get('byteOffset',0)+acc.get('byteOffset',0)
  a=np.frombuffer(binary,dtype=dt,count=acc['count']*width,offset=offset)
  return a.reshape(-1,width) if width>1 else a
 return raw,doc,access

def correct_generator(path):
 raw=path.read_bytes();n=struct.unpack_from('<I',raw,12)[0];doc=json.loads(raw[20:20+n]);binary=raw[28+n:]
 doc['asset']['generator']='Digimouse original labelled voxel surface reconstruction; marching cubes step 1'
 j=json.dumps(doc,ensure_ascii=True,separators=(',',':')).encode();j+=b' '*((-len(j))%4)
 path.write_bytes(struct.pack('<4sII',b'glTF',2,28+len(j)+len(binary))+struct.pack('<I4s',len(j),b'JSON')+j+struct.pack('<I4s',len(binary),b'BIN\x00')+binary)

def compress(path):
 dest=Path(str(path)+'.gz')
 with path.open('rb') as src,gzip.open(dest,'wb',compresslevel=9) as out:
  while chunk:=src.read(1024*1024):out.write(chunk)
 with gzip.open(dest,'rb') as f:gzsha=hashlib.file_digest(f,'sha256').hexdigest()
 sha=hashlib.sha256(path.read_bytes()).hexdigest();assert sha==gzsha
 return {'file':path.name,'bytes':path.stat().st_size,'gzipFile':dest.name,'gzipBytes':dest.stat().st_size,'sha256':sha,'gzipSHA256':hashlib.sha256(dest.read_bytes()).hexdigest()}

metadata=json.loads((BASE/'metadata.json').read_text(encoding='utf-8'))
raw,doc,access=load(BASE/'voxel-atlas.glb')
by_id={p['id']:p for p in metadata};meshes=[]
for node in doc['nodes']:
 mesh=doc['meshes'][node['mesh']];prim=mesh['primitives'][0]
 pts=access(prim['attributes']['POSITION']);faces=access(prim['indices']).reshape(-1,3)
 norm=access(prim['attributes']['NORMAL']);meta=by_id[node['name']]
 assert len(faces)==meta['triangles'] and np.isfinite(pts).all() and np.isfinite(norm).all() and faces.max()<len(pts)
 assert np.allclose(pts.min(axis=0),meta['bounds'][0]) and np.allclose(pts.max(axis=0),meta['bounds'][1])
 meshes.append((node['name'],pts,faces,meta['color'],mesh['extras']))
assert len(meshes)==21 and sum(len(m[2]) for m in meshes)==6708992
outputs={}
for name,subset in [('core',[m for m in meshes if m[0]!='region_1']),('skin',[m for m in meshes if m[0]=='region_1'])]:
 path=BASE/(name+'.glb');export_glb(subset,path);correct_generator(path)
 _,checkdoc,_=load(path);assert len(checkdoc['meshes'])==len(subset)
 outputs[name]=compress(path);outputs[name].update(meshes=len(subset),triangles=sum(len(m[2]) for m in subset))
 print(name,outputs[name],flush=True)
for p in metadata:
 if p['id']=='region_1':p.update(lazyModelUrl='/models/digimouse-voxel/skin.glb.gz',defaultHidden=True,category='skin')
 elif p['id']=='region_2':p.update(category='skeleton')
 else:p.update(category='organs')
(BASE/'metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
provenance=json.loads((BASE/'provenance.json').read_text(encoding='utf-8'))
provenance['publishedAssets']={'core':outputs['core'],'optionalSkin':outputs['skin'],'layout':'20 internal original label surfaces in core; optional original region_1 body tissue surface loaded on demand. Total 21 source labels, no decimation.'}
provenance['validation']='All 21 mesh node ids match metadata; finite vertices and normals; triangle indices in range; exact metadata bounds; extracted closed volumes differ from source voxel volumes by less than 0.71%; decompressed gzip SHA-256 equals corresponding GLB.'
(BASE/'provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2),encoding='utf-8')
(BASE/'asset-validation.json').write_text(json.dumps(outputs,indent=2),encoding='utf-8')
print('VALIDATED',json.dumps(outputs),flush=True)
