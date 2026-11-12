import json,struct
import numpy as np

def normals(points, faces):
    xyz=points[faces]
    norm=np.cross(xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0])
    out=np.zeros_like(points)
    for i in range(3):
        np.add.at(out,faces[:,i],norm)
    lengths=np.linalg.norm(out,axis=1)
    out/=np.maximum(lengths,1e-20)[:,None]
    return out.astype('<f4')

def export_glb(meshes, path):
    doc={'asset':{'version':'2.0','generator':'Self-authored mouse teaching extension; generate_digestive.py; smooth swept surfaces',
                  'copyright':'Animal Atlas contributors. CC BY-SA 4.0. Original procedural teaching illustration, not CT or specimen data.',
                  'extras':{'license':'CC-BY-SA-4.0','licenseUrl':'https://creativecommons.org/licenses/by-sa/4.0/'}},
         'scene':0,'scenes':[{'nodes':[]}], 'nodes':[], 'meshes':[], 'materials':[],
         'bufferViews':[], 'accessors':[], 'buffers':[]}
    binary=bytearray()
    def accessor(a, kind, component, target):
        while len(binary)%4: binary.extend(b'\x00')
        offset=len(binary); raw=a.tobytes(); binary.extend(raw)
        view=len(doc['bufferViews'])
        doc['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':len(raw),'target':target})
        acc={'bufferView':view,'byteOffset':0,'componentType':component,'count':len(a),'type':kind}
        if kind=='VEC3':
            acc.update(min=a.min(axis=0).tolist(),max=a.max(axis=0).tolist())
        else:
            acc.update(min=[int(a.min())],max=[int(a.max())])
        idx=len(doc['accessors']);doc['accessors'].append(acc)
        return idx
    for name, pts, faces, color, extras in meshes:
        pos=accessor(pts,'VEC3',5126,34962)
        norm=accessor(normals(pts,faces),'VEC3',5126,34962)
        idx=accessor(faces.ravel(),'SCALAR',5125,34963)
        rgb=[int(color[i:i+2],16)/255 for i in (1,3,5)]
        mid=len(doc['materials']); doc['materials'].append({'name':name,'pbrMetallicRoughness':{'baseColorFactor':rgb+[1],'metallicFactor':0,'roughnessFactor':0.65},'doubleSided':False})
        mi=len(doc['meshes']);doc['meshes'].append({'name':name,'primitives':[{'attributes':{'POSITION':pos,'NORMAL':norm},'indices':idx,'material':mid}],'extras':extras})
        ni=len(doc['nodes']);doc['nodes'].append({'name':name,'mesh':mi,'extras':extras});doc['scenes'][0]['nodes'].append(ni)
    doc['buffers']=[{'byteLength':len(binary)}]
    j=json.dumps(doc,ensure_ascii=True,separators=(',',':')).encode()
    j+=b' '*((-len(j))%4);binary.extend(b'\x00'*((-len(binary))%4))
    total=12+8+len(j)+8+len(binary)
    path.write_bytes(struct.pack('<4sII',b'glTF',2,total)+struct.pack('<I4s',len(j),b'JSON')+j+struct.pack('<I4s',len(binary),b'BIN\x00')+binary)

