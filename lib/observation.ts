import type {AtlasPart, AtlasState, View} from './atlas-types';

export type Observation = {version:1; extended:boolean; visible:string[]; selected:string|null; isolate:boolean; explode:number; view:View};
export type SavedObservation = {id:string; title:string; savedAt:string; observation:Observation};
export const OBSERVATIONS_KEY = 'mouse-atlas.observations.v1';
const views:View[] = ['three-quarter','front','side','back'];

export function parseObservation(value:unknown):Observation|null {
 if(!value || typeof value!=='object')return null;
 const o=value as Record<string,unknown>;
 if(o.version!==1 || typeof o.extended!=='boolean' || !Array.isArray(o.visible) || o.visible.length>200 || !o.visible.every(id=>typeof id==='string' && /^[a-zA-Z0-9_-]{1,100}$/.test(id)))return null;
 if(typeof o.explode!=='number' || !Number.isFinite(o.explode) || !views.includes(o.view as View))return null;
 return {version:1,extended:o.extended,visible:[...new Set(o.visible)] as string[],selected:typeof o.selected==='string'?o.selected:null,isolate:o.isolate===true,explode:Math.min(1,Math.max(0,o.explode)),view:o.view as View};
}
export function captureObservation(state:AtlasState,extended:boolean):Observation {
 return {version:1,extended,visible:state.visible,selected:state.selected,isolate:state.isolate,explode:state.explode,view:state.view};
}
export function restoreObservation(o:Observation,parts:AtlasPart[],reset:number):AtlasState {
 const allowed=new Set(parts.filter(p=>o.extended||p.origin!=='teaching').map(p=>p.id));
 const visible=o.visible.filter(id=>allowed.has(id));
 const selected=o.selected&&allowed.has(o.selected)&&visible.includes(o.selected)?o.selected:null;
 return {visible,selected,isolate:!!selected&&o.isolate,explode:o.explode,view:o.view,rotate:false,reset};
}
export function observationFromHash(hash:string):Observation|null {
 try {if(hash.length>30000)return null;const value=new URLSearchParams(hash.replace(/^#/, '')).get('atlas');return value?parseObservation(JSON.parse(value)):null;}catch{return null;}
}
export function observationURL(base:string,o:Observation):string {
 const url=new URL(base);url.searchParams.delete('practice');url.searchParams.delete('specimen');url.hash=new URLSearchParams({atlas:JSON.stringify(o)}).toString();return url.toString();
}
export function readSavedObservations(raw:string|null):SavedObservation[] {
 try {const rows=JSON.parse(raw||'[]');if(!Array.isArray(rows))return [];return rows.slice(0,12).flatMap(row=>{const observation=parseObservation(row?.observation);return observation&&typeof row.id==='string'&&typeof row.title==='string'&&typeof row.savedAt==='string'?[{id:row.id.slice(0,100),title:row.title.slice(0,60),savedAt:row.savedAt,observation}]:[];});}catch{return [];}
}
