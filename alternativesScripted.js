document.getElementById("findAlternatives").addEventListener("click", function () {
  // Simulate finding eco-friendly alternatives
  let alternatives = `
    <div class="alternative">Eco-Friendly Shampoo - $10.99</div>
    <div class="alternative">Sustainable Toothbrush - $3.99</div>
    <div class="alternative">Biodegradable Soap - $2.99</div>
  `;
  document.getElementById("alternativesList").innerHTML = alternatives;
});
