"""Original mouse teaching geometry. This is NOT recovered specimen anatomy.
Raw millimetre coordinates are retained; source organ surfaces only anchor endpoints.
Run with NumPy and Pillow. No source mesh is edited, smoothed, or redistributed here.
"""
from pathlib import Path
import gzip, json, struct, hashlib, math, argparse
import numpy as np
from glb_writer import export_glb

SCRIPT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,default=SCRIPT)
parser.add_argument('--metadata',type=Path,default=SCRIPT.parents[1]/'animal-atlas/public/models/digimouse-voxel/metadata.json')
parser.add_argument('--source-core',type=Path,default=None)
parser.add_argument('--skip-preview',action='store_true',help='Skip the optional Pillow offline review image')
args=parser.parse_args()
BASE=args.output;BASE.mkdir(parents=True,exist_ok=True)
SOURCE=args.metadata.parent
SOURCE_CORE=args.source_core or SOURCE/'core.glb.gz'
SOURCES=[
 {'title':'Margaret J. Cook, The Anatomy of the Laboratory Mouse: abdominal viscera in situ', 'url':'https://informatics.jax.org/cookbook/figures/figure54.shtml'},
 {'title':'Cook: alimentary canal', 'url':'https://www.informatics.jax.org/cookbook/figures/figure57.shtml'},
 {'title':'Cook: trachea and lungs', 'url':'https://informatics.jax.org/cookbook/figures/figure53.shtml'},
 {'title':'Cook: male urogenital system', 'url':'https://informatics.jax.org/cookbook/figures/figure62.shtml'},
 {'title':'Cook: bladder and prostate', 'url':'https://informatics.jax.org/cookbook/figures/figure67.shtml'},
 {'title':'INHAND rodent gastrointestinal nomenclature and morphology', 'url':'https://pmc.ncbi.nlm.nih.gov/articles/PMC4765498/'},
]

def read_source():
    raw=gzip.decompress(SOURCE_CORE.read_bytes())
    jl=struct.unpack_from('<I',raw,12)[0]; doc=json.loads(raw[20:20+jl]); binary=raw[28+jl:]
    def array(ai):
        a=doc['accessors'][ai];v=doc['bufferViews'][a['bufferView']]
        dtype={5126:'<f4',5125:'<u4',5123:'<u2'}[a['componentType']]
        width={'VEC3':3,'SCALAR':1}[a['type']]
        return np.frombuffer(binary,dtype=dtype,count=a['count']*width,offset=v.get('byteOffset',0)+a.get('byteOffset',0)).reshape(-1,width)
    out={}
    for mesh in doc['meshes']:
        p=mesh['primitives'][0]
        out[mesh['name']]=(array(p['attributes']['POSITION']).copy(),array(p['indices']).reshape(-1,3).copy())
    return out

SOURCE_MESH=read_source()
anchors={}
def anchor(name,proposal):
    p=SOURCE_MESH[name][0]; idx=np.argmin(np.sum((p-np.array(proposal))**2,axis=1))
    point=p[idx].astype(float)
    anchors[name+':'+','.join(map(str,proposal))]=point.tolist()
    return point.tolist()

def spline(control,samples_per_span=24):
    """Centripetal interpolation is approximated using dense chord-length resampling.
    Catmull-Rom interpolates authored landmarks without straight polygonal elbows.
    """
    p=np.asarray(control,dtype=float)
    ex=np.vstack([2*p[0]-p[1],p,2*p[-1]-p[-2]])
    pieces=[]
    for i in range(len(p)-1):
        a,b,c,d=ex[i:i+4]; t=np.linspace(0,1,samples_per_span,endpoint=False)[:,None]
        pieces.append(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
    dense=np.vstack(pieces+[p[-1:]])
    lengths=np.r_[0,np.cumsum(np.linalg.norm(np.diff(dense,axis=0),axis=1))]
    count=max(32,int(lengths[-1]/.10)+1)
    uniform=np.linspace(0,lengths[-1],count)
    return np.stack([np.interp(uniform,lengths,dense[:,j]) for j in range(3)],axis=1)

def sweep(control,radius=.65,sides=32,rings=False,bag=False):
    p=spline(control); n=len(p); t=np.linspace(0,1,n)
    tangent=np.gradient(p,axis=0); tangent/=np.linalg.norm(tangent,axis=1)[:,None]
    # Parallel transport frame: prevents twisting at the inflection points of coils.
    normal=np.empty_like(p); normal[0]=np.cross(tangent[0],[0,0,1])
    if np.linalg.norm(normal[0])<.01:normal[0]=np.cross(tangent[0],[0,1,0])
    normal[0]/=np.linalg.norm(normal[0])
    for i in range(1,n):
        norm=normal[i-1]-np.dot(normal[i-1],tangent[i])*tangent[i]
        normal[i]=norm/np.linalg.norm(norm)
    binormal=np.cross(tangent,normal)
    theta=np.arange(sides)*2*np.pi/sides
    if np.isscalar(radius): radii=np.ones(n)*radius
    else:radii=np.interp(t,np.linspace(0,1,len(radius)),radius)
    # Very small, smooth calibre variation; no balls, haustra, or artificial villi.
    radii*=1+.018*np.sin(t*8*np.pi)+.009*np.sin(t*19*np.pi)
    r=np.repeat(radii[:,None],sides,axis=1)
    if rings:
        phase=np.arange(n)*np.linalg.norm(np.diff(p,axis=0),axis=1).mean()/.72
        raised=np.maximum(0,np.cos(phase*2*np.pi))**5
        cshape=np.clip((np.cos(theta)+.8)*1.3,0,1)
        r+=.075*raised[:,None]*cshape[None,:]
    # The caecal bag is a broad curved blind sac, elliptical instead of a sphere chain.
    aspect=.75 if bag else 1
    points=p[:,None,:]+r[:,:,None]*(np.cos(theta)[None,:,None]*normal[:,None,:]+aspect*np.sin(theta)[None,:,None]*binormal[:,None,:])
    points=points.reshape(-1,3)
    faces=[]
    for i in range(n-1):
        for j in range(sides):
            a=i*sides+j;b=i*sides+(j+1)%sides;c=(i+1)*sides+j;d=(i+1)*sides+(j+1)%sides
            faces.extend([(a,b,c),(b,d,c)])
    points=np.vstack([points,p[0],p[-1]])
    for j in range(sides):
        faces.extend([(n*sides,(j+1)%sides,j),(n*sides+1,(n-1)*sides+j,(n-1)*sides+(j+1)%sides)])
    faces=np.asarray(faces,dtype='<u4');points=points.astype('<f4')
    # Ensure closed outward winding for glTF single-sided materials.
    tri=points[faces];volume=np.einsum('ij,ij->i',tri[:,0],np.cross(tri[:,1],tri[:,2])).sum()/6
    if volume<0:faces=faces[:,[0,2,1]]
    return points,faces,float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum())

meshes=[];metadata=[]
def add(id,name,en,category,control,radius,color,desc,**kwargs):
    pts,faces,length=sweep(control,radius,**kwargs)
    bounds=[pts.min(axis=0).tolist(),pts.max(axis=0).tolist()]
    item={'id':id,'name':name,'en':en,'color':color,'sourceName':'Original mouse teaching model: '+en,
      'description':desc+' 自制教学补充，按小鼠解剖资料和现有器官位置建模；不是该标本的扫描分割，走行与尺寸为教学近似。',
      'category':category,'origin':'teaching','bounds':bounds,'center':((pts.min(axis=0)+pts.max(axis=0))/2).tolist(),
      'vertices':len(pts),'triangles':len(faces),'centerlineLengthMM':length,'sources':SOURCES,
      'units':'mm','defaultHidden':False}
    metadata.append(item); meshes.append((id,pts,faces,color,{'origin':'teaching','category':category,'notSpecimenSegmentation':True}))

# Source surface endpoints anchor the new conduits; source shapes remain untouched.
cardia=anchor('region_15',[20.2,49.8,12.5]);pylorus=anchor('region_15',[18.5,54.6,9.2])
add('teaching_digestive_esophagus','食管','Esophagus','digestive',
 [[18.8,22.5,8.6],[18.7,27,10.6],[18.5,34,12.8],[18.0,40,14.5],[18.7,46,14.8],cardia],
 [.48,.49,.53,.56,.61], '#bc7a80','连接咽部与胃贲门；在气管背侧穿行胸部。')

duo=[pylorus,[17.5,56.2,8.2],[14.3,57.1,7.3],[12.5,59.0,7.2],[13.7,60.1,7.9],[16.2,58.9,8.4],[17.1,57.8,8.1]]
add('teaching_digestive_duodenum','十二指肠','Duodenum','digestive',duo,[.62,.65,.69,.70,.67], '#c98c83','小肠起始段，从胃幽门延续为弯曲肠段，与胰腺区域相邻。')

# A continuous path folds irregularly through three depth layers.  Each U-turn
# has a different orientation/extent; the bundle is neither a planar grid nor
# a repeated spring. These authored loops are illustrative, not measured bowel.
jej=[duo[-1],[20.0,57.6,6.3],[23.2,58.7,4.8],[24.3,61.2,4.7],
 [22.7,62.6,4.6],[21.5,60.4,4.5],[19.7,59.3,4.6],[18.7,60.8,4.8],
 [20.0,63.5,4.9],[20.0,65.3,4.9],[18.4,65.7,4.6],[17.7,63.3,4.4],
 [16.6,60.9,4.6],[15.0,60.6,4.8],[14.0,62.2,4.8],[15.7,64.2,4.7],
 [16.7,66.6,5.0],[15.1,67.6,5.2],[13.7,66.1,5.2],[12.2,63.6,4.8],
 [10.6,62.5,4.9],[9.7,64.0,5.1],[10.7,66.6,5.4],[12.5,68.0,6.7],
 # Middle depth: oblique return curls travel across the previous layer.
 [14.1,67.7,7.4],[15.1,66.3,7.6],[13.0,65.3,7.8],[10.7,64.5,7.8],
 [10.2,62.2,7.7],[12.2,61.6,7.8],[14.8,63.3,7.5],[17.0,63.8,7.3],
 [18.2,62.4,7.5],[16.5,60.3,7.8],[13.9,58.9,7.8],[14.3,57.6,7.7],
 [17.5,58.0,7.3],[20.4,59.3,7.2],[21.8,61.1,7.2],[20.3,63.0,7.4],
 [20.8,65.5,7.3],[22.7,66.3,7.2],[24.4,64.8,7.3],[23.5,62.9,7.3],
 [23.9,60.2,8.3],[22.1,58.8,9.8]]
add('teaching_digestive_jejunum','空肠','Jejunum','digestive',jej,[.54,.56,.52,.55,.51,.53,.55],'#d5a091','小肠中段，形成腹腔内多层、方向不同的盘曲肠袢；教学模型保留连续管状走行。')

ile=[jej[-1],[20.2,58.3,10.1],[18.7,59.7,10.4],[19.3,61.7,10.5],
 [21.5,62.8,10.3],[21.9,64.4,10.2],[20.0,65.3,10.5],[18.8,63.8,10.7],
 [16.7,62.2,10.8],[14.7,62.6,10.7],[14.4,64.5,10.4],[16.2,66.1,10.3],
 [15.5,67.7,10.3],[13.4,67.6,10.5],[11.7,65.7,10.5],[11.3,63.5,10.4],
 [12.4,60.8,10.3],[14.1,59.9,10.1],[16.0,60.7,10.2],[17.3,59.5,10.2],
 [18.3,57.5,10.2],[20.0,57.1,10.0],[22.4,58.0,10.1],[24.0,60.2,10.0],
 [24.7,62.7,9.4],[23.2,65.0,8.8]]
add('teaching_digestive_ileum','回肠','Ileum','digestive',ile,[.52,.51,.53,.49,.51],'#c99484','小肠末段，进一步盘曲后连接盲肠基部邻近的回盲区域。空肠与回肠之间用教学分段区分，不表示肉眼可见切线。')

cecum=[ile[-1],[25.1,65.9,8.4],[27.1,68.0,8.0],[26.8,70.1,8.1],[24.5,70.0,8.9],[23.5,68.6,9.8]]
add('teaching_digestive_cecum','盲肠','Cecum','digestive',cecum,[.70,1.75,2.45,2.25,1.55,.10],'#b79b86',
 '小鼠具有相对发达的弯曲盲端囊袋，是肠道发酵的重要部位。回肠与结肠在基部邻近处衔接；未添加人体样阑尾。',sides=48,bag=True)

colon=[[23.4,65.0,8.6],[22.5,63.0,10.5],[20.3,60.7,10.4],[18.2,61.0,10.7],
 [17.5,64.0,11.1],[17.6,67.8,11.5],[17.5,71.0,11.6]]
add('teaching_digestive_colon','结肠','Colon','digestive',colon,[.86,.86,.82,.80,.74],'#ba8e84',
 '由盲肠基部延续并转向骨盆，鼠结肠外表较光滑，未建成人体式结肠袋或结肠带。')
add('teaching_digestive_rectum','终末结肠 / 直肠','Terminal colon / rectal segment','digestive',
 [colon[-1],[17.5,73.5,11.2],[17.4,76.0,10.2],[17.2,78.0,9.0]], [.73,.68,.59,.49],'#ac7f7a',
 '大肠末端通向肛管的教学分段；小鼠该区域与人的直肠、乙状结肠分区并不等同。')

trachea=[[18.8,23.3,6.8],[18.8,26.7,7.4],[18.5,30.5,8.9],[18.2,34.0,10.1],[18.1,36.8,11.1]]
add('teaching_airway_trachea','气管','Trachea','respiratory',trachea,[.56,.52,.49,.46],'#b9b5a2',
 '气道由颈部进入胸腔后分为两侧主支气管；表面以细浅的非完整环状起伏提示软骨环。',rings=True)
add('teaching_airway_bronchus_a','主支气管 A','Main bronchus A','respiratory',
 [trachea[-1],[16.6,38.3,11.6],[14.7,40.1,12.1],[14.0,42.5,12.0]], [.44,.39,.31,.24],'#bbb1a3',
 '气管分叉后进入原肺组织较小 X 坐标一侧的主支气管。A/B 是源坐标标记，不代表已核实的解剖左右。')
add('teaching_airway_bronchus_b','主支气管 B','Main bronchus B','respiratory',
 [trachea[-1],[19.7,38.1,11.5],[21.3,39.7,12.0],[21.8,42.0,12.0]], [.44,.38,.31,.24],'#c1b5a6',
 '气管分叉后进入原肺组织较大 X 坐标一侧的主支气管。A/B 是源坐标标记，不代表已核实的解剖左右。')

ka=anchor('region_19_a',[14.4,61.0,13.4]);kb=anchor('region_19_b',[19.0,62.3,13.4])
ba=anchor('region_13',[14.9,68.8,9.3]);bb=anchor('region_13',[18.3,69.4,9.0])
add('teaching_ureter_a','输尿管 A','Ureter A','urinary',
 [ka,[14.8,62.8,13.6],[14.3,65.2,12.7],[14.8,67.3,11.2],ba], [.24,.24,.23,.21], '#d7b494',
 '将肾脏 A 邻近肾门的区域连接到膀胱后方；教学走行保留轻微自然弯曲。')
add('teaching_ureter_b','输尿管 B','Ureter B','urinary',
 [kb,[19.4,64.3,13.9],[19.8,66.5,12.8],[19.2,68.3,10.9],bb], [.24,.24,.23,.21], '#d3ac90',
 '将肾脏 B 邻近肾门的区域连接到膀胱后方；A/B 沿用原模型的成对器官命名。')

def render_review():
    from PIL import Image,ImageDraw,ImageFont
    image=Image.new('RGB',(1500,1100),'#edf0f1');draw=ImageDraw.Draw(image)
    meta={x['id']:x for x in json.loads(args.metadata.read_text(encoding='utf-8-sig'))}
    # Orthographic ventral review of the actual source and the authored supplement.
    for panel,azimuth in enumerate((0,0.60)):
        light=np.array([-.25,-.35,-.90]); light/=np.linalg.norm(light)
        faces_to_draw=[]
        to_draw=[]
        for key in ['region_15','region_18','region_13','region_19_a','region_19_b','region_9','region_21']:
            p,f=SOURCE_MESH[key];to_draw.append((p,f,meta[key]['color'],5))
        to_draw += [(p,f,c,1) for _,p,f,c,_ in meshes]
        c=math.cos(azimuth);s=math.sin(azimuth)
        for points,faces,color,step in to_draw:
            xyz=points[faces[::step]]
            rotated=xyz.copy();rotated[:,:,0]=(xyz[:,:,0]-18)*c+(xyz[:,:,2]-10)*s+18
            rotated[:,:,2]=-(xyz[:,:,0]-18)*s+(xyz[:,:,2]-10)*c+10
            ns=np.cross(rotated[:,1]-rotated[:,0],rotated[:,2]-rotated[:,0]);ln=np.linalg.norm(ns,axis=1);ns/=np.maximum(ln[:,None],1e-10)
            visible=ns[:,2]<0
            rgb=np.array([int(color[k:k+2],16) for k in (1,3,5)])
            brightness=.62+.38*np.maximum(0,ns@light)
            projected=np.stack([rotated[:,:,0]*20+panel*750-15,rotated[:,:,1]*12.0+40],axis=2)
            for i in np.flatnonzero(visible):
                faces_to_draw.append((float(rotated[i,:,2].mean()),projected[i],tuple(np.minimum(255,rgb*brightness[i]).astype(int))))
        for _,xy,color in sorted(faces_to_draw,key=lambda a:-a[0]):draw.polygon([tuple(x) for x in xy],fill=color)
        draw.text((30+panel*750,15),'TEACHING EXTENSION + SOURCE ORGAN ANCHORS | '+('ventral' if panel==0 else 'oblique'),fill='#34454a')
    image.save(BASE/'review.png')

if __name__=='__main__':
    export_glb(meshes,BASE/'core.glb')
    with gzip.GzipFile(filename=str(BASE/'core.glb.gz'),mode='wb',mtime=0,compresslevel=9) as f:f.write((BASE/'core.glb').read_bytes())
    (BASE/'metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf8')
    provenance={'title':'Mouse digestive and conduit teaching extension','origin':'teaching','species':'Mus musculus',
      'authorship':'Original procedural teaching geometry authored for Animal Atlas; no external mesh copied',
      'license':'CC-BY-SA-4.0','licenseUrl':'https://creativecommons.org/licenses/by-sa/4.0/',
      'licenseScope':'New authored geometry and scripts; source Digimouse remains under its original CC BY-SA license. Anatomy reference figures were consulted for factual morphology only; no reference images or external meshes are reproduced.',
      'sourceAtlas':'https://neuroimage.usc.edu/neuro/Digimouse','sourceCoreSHA256':hashlib.sha256(SOURCE_CORE.read_bytes()).hexdigest(),
      'sources':SOURCES,'coordinateSystem':'Source raw millimetres; head toward decreasing Y, ventral toward decreasing Z. No verified left/right labeling.',
      'anchors':anchors,'limitations':['Teaching approximation, not CT-derived segmentation or verified registration.','Loop number, lumen calibre, total bowel length and segment boundaries are illustrative, not specimen measurements.','No intestinal villi, haustra, taenia coli, appendix or separate histological layers are modeled.','Source organ meshes are read for anchoring and remain unchanged.','Caecum and ileum/colon meet by small overlapping closed surfaces; lumen flow continuity is conceptual, not surgical/manufacturing grade.'],
      'parts':len(metadata),'triangles':sum(x['triangles'] for x in metadata),'compressedBytes':(BASE/'core.glb.gz').stat().st_size}
    (BASE/'provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2),encoding='utf8')
    if not args.skip_preview: render_review()
    print(json.dumps({'parts':len(metadata),'triangles':provenance['triangles'],'gzipBytes':provenance['compressedBytes'],'anchors':anchors},indent=2))
