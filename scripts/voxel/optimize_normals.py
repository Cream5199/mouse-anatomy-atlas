from pathlib import Path
import json, struct, hashlib, gzip, time
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/'pydeps'))
import numpy as np
SOURCE=Path(__file__).resolve().parent
BASE=SOURCE/'.cache'
BASE.mkdir(exist_ok=True)
results={}
for prefix in ['core','skin']:
 started_at=time.time();source=BASE/(prefix+'.glb');raw=bytearray(source.read_bytes())
 json_size=struct.unpack_from('<I',raw,12)[0];doc=json.loads(raw[20:20+json_size]);binary_start=28+json_size
 def view(accessor_index):
  a=doc['accessors'][accessor_index];v=doc['bufferViews'][a['bufferView']]
  assert 'byteStride' not in v
  components={'VEC3':3,'SCALAR':1}[a['type']]
  start=binary_start+v.get('byteOffset',0)+a.get('byteOffset',0)
  dtype={5126:'<f4',5125:'<u4'}[a['componentType']]
  size=a['count']*components*4
  return start,size,dtype,components
 protected=[];before_hashes={};normal_stats=[]
 for mesh in doc['meshes']:
  for primitive in mesh['primitives']:
   for label,index in [('POSITION',primitive['attributes']['POSITION']),('indices',primitive['indices'])]:
    start,size,_,_=view(index);key=mesh['name']+':'+label
    protected.append((key,start,size));before_hashes[key]=hashlib.sha256(raw[start:start+size]).hexdigest()
   start,size,dtype,width=view(primitive['attributes']['NORMAL'])
   orig=np.frombuffer(raw,dtype=dtype,count=size//4,offset=start).reshape(-1,width).copy().astype(np.float64)
   rounded=np.round(orig,5).astype('<f4');new=rounded.astype(np.float64)
   oldlen=np.linalg.norm(orig,axis=1);newlen=np.linalg.norm(new,axis=1);valid=(oldlen>1e-12)&(newlen>1e-12)
   cosine=np.clip(np.einsum('ij,ij->i',orig[valid],new[valid])/(oldlen[valid]*newlen[valid]),-1,1)
   maxangle=float(np.degrees(np.arccos(cosine)).max()) if valid.any() else 0
   maxlen=float(np.max(np.abs(oldlen-newlen)))
   assert np.isfinite(new).all() and np.array_equal(oldlen>1e-12,newlen>1e-12)
   assert maxangle<.001 and maxlen<.00001
   raw[start:start+size]=rounded.tobytes()
   normal_stats.append({'mesh':mesh['name'],'maxAngularErrorDegrees':maxangle,'maxLengthChange':maxlen,'vertices':len(orig)})
 after_hashes={key:hashlib.sha256(raw[start:start+size]).hexdigest() for key,start,size in protected}
 assert before_hashes==after_hashes
 out=BASE/(prefix+'-web.glb');out.write_bytes(raw)
 packed=BASE/(prefix+'-web.glb.gz')
 with gzip.open(packed,'wb',compresslevel=9) as dst:dst.write(raw)
 original_sha=hashlib.sha256(raw).hexdigest()
 with gzip.open(packed,'rb') as src:assert hashlib.file_digest(src,'sha256').hexdigest()==original_sha
 result={'file':out.name,'bytes':len(raw),'gzipFile':packed.name,'gzipBytes':packed.stat().st_size,'sha256':original_sha,
  'gzipSHA256':hashlib.sha256(packed.read_bytes()).hexdigest(),'geometrySHA256ByMeshAndAccessor':before_hashes,
  'normalStatistics':normal_stats,'normalChange':'Only NORMAL float32 values rounded to five decimal places. POSITION and triangle index accessor bytes exactly unchanged.',
  'maxNormalAngularErrorDegrees':max(x['maxAngularErrorDegrees'] for x in normal_stats),'maxNormalLengthChange':max(x['maxLengthChange'] for x in normal_stats)}
 if packed.stat().st_size>24*1024*1024:
  blob=packed.read_bytes();chunk_size=(len(blob)+1)//2;assert chunk_size<20*1024*1024
  volumes=[]
  for i,offset in enumerate(range(0,len(blob),chunk_size),1):
   part=BASE/(prefix+f'-web.glb.gz.part{i}');content=blob[offset:offset+chunk_size];part.write_bytes(content)
   volumes.append({'file':part.name,'bytes':len(content),'sha256':hashlib.sha256(content).hexdigest()})
  joined=b''.join((BASE/p['file']).read_bytes() for p in volumes);assert hashlib.sha256(joined).hexdigest()==result['gzipSHA256']
  result['volumes']=volumes;result['volumeUse']='Fetch volumes in order, concatenate binary bytes, then decompress one gzip stream.'
 results[prefix]=result
 print(prefix,json.dumps({k:v for k,v in result.items() if k not in ['geometrySHA256ByMeshAndAccessor','normalStatistics']}),flush=True)
 print('elapsedSeconds',time.time()-started_at,flush=True)
(BASE/'normal-optimization-validation.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
provenance=json.loads((BASE/'provenance.json').read_text(encoding='utf-8'))
provenance['normalPrecisionOptimization']={'changes':'Only NORMAL float32 attributes rounded to five decimal places to reduce gzip entropy; original POSITION and triangle index accessor bytes verified identical, no geometry changes.',
 'validation':'normal-optimization-validation.json','core':{k:v for k,v in results['core'].items() if k not in ['geometrySHA256ByMeshAndAccessor','normalStatistics']},'skin':{k:v for k,v in results['skin'].items() if k not in ['geometrySHA256ByMeshAndAccessor','normalStatistics']}}
(BASE/'provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2),encoding='utf-8')
