const { Resvg } = require("@resvg/resvg-js");
const fs = require("fs");

const svg = fs.readFileSync(process.argv[2]);
const width = Number(process.argv[4] || 480);
const resvg = new Resvg(svg, {
  fitTo: { mode: "width", value: width },
  background: "#0E1A2B",
});
fs.writeFileSync(process.argv[3], resvg.render().asPng());
