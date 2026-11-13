import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import assert from 'node:assert/strict';
import {pathToFileURL} from 'node:url';
import ts from 'typescript';
import * as THREE from 'three';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'mouse-atlas-check-'));
async function compile(name){let code=ts.transpileModule(fs.readFileSync(new URL('../lib/'+name+'.ts',import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText;code=code.replace("from 'three'",'from '+JSON.stringify(pathToFileURL(require.resolve('three').replace(/three\.cjs$/,'three.module.js')).href));const dest=path.join(temp,name+'.mjs');fs.writeFileSync(dest,code);return import(pathToFileURL(dest).href);}
try{
 const {captureObservation,parseObservation,restoreObservation,observationURL,observationFromHash,readSavedObservations}=await compile('observation');
 const parts=[{id:'region_9',origin:'scan'},{id:'teaching_test',origin:'teaching'}];
 const s={visible:['region_9','teaching_test'],selected:'region_9',isolate:true,explode:.77,view:'side',rotate:true,reset:4};
 const observation=captureObservation(s,true),url=observationURL('https://example.test/mouse-anatomy-atlas/?practice=1&tracking=private-example',observation);
 assert.deepEqual(observationFromHash(new URL(url).hash),observation);assert.equal(new URL(url).search,'');assert.equal(new URL(url).pathname,'/mouse-anatomy-atlas/');
 assert.deepEqual(restoreObservation(observation,parts,5),{...s,rotate:false,reset:5});
 assert.deepEqual(restoreObservation({...observation,extended:false,selected:'teaching_test',visible:['region_9','teaching_test','missing']},parts,1),{visible:['region_9'],selected:null,isolate:false,explode:.77,view:'side',rotate:false,reset:1});
 for(const input of [null,{},[],{...observation,visible:['<script>']},{...observation,visible:Array(201).fill('region_9')},{...observation,explode:NaN}])assert.equal(parseObservation(input),null);
 assert.equal(observationFromHash('#atlas=%broken'),null);assert.deepEqual(readSavedObservations('{bad'),[]);assert.equal(parseObservation({...observation,explode:9}).explode,1);
 const {preparePartExport}=await compile('model-export');
 const raw=new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(12,20,30),new THREE.Vector3(13,21,30),new THREE.Vector3(13,20,31)]);
 const transform=new THREE.Matrix4().makeScale(.025,.025,.025).multiply(new THREE.Matrix4().makeRotationX(Math.PI)).multiply(new THREE.Matrix4().makeTranslation(-10,-50,-10));
 const geometry=raw.clone().applyMatrix4(transform);geometry.computeBoundingBox();const center=geometry.boundingBox.getCenter(new THREE.Vector3());geometry.translate(...center.clone().negate().toArray());
 const material=new THREE.MeshStandardMaterial({emissive:'#35566a',emissiveIntensity:.15,opacity:.18,transparent:true});const mesh=new THREE.Mesh(geometry,material);mesh.position.set(100,100,100);
 const prepared=preparePartExport(mesh,{id:'region_9',name:'心脏',en:'Heart',center:center.toArray()},transform.clone().invert(),'Source authors and license');
 const exported=prepared.group.children[0],positions=exported.geometry.getAttribute('position');
 for(let i=0;i<positions.count;i++)for(let axis=0;axis<3;axis++)assert.ok(Math.abs(positions.array[i*3+axis]-raw.getAttribute('position').array[i*3+axis]/1000)<1e-7,'Export preserves assembled metre coordinates');
 assert.equal(exported.material.emissiveIntensity,0);assert.equal(exported.material.opacity,1);assert.notEqual(exported.material,material);assert.equal(material.emissiveIntensity,.15);assert.equal(exported.userData.attribution,'Source authors and license');assert.equal(exported.userData.units,'metres');
 prepared.dispose();raw.dispose();geometry.dispose();material.dispose();
 console.log('PASS: observation links, mode/ID validation, corrupted storage, original export coordinates, neutral materials and provenance.');
}finally{fs.rmSync(temp,{recursive:true,force:true});}
