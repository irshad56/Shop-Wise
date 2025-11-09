document.getElementById("compareButton").addEventListener("click", function () {
  // Simulate comparing products
  let comparisonData = `
    <table>
      <tr>
        <th>Product</th>
        <th>Price</th>
        <th>Sustainability Score</th>
      </tr>
      <tr>
        <td>Product A</td>
        <td>$15.99</td>
        <td>80%</td>
      </tr>
      <tr>
        <td>Product B</td>
        <td>$12.99</td>
        <td>85%</td>
      </tr>
      <tr>
        <td>Product C</td>
        <td>$14.99</td>
        <td>90%</td>
      </tr>
    </table>
  `;
  document.getElementById("comparisonTable").innerHTML = comparisonData;
});
