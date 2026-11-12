from pathlib import Path
import sys, zipfile, struct, json, hashlib, gzip, time
SOURCE=Path(__file__).resolve().parent
BASE=SOURCE/'.cache'
BASE.mkdir(exist_ok=True)
sys.path.insert(0,str(SOURCE/'pydeps'))

import numpy as np
from skimage.measure import marching_cubes
from convert_mouse import export_glb

LABELS=[
 (1,'体表组织','Skin','#cd9d88','skin'),
 (2,'骨骼','Skeleton','#eadfc2','skeleton'),
 (3,'眼','Eyes','#506475','eye'),
 (4,'延髓','Medulla','#bd91ad','medulla'),
 (5,'小脑','Cerebellum','#dca7b5','cerebellum'),
 (6,'嗅球','Olfactory bulbs','#dba4c5','olfactory bulbs'),
 (7,'大脑外部区域','External cerebrum','#d593a5','external cerebrum'),
 (8,'纹状体','Striatum','#b487b1','striatum'),
 (9,'心脏','Heart','#aa3f43','heart'),
 (10,'脑其余区域','Rest of brain','#c39ba7','rest of the brain'),
 (11,'咬肌','Masseter muscles','#b9736a','masseter muscles'),
 (12,'泪腺','Lachrymal glands','#cbaa86','lachrymal glands'),
 (13,'膀胱','Bladder','#d8a171','bladder'),
 (14,'睾丸','Testes','#d3a17e','testis'),
 (15,'胃','Stomach','#c77c82','stomach'),
 (16,'脾','Spleen','#875174','spleen'),
 (17,'胰腺','Pancreas','#dec38b','pancreas'),
 (18,'肝脏','Liver','#87484b','liver'),
 (19,'肾脏','Kidneys','#a7494d','kidneys'),
 (20,'肾上腺','Adrenal glands','#d4b36f','adrenal glands'),
 (21,'肺','Lungs','#d799a0','lungs')
]
started=time.time()
with zipfile.ZipFile(SOURCE/'atlas.zip') as z:
 assert z.testzip() is None
 hdr=z.read('atlas/atlas_380x992x208.hdr')
 dims=struct.unpack_from('<8h',hdr,40)[1:4]
 spacing=np.array(struct.unpack_from('<8f',hdr,76)[1:4],dtype=np.float64)
 assert struct.unpack_from('<i',hdr,0)[0]==348
 assert struct.unpack_from('<2h',hdr,70)==(2,8)
 assert struct.unpack_from('<f',hdr,108)[0]==0
 raw=z.read('atlas/atlas_380x992x208.img')
 for name in ['atlas_380x992x208.txt','LICENSE.txt']:
  (BASE/name).write_bytes(z.read('atlas/'+name))
vol=np.frombuffer(raw,dtype=np.uint8).reshape(dims,order='F')
assert len(raw)==int(np.prod(dims))
assert np.array_equal(np.unique(vol),np.arange(22))
print('HEADER',dims,spacing,'labels',np.unique(vol).tolist(),flush=True)
meshes=[];metadata=[];checks=[]
for region,name,en,color,source in LABELS:
 mask=(vol==region)
 extents=[]
 for axis in range(3):
  axes=tuple(i for i in range(3) if i!=axis)
  found=np.flatnonzero(np.any(mask,axis=axes))
  extents.append((int(found[0]),int(found[-1])+1))
 slices=tuple(slice(a,b) for a,b in extents)
 cropped=np.pad(mask[slices],1).astype(np.uint8)
 verts,faces,_,_=marching_cubes(cropped,level=.5,spacing=tuple(spacing),step_size=1,allow_degenerate=False,method='lewiner',gradient_direction='descent')
 verts+=(np.array([a for a,b in extents])-1)*spacing
 verts=verts.astype('<f4');faces=faces.astype('<u4')
 xyz=verts[faces]
 signed_volume=float(np.einsum('ij,ij->i',xyz[:,0],np.cross(xyz[:,1],xyz[:,2])).sum()/6)
 if signed_volume<0:
  faces=faces[:,[0,2,1]].copy();signed_volume=-signed_volume
 area2=np.linalg.norm(np.cross(xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0]),axis=1)
 assert np.isfinite(verts).all() and np.isfinite(area2).all()
 assert faces.max()<len(verts) and area2.min()>0 and signed_volume>0
 # Compare enclosed surface volume with the literal labelled voxel volume.
 voxel_count=int(mask.sum()); voxel_volume=voxel_count*float(np.prod(spacing))
 relative_error=abs(signed_volume-voxel_volume)/voxel_volume
 voxel_center=[]
 for axis in range(3):
  counts=mask.sum(axis=tuple(i for i in range(3) if i!=axis))
  voxel_center.append(float(np.dot(counts,np.arange(dims[axis]))/voxel_count*spacing[axis]))
 item={'id':f'region_{region}','region':region,'name':name,'en':en,'color':color,'sourceName':source,
 'vertices':len(verts),'triangles':len(faces),'bounds':[verts.min(axis=0).tolist(),verts.max(axis=0).tolist()],
 'center':verts.mean(axis=0).tolist(),'centroid':verts.mean(axis=0).tolist(),'voxelCenter':voxel_center,
 'voxels':voxel_count}
 metadata.append(item)
 checks.append({'region':region,'vertices':len(verts),'triangles':len(faces),'minimumDoubleArea':float(area2.min()),'surfaceVolumeMM3':signed_volume,'voxelVolumeMM3':voxel_volume,'relativeVolumeDifference':relative_error})
 meshes.append((item['id'],verts,faces,color,{'region':region,'sourceName':source,'method':'Original 0.1 mm segmentation; marching cubes step 1; no smoothing or decimation'}))
 print(region,name,'triangles',len(faces),'center',voxel_center,'volume difference',relative_error,flush=True)
 del xyz,mask,cropped
print('Export',sum(p['triangles'] for p in metadata),'triangles',flush=True)
path=BASE/'voxel-atlas.glb'
export_glb(meshes,path)
if path.stat().st_size>24*1024*1024:
 with path.open('rb') as src,gzip.open(str(path)+'.gz','wb',compresslevel=9) as dst:
  while chunk:=src.read(1024*1024):dst.write(chunk)
(BASE/'metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
provenance={
 'title':'Digimouse original 0.1 mm labelled voxel atlas, surface reconstruction',
 'source':'https://neuroimage.usc.edu/mouse_atlas/atlas.zip',
 'sourcePage':'https://neuroimage.usc.edu/neuro/Digimouse_Download',
 'license':'CC BY-SA 4.0','licensePage':'https://neuroimage.usc.edu/neuro/Digimouse_license',
 'authors':'B. Dogdas, D. Stout, A. Chatziioannou, R. M. Leahy',
 'citation':'Digimouse: A 3D Whole Body Mouse Atlas from CT and Cryosection Data. Phys. Med. Biol. 52:577–587 (2007).',
 'doi':'https://doi.org/10.1088/0031-9155/52/3/003',
 'changes':'Direct Lewiner marching cubes at level 0.5, step_size=1, from each original labelled voxel mask. Masks padded with background to close surfaces. No smoothing, subdivision, decimation, coordinate-axis swaps or invented anatomy. Winding corrected outward; vertex normals computed; illustrative colors assigned.',
 'data':{'format':'Analyze 7.5','dimensions':dims,'datatype':'uint8','spacingMM':spacing.tolist(),'storageOrder':'Analyze first index x varies fastest (Fortran reshape)','headerOrient':int(hdr[252]),'headerOriginatorBytes':list(hdr[253:263]),'coordinates':'Zero-based voxel indices times header spacing; no supplied affine/anatomical laterality; no axis inversion or rescaling performed.'},
 'warnings':['21 non-background labels are source regions, not individual anatomical structures. Some labels contain paired organs.','Skeleton is one region; complete vessels, individual muscles and nerves are not segmented.','Label 1 source name skin occupies surrounding body tissues as well as outer boundary; hide for internal anatomy.','Source header does not establish anatomical left/right. Preserve source coordinates and do not relabel paired organs by guessed laterality.'],
 'originalArchiveSHA256':hashlib.sha256((SOURCE/'atlas.zip').read_bytes()).hexdigest(),
 'glbSHA256':hashlib.sha256(path.read_bytes()).hexdigest(),
 'totalTriangles':sum(x['triangles'] for x in metadata),'glbBytes':path.stat().st_size,
 'conversionSeconds':time.time()-started
}
(BASE/'provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2),encoding='utf-8')
(BASE/'validation.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
print('DONE',provenance['totalTriangles'],path.stat().st_size,'bytes',time.time()-started,'seconds',flush=True)
