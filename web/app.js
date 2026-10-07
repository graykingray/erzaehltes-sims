const button = document.querySelector("#next");
const caption = document.querySelector("#caption");
const clock = document.querySelector("#clock");
const background = document.querySelector("#background");
const characters = document.querySelector("#characters");
const note = document.querySelector("#note");

function assetName(name) {
  return name.toLowerCase();
}

function renderScene(scene) {
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
  for (const part of parts) {
    const character = document.querySelector(
      `.character[data-name="${part.speaker}"]`
    );
    character?.classList.add("speaking");

    const audio = new Audio(part.audio);
    await audio.play();
    await new Promise(resolve => {
      audio.onended = resolve;
      audio.onerror = resolve;
    });

    character?.classList.remove("speaking");
  }
}

button.addEventListener("click", async () => {
  button.disabled = true;
  caption.textContent = "Die nächste Szene entsteht …";
  try {
    const response = await fetch("/api/next-scene", {method: "POST"});
    if (!response.ok) throw new Error(await response.text());
    const scene = await response.json();
    renderScene(scene);
    await playSpeech(scene.speech);
  } catch (error) {
    caption.textContent = "Fehler: " + error.message;
  } finally {
    button.disabled = false;
  }
});
