import type {Specimen} from '@/lib/atlas-types';
export const mouse:Specimen = {
 id:'digimouse-voxel',
 native:{modelUrl:'/models/digimouse-voxel/core.glb.gz',metadataUrl:'/models/digimouse-voxel/metadata.json',rotation:[Math.PI,0,0],attributionUrl:'/models/digimouse-voxel/ATTRIBUTION.txt',supplements:['digestive','vascular','muscles'].map(name=>({modelUrl:'/models/mouse-teaching/'+name+'/core.glb.gz',metadataUrl:'/models/mouse-teaching/'+name+'/metadata.json'}))},
 license:'CC BY-SA 4.0',creditShort:'Digimouse',name:'小鼠解剖图谱',en:'Mus musculus · Digimouse',category:'哺乳动物',
 author:'Dogdas · Stout · Chatziioannou · Leahy',method:'0.1 mm 原始分割',title:'Digimouse component-resolved atlas',url:'https://neuroimage.usc.edu/neuro/Digimouse',
 description:'由 Digimouse 原始 0.1 mm 标注体素重建，保留扫描分割的表面与相对位置。六组成对结构已进一步拆成独立对象，可以逐个选择、展开和合拢。',
 scope:'原始 27 个对象叠加小鼠肠道、主要血管和肌群的教学补建。补建结构用于整体形态与空间关系学习，不是原标本的实测分割。',
 study:['先观察整体位置，再选择一个系统。','展开结构，单独放大观察。','合拢后练习辨认器官。']
};
