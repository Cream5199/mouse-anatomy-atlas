import * as THREE from 'three';
import type {AtlasPart} from './atlas-types';

// Export the original assembled position, never a temporary exploded transform.
// The viewer is normalized; reverse that transform and convert source mm to glTF metres.
export function preparePartExport(mesh:THREE.Mesh,part:AtlasPart,inverseDisplay:THREE.Matrix4,attribution:string) {
 const geometry=mesh.geometry.clone();
 const center=part.center??[0,0,0];
 geometry.translate(center[0],center[1],center[2]).applyMatrix4(inverseDisplay).scale(.001,.001,.001);
 const materials=(Array.isArray(mesh.material)?mesh.material:[mesh.material]).map(source=>{
  const material=source.clone();
  if(material instanceof THREE.MeshStandardMaterial){material.emissive.set('#000000');material.emissiveIntensity=0;material.opacity=1;material.transparent=false;material.depthWrite=true;}
  return material;
 });
 const copy=new THREE.Mesh(geometry,Array.isArray(mesh.material)?materials:materials[0]);
 copy.name=part.id;
 copy.userData={id:part.id,name:part.name,english:part.en,origin:part.origin==='teaching'?'teaching-approximation':'scan-label-surface',license:'CC BY-SA 4.0',licenseURL:'https://creativecommons.org/licenses/by-sa/4.0/',units:'metres',position:'Assembled source coordinates; original source mm converted to metres.',attribution,limitations:'Teaching extensions are not measured segmentations. A/B are not verified anatomical laterality. Not validated for specimen-specific sampling, measurement or procedures.'};
 const group=new THREE.Group();group.name='Mouse Atlas';group.userData={...copy.userData};group.add(copy);
 return {group,dispose:()=>{geometry.dispose();materials.forEach(m=>m.dispose())}};
}
