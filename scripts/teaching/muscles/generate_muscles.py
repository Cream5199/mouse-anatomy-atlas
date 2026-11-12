# SPDX-License-Identifier: CC-BY-SA-4.0
"""Author major mouse muscle groups aligned to fixed Digimouse landmarks.
Teaching reconstruction only: no muscle surfaces are claimed to be segmented CT.
Usage: python generate_muscles.py --output generated --landmarks landmarks.json
Requires NumPy and SciPy. Output geometry is in untransformed source millimetres.
"""
from pathlib import Path
import argparse,json,struct,gzip,hashlib,sys
SOURCE=Path(__file__).resolve().parent
sys.path.insert(0,str(SOURCE/'pydeps'))
import numpy as np
from scipy.interpolate import CubicSpline
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,default=SOURCE)
parser.add_argument('--landmarks',type=Path,default=SOURCE/'landmarks.json')
args=parser.parse_args();OUT=args.output.resolve();OUT.mkdir(parents=True,exist_ok=True)
LANDMARKS=json.loads(args.landmarks.read_text(encoding='utf-8'))

def point(name):return np.array(LANDMARKS[name]['point'],float)
def linear(c):return np.where(c<=.04045,c/12.92,((c+.055)/1.055)**2.4)
def loft(path,width,depth,phase=0,skew=.12,bands=False,n=80,rings=48,color='#b87879'):
 p=np.array(path,float);distance=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))];t=np.linspace(0,1,n)
 spline=CubicSpline(distance/distance[-1],p,axis=0,bc_type='natural');center=spline(t);tangent=spline(t,1);tangent/=np.linalg.norm(tangent,axis=1)[:,None]
 dep=np.tile([0.,0.,1.],(n,1));dep-=np.sum(dep*tangent,axis=1)[:,None]*tangent;dep/=np.linalg.norm(dep,axis=1)[:,None]
 wide=np.cross(dep,tangent);angle=np.arange(rings)*2*np.pi/rings
 # Narrow attachment/tendon ends, asymmetric bulging muscle belly, mild twist.
 belly=np.sin(np.pi*t)**.72;profile=(.06+.94*belly)*(1+skew*np.cos(np.pi*t))
 if bands:
  for intersection in [.27,.48,.69]:profile*=1-.15*np.exp(-((t-intersection)/.027)**2)
 twist=.16*np.sin(np.pi*t+phase);cos=np.cos(angle[None,:]+twist[:,None]);sin=np.sin(angle[None,:]+twist[:,None])
 # Longitudinal fascicle relief follows the changing surface; deliberately
 # subtle, not an artificial scan noise texture or stacks of primitives.
 ridge=1+.036*belly[:,None]**1.5*np.cos(10*angle[None,:]+1.6*np.sin(np.pi*t[:,None])+phase)
 ridge+=.006*belly[:,None]*np.sin(42*np.pi*t[:,None]+2*angle[None,:])
 vertices=center[:,None,:]+wide[:,None,:]*(width*profile[:,None]*cos*ridge)[:,:,None]+dep[:,None,:]*(depth*profile[:,None]*sin*ridge)[:,:,None]
 v=vertices.reshape(-1,3).astype('<f4');f=[]
 for i in range(n-1):
  for j in range(rings):
   k=(j+1)%rings;f.extend([(i*rings+j,(i+1)*rings+j,(i+1)*rings+k),(i*rings+j,(i+1)*rings+k,i*rings+k)])
 start=len(v);v=np.vstack([v,center[0],center[-1]]).astype('<f4')
 for j in range(rings):
  k=(j+1)%rings;f.append((start,k,j));f.append((start+1,(n-1)*rings+j,(n-1)*rings+k))
 f=np.array(f,dtype='<u4');q=v[f];signed=float(np.einsum('ij,ij->i',q[:,0],np.cross(q[:,1],q[:,2])).sum()/6)
 if signed<0:f=f[:,[0,2,1]].copy()
 base=np.array([int(color[i:i+2],16)/255 for i in [1,3,5]])
 tendon=np.clip((np.abs(t-.5)-.29)/.18,0,1);tendon=tendon*tendon*(3-2*tendon)
 tint=base[None,None,:]*(1+.038*np.cos(10*angle[None,:,None]+phase+1.3*np.sin(t[:,None,None]*np.pi)))
 tint=np.broadcast_to(tint,(n,rings,3)).copy();ivory=np.array([.85,.825,.77])
 tint=tint*(1-tendon[:,None,None])+ivory[None,None,:]*tendon[:,None,None]
 colors=np.vstack([linear(np.clip(tint,0,1)).reshape(-1,3),linear(ivory)[None,:],linear(ivory)[None,:]])
 colors=np.round(np.c_[colors,np.ones(len(colors))]*255).astype('u1')
 return v,f,colors

def join(chunks):
 vertices=[];faces=[];colors=[];offset=0
 for v,f,c in chunks:vertices.append(v);faces.append(f+offset);colors.append(c);offset+=len(v)
 return np.concatenate(vertices),np.concatenate(faces),np.concatenate(colors)

parts=[]
def add(key,cn,en,side,path,width,depth,description,hidden=False,bands=False,bundles=1,color='#b87879'):
 chunks=[loft(path,width,depth,phase=.5 if side=='b' else 0,bands=bands,color=color)]
 if bundles>1:
  for i in range(bundles-1):
   p=np.array(path,float);p[:,2]-=depth*.50;p[:,0]+=(i-(bundles-2)/2)*width*.65
   chunks.append(loft(p,width*.39,depth*.62,phase=i*.6+.5,n=64,rings=32,color=color))
 v,f,c=join(chunks);id='teaching_muscle_'+key+'_'+side;label=side.upper()
 meta={'id':id,'name':cn+' '+label,'en':en+' '+label,'color':color,'sourceName':en,'description':description,
 'category':'muscular','origin':'teaching','defaultHidden':hidden,'vertexColors':True,
 'bounds':[v.min(axis=0).tolist(),v.max(axis=0).tolist()],'center':v.mean(axis=0).tolist(),'centroid':v.mean(axis=0).tolist(),
 'vertices':len(v),'triangles':len(f),'pairMember':label,
 'pairDesignation':'A/B match source positional sides; anatomical left/right is not established.',
 'provenance':{'kind':'self-authored teaching reconstruction','scanDerived':False,'registration':'Fixed source skeleton landmarks; original raw millimetre coordinate frame','generator':'generate_muscles.py'}}
 parts.append((meta,v,f,c))

for side,sign in [('a',-1),('b',1)]:
 sh=point('shoulder_'+side);el=point('elbow_'+side);wr=point('wrist_'+side);hip=point('hip_'+side);knee=point('knee_'+side);ankle=point('ankle_'+side)
 # Forelimb geometry follows the actual raised forearms in this specimen.
 add('biceps_brachii','肱二头肌','Biceps brachii',side,[sh+[0,0,-.3],sh*.62+el*.38+[0,-.6,-.8],sh*.24+el*.76+[0,-.45,-.65],el+[0,-.8,-.1]],1.12,.76,'上臂前侧的教学肌腹与渐尖肌腱，沿真实肱骨位置布置，用于识别上臂屈肌关系。')
 add('triceps_brachii','肱三头肌群','Triceps brachii group',side,[sh+[0,1.6,1.2],sh*.6+el*.4+[0,1.35,1.05],sh*.25+el*.75+[0,1.1,.9],el+[0,.65,.6]],1.55,.95,'上臂后侧肌群的教学重建，与肱二头肌分开展示；肌头合并为一个可选肌群。',bundles=2,color='#ad6c71')
 add('forearm_flexors','前臂屈肌群','Forearm flexor group',side,[el+[0,-.6,-.45],el*.70+wr*.30+[0,0,-.85],el*.28+wr*.72+[0,0,-.65],wr+[0,.2,-.12]],1.00,.60,'沿真实前臂弯曲走向布置的屈肌群，保留肌腹到腕部肌腱的渐变形态。',color='#b37579')
 add('forearm_extensors','前臂伸肌群','Forearm extensor group',side,[el+[sign*.45,-.6,.45],el*.66+wr*.34+[sign*.55,0,.85],el*.23+wr*.77+[sign*.45,0,.55],wr+[sign*.2,-.6,.15]],.87,.55,'前臂伸肌群的教学表示，与屈肌群分层，可分别隐藏以查看桡尺骨。',color='#c08787')
 # Four principal hindlimb groups; endpoints track the splayed femur and tibia.
 add('quadriceps','股四头肌群','Quadriceps group',side,[hip+[0,-.5,-.15],hip*.65+knee*.35+[0,-1.3,-1.0],hip*.27+knee*.73+[0,-1.1,-.65],knee+[0,-.2,-.2]],2.05,1.15,'大腿前侧伸膝肌群的教学重建，用多个细长肌腹表达肌头与肌束，并与原股骨保持同一姿态。',bundles=3,color='#b67378')
 add('biceps_femoris','股二头肌群','Biceps femoris group',side,[hip+[0,1.2,.5],hip*.60+knee*.40+[0,1.8,.65],hip*.20+knee*.80+[0,1.35,.35],knee+[0,.7,.15]],2.18,1.10,'大腿后外侧肌群的教学表示，可与股四头肌群分别观察；附着位置仅用于结构关系学习。',bundles=2,color='#a96c73')
 add('gastrocnemius','腓肠肌群','Gastrocnemius group',side,[knee+[0,.4,.7],knee*.76+ankle*.24+[sign*.70,.3,1.3],knee*.40+ankle*.60+[sign*.75,0,.85],ankle+[0,-.2,.3]],1.75,1.15,'小腿后侧肌腹逐渐收束为远端肌腱，按源标本的弯膝姿态补建；双头合并为一个教学肌群。',bundles=2,color='#ae6e76')
 add('tibialis_anterior','胫骨前肌','Tibialis anterior',side,[knee+[-sign*.35,.75,-.15],knee*.70+ankle*.30+[-sign*.8,.05,-.45],knee*.23+ankle*.77+[-sign*.4,0,-.4],ankle+[0,.1,-.1]],1.04,.63,'沿胫骨前侧的细长肌腹与肌腱，表现其与后侧腓肠肌的相对层次。',color='#bd8182')
 # Trunk and cervical groups deliberately leave the central viscera window.
 medial=17.5+sign*1.6
 add('pectoralis','胸肌群','Pectoral muscle group',side,[[medial,43.0,4.6],[17.5+sign*3.7,39.0,4.7],sh+[sign*.45,3.0,-1.9],sh+[sign*.15,.7,-.45]],2.40,.67,'胸前侧的扇形教学肌群，两侧分开显示，保留中线窗口以观察心肺及其他内部结构。',color='#b87a7a')
 x=17.5+sign*7.0
 add('external_oblique','腹外斜肌','External oblique muscle',side,[[x,47.5,7.0],[x-sign*.5,54.0,5.7],[x-sign*.75,64.0,5.4],[17.5+sign*4.6,73.0,6.5]],2.7,.74,'腹壁外侧的扁平斜行肌片，默认隐藏以保留内脏视野；开启后可查看腹壁层次。',hidden=True,color='#bf8586')
 x=17.5+sign*1.6
 add('rectus_abdominis','腹直肌','Rectus abdominis',side,[[x,45.0,3.5],[x-sign*.2,53.0,3.0],[x-sign*.05,64.0,3.7],[x+sign*.25,74.0,5.2]],1.15,.56,'腹侧中线两旁的纵行肌带，用连续曲面表现分段腱划；默认隐藏以便观察内脏。',hidden=True,bands=True,color='#c18a88')
 x=17.6+sign*2.05
 add('erector_spinae','竖脊肌群','Erector spinae group',side,[[x,31.0,14.9],[x-sign*.15,42.0,17.0],[x-sign*.25,58.5,18.0],[x-sign*.1,69.8,13.1]],1.17,.93,'沿原脊柱两旁布置的背部纵肌群，表现躯干背侧连续肌柱及其与脊柱的关系。',color='#b57a7d')
 add('sternomastoid','胸骨乳突肌','Sternomastoid muscle',side,[[17.9+sign*4.5,24.5,10.0],[17.9+sign*3.3,27.3,8.2],[17.9+sign*2.0,31.0,5.7],[17.9+sign*1.0,34.0,4.3]],.95,.63,'颈前侧从颅底附近向胸骨方向延伸的教学肌束，用于观察颈部纵行肌群关系。',color='#b77b7d')

def normals(v,f):
 q=v[f];fn=np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]);out=np.zeros_like(v)
 for i in range(3):np.add.at(out,f[:,i],fn)
 out/=np.maximum(np.linalg.norm(out,axis=1)[:,None],1e-14)
 return np.round(out,5).astype('<f4')

doc={'asset':{'version':'2.0','generator':'Self-authored mouse teaching muscle lofts; generate_muscles.py','copyright':'Original teaching surfaces; aligned to attributed Digimouse skeleton coordinates.'},'scene':0,'scenes':[{'nodes':[]}],
 'nodes':[],'meshes':[],'materials':[],'buffers':[],'bufferViews':[],'accessors':[]}
binary=bytearray()
def accessor(a,kind,component,target,normalized=False):
 while len(binary)%4:binary.extend(b'\x00')
 offset=len(binary);raw=a.tobytes();binary.extend(raw);bi=len(doc['bufferViews']);doc['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':len(raw),'target':target})
 acc={'bufferView':bi,'byteOffset':0,'componentType':component,'count':len(a),'type':kind}
 if normalized:acc['normalized']=True
 if kind=='VEC3':acc.update(min=a.min(axis=0).tolist(),max=a.max(axis=0).tolist())
 elif kind=='SCALAR':acc.update(min=[int(a.min())],max=[int(a.max())])
 ix=len(doc['accessors']);doc['accessors'].append(acc);return ix
validation=[]
for m,v,f,c in parts:
 n=normals(v,f);assert np.isfinite(v).all() and np.isfinite(n).all() and f.max()<len(v)
 xyz=v[f];area=np.linalg.norm(np.cross(xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0]),axis=1);assert area.min()>1e-10
 assert v[:,0].min()>0 and v[:,0].max()<37 and v[:,1].min()>12 and v[:,1].max()<94 and v[:,2].min()>-1 and v[:,2].max()<22, (m['id'],v.min(axis=0),v.max(axis=0))
 pos=accessor(v,'VEC3',5126,34962);norm=accessor(n,'VEC3',5126,34962);col=accessor(c,'VEC4',5121,34962,True);idx=accessor(f.ravel(),'SCALAR',5125,34963)
 material=len(doc['materials']);doc['materials'].append({'name':m['id'],'pbrMetallicRoughness':{'baseColorFactor':[1,1,1,1],'metallicFactor':.02,'roughnessFactor':.63},'doubleSided':False})
 node=len(doc['nodes']);doc['scenes'][0]['nodes'].append(node);doc['nodes'].append({'name':m['id'],'mesh':len(doc['meshes'])})
 doc['meshes'].append({'name':m['id'],'primitives':[{'attributes':{'POSITION':pos,'NORMAL':norm,'COLOR_0':col},'indices':idx,'material':material}],
 'extras':{'origin':'teaching','scanDerived':False,'group':m['sourceName'],'coordinates':'Original Digimouse raw mm frame'}})
 validation.append({'id':m['id'],'vertices':len(v),'triangles':len(f),'minimumDoubleArea':float(area.min()),'finite':True,'validIndices':True})
doc['buffers']=[{'byteLength':len(binary)}];j=json.dumps(doc,separators=(',',':')).encode();j+=b' '*((-len(j))%4);binary.extend(b'\x00'*((-len(binary))%4))
path=OUT/'core.glb';path.write_bytes(struct.pack('<4sII',b'glTF',2,28+len(j)+len(binary))+struct.pack('<I4s',len(j),b'JSON')+j+struct.pack('<I4s',len(binary),b'BIN\x00')+binary)
with (OUT/'core.glb.gz').open('wb') as dst:
 with gzip.GzipFile(filename='',mode='wb',fileobj=dst,mtime=0,compresslevel=9) as packed:packed.write(path.read_bytes())
sha=hashlib.sha256(path.read_bytes()).hexdigest()
with gzip.open(OUT/'core.glb.gz','rb') as src:assert hashlib.file_digest(src,'sha256').hexdigest()==sha
(OUT/'metadata.json').write_text(json.dumps([m for m,v,f,c in parts],ensure_ascii=False,indent=2),encoding='utf-8')
np.savez_compressed(OUT/'preview-meshes.npz',**{m['id']+'_v':v for m,v,f,c in parts},**{m['id']+'_f':f for m,v,f,c in parts},**{m['id']+'_c':c for m,v,f,c in parts})
provenance={'title':'Mouse teaching muscle extension','origin':'teaching','license':'CC BY-SA 4.0','licenseUrl':'https://creativecommons.org/licenses/by-sa/4.0/','scanDerived':False,'generator':'generate_muscles.py','sourceLandmarks':'landmarks.json',
 'alignmentSource':{'title':'Digimouse 0.1 mm atlas skeleton','url':'https://neuroimage.usc.edu/neuro/Digimouse_Download','authors':'B. Dogdas, D. Stout, A. Chatziioannou, R. M. Leahy','license':'CC BY-SA 4.0'},
 'anatomicalReferences':[{'title':'A Whole-Body Musculoskeletal Model of the Mouse','url':'https://pmc.ncbi.nlm.nih.gov/articles/PMC8865483/'},{'title':'Musculoskeletal Geometry, Muscle Architecture and Functional Specialisations of the Mouse Hindlimb','url':'https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0147669'},{'title':'MGI skeletal muscle anatomical terminology','url':'https://www.informatics.jax.org/vocab/gxd/anatomy/EMAPA%3A35988'}],
 'method':'Authored curved lofts with tapering tendon ends, asymmetric bellies, mild fascicle surface relief and linear-space vertex colors. Source skeleton landmarks determine pose; surfaces are not extracted from specimen muscle scans.',
 'scope':'26 named teaching muscle groups, paired A/B; not a complete measured muscle atlas. Some multiheaded muscles remain grouped. A/B do not assert anatomical laterality.',
 'coordinates':'Original raw millimetres, head toward smaller y, ventral observer toward smaller z; viewer applies shared X-axis pi rotation.',
 'parts':len(parts),'triangles':sum(len(f) for m,v,f,c in parts),'bytes':path.stat().st_size,'gzipBytes':(OUT/'core.glb.gz').stat().st_size,'decompressedSHA256':sha,'vertexColorNote':'COLOR_0 is linear RGB normalized uint8; use vertexColors=true with white base material.',
 'defaultHidden':[m['id'] for m,v,f,c in parts if m['defaultHidden']]}
(OUT/'provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'validation.json').write_text(json.dumps(validation,indent=2),encoding='utf-8')
print(json.dumps(provenance,ensure_ascii=True),flush=True)
