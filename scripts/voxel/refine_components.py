"""Separate six validated paired Digimouse labels without changing geometry.

Run after optimize_normals.py. Requires Python 3.12, numpy and scipy.
The input metadata must still contain the original 21 source-region rows.
Published curated metadata can be preserved separately by the caller.
"""
from pathlib import Path
import argparse,sys,json,struct,hashlib,gzip,copy
sys.path.insert(0,str(Path(__file__).resolve().parent/'pydeps'))
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--input',required=True,help='Original core-web.glb or core-web.glb.gz')
parser.add_argument('--metadata',required=True,help='Original 21-row generated metadata.json')
parser.add_argument('--output',required=True,help='Output directory for refined core and metadata')
parser.add_argument('--provenance',help='Optional original provenance.json to extend')
parser.add_argument('--expected-sha',help='Optional expected decompressed output GLB SHA-256')
args=parser.parse_args()
SOURCE_GLB=Path(args.input).resolve()
INPUT_META=Path(args.metadata).resolve()
BASE=Path(args.output).resolve()
BASE.mkdir(parents=True,exist_ok=True)

def uncompressed_bytes(path):
 raw=path.read_bytes()
 return gzip.decompress(raw) if raw[:2]==b'\x1f\x8b' else raw

def read_glb(path):
 raw=uncompressed_bytes(path);size=struct.unpack_from('<I',raw,12)[0];doc=json.loads(raw[20:20+size]);binary=memoryview(raw)[28+size:]
 def read(index):
  a=doc['accessors'][index];b=doc['bufferViews'][a['bufferView']];width={'VEC3':3,'SCALAR':1}[a['type']]
  arr=np.frombuffer(binary,dtype={5126:'<f4',5125:'<u4'}[a['componentType']],count=a['count']*width,offset=b.get('byteOffset',0)+a.get('byteOffset',0))
  return arr.reshape(-1,width) if width>1 else arr
 return doc,read

def components(vertices,faces):
 rows=np.concatenate([faces[:,0],faces[:,1]]);cols=np.concatenate([faces[:,1],faces[:,2]])
 graph=coo_matrix((np.ones(len(rows),dtype=np.uint8),(rows,cols)),shape=(len(vertices),len(vertices))).tocsr()
 n,labels=connected_components(graph,directed=False);face_labels=labels[faces[:,0]]
 assert np.array_equal(face_labels,labels[faces[:,1]]) and np.array_equal(face_labels,labels[faces[:,2]])
 counts=np.bincount(face_labels,minlength=n);order=np.argsort(counts)[::-1]
 result=[]
 for index in order:
  selected=labels==index;v=vertices[selected]
  if len(v)==0:continue
  localfaces=faces[face_labels==index];xyz=vertices[localfaces]
  volume=float(np.einsum('ij,ij->i',xyz[:,0],np.cross(xyz[:,1],xyz[:,2])).sum()/6)
  result.append({'component':int(index),'vertices':int(selected.sum()),'triangles':int(counts[index]),'bounds':[v.min(axis=0).tolist(),v.max(axis=0).tolist()],'center':v.mean(axis=0).tolist(),'signedVolumeMM3':volume})
 return labels,face_labels,result

SPLIT={
 'region_3':('眼','Eye','成对眼球之一，可单独观察形态以及与脑部、泪腺的相对位置。'),
 'region_11':('咬肌','Masseter muscle','成对咬肌之一，保留源图谱中的实际外形与位置。'),
 'region_12':('泪腺','Lachrymal gland','成对泪腺之一，从原始泪腺标签的完整独立分割体中分出。'),
 'region_14':('睾丸','Testis','成对睾丸之一，两侧分别保留源标本中的实际形态与位置。'),
 'region_19':('肾脏','Kidney','成对肾脏之一，可分别观察其外形和与邻近器官的空间关系。'),
 'region_20':('肾上腺','Adrenal gland','成对肾上腺之一，从原始肾上腺标签的完整独立分割体中分出。')
}
doc,read=read_glb(SOURCE_GLB)
original_meta=json.loads(INPUT_META.read_text(encoding='utf-8'));lookup={p['id']:p for p in original_meta}
assert all(parent in lookup for parent in SPLIT) and 'region_1' in lookup, 'Use original 21-row generated metadata, not previously refined public metadata'
new_meta=[copy.deepcopy(lookup['region_1'])];meshes=[];verification=[];splits=[]
for mesh in doc['meshes']:
 primitive=mesh['primitives'][0];v=read(primitive['attributes']['POSITION']);normal=read(primitive['attributes']['NORMAL']);f=read(primitive['indices']).reshape(-1,3)
 parent=mesh['name'];meta=lookup[parent];material=copy.deepcopy(doc['materials'][primitive['material']])
 original_triangle_sha=hashlib.sha256(v[f].tobytes()).hexdigest()
 assignments=[]
 if parent in SPLIT:
  vl,fl,summary=components(v,f);assert len(summary)==2, 'Only exact two-component paired labels can be split'
  ordered=sorted(summary,key=lambda c:c['center'][0])
  # Require genuine spatially separated complete components, not a tiny island.
  assert min(s['triangles'] for s in ordered)>2000
  assert min(s['triangles'] for s in ordered)/max(s['triangles'] for s in ordered)>.50
  assert ordered[0]['bounds'][1][0]<ordered[1]['bounds'][0][0]
  for suffix,component in zip(['a','b'],ordered):
   selected=np.flatnonzero(fl==component['component']);indices,remap=np.unique(f[selected],return_inverse=True)
   vv=v[indices].copy();nn=normal[indices].copy();ff=remap.reshape(-1,3).astype('<u4')
   assert np.array_equal(vv[ff],v[f[selected]]) and np.array_equal(nn,normal[indices])
   label=suffix.upper();cn,en,description=SPLIT[parent];child=copy.deepcopy(meta)
   for key in ['voxelCenter','voxels']:child.pop(key,None)
   child.update(id=parent+'_'+suffix,name=cn+' '+label,en=en+' '+label,description=description,
    vertices=len(vv),triangles=len(ff),bounds=[vv.min(axis=0).tolist(),vv.max(axis=0).tolist()],
    center=vv.mean(axis=0).tolist(),centroid=vv.mean(axis=0).tolist(),sourceRegionId=parent,
    sourceRegionName=meta['name'],sourceLabelName=meta['sourceName'],sourceComponentId=component['component'],
    pairMember=label,pairDesignation='A/B distinguish source components; anatomical laterality is not established by the source header.',
    refinement='One complete connected component of the original paired-organ label; no surface cutting or remeshing.')
   new_meta.append(child);meshes.append((child,vv,nn,ff,material));assignments.append(selected)
  splits.append({'sourceRegionId':parent,'sourceName':meta['sourceName'],'components':ordered,'outputs':[parent+'_a',parent+'_b'],'rule':'A is the complete component with smaller source X centroid, B the larger. This does not assert anatomical left/right.'})
 else:
  child=copy.deepcopy(meta);child['sourceRegionId']=parent;new_meta.append(child)
  meshes.append((child,v.copy(),normal.copy(),f.copy(),material));assignments=[np.arange(len(f))]
 coverage=np.zeros(len(f),np.uint8)
 for selected in assignments:coverage[selected]+=1
 assert np.all(coverage==1)
 # Reconstruct source face order to verify exact original triangle coordinates.
 rebuilt=np.empty_like(v[f])
 for selected in assignments:rebuilt[selected]=v[f[selected]]
 recovered_sha=hashlib.sha256(rebuilt.tobytes()).hexdigest();assert recovered_sha==original_triangle_sha
 verification.append({'sourceRegionId':parent,'originalFaces':len(f),'outputFaces':sum(len(x) for x in assignments),'faceCoverageExactlyOnce':True,'triangleCoordinatesSHA256':original_triangle_sha,'normalValuesPreserved':True})

out={'asset':{'version':'2.0','generator':'Digimouse original voxel surfaces; six paired source regions separated at existing connected components',
 'copyright':'Digimouse, USC Biomedical Imaging Group. CC BY-SA 4.0.'},'scene':0,'scenes':[{'nodes':[]}],
 'nodes':[],'meshes':[],'materials':[],'bufferViews':[],'accessors':[],'buffers':[]}
binary=bytearray()
def accessor(a,kind,component,target):
 while len(binary)%4:binary.extend(b'\x00')
 offset=len(binary);raw=a.tobytes();binary.extend(raw)
 bi=len(out['bufferViews']);out['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':len(raw),'target':target})
 acc={'bufferView':bi,'byteOffset':0,'componentType':component,'count':len(a),'type':kind}
 if kind=='VEC3':acc.update(min=a.min(axis=0).tolist(),max=a.max(axis=0).tolist())
 else:acc.update(min=[int(a.min())],max=[int(a.max())])
 idx=len(out['accessors']);out['accessors'].append(acc);return idx
for m,v,n,f,material in meshes:
 assert np.isfinite(v).all() and np.isfinite(n).all() and f.max()<len(v)
 pos=accessor(v.astype('<f4',copy=False),'VEC3',5126,34962);norm=accessor(n.astype('<f4',copy=False),'VEC3',5126,34962);idx=accessor(f.ravel().astype('<u4',copy=False),'SCALAR',5125,34963)
 mi=len(out['materials']);material['name']=m['id'];out['materials'].append(material)
 ni=len(out['nodes']);out['nodes'].append({'name':m['id'],'mesh':len(out['meshes'])});out['scenes'][0]['nodes'].append(ni)
 out['meshes'].append({'name':m['id'],'primitives':[{'attributes':{'POSITION':pos,'NORMAL':norm},'indices':idx,'material':mi}],
 'extras':{'sourceRegionId':m['sourceRegionId'],'sourceLabelName':m['sourceName'],'refinedComponent':m.get('pairMember'),'geometryUnchanged':True}})
out['buffers']=[{'byteLength':len(binary)}]
j=json.dumps(out,ensure_ascii=True,separators=(',',':')).encode();j+=b' '*((-len(j))%4);binary.extend(b'\x00'*((-len(binary))%4))
path=BASE/'core.glb';path.write_bytes(struct.pack('<4sII',b'glTF',2,28+len(j)+len(binary))+struct.pack('<I4s',len(j),b'JSON')+j+struct.pack('<I4s',len(binary),b'BIN\x00')+binary)
with (BASE/'core.glb.gz').open('wb') as dst:
 with gzip.GzipFile(filename='',mode='wb',compresslevel=9,fileobj=dst,mtime=0) as packed:packed.write(path.read_bytes())
digest=hashlib.sha256(path.read_bytes()).hexdigest()
if args.expected_sha:assert digest==args.expected_sha, f'Unexpected output geometry/GLB digest: {digest}'
with gzip.open(BASE/'core.glb.gz','rb') as source:assert hashlib.file_digest(source,'sha256').hexdigest()==digest
assert len(meshes)==26 and len(new_meta)==27 and sum(len(f) for m,v,n,f,material in meshes)==2819068
(BASE/'metadata.json').write_text(json.dumps(new_meta,ensure_ascii=False,indent=2),encoding='utf-8')
(BASE/'geometry-validation.json').write_text(json.dumps({'parents':verification,'totalFaces':2819068,'sourceMeshCount':20,'refinedMeshCount':26,'allTriangleCoordinatesUnchanged':True,'allOriginalFacesIncludedExactlyOnce':True,'allNormalValuesPreserved':True},indent=2),encoding='utf-8')
(BASE/'paired-component-map.json').write_text(json.dumps(splits,ensure_ascii=False,indent=2),encoding='utf-8')
provenance=json.loads(Path(args.provenance).read_text(encoding='utf-8')) if args.provenance else {'title':'Digimouse component refinement','sourcePage':'https://neuroimage.usc.edu/neuro/Digimouse_Download','license':'CC BY-SA 4.0','authors':'B. Dogdas, D. Stout, A. Chatziioannou, R. M. Leahy'}
provenance['componentRefinement']={'sourceCore':'Digimouse 21-label 0.1 mm voxel atlas, 20 internal meshes + optional skin','sourceCoreSHA256':hashlib.sha256(uncompressed_bytes(SOURCE_GLB)).hexdigest(),
 'changes':'Only six original paired labels, each containing exactly two complete and spatially separate connected components, were split into independent meshes. No original triangle was cut, deleted, added, remeshed, smoothed or moved. Original rounded normals retained. Skin unchanged.',
 'sourceLabelCount':21,'selectableObjectCount':27,'coreMeshCount':26,'coreTriangles':2819068,'splitRegions':list(SPLIT),
 'laterality':'Analyze header provides no reliable anatomical-side affine. A/B are positional component identifiers, not anatomical left/right.',
 'unsplitReasons':{'lungs':'One connected source surface; no lobe segmentation inferred','liver':'One connected source surface; no lobe segmentation inferred','skeleton':'140 disconnected surface components do not provide 140 validated named bones','restOfBrain':'79 disconnected components do not establish distinct named brain regions'},
 'files':{'core.glb.gz':{'bytes':(BASE/'core.glb.gz').stat().st_size,'decompressedBytes':path.stat().st_size,'decompressedSHA256':digest,'gzipSHA256':hashlib.sha256((BASE/'core.glb.gz').read_bytes()).hexdigest()}},
 'mapping':'paired-component-map.json','validation':'geometry-validation.json'}
(BASE/'provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2),encoding='utf-8')
print('READY',json.dumps(provenance['componentRefinement'],ensure_ascii=True),flush=True)
