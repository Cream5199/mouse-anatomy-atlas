from pathlib import Path
import struct, zlib, zipfile, json, hashlib
import numpy as np

BASE = Path(__file__).resolve().parent
DTYPES = {1:'i1',2:'u1',3:'<i2',4:'<u2',5:'<i4',6:'<u4',7:'<f4',9:'<f8',12:'<i8',13:'<u8'}

def elem(data, p):
    tag = struct.unpack_from('<I', data, p)[0]
    if tag >> 16:
        size, kind = tag >> 16, tag & 65535
        return kind, data[p+4:p+4+size], p+8
    kind, size = struct.unpack_from('<II', data, p)
    end = p+8+size
    return kind, data[p+8:end], end if kind == 15 else (end+7)//8*8

def readmat(path):
    data = path.read_bytes()
    assert data[126:128] == b'IM'
    result = {}
    def scan(data, pos):
        while pos + 8 <= len(data):
            kind, payload, pos = elem(data, pos)
            if kind == 15:
                scan(zlib.decompress(payload), 0)
            elif kind == 14:
                _, flags, off = elem(payload, 0)
                _, dims, off = elem(payload, off)
                _, name, off = elem(payload, off)
                typ, raw, off = elem(payload, off)
                shape = tuple(np.frombuffer(dims, dtype='<i4'))
                if typ not in DTYPES:
                    print('metadata',name.decode(),typ,repr(raw[:300]))
                    continue
                result[name.decode()] = np.frombuffer(raw, dtype=DTYPES[typ]).reshape(shape, order='F').copy()
    scan(data, 128)
    return result

LABELS = [
    (1,'体表内软组织','Inside skin (muscle)','#cd9d88','inside skin (muscle)'),
    (2,'脑','Brain','#d593a5','brain'),
    (3,'心脏','Heart','#aa3f43','heart'),
    (4,'膀胱','Bladder','#d8a171','bladder'),
    (5,'胃','Stomach','#c77c82','stomach'),
    (6,'脾','Spleen','#875174','spleen'),
    (7,'肾脏 7','Kidney 7','#a7494d','kidneys'),
    (8,'肾脏 8','Kidney 8','#af5358','kidneys'),
    (9,'肺 9','Lung 9','#d799a0','lungs'),
    (10,'肺 10','Lung 10','#d2a0a7','lungs'),
    (11,'胰腺','Pancreas','#dec38b','pancreas'),
    (12,'肝脏','Liver','#87484b','liver'),
    (13,'骨骼','Skeleton','#eadfc2','skeleton'),
    (14,'肌肉 14','Muscle 14','#b9736a','muscle'),
    (15,'肌肉 15','Muscle 15','#bc7a72','muscle'),
    (16,'睾丸 16','Testis 16','#d3a17e','testis'),
    (17,'睾丸 17','Testis 17','#cea985','testis')
]

def tet_surface(tets, points):
    # An organ boundary is exactly the triangle incident to one tetrahedron
    # of that organ. Orient every face away from its opposite vertex.
    combos = np.array([[1,2,3],[0,3,2],[0,1,3],[0,2,1]])
    faces = tets[:,combos].reshape(-1,3).copy()
    opposite = tets.reshape(-1)
    xyz = points[faces]
    cross = np.cross(xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0])
    inward = (cross*(points[opposite]-xyz[:,0])).sum(axis=1)>0
    faces[inward] = faces[inward][:,[0,2,1]]
    _, index, counts = np.unique(np.sort(faces,axis=1), axis=0, return_index=True, return_counts=True)
    surface = faces[index[counts==1]]
    assert counts.max() <= 2, 'Non-manifold tetrahedral incidence'
    return compact(points, surface)

def compact(points, faces):
    unique, inverse = np.unique(faces, return_inverse=True)
    return points[unique].astype('<f4'), inverse.reshape(-1,3).astype('<u4')

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
    doc={'asset':{'version':'2.0','generator':'Digimouse labelled tetrahedral boundary conversion',
                  'copyright':'Digimouse, USC Biomedical Imaging Group. CC BY-SA 4.0.'},
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

if __name__ == '__main__':
    with zipfile.ZipFile(BASE/'tesselated_atlas.zip') as archive:
        assert archive.testzip() is None
        for file in archive.infolist():
            if not file.is_dir():
                (BASE/Path(file.filename).name).write_bytes(archive.read(file))
    arrays = readmat(BASE/'Tesselated_Atlas.mat')
    for name, a in arrays.items():
        print(name, a.shape, a.dtype, 'min',a.min(), 'max',a.max(), flush=True)
    np.savez(BASE/'original-arrays.npz', **arrays)
    points=arrays['r']; tets=arrays['T'].astype(np.int64)-1; regions=arrays['cond'].ravel()
    print('coordinate bounds',points.min(axis=0),points.max(axis=0),flush=True)
    metadata=[]; meshes=[]
    for region,name,en,color,source in LABELS:
        pts,faces=tet_surface(tets[regions==region], points)
        item={'id':region,'meshName':f'region_{region}','name':name,'en':en,'color':color,'sourceName':source,
              'vertices':len(pts),'triangles':len(faces),'centroid':pts.mean(axis=0).tolist(),
              'bounds':[pts.min(axis=0).tolist(),pts.max(axis=0).tolist()]}
        metadata.append(item)
        meshes.append((f'region_{region}',pts,faces,color,{'region':region,'sourceName':source}))
        print(region,name,'vertices',len(pts),'faces',len(faces),'center',pts.mean(axis=0),flush=True)
    export_glb(meshes, BASE/'digimouse.glb')
    hullpts,hullfaces=tet_surface(tets,points)
    export_glb([('body_surface',hullpts,hullfaces,'#cd9d88',{'sourceName':'outer surface of full tetrahedral atlas'})], BASE/'body-surface.glb')
    (BASE/'metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
    provenance={'title':'Digimouse tessellated atlas','source':'https://neuroimage.usc.edu/mouse_atlas/tesselated_atlas.zip',
                'sourcePage':'https://neuroimage.usc.edu/neuro/Digimouse_Download',
                'license':'CC BY-SA 4.0','licensePage':'https://neuroimage.usc.edu/neuro/Digimouse_license',
                'authors':'B. Dogdas, D. Stout, A. Chatziioannou, R. M. Leahy',
                'citation':'Digimouse: A 3D Whole Body Mouse Atlas from CT and Cryosection Data. Phys. Med. Biol. 52:577-587 (2007).',
                'doi':'https://doi.org/10.1088/0031-9155/52/3/003',
                'changes':'Converted labelled tetrahedron boundaries into independent indexed triangle meshes; computed smooth vertex normals; assigned illustrative colors. Original coordinates retained, no smoothing, decimation or invented anatomy.',
                'coordinateBounds':[points.min(axis=0).tolist(),points.max(axis=0).tolist()],
                'warnings':['The tessellated download has 17 labels; it does not contain every structure listed for the higher-detail voxel atlas.',
                            'Paired organs retain numeric source labels. Laterality is not specified in the source label file.',
                            'Region 1 contains surrounding soft tissue and internal organ interface surfaces; body-surface.glb supplies only the exterior boundary.',
                            'Skeleton remains one complete labelled region; there is no per-bone anatomy.'],
                'sha256':hashlib.sha256((BASE/'tesselated_atlas.zip').read_bytes()).hexdigest()}
    (BASE/'provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2),encoding='utf-8')
    print('EXPORTED', (BASE/'digimouse.glb').stat().st_size, 'bytes',flush=True)
