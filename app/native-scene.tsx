'use client';
import {sitePath} from '@/lib/site-path';
import {useEffect,useImperativeHandle,useRef,useState} from 'react';
import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';
import type {AtlasPart,SceneProps,View,ModelUrl} from '@/lib/atlas-types';
import {createExplosionLayout,explodedPosition} from '@/lib/explosion-layout';
import {placeAnatomyLabels,anatomyLabelName,type LabelAnchor} from '@/lib/anatomy-label-layout';
import {preparePartExport} from '@/lib/model-export';

export default function NativeScene(props:SceneProps){
 const exportPart=useRef<((id:string)=>Promise<Blob>)|null>(null);
 useImperativeHandle(props.apiRef,()=>({exportPart:(id:string)=>{if(!exportPart.current)return Promise.reject(new Error('模型尚未加载，请稍后重试。'));return exportPart.current(id)}}),[]);
 const host=useRef<HTMLDivElement>(null),latest=useRef(props);latest.current=props;
 const leaderNodes=useRef(new Map<string,SVGLineElement>()),tooltip=useRef<HTMLDivElement>(null),labelGuide=useRef<HTMLDivElement>(null);
 function hideLabelDetails(){if(tooltip.current)tooltip.current.hidden=true}
 function showLabelDetails(p:AtlasPart){const node=labelNodes.current.get(p.id),tip=tooltip.current,el=host.current;if(!node||!tip||!el)return;const r=node.getBoundingClientRect(),container=el.getBoundingClientRect();tip.textContent=p.name+(p.origin==='teaching'&&!p.name.includes('教学')?' · 教学补建':'');tip.hidden=false;tip.style.left=Math.max(4,Math.min(el.clientWidth-tip.offsetWidth-4,r.left-container.left+r.width/2-tip.offsetWidth/2))+'px';const above=r.top-container.top-tip.offsetHeight-7;tip.style.top=(above>=4?above:Math.min(el.clientHeight-tip.offsetHeight-4,r.bottom-container.top+7))+'px'}
 const labelNodes=useRef(new Map<string,HTMLButtonElement>()),[labels,setLabels]=useState<AtlasPart[]>([]),[notice,setNotice]=useState(''),retryLazy=useRef(()=>{});
 useEffect(()=>{
  const el=host.current;if(!el)return;let stopped=false,frame=0,renderer:THREE.WebGLRenderer;
  try{renderer=new THREE.WebGLRenderer({antialias:true,powerPreference:'high-performance'})}catch{latest.current.onError('浏览器未能启动三维显示，请启用 WebGL 后重试。');return}
  renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.setClearColor('#f2f3f3');renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.02;
  el.appendChild(renderer.domElement);renderer.domElement.tabIndex=0;renderer.domElement.setAttribute('aria-label',props.specimen.name+'三维模型：拖动旋转、滚轮缩放、点击选择，方向键旋转，加减键缩放。');
  const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(34,1,.01,100);
  const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.dampingFactor=.08;controls.enablePan=true;controls.minDistance=.2;controls.maxDistance=30;controls.autoRotateSpeed=.6;
  const pmrem=new THREE.PMREMGenerator(renderer),room=new RoomEnvironment(),env=pmrem.fromScene(room,.04);scene.environment=env.texture;room.dispose();pmrem.dispose();
  scene.add(new THREE.HemisphereLight('#ffffff','#a7acb2',.8));const key=new THREE.DirectionalLight('#fff4e8',2.0);key.position.set(-3,5,5);scene.add(key);const rim=new THREE.DirectionalLight('#dce8ff',1.3);rim.position.set(4,2,-3);scene.add(rim);
  const meshes=new Map<string,THREE.Mesh<THREE.BufferGeometry,THREE.MeshStandardMaterial>>();let parts:AtlasPart[]=[],amount=0,previousKey='',layout=createExplosionLayout([]),cameraTween=false,manualCamera=false,previousExplode=0,renderRevision=0,lastRenderKey='';
  let desiredCamera=new THREE.Vector3(.4,.1,5),desiredTarget=new THREE.Vector3(),oldTime=0;camera.position.copy(desiredCamera);
  const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
  const directions:Record<View,THREE.Vector3>={'three-quarter':new THREE.Vector3(.38,.08,1).normalize(),front:new THREE.Vector3(0,0,1),side:new THREE.Vector3(1,0,0),back:new THREE.Vector3(0,0,-1)};
  function fit(visible:AtlasPart[],a:number){
   const bounds=new THREE.Box3();for(const p of visible){const m=meshes.get(p.id);if(m){m.updateMatrixWorld();bounds.expandByObject(m)}}
   if(bounds.isEmpty())bounds.setFromCenterAndSize(new THREE.Vector3(),new THREE.Vector3(1,2,1));
   const size=bounds.getSize(new THREE.Vector3());bounds.getCenter(desiredTarget);
   const view=latest.current.state.view,dir=directions[view],w=view==='side'?size.z:size.x;
   const distance=Math.max(size.y,w/Math.max(.25,camera.aspect))/.61*1.18+size.z*.6;
   desiredCamera.copy(desiredTarget).addScaledVector(dir,Math.max(.7,distance));cameraTween=true;
  }
  const labelSizes=new Map<string,{width:number;height:number}>();let labelLayoutDirty=true,lastLabelUpdate=0,lastAnnotationState='';
  const resize=()=>{if(!el.clientWidth||!el.clientHeight)return;renderer.setSize(el.clientWidth,el.clientHeight);camera.aspect=el.clientWidth/el.clientHeight;camera.updateProjectionMatrix();previousKey='';renderRevision++;labelSizes.clear();labelLayoutDirty=true;hideLabelDetails()};
  const observer=new ResizeObserver(resize);observer.observe(el);resize();
  const abort=new AbortController();
  const assets=props.specimen.native!;
  async function loadModel(url:ModelUrl,report:(message:string)=>void){
   const urls=Array.isArray(url)?url:[url],responses=await Promise.all(urls.map(path=>fetch(sitePath(path),{signal:abort.signal})));
   if(responses.some(r=>!r.ok))throw Error('model');
   const sizes=responses.map(r=>Number(r.headers.get('Content-Length'))),total=sizes.every(n=>n>0)?sizes.reduce((a,b)=>a+b,0):0;
   const chunks:Uint8Array[]=[];let received=0,reported=0;
   for(const response of responses){const reader=response.body?.getReader();
    if(reader){for(;;){const chunk=await reader.read();if(chunk.done)break;chunks.push(chunk.value);received+=chunk.value.length;if(!stopped&&received-reported>300000){reported=received;report(total?'正在下载模型 · '+Math.min(99,Math.round(received/total*100))+'%':'正在下载模型 · '+(received/1048576).toFixed(1)+' MB')}}}
    else{const chunk=new Uint8Array(await response.arrayBuffer());chunks.push(chunk);received+=chunk.length}
   }
   if(stopped)throw Error('aborted');report('正在准备三维结构');
   const joined=new Uint8Array(received);let offset=0;for(const chunk of chunks){joined.set(chunk,offset);offset+=chunk.length}let buffer:ArrayBuffer=joined.buffer;
   if(joined[0]===31&&joined[1]===139)buffer=await new Response(new Blob([buffer]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
   return new GLTFLoader().parseAsync(buffer,'');
  }
  const transform=new THREE.Matrix4(),attempted=new Set<string>();
  exportPart.current=async(id:string)=>{
   if(stopped)throw new Error('模型已关闭，请重新加载。');
   const p=parts.find(p=>p.id===id),mesh=meshes.get(id);
   if(!p||!mesh)throw new Error('该结构尚未加载，请显示它并等待加载完成后重试。');
   const source=p.origin==='teaching'?'/models/mouse-teaching/ATTRIBUTION.txt':'/models/digimouse-voxel/ATTRIBUTION.txt';
   const response=await fetch(sitePath(source),{signal:abort.signal});if(!response.ok)throw new Error('来源说明未能加载，请重试。');
   const attribution=await response.text();
   if(stopped)throw new Error('模型已关闭，请重新加载。');
   const {GLTFExporter}=await import('three/addons/exporters/GLTFExporter.js');
   if(stopped)throw new Error('模型已关闭，请重新加载。');
   const prepared=preparePartExport(mesh,p,transform.clone().invert(),attribution);
   try{const buffer=await new GLTFExporter().parseAsync(prepared.group,{binary:true});if(!(buffer instanceof ArrayBuffer))throw new Error('模型导出失败');return new Blob([buffer],{type:'model/gltf-binary'});}finally{prepared.dispose();}
  };
  const disposeSource=(root:THREE.Object3D)=>root.traverse(o=>{if(o instanceof THREE.Mesh){o.geometry.dispose();(Array.isArray(o.material)?o.material:[o.material]).forEach(m=>m.dispose())}});
  function addSourceMesh(source:THREE.Mesh,p:AtlasPart){
   const geometry=source.geometry.clone().applyMatrix4(source.matrixWorld).applyMatrix4(transform);geometry.computeBoundingBox();if(!geometry.getAttribute('normal'))geometry.computeVertexNormals();
   const bounds=geometry.boundingBox!,origin=bounds.getCenter(new THREE.Vector3()),partBounds=[bounds.min.toArray(),bounds.max.toArray()];geometry.translate(-origin.x,-origin.y,-origin.z);
   const material=new THREE.MeshStandardMaterial({color:geometry.hasAttribute('color')?'#ffffff':p.color,vertexColors:geometry.hasAttribute('color'),roughness:p.category==='muscular'?.64:.53,metalness:.025,side:THREE.DoubleSide,transparent:p.category==='skin',opacity:p.category==='skin'?.18:1,depthWrite:p.category!=='skin'});
   const mesh=new THREE.Mesh(geometry,material);mesh.name=p.id;mesh.position.copy(origin);mesh.userData.partId=p.id;scene.add(mesh);meshes.set(p.id,mesh);renderRevision++;
   return {...p,bounds:partBounds,center:origin.toArray()};
  }
  async function loadLazy(p:AtlasPart){
   if(!p.lazyModelUrl||attempted.has(p.id)||stopped)return;attempted.add(p.id);setNotice('正在加载'+p.name);
   try{const gltf=await loadModel(p.lazyModelUrl,message=>{if(!stopped)setNotice(p.name+' · '+message)});if(stopped){disposeSource(gltf.scene);return}gltf.scene.updateMatrixWorld(true);let source:THREE.Mesh|undefined;gltf.scene.traverse(o=>{if(o instanceof THREE.Mesh&&o.name===p.id)source=o});if(!source){disposeSource(gltf.scene);throw Error('Missing region')}
    const prepared=addSourceMesh(source,p);Object.assign(p,{bounds:prepared.bounds,center:prepared.center});disposeSource(gltf.scene);previousKey='';setNotice('');
   }catch{if(!stopped)setNotice('体表加载失败，请重试。')}
  }
  retryLazy.current=()=>{attempted.clear();setNotice('')};
  const sources=[assets,...assets.supplements||[]];
  Promise.all(sources.map(async(source,index)=>{
   const [gltf,data]=await Promise.all([loadModel(source.modelUrl,message=>{if(index===0)latest.current.onProgress?.(message)}),fetch(sitePath(source.metadataUrl),{signal:abort.signal}).then(r=>{if(!r.ok)throw Error('metadata');return r.json()})]);
   if(!Array.isArray(data)||data.length===0){disposeSource(gltf.scene);throw Error('Missing metadata')}
   if(stopped){disposeSource(gltf.scene);throw Error('aborted')}
   return {gltf,metadata:data as AtlasPart[]};
  })).then(bundles=>{
   if(stopped){bundles.forEach(b=>disposeSource(b.gltf.scene));return}
   const metadata=bundles.flatMap(b=>b.metadata),originals:THREE.Mesh[]=[];
   if(new Set(metadata.map(p=>p.id)).size!==metadata.length)throw Error('Duplicate anatomy ids');
   bundles.forEach(b=>{b.gltf.scene.updateMatrixWorld(true);b.gltf.scene.traverse(o=>{if(o instanceof THREE.Mesh)originals.push(o)})});
   const whole=new THREE.Box3();bundles[0].metadata.forEach(p=>p.bounds?.forEach(v=>whole.expandByPoint(new THREE.Vector3(...v))));if(whole.isEmpty())whole.setFromObject(bundles[0].gltf.scene);
   const size=whole.getSize(new THREE.Vector3()),center=whole.getCenter(new THREE.Vector3()),scale=2.5/Math.max(size.x,size.y,size.z);
   transform.makeScale(scale,scale,scale).multiply(new THREE.Matrix4().makeRotationFromEuler(new THREE.Euler(...assets.rotation))).multiply(new THREE.Matrix4().makeTranslation(-center.x,-center.y,-center.z));
   parts=metadata.map(p=>{
    const source=originals.find(m=>m.name===p.id);if(source)return addSourceMesh(source,p);
    if(!p.lazyModelUrl||!p.bounds)throw Error('Missing source region '+p.id);
    const bounds=new THREE.Box3(new THREE.Vector3(...p.bounds[0]),new THREE.Vector3(...p.bounds[1])).applyMatrix4(transform);
    return {...p,bounds:[bounds.min.toArray(),bounds.max.toArray()],center:bounds.getCenter(new THREE.Vector3()).toArray()};
   });
   bundles.forEach(b=>disposeSource(b.gltf.scene));setLabels(parts);latest.current.onParts(parts);latest.current.onReady();previousKey='';
  }).catch(()=>{if(!stopped)latest.current.onError('三维解剖模型未能加载，请重新加载。')});
  const ray=new THREE.Raycaster(),pointer=new THREE.Vector2();let down={x:0,y:0};
  // User input owns the camera until an explicit framing action (view, isolate, slider or reset).
  const interrupt=()=>{cameraTween=false;manualCamera=true};
  const start=(e:PointerEvent)=>{down={x:e.clientX,y:e.clientY};interrupt()};
  const pick=(e:PointerEvent)=>{if(Math.hypot(e.clientX-down.x,e.clientY-down.y)>5)return;const r=renderer.domElement.getBoundingClientRect();pointer.set((e.clientX-r.left)/r.width*2-1,-(e.clientY-r.top)/r.height*2+1);ray.setFromCamera(pointer,camera);const hit=ray.intersectObjects([...meshes.values()].filter(m=>m.visible))[0];if(hit)latest.current.onSelect(hit.object.userData.partId)};
  const keyboard=(e:KeyboardEvent)=>{if(['ArrowLeft','ArrowRight','+','=','-'].includes(e.key)){e.preventDefault();interrupt();const v=camera.position.clone().sub(controls.target);if(e.key.startsWith('Arrow'))v.applyAxisAngle(new THREE.Vector3(0,1,0),e.key==='ArrowLeft'?.16:-.16);else v.multiplyScalar(e.key==='-'?1.1:.9);camera.position.copy(controls.target).add(v)}};
  renderer.domElement.addEventListener('pointerdown',start);renderer.domElement.addEventListener('pointerup',pick);renderer.domElement.addEventListener('keydown',keyboard);renderer.domElement.addEventListener('wheel',interrupt,{passive:true});
  const projected=new THREE.Vector3();
  function updateLabels(){
   const active=!latest.current.hideLabels&&amount>=.92,anchors:LabelAnchor[]=[];
   for(const p of parts){const node=labelNodes.current.get(p.id),line=leaderNodes.current.get(p.id),mesh=meshes.get(p.id);if(line)line.style.display='none';if(!node)continue;
    node.hidden=true;if(!active||!mesh?.visible)continue;
    let size=labelSizes.get(p.id);if(!size){node.style.width='';node.style.height='';node.style.visibility='hidden';node.hidden=false;size={width:node.offsetWidth,height:node.offsetHeight};node.hidden=true;node.style.visibility='';if(size.width&&size.height)labelSizes.set(p.id,size)}
    projected.copy(mesh.position);projected.y+=(p.bounds![1][1]-p.bounds![0][1])/2+.025;projected.project(camera);
    if(projected.z< -1||projected.z>1||!size?.width)continue;
    anchors.push({id:p.id,x:(projected.x*.5+.5)*el!.clientWidth,y:(-projected.y*.5+.5)*el!.clientHeight,...size});
   }
   const placed=placeAnatomyLabels(anchors,el!.clientWidth,Math.max(0,el!.clientHeight-30));
   for(const p of placed){const node=labelNodes.current.get(p.id)!;node.style.left=p.left+'px';node.style.top=p.top+'px';node.style.width=p.width+'px';node.style.height=p.height+'px';node.hidden=false;
    const line=leaderNodes.current.get(p.id);if(line){const endX=Math.max(p.left,Math.min(p.left+p.width,p.x)),endY=Math.max(p.top,Math.min(p.top+p.height,p.y));if(Math.hypot(endX-p.x,endY-p.y)>4){line.setAttribute('x1',String(p.x));line.setAttribute('y1',String(p.y));line.setAttribute('x2',String(endX));line.setAttribute('y2',String(endY));line.style.display=''}}
   }
   if(labelGuide.current){labelGuide.current.hidden=!active||placed.length===anchors.length;labelGuide.current.textContent='点击结构查看名称与详情'}
   if(!active)hideLabelDetails();
  }
  function animate(time:number){
   if(stopped)return;frame=requestAnimationFrame(animate);const dt=Math.min(.05,(time-oldTime)/1000||.016);oldTime=time;
   const s=latest.current.state,visible=parts.filter(p=>s.isolate?p.id===s.selected:s.visible.includes(p.id));
   const beforeAmount=amount,nextAmount=reduced?s.explode:THREE.MathUtils.damp(amount,s.explode,8,dt);amount=Math.abs(nextAmount-s.explode)<.0001?s.explode:nextAmount;const moving=amount!==beforeAmount;
   const stateKey=[s.visible.join(','),s.isolate,s.isolate?s.selected:'',s.view,s.reset,camera.aspect].join('|');
   if(stateKey!==previousKey){layout=createExplosionLayout(visible,camera.aspect);previousKey=stateKey;manualCamera=false;cameraTween=true}
   if(s.explode!==previousExplode){previousExplode=s.explode;manualCamera=false;cameraTween=true}
   parts.forEach(p=>{const m=meshes.get(p.id),index=visible.indexOf(p);if(!m){if(index>=0&&p.lazyModelUrl)void loadLazy(p);const label=labelNodes.current.get(p.id);if(label)label.hidden=true;return}m.visible=index>=0;if(m.visible){const position=explodedPosition(p,index,visible.length,amount,layout.cells.get(p.id));m.position.set(position[0],position[1],position[2]);m.material.emissive.set(s.selected===p.id?'#35566a':'#000000');m.material.emissiveIntensity=s.selected===p.id?.15:0;if(p.category==='skin')m.material.opacity=s.isolate?1:.18}});
   if(!manualCamera&&(moving||cameraTween))fit(visible,amount);
   const tweening=cameraTween;if(cameraTween){const k=reduced?1:1-Math.exp(-7*dt);camera.position.lerp(desiredCamera,k);controls.target.lerp(desiredTarget,k);if(camera.position.distanceTo(desiredCamera)<.002&&controls.target.distanceTo(desiredTarget)<.002)cameraTween=false}
   controls.autoRotate=s.rotate&&!reduced&&!cameraTween&&(s.isolate||amount<.4);const orbitChanged=controls.update(),renderKey=[stateKey,s.selected,renderRevision].join('|');if(moving||tweening||orbitChanged||renderKey!==lastRenderKey){labelLayoutDirty=true;hideLabelDetails();renderer.render(scene,camera);lastRenderKey=renderKey}const annotationState=[renderKey,latest.current.hideLabels,amount>=.92,labelNodes.current.size].join('|');if(annotationState!==lastAnnotationState){labelLayoutDirty=true;lastAnnotationState=annotationState;}if(labelLayoutDirty&&(time-lastLabelUpdate>80||!moving&&!tweening&&!orbitChanged)){camera.updateMatrixWorld();updateLabels();lastLabelUpdate=time;labelLayoutDirty=false}
  }
  frame=requestAnimationFrame(animate);
  return()=>{stopped=true;abort.abort();cancelAnimationFrame(frame);observer.disconnect();controls.dispose();env.dispose();meshes.forEach(m=>{m.geometry.dispose();m.material.dispose()});renderer.domElement.removeEventListener('pointerdown',start);renderer.domElement.removeEventListener('pointerup',pick);renderer.domElement.removeEventListener('keydown',keyboard);renderer.domElement.removeEventListener('wheel',interrupt);renderer.dispose();renderer.domElement.remove()};
 },[props.specimen.id]);
 return <div className="atlas-scene native-atlas-scene" ref={host}>{notice&&<div className="asset-notice" role="status">{notice}{notice.includes('失败')&&<button onClick={()=>retryLazy.current()}>重试</button>}</div>}<svg className="anatomy-label-leaders" aria-hidden="true">{labels.map(p=><line key={p.id} ref={node=>{if(node)leaderNodes.current.set(p.id,node);else leaderNodes.current.delete(p.id)}} style={{display:'none'}}/>)}</svg>{labels.map(p=><button hidden key={p.id} className="exploded-label" aria-label={p.name} aria-describedby="anatomy-label-tooltip" ref={node=>{if(node)labelNodes.current.set(p.id,node);else labelNodes.current.delete(p.id)}} onMouseEnter={()=>showLabelDetails(p)} onMouseLeave={hideLabelDetails} onFocus={()=>showLabelDetails(p)} onBlur={hideLabelDetails} onClick={()=>{hideLabelDetails();props.onSelect(p.id)}}><span className="anatomy-label-name">{anatomyLabelName(p.name)}</span></button>)}<div hidden role="tooltip" id="anatomy-label-tooltip" className="anatomy-label-tooltip" ref={tooltip}/><div hidden className="anatomy-label-guide" ref={labelGuide}/></div>
}
