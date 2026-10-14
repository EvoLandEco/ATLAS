import {test} from 'node:test';
import assert from 'node:assert/strict';
import {connectScrollCue} from '../public/scroll.js';

test('scroll cues follow overflow, resize and the end of the pane without losing keyboard focus', () => {
  const original = {ResizeObserver:globalThis.ResizeObserver, document:globalThis.document, matchMedia:globalThis.matchMedia};
  let resize, reduced=false, focused=false, request;
  const events=new Map(), observed=[];
  const scroll={clientHeight:200,scrollHeight:600,scrollTop:0,addEventListener:(name,fn)=>events.set(name,fn),focus:()=>{focused=true;},scrollBy:value=>{request=value;}};
  const content={}, attributes=new Map();
  const cue={dataset:{},setAttribute:(key,value)=>attributes.set(key,value),addEventListener:(name,fn)=>events.set(`cue:${name}`,fn)};
  globalThis.ResizeObserver=class {constructor(fn){resize=fn;}observe(element){observed.push(element);}};
  globalThis.document={activeElement:null};
  globalThis.matchMedia=()=>({matches:reduced});
  try {
    connectScrollCue(scroll,content,cue);
    assert.deepEqual(observed,[scroll,content]);
    assert.equal(cue.dataset.more,'true');
    assert.equal(cue.tabIndex,0);
    events.get('cue:click')();
    assert.deepEqual(request,{top:200,behavior:'smooth'});
    reduced=true;events.get('cue:click')();
    assert.equal(request.behavior,'instant');
    document.activeElement=cue;scroll.scrollTop=399.5;events.get('scroll')();
    assert.equal(cue.dataset.more,'false');
    assert.equal(cue.tabIndex,-1);
    assert.equal(attributes.get('aria-hidden'),'true');
    assert.equal(focused,true);
    scroll.scrollHeight=800;resize();
    assert.equal(cue.dataset.more,'true');
    scroll.clientHeight=0;resize();
    assert.equal(cue.dataset.more,'false');
    scroll.clientHeight=900;scroll.scrollTop=0;resize();
    assert.equal(cue.dataset.more,'false');
  } finally {Object.assign(globalThis,original);}
});
