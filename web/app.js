const caption = document.querySelector("#caption");
const clock = document.querySelector("#clock");
const background = document.querySelector("#background");
const characters = document.querySelector("#characters");
const note = document.querySelector("#note");
const buttons = [...document.querySelectorAll("button")];
let currentScene = null;

function assetName(name) { return name.toLowerCase(); }

function renderScene(scene) {
  currentScene = scene;
  clock.textContent = scene.time;
  caption.textContent = scene.story;
  background.src = `/assets/backgrounds/${scene.background}.png`;
  characters.replaceChildren();

  for (const character of scene.characters) {
    const img = document.createElement("img");
    img.className = `character ${character.position}`;
    img.dataset.name = character.name;
    img.alt = character.name;
    img.src = `/assets/characters/${assetName(character.name)}/${character.pose}.png`;
    characters.appendChild(img);
  }
  note.hidden = !scene.note;
  note.textContent = scene.note || "";
}

async function playSpeech(parts) {
  for (const part of parts || []) {
    const character = document.querySelector(`.character[data-name="${part.speaker}"]`);
    character?.classList.add("speaking");
    const audio = new Audio(part.audio);
    try {
      await audio.play();
      await new Promise(resolve => {
        audio.onended = resolve;
        audio.onerror = resolve;
      });
    } finally {
      character?.classList.remove("speaking");
    }
  }
}

async function requestScene(url, loadingText, autoplay=true) {
  buttons.forEach(b => b.disabled = true);
  caption.textContent = loadingText;
  try {
    const response = await fetch(url, {method: "POST"});
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.detail || response.statusText);
    }
    const scene = await response.json();
    renderScene(scene);
    if (autoplay) await playSpeech(scene.speech);
  } catch (error) {
    caption.textContent = currentScene?.story || ("Fehler: " + error.message);
  } finally {
    buttons.forEach(b => b.disabled = false);
  }
}

document.querySelector("#next").onclick = () =>
  requestScene("/api/next-scene", "Die nächste Szene entsteht …");

document.querySelector("#previous").onclick = () =>
  requestScene("/api/previous-scene", "Zurück …", false);

document.querySelector("#replay").onclick = async () => {
  if (!currentScene) return;
  await playSpeech(currentScene.speech);
};

document.querySelector("#regenerate").onclick = () =>
  requestScene("/api/regenerate-scene", "Die Szene wird neu erzählt …");
