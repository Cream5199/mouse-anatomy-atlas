"""Original mouse major-vessel teaching trees anchored to Digimouse raw mm space.

Curve paths are authored, NOT vascular segmentation or measured vessel locations.
Source surfaces are read only for landmarks; no source triangles are copied here.
Run with Python and NumPy. No network, external mesh tools, or SciPy are needed.
"""
from pathlib import Path
import sys, json, gzip, hashlib, struct, argparse
import numpy as np
BASE=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,default=BASE)
ARGS=parser.parse_args()
OUTPUT=ARGS.output.resolve();OUTPUT.mkdir(parents=True,exist_ok=True)
from glb_writer import export_glb

STEP=.075
SIDES=20
TREES=[]
ALL_PATHS={}

def smooth_curve(d,p,q):
 # Cubic Hermite interpolation in chord-length space, implemented in NumPy.
 slopes=np.empty_like(p);slopes[0]=(p[1]-p[0])/(d[1]-d[0]);slopes[-1]=(p[-1]-p[-2])/(d[-1]-d[-2])
 if len(p)>2:slopes[1:-1]=(p[2:]-p[:-2])/(d[2:]-d[:-2])[:,None]
 ii=np.minimum(np.searchsorted(d,q,side='right')-1,len(d)-2);ii=np.maximum(ii,0)
 h=d[ii+1]-d[ii];u=(q-d[ii])/h;u=u[:,None];hh=h[:,None]
 a=p[ii];b=p[ii+1];ma=slopes[ii];mb=slopes[ii+1]
 c=(2*u**3-3*u**2+1)*a+(u**3-2*u**2+u)*hh*ma+(-2*u**3+3*u**2)*b+(u**3-u**2)*hh*mb
 t=(6*u**2-6*u)*a/hh+(3*u**2-4*u+1)*ma+(-6*u**2+6*u)*b/hh+(3*u**2-2*u)*mb
 return c,t

class Tree:
 def __init__(self,key,name,en,kind,description):
  self.id='teaching_'+('artery_' if kind=='arterial' else 'vein_')+key
  self.name=name+'（教学）';self.en=en;self.kind=kind;self.description=description
  self.paths=[];self.vertices=[];self.faces=[]
 def path(self,points,radii,label='regional branch'):
  points=np.array(points,float);radii=np.broadcast_to(radii,(len(points),)).astype(float)
  d=np.r_[0,np.cumsum(np.linalg.norm(np.diff(points,axis=0),axis=1))]
  assert np.all(np.diff(d)>0) and np.min(radii)>=.05
  n=max(6,int(np.ceil(d[-1]/STEP))+1);q=np.linspace(0,d[-1],n)
  c,t=smooth_curve(d,points,q);t/=np.linalg.norm(t,axis=1)[:,None]
  r=np.interp(q,d,radii)
  # Parallel-transport-like frame: reproject prior normal perpendicular to tangent.
  normal=[];prev=np.cross(t[0],[0,0,1])
  if np.linalg.norm(prev)<.1:prev=np.cross(t[0],[0,1,0])
  prev/=np.linalg.norm(prev)
  for tangent in t:
   nv=prev-tangent*np.dot(prev,tangent)
   if np.linalg.norm(nv)<.1:nv=np.cross(tangent,[1,0,0])
   nv/=np.linalg.norm(nv);normal.append(nv);prev=nv
  normal=np.array(normal);binormal=np.cross(t,normal)
  th=np.arange(SIDES)*2*np.pi/SIDES
  rings=c[:,None,:]+r[:,None,None]*(np.cos(th)[None,:,None]*normal[:,None,:]+np.sin(th)[None,:,None]*binormal[:,None,:])
  verts=rings.reshape(-1,3);faces=[]
  for i in range(n-1):
   for j in range(SIDES):
    a=i*SIDES+j;b=i*SIDES+(j+1)%SIDES;cc=(i+1)*SIDES+j;dd=(i+1)*SIDES+(j+1)%SIDES
    faces.extend([(a,b,cc),(b,dd,cc)])
  # Closed caps lie within parent vessel at branches. Connected curves overlap
  # intentionally at junctions; each anatomical region is one glTF mesh.
  verts=np.vstack((verts,c[0],c[-1]));i0=n*SIDES;i1=i0+1
  for j in range(SIDES):
   faces.append((i0,(j+1)%SIDES,j));faces.append((i1,(n-1)*SIDES+j,(n-1)*SIDES+(j+1)%SIDES))
  faces=np.array(faces,dtype=np.uint32)
  # Establish outward winding independent of curve/frame orientation.
  xyz=verts[faces];vol=np.einsum('ij,ij->i',xyz[:,0],np.cross(xyz[:,1],xyz[:,2])).sum()/6
  if vol<0:faces=faces[:,[0,2,1]]
  offset=sum(len(x) for x in self.vertices);self.vertices.append(verts.astype('<f4'));self.faces.append(faces+offset)
  self.paths.append({'label':label,'points':points.tolist(),'radii':radii.tolist(),'lengthMm':round(float(d[-1]),3)})
  return self
 def finish(self):
  v=np.vstack(self.vertices).astype('<f4');f=np.vstack(self.faces).astype('<u4')
  color='#B86361' if self.kind=='arterial' else '#668AA4'
  meta={'id':self.id,'name':self.name,'en':self.en,'color':color,'sourceName':self.en,
   'description':self.description+' 依据原图谱器官和骨骼定位自主补绘，主干连接参照小鼠解剖；曲线、管径和末端分布为教学示意，非原标本血管分割。A/B仅标示模型两侧。',
   'category':self.kind,'origin':'teaching','bounds':[v.min(0).tolist(),v.max(0).tolist()],
   'center':v.mean(0).tolist(),'centroid':v.mean(0).tolist(),'vertices':len(v),'triangles':len(f),
   'originalAtlasLabel':False,'paths':len(self.paths),'defaultHidden':False,'license':'CC-BY-SA-4.0'}
  TREES.append((meta,v,f));ALL_PATHS[self.id]=self.paths
  return self

# Named shared centerline junctions. A=lower raw X, B=higher raw X.
# The common murine arch topology is represented without claiming specimen L/R.
HEART_AO=(19.2,38.6,8.7);ARCH_A=(18.5,34.5,10.5);ARCH_B=(20.0,34.2,11.7);ARCH_SUB=(20.5,35.5,13.0)
BCT=(16.7,31.5,9.0);AO_CEL=(18.9,49.5,14.1);AO_MES=(18.65,53,14.3);AO_RA=(18.3,57.8,14.6);AO_RB=(18.2,59.6,14.8);AO_END=(18.0,71.5,14.2)
CAVA_TOP=(16.6,39.0,9.0);CAVA_RA=(16.2,59,13.0);CAVA_RB=(16.25,60.5,13.1);CAVA_END=(17.1,72,13.0)
CRAN_A=(15.7,32,8.2);CRAN_B=(22.1,31,8.8)

a=Tree('aorta','主动脉弓与降主动脉','Aortic arch and descending aorta','arterial','由心基部上行，经主动脉弓转入胸腹部降主动脉，至骨盆分叉；保留少量胸壁和腰部支。')
a.path([HEART_AO,(18.3,36,8.8),ARCH_A,ARCH_B,ARCH_SUB,(20,39,13.6),(19.2,44,14),AO_CEL,AO_MES,AO_RA,AO_RB,(18,66,14.7),AO_END],[.43,.42,.41,.40,.38,.37,.36,.35,.33,.31,.30,.28,.25],'aortic main course')
for y in [40,43,46]:
 root=(19.7-(y-40)*.09,y,13.8)
 for s in [-1,1]:a.path([root,(root[0]+s*2,y+.3,14.1),(root[0]+s*4.2,y+.9,13.4)],[.12,.095,.06],'selected intercostal regional branch')
a.path([(18.15,64,14.8),(20,64.5,15),(21.2,65.5,14.6)],[.12,.09,.06],'selected lumbar branch').finish()

a=Tree('head_neck','头颈动脉树','Head and neck arterial tree','arterial','示意头臂干及两侧颈部供血；一侧颈总动脉与前肢支共用头臂干，另一侧颈支直接起自主动脉弓。')
a.path([ARCH_A,(17.5,32.5,9.5),BCT],[.27,.25,.24],'brachiocephalic trunk')
for side,pts in [('A',[BCT,(16.7,28,9),(16.3,24,8.2),(15.8,21,7.2)]),('B',[ARCH_B,(21.4,31,10),(21.8,27,9),(22.2,23,7.8),(22.5,21,6.8)])]:
 a.path(pts,np.linspace(.235,.17,len(pts)),'common carotid '+side);e=np.array(pts[-1]);sign=-1 if side=='A' else 1
 a.path([e,e+[sign*.5,-2,1.1],e+[sign*1.1,-4,2.0],e+[sign*.4,-6,2.8]],[.145,.12,.095,.07],'internal carotid regional continuation '+side)
 a.path([e,e+[sign*1.3,-2,-1],e+[sign*1.7,-5,-1.2],e+[sign*1.0,-8,-.3]],[.14,.11,.08,.055],'external carotid facial continuation '+side)
 a.path([e+[sign*1.3,-2,-1],e+[sign*2.8,-2.5,-.6],e+[sign*3,-4,.3]],[.095,.075,.05],'facial muscular branch '+side)
a.finish()

ARM_A=[BCT,(13.0,31,9.7),(10,31.2,7.6),(7.4,32.8,4.4),(6.0,31.3,3.9),(6.2,27,3.4),(6.5,23,3.35),(6.6,20.3,3.6)]
ARM_B=[ARCH_SUB,(23.0,32.0,10.0),(26.1,30.8,7.7),(29.1,29.5,4.5),(30.0,27,3.8),(30.0,22.5,3.65),(30.0,18.0,3.3)]
for side,pts,sgn in [('a',ARM_A,-1),('b',ARM_B,1)]:
 a=Tree('forelimb_'+side,'前肢'+side.upper()+'动脉树','Forelimb '+side.upper()+' arterial tree','arterial','锁骨下—腋—肱动脉走向沿原骨骼肩、肘、腕延伸，附少量前臂及掌部支。')
 a.path(pts,np.linspace(.23,.09,len(pts)),'subclavian-axillary-brachial regional course')
 a.path([pts[1],(pts[1][0]+sgn*1.4,pts[1][1]+1.3,pts[1][2]+1),(pts[1][0]+sgn*2.8,pts[1][1]+4,pts[1][2]-.4)],[.13,.10,.06],'shoulder regional branch')
 branch=np.array(pts[-3]);end=np.array(pts[-1])
 a.path([branch,branch+[sgn*.9,-1.5,.3],end+[sgn*1,-.4,.1]],[.13,.10,.065],'forearm companion artery')
 for dx in [-.8,0,.8]:a.path([end,end+[dx,-1.0,.1],end+[dx*1.4,-2.1,.25]],[.09,.07,.05],'selected palmar terminal branch')
 a.finish()

RENALS=[('A',AO_RA,(14.6,59,14.2),(11.4,59.5,14.6),-1),('B',AO_RB,(19.7,60.5,14.1),(22.85,60.6,15.0),1)]
a=Tree('renal','肾及肾上腺动脉树','Renal and suprarenal arterial trees','arterial','由腹主动脉至两侧肾门，在肾轮廓内示意少量分支，并附向肾上腺方向的小支。')
for side,root,hilum,c,sgn in RENALS:
 a.path([root,((root[0]+hilum[0])/2,hilum[1]-.4,14.3),hilum,c],[.22,.20,.18,.13],'renal artery '+side)
 c=np.array(c)
 for dy in [-2.5,0,2.7]:
  mid=c+[sgn*.7,dy*.6,-.7];end=c+[sgn*1.7,dy,-1.3]
  a.path([c,mid,end],[.12,.095,.06],'renal intraparenchymal regional branch '+side)
 a.path([hilum,(hilum[0],57,15.1),((14.4 if side=='A' else 19.0),55.1,15.5)],[.10,.08,.055],'suprarenal regional branch '+side)
a.finish()

a=Tree('celiac','腹腔动脉分支','Celiac arterial branches','arterial','腹腔干分向肝、胃和脾的区域，利用原脏器位置约束终端；未描绘完整叶内血管。')
CEL=(18.0,50.4,11.3)
a.path([AO_CEL,(18.6,49.7,12.5),CEL],[.22,.21,.20],'celiac trunk')
for name,points in [('hepatic',[CEL,(16,50,9.8),(13,49,8),(10,48,7.3)]),('gastric',[CEL,(21,51.2,10),(24,51.6,9.1),(26.5,53,9.8)]),('splenic',[CEL,(22,53,12),(25.5,55.3,13),(27.5,57,13.3)])]:
 a.path(points,[.17,.14,.11,.07],name+' regional branch')
 a.path([points[2],np.array(points[2])+[.5,1.3,-1],np.array(points[3])+[-1,1.7,-1.2]],[.10,.08,.055],name+' secondary branch')
a.finish()

a=Tree('mesenteric','肠系膜主要动脉树','Major mesenteric arterial tree','arterial','由腹主动脉向腹腔中下部展开少量递减分支，示意肠系膜供血区域；不代表固定肠袢或真实末端分布。')
MES=(18.5,58.5,9.8)
a.path([AO_MES,(18.5,55,12),MES,(18.1,63,8.5),(18.6,67,8.4)],[.25,.23,.20,.16,.12],'cranial mesenteric main course')
for i,(x,y,z) in enumerate([(12,62,8.3),(24,62.5,8.1),(10.8,66,7.8),(24.5,67.3,7.3),(15,69,7.2),(22,70,8)]):
 root=MES if i<2 else (18.1,63,8.5)
 mid=((root[0]+x)/2,y-1.4,z+.6)
 a.path([root,mid,(x,y,z)],[.14,.105,.075],'intestinal regional branch')
 for off in [-1,1]:a.path([mid,(x+off*.6,y-.2,z+.1),(x+off*1.1,y+1.2,z-.2)],[.095,.075,.05],'selected intestinal terminal branch')
a.path([(18,67.5,14.6),(17,68.5,11.5),(16.3,70,9.2)],[.12,.095,.065],'caudal mesenteric regional branch').finish()

LEG_A=[AO_END,(15,74,12.6),(12.1,76.5,10.3),(8.0,75.8,6.6),(5.3,75.5,3.7),(4.8,79,3.2),(6.8,84.5,3),(8.4,89.4,2.9)]
LEG_B=[AO_END,(21,73.8,13),(24,76,10.0),(28.0,73.8,7.0),(30.1,73.8,5.25),(29.5,79,4.4),(28.2,85,3.8),(27.1,89.5,3.65)]
a=Tree('iliac_hindlimbs','髂与后肢动脉树','Iliac and hindlimb arterial trees','arterial','主动脉分向髂、股、腘及小腿区域，依据两侧真实屈曲后肢走向补绘，附盆壁与足部小支。')
for side,pts,s in [('A',LEG_A,-1),('B',LEG_B,1)]:
 a.path(pts,[.24,.23,.22,.20,.18,.145,.11,.085],'iliac-femoral-popliteal course '+side)
 a.path([pts[1],(18+s*2,77,10),(18+s*2.7,80,9)],[.14,.11,.075],'internal iliac regional branch '+side)
 a.path([pts[2],np.array(pts[3])+[0,1.8,.6],np.array(pts[4])+[s*.1,2,1.2]],[.15,.11,.065],'deep femoral regional branch '+side)
 a.path([pts[4],np.array(pts[5])+[-s*.6,.1,-.25],np.array(pts[6])+[-s*.7,0,-.3],np.array(pts[7])+[-s*.6,0,-.15]],[.12,.10,.08,.055],'saphenous regional branch '+side)
 for dx in [-.7,.2,.9]:a.path([pts[-1],np.array(pts[-1])+[dx,.7,0],np.array(pts[-1])+[dx*1.5,1.5,-.1]],[.085,.065,.05],'pedal regional ending '+side)
a.finish()

a=Tree('pulmonary','肺动脉分支','Pulmonary arterial branches','arterial','由心基部通向两侧肺门及肺内区域的简化分支；红色仅按动脉类别编码，不表示富氧血。')
PR=(18.6,38.3,10.5)
a.path([(18.3,39.2,9),PR],[.31,.28],'pulmonary trunk')
for s in [-1,1]:
 root=(18.6+s*3.1,39,12.3)
 a.path([PR,(18.6+s*1.7,38.6,11.6),root],[.24,.21,.18],'pulmonary artery regional course')
 for yy,xx in [(35.8,1.1),(42.2,1.5),(45,1.0)]:a.path([root,(root[0]+s*.6,(yy+39)/2,12.5),(root[0]+s*xx,yy,12.0)],[.15,.11,.075],'pulmonary regional ending')
a.finish()

# Veins have their own paths and collector topology, not a mirrored arterial net.
v=Tree('cavae','腔静脉主干','Caval trunks','venous','示意尾侧腔静脉及小鼠双侧头端腔静脉至心基部的回流；不按人类单侧上腔静脉外观绘制。')
v.path([CAVA_END,(16.4,68,13.1),CAVA_RB,CAVA_RA,(16,55,12.5),(15.7,50,11.8),(16.1,45,10.4),CAVA_TOP],[.32,.34,.37,.38,.39,.42,.44,.43],'caudal vena cava')
v.path([CRAN_A,(16,34.5,8.4),CAVA_TOP],[.34,.36,.38],'cranial vena cava A')
v.path([CRAN_B,(22,34.5,9.4),(20.8,37,10.6),(18.3,39.3,10.1)],[.31,.33,.32,.30],'cranial vena cava B with heart-side continuation')
v.finish()

v=Tree('head_neck','头颈静脉树','Head and neck venous trees','venous','较表浅的头面和颈部区域回流支汇向两侧头端腔静脉，保持与颈动脉不同的曲线路径。')
for name,root,sign in [('A',CRAN_A,-1),('B',CRAN_B,1)]:
 neck=(root[0]+sign*1.4,25.3,6.4);jaw=(root[0]+sign*1.8,20.4,5.0)
 v.path([root,(root[0]+sign*.7,28,7.1),neck,jaw],[.28,.25,.21,.16],'jugular regional course '+name)
 v.path([jaw,(jaw[0]+sign*.9,17.4,5.1),(jaw[0]+sign*.7,13.6,6.1)],[.145,.105,.065],'facial venous course '+name)
 v.path([jaw,(jaw[0]-sign*.4,18.2,8.1),(jaw[0]-sign*.8,15.2,9.0)],[.125,.09,.06],'deep facial regional course '+name)
 v.path([neck,(neck[0]+sign*1.6,22,7.0),(neck[0]+sign*2,19,8.5)],[.13,.10,.065],'superficial cervical regional branch '+name)
v.finish()

for side,arterial,root,sgn in [('a',ARM_A,CRAN_A,-1),('b',ARM_B,CRAN_B,1)]:
 pts=[root]+[(p[0]+sgn*.6,p[1]+.3,max(1.6,p[2]-.7)) for p in arterial[1:]]
 v=Tree('forelimb_'+side,'前肢'+side.upper()+'静脉树','Forelimb '+side.upper()+' venous tree','venous','沿源骨骼前肢回流至腋和锁骨下区域，保留主干和少量表浅分支；末端不是实测毛细血管。')
 v.path(pts,np.linspace(.28,.105,len(pts)),'subclavian-axillary regional venous course')
 v.path([pts[2],np.array(pts[3])+[-sgn*.7,.5,-.2],np.array(pts[-2])+[-sgn*.7,0,-.1]],[.18,.14,.09],'superficial forearm regional vein')
 for dx in [-.8,.4]:v.path([pts[-1],np.array(pts[-1])+[dx,-1,.1],np.array(pts[-1])+[dx*1.6,-1.8,.2]],[.105,.08,.055],'palmar venous regional ending')
 v.finish()

v=Tree('renal','肾静脉树','Renal venous trees','venous','两侧肾门向尾侧腔静脉回流；跨中线的一侧肾静脉位于主动脉腹侧，避免穿过其中心。')
for side,root,hilum,c,sgn in RENALS:
 origin=CAVA_RA if side=='A' else CAVA_RB
 hh=(hilum[0],hilum[1]+.4,hilum[2]-.7);cc=np.array(c)+[0,.3,-.7]
 v.path([origin,((origin[0]+hh[0])/2,hh[1],12.8),hh,cc],[.26,.23,.20,.16],'renal venous course '+side)
 for dy in [-2.4,2.6]:v.path([cc,cc+[sgn*.6,dy*.6,-.5],cc+[sgn*1.4,dy,-.9]],[.14,.11,.075],'renal regional tributary '+side)
v.finish()

v=Tree('portal_mesenteric','肝门与肠系膜静脉树','Hepatic portal and mesenteric venous tree','venous','肠系膜、胃和脾区域回流汇入肝门静脉后进入肝内；不直接连接腔静脉，保留肝门系统关系。')
PORTAL=(17.6,52.2,9.7);PV_MES=(18.3,59.5,8.6)
v.path([PORTAL,(17.9,55.4,9.4),PV_MES,(18.7,64,7.8),(18.8,67.7,7.7)],[.33,.31,.27,.23,.17],'portal-superior mesenteric venous course')
v.path([PORTAL,(16.0,50,8.8),(13.6,49,7.9)],[.30,.24,.16],'intrahepatic portal regional branch A')
v.path([PORTAL,(20,49.5,9.3),(23,48.5,8.6)],[.27,.21,.14],'intrahepatic portal regional branch B')
v.path([(17.9,55.4,9.4),(22,56,11.3),(26,56.8,12.3)],[.24,.19,.12],'splenic venous tributary')
v.path([(22,56,11.3),(24.4,53.7,10.0),(25.8,51.8,9.5)],[.15,.11,.07],'gastric venous tributary')
for x,y in [(12,62.5),(24,63),(11.4,67),(24,68),(15,70),(21.6,70.5)]:
 root=PV_MES if y<65 else (18.7,64,7.8)
 v.path([root,((x+root[0])/2,y-1.2,7.8),(x,y,7.1)],[.17,.13,.085],'intestinal regional venous tributary')
v.finish()

v=Tree('hepatic','肝静脉汇流','Hepatic venous collectors','venous','肝内区域支汇向穿过肝后部的尾侧腔静脉，与肝门静脉保留不同的汇流终点。')
collector=(15.9,47.4,11.0)
for pts in [[collector,(13,48.8,10),(10.4,51,8.4),(8.8,54.1,7.5)],[collector,(18.8,48.7,11),(23,49.6,10.3),(26,51,9.9)],[collector,(16,51.5,11.5),(16.5,56,12),(17,58,12.1)]]:
 v.path(pts,[.28,.24,.19,.12],'hepatic regional collector')
v.finish()

v=Tree('iliac_hindlimbs','髂与后肢静脉树','Iliac and hindlimb venous trees','venous','两侧足、小腿和股部区域经髂静脉汇入尾侧腔静脉，走向随标本两侧后肢姿势。')
for side,aa,s in [('A',LEG_A,-1),('B',LEG_B,1)]:
 pts=[CAVA_END]+[(p[0]-s*.6,p[1]+.5,max(1.8,p[2]-.5)) for p in aa[1:]]
 v.path(pts,[.31,.29,.28,.25,.22,.19,.15,.11],'iliac-femoral regional venous course '+side)
 v.path([pts[2],np.array(pts[3])+[0,1.7,.2],np.array(pts[4])+[-s*.6,2.3,.4]],[.19,.15,.10],'deep femoral regional tributary '+side)
 v.path([pts[4],np.array(pts[5])+[s*.9,0,-.1],np.array(pts[6])+[s*.8,0,-.2],np.array(pts[7])+[s*.6,0,0]],[.17,.14,.105,.075],'saphenous regional venous course '+side)
 for dx in [-.7,.8]:v.path([pts[-1],np.array(pts[-1])+[dx,.7,0],np.array(pts[-1])+[dx*1.4,1.4,0]],[.11,.08,.06],'pedal venous regional ending '+side)
v.finish()

v=Tree('pulmonary','肺静脉分支','Pulmonary venous branches','venous','肺内区域汇流至心基部的独立静脉树，蓝色用于静脉类别辨认，不代表含氧状态。')
for s in [-1,1]:
 root=(18.8,40,10.5);hub=(18.2+s*2.7,41.5,11.1)
 v.path([root,(18.5+s*1.4,40.7,10.7),hub],[.23,.21,.18],'pulmonary venous collector')
 for yy in [36.7,43.4,45.5]:v.path([hub,(hub[0]+s*.8,(yy+41.5)/2,11.5),(hub[0]+s*1.2,yy,11.1)],[.15,.12,.085],'pulmonary regional tributary')
v.finish()

def save():
 assert len(TREES)==18
 meshes=[(m['id'],v,f,m['color'],{'partId':m['id'],'origin':'teaching','scanDerived':False}) for m,v,f in TREES]
 path=OUTPUT/'core.glb';export_glb(meshes,path)
 raw=path.read_bytes();nn=struct.unpack_from('<I',raw,12)[0];doc=json.loads(raw[20:20+nn]);binary=raw[28+nn:]
 doc['asset']['generator']='Original mouse major-vessel teaching extension; generate_vascular.py'
 doc['asset']['copyright']='Original authored mouse vascular teaching extension. CC BY-SA 4.0. Anchored to Digimouse; not vascular segmentation.'
 jj=json.dumps(doc,separators=(',',':')).encode();jj+=b' '*((-len(jj))%4)
 path.write_bytes(struct.pack('<4sII',b'glTF',2,28+len(jj)+len(binary))+struct.pack('<I4s',len(jj),b'JSON')+jj+struct.pack('<I4s',len(binary),b'BIN\0')+binary)
 (OUTPUT/'core.glb.gz').write_bytes(gzip.compress(path.read_bytes(),compresslevel=9,mtime=0))
 (OUTPUT/'metadata.json').write_text(json.dumps([m for m,_,_ in TREES],ensure_ascii=False,indent=2),encoding='utf8')
 (OUTPUT/'authored-paths.json').write_text(json.dumps(ALL_PATHS,ensure_ascii=False,indent=2),encoding='utf8')
 report={'meshes':len(TREES),'triangles':sum(len(f) for _,_,f in TREES),'vertices':sum(len(v) for _,v,_ in TREES),'gzipBytes':(OUTPUT/'core.glb.gz').stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'sourceCoordinateSystem':'Original Digimouse raw mm: cranial=-Y, ventral=-Z; A=lower X, B=higher X. A/B not verified anatomical sides.','origin':'teaching','scanDerived':False,'selectedRegionalBranchesOnly':True,'junctionMethod':'Independent smooth capped curve tubes intersect at shared centerline junctions. Each named tree is a single mesh; no Boolean-union or CFD-manifold claim.'}
 report['license']='CC-BY-SA-4.0';report['licenseUrl']='https://creativecommons.org/licenses/by-sa/4.0/'
 (OUTPUT/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
 print(json.dumps(report),flush=True)

if __name__=='__main__':save()
