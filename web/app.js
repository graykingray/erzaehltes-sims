const button = document.querySelector("#next");
const caption = document.querySelector(".caption");

button.addEventListener("click", () => {
  caption.textContent =
    "Das Papiertheater funktioniert. Als Nächstes verbinden wir es mit den echten Szenen aus Python.";
});
