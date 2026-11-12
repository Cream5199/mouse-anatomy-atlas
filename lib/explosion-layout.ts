// Adapted from Human Atlas (MIT); source attribution: /licenses/human-atlas.txt.
import type {AtlasPart} from './atlas-types';
export type LayoutCell={x:number;y:number;width:number;height:number};
export function createExplosionLayout(parts:AtlasPart[],aspect=1){
 const cards=parts.map(p=>({id:p.id,width:Math.max(.035,p.bounds![1][0]-p.bounds![0][0])+.10,height:Math.max(.035,p.bounds![1][1]-p.bounds![0][1])+.13}));
 const area=cards.reduce((n,c)=>n+c.width*c.height,0),targetWidth=Math.max(.3,...cards.map(c=>c.width),Math.sqrt(area*Math.max(.5,Math.min(1.5,aspect)))*1.18);
 cards.sort((a,b)=>b.height-a.height||a.id.localeCompare(b.id));
 const cells=new Map<string,LayoutCell>();let x=0,y=0,row=0,width=0;
 for(const c of cards){if(x>0&&x+c.width>targetWidth){x=0;y+=row;row=0}cells.set(c.id,{x:x+c.width/2,y:-y-c.height/2,width:c.width,height:c.height});x+=c.width;width=Math.max(width,x);row=Math.max(row,c.height)}
 const height=y+row;cells.forEach(c=>{c.x-=width/2;c.y+=height/2});return {cells,width,height};
}
/** Exact source positions at 0; separate, original-size source meshes at 1. */
export function explodedPosition(part:AtlasPart,index:number,count:number,amount:number,cell?:LayoutCell){
 const c=part.center!,angle=index/Math.max(1,count)*Math.PI*2;
 const radial=[Math.sin(angle)*.65,c[1]*.24,Math.cos(angle)*.65];
 if(amount<=.45){const t=amount/.45;return c.map((v,i)=>v+radial[i]*t)}
 const t=(amount-.45)/.55,destination=cell?[cell.x,cell.y,0]:c;
 return c.map((v,i)=>(v+radial[i])*(1-t)+destination[i]*t);
}
