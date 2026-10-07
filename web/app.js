const $=s=>document.querySelector(s);
const caption=$("#caption"), clock=$("#clock"), background=$("#background"), characters=$("#characters"), note=$("#note");
const buttons=[...document.querySelectorAll("button")]; let currentScene=null, currentAudio=null, speechRun=0;
function numberFromUrl(){const m=location.pathname.match(/^\/scene\/(\d+)$/);return m?Number(m[1]):1}
function render(scene){
 currentScene=scene; const n=scene.number || scene.index+1;
 clock.textContent=scene.time; $("#scene-number").textContent=`Szene ${n}`; $("#scene-time").textContent=`· ${scene.time} Uhr`;
 caption.textContent=scene.story; background.src=`/assets/backgrounds/${scene.background}.png`; characters.replaceChildren();
 for(const c of scene.characters){const img=document.createElement("img");img.className=`character ${c.position}`;img.dataset.name=c.name;img.alt=c.name;img.src=`/assets/characters/${c.name.toLowerCase()}/${c.pose}.png`;characters.appendChild(img)}
 note.hidden=!scene.note;note.textContent=scene.note||""; $("#previous").disabled=n<=1;
}
function stopSpeech(){speechRun++;if(currentAudio){currentAudio.pause();currentAudio.currentTime=0;currentAudio=null}document.querySelectorAll(".speaking").forEach(el=>el.classList.remove("speaking"))}
async function speak(parts){stopSpeech();const run=speechRun;for(const p of parts||[]){if(run!==speechRun)return;const ch=document.querySelector(`.character[data-name="${p.speaker}"]`);ch?.classList.add("speaking");const a=new Audio(p.audio);currentAudio=a;try{await a.play();await new Promise(r=>{a.onended=r;a.onerror=r});if(run!==speechRun)return}finally{ch?.classList.remove("speaking");if(currentAudio===a)currentAudio=null}}}
async function load(number,{generate=true,autoplay=false,push=false}={}){
 buttons.forEach(b=>b.disabled=true);caption.textContent=generate?"Szene wird geladen …":"Laden …";
 try{const r=await fetch(`/api/scenes/${number}`);if(!r.ok){const d=await r.json().catch(()=>({}));throw new Error(d.detail||r.statusText)}
 const scene=await r.json();render(scene);if(push)history.pushState({number},"",`/scene/${number}`);if(autoplay)await speak(scene.speech)}
 catch(e){caption.textContent=currentScene?.story||("Fehler: "+e.message)}
 finally{buttons.forEach(b=>b.disabled=false);if(currentScene)$("#previous").disabled=(currentScene.index===0)}
}
$("#previous").onclick=()=>{const n=(currentScene?.index??0)+1;if(n>1)load(n-1,{push:true})};
$("#next").onclick=()=>{const n=(currentScene?.index??-1)+2;load(n,{push:true,autoplay:true})};
$("#replay").onclick=()=>currentScene&&speak(currentScene.speech);
$("#stop").onclick=stopSpeech;
$("#regenerate").onclick=async()=>{if(!currentScene)return;buttons.forEach(b=>b.disabled=true);caption.textContent="Die Szene wird neu erzählt …";try{const n=currentScene.index+1;const r=await fetch(`/api/scenes/${n}/regenerate`,{method:"POST"});if(!r.ok){const d=await r.json();throw new Error(d.detail)}const s=await r.json();render(s);await speak(s.speech)}catch(e){caption.textContent=currentScene.story}finally{buttons.forEach(b=>b.disabled=false)}};
window.onpopstate=()=>load(numberFromUrl());
const initial=numberFromUrl();if(location.pathname==="/")history.replaceState({number:1},"","/scene/1");load(initial);
