export type LabelAnchor={id:string;x:number;y:number;width:number;height:number};
export type LabelPlacement=LabelAnchor&{left:number;top:number};
const overlaps=(a:LabelPlacement,b:LabelPlacement,gap:number)=>a.left<b.left+b.width+gap&&a.left+a.width+gap>b.left&&a.top<b.top+b.height+gap&&a.top+a.height+gap>b.top;
/** Show names only where nearby space is available; crowded structures remain selectable in 3D. */
export function placeAnatomyLabels(anchors:LabelAnchor[],width:number,height:number){
 const padding=5,gap=6;
 const valid=anchors.filter(a=>[a.x,a.y,a.width,a.height].every(Number.isFinite)&&a.width>0&&a.height>0&&a.x>=0&&a.x<=width&&a.y>=0&&a.y<=height).sort((a,b)=>a.y-b.y||a.x-b.x||a.id.localeCompare(b.id));
 const placed:LabelPlacement[]=[];
 const clamp=(n:number,lo:number,hi:number)=>Math.max(lo,Math.min(hi,n));
 for(const a of valid){
  const w=a.width,h=a.height;if(w>width-2*padding||h>height-2*padding)continue;
  const candidates=[{left:a.x-w/2,top:a.y-h-9},{left:a.x-w/2,top:a.y+9},{left:a.x-w-12,top:a.y-h/2},{left:a.x+12,top:a.y-h/2}];
  for(const dy of [-28,28,-56,56])candidates.push({left:a.x-w/2,top:a.y-h-9+dy});
  const found=candidates.map(c=>({...a,left:clamp(c.left,padding,width-padding-w),top:clamp(c.top,padding,height-padding-h)})).find(c=>Math.hypot(c.left+w/2-a.x,c.top+h/2-a.y)<100&&!placed.some(p=>overlaps(c,p,gap)));
  if(found)placed.push(found);
 }
 return placed;
}
export function anatomyLabelName(name:string){return name.replace(/\s*[（(]教学[）)]\s*$/,'').trim()}
