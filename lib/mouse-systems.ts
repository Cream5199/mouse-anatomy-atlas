import type {AtlasPart} from './atlas-types';
export const mouseSystems = [
 {id:'digestive',name:'消化系统',regions:[15,17,18]},
 {id:'urinary',name:'泌尿系统',regions:[19,13]},
 {id:'cardiorespiratory',name:'心脏与呼吸',regions:[9,21]},
 {id:'arterial',name:'主要动脉',regions:[]},
 {id:'venous',name:'主要静脉',regions:[]},
 {id:'muscular',name:'骨骼肌群',regions:[]},
 {id:'glands',name:'内分泌与免疫',regions:[20,16]},
 {id:'reproductive',name:'生殖系统',regions:[14]},
 {id:'nervous',name:'脑部分区',regions:[4,5,6,7,8,10]},
 {id:'head',name:'眼、泪腺与咬肌',regions:[3,12,11]},
 {id:'framework',name:'骨骼与体表',regions:[2,1]},
] as const;
export function sourceRegion(part:AtlasPart){return Number(part.id.split('_')[1])}
export function isTeaching(part:AtlasPart){return part.origin==='teaching'}
export function systemFor(part:AtlasPart){
 if(isTeaching(part)){
  const category=part.category==='respiratory'?'cardiorespiratory':part.category;
  return mouseSystems.find(s=>s.id===category)??mouseSystems[0];
 }
 return mouseSystems.find(s=>(s.regions as readonly number[]).includes(sourceRegion(part)))??mouseSystems[0];
}
export function isVisceral(part:AtlasPart){return isTeaching(part)?['digestive','respiratory','urinary'].includes(part.category||''):[9,13,14,15,16,17,18,19,20,21].includes(sourceRegion(part))}
export function isVascular(part:AtlasPart){return part.category==='arterial'||part.category==='venous'}
export function isMuscular(part:AtlasPart){return part.category==='muscular'||sourceRegion(part)===11}
export function practiceKey(part:AtlasPart){return part.id.replace(/_[ab]$/,'')}
export function practiceName(part:AtlasPart){return part.name.replace(/\s*[AB]$/,'')}
