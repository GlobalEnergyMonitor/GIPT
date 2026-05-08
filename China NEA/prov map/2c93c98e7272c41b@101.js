function _1(md){return(
md`# China’s solar PV capacity by province and installation type
`
)}

function _d3(require){return(
require("d3@7")
)}

function _settings(){return(
{
  width: 1000,      // overall SVG canvas width
  height: 900,      // overall SVG canvas height

  boxScale: 7.8,    // master size multiplier for all province rectangles
  aspectRatio: 1.8, // width / height for ALL rectangles; keeps them consistently wide

  xStep: 120,       // horizontal spacing between province anchor points
  yStep: 88,        // vertical spacing between province anchor points

  marginLeft: 30,   // pushes the whole schematic right
  marginTop: 24,    // pushes the whole schematic down

  labelOffset: 20,  // distance between the rectangle baseline and province label

  plotOffsetX: 0,
  plotOffsetY: -5,
  
  title: "China’s solar PV capacity by province and installation type",
  subtitle: "Schematic province boxes; rectangle area represents total PV capacity in gigawatts. Dark inset shows utility-scale PV, and the remaining area shows distributed PV.",
  footer: "Source: National Energy Administration. Province positions are schematic and do not represent exact geography.",

  colors: {
    utility: "#148f77",     // dark green inset = utility-scale PV
    distributed: "#bfe8df", // light fill = distributed PV (shown as the remainder)
    outline: "#9aa3af",     // dashed outline for total PV
    text: "#2f3440",        // province label color
    subtext: "#6b7280",     // subtitle 
    background: "#ffffff"   // chart background
  }
}
)}

function _pv(){return(
[
  {province: "Anhui", total: 56.255, utility: 16.596, distributed: 39.658, households: 18.129},
  {province: "Beijing", total: 2.102, utility: 0.081, distributed: 2.021, households: 0.730},
  {province: "Chongqing", total: 5.850, utility: 1.549, distributed: 4.301, households: 0.517},
  {province: "Fujian", total: 17.344, utility: 1.372, distributed: 15.972, households: 6.166},
  {province: "Gansu", total: 38.530, utility: 35.687, distributed: 2.843, households: 0.699},
  {province: "Guangdong", total: 62.480, utility: 16.089, distributed: 46.391, households: 8.501},
  {province: "Guangxi", total: 32.738, utility: 13.912, distributed: 18.826, households: 0.691},
  {province: "Guizhou", total: 28.719, utility: 25.739, distributed: 2.980, households: 1.830},
  {province: "Hainan", total: 9.601, utility: 5.983, distributed: 3.617, households: 0.340},
  {province: "Hebei", total: 84.629, utility: 48.732, distributed: 35.897, households: 23.360},
  {province: "Heilongjiang", total: 9.171, utility: 5.378, distributed: 3.793, households: 1.547},
  {province: "Henan", total: 55.658, utility: 6.775, distributed: 48.883, households: 28.977},
  {province: "Hubei", total: 44.845, utility: 22.282, distributed: 22.563, households: 4.967},
  {province: "Hunan", total: 27.439, utility: 7.135, distributed: 20.304, households: 12.006},
  {province: "Inner M.", total: 60.555, utility: 55.639, distributed: 4.916, households: 1.850},
  {province: "Jiangsu", total: 89.684, utility: 25.671, distributed: 64.013, households: 22.280},
  {province: "Jiangxi", total: 28.723, utility: 14.002, distributed: 14.721, households: 7.843},
  {province: "Jilin", total: 7.245, utility: 4.383, distributed: 2.862, households: 1.684},
  {province: "Liaoning", total: 15.546, utility: 6.091, distributed: 9.456, households: 6.834},
  {province: "Ningxia", total: 41.809, utility: 39.164, distributed: 2.645, households: 0.386},
  {province: "Qinghai", total: 42.576, utility: 42.092, distributed: 0.484, households: 0.073},
  {province: "Shaanxi", total: 41.930, utility: 28.173, distributed: 13.758, households: 6.402},
  {province: "Shandong", total: 94.849, utility: 34.160, distributed: 60.689, households: 29.403},
  {province: "Shanghai", total: 6.251, utility: 0.620, distributed: 5.632, households: 0.502},
  {province: "Shanxi", total: 49.505, utility: 34.364, distributed: 15.141, households: 7.767},
  {province: "Sichuan", total: 19.801, utility: 13.219, distributed: 6.582, households: 1.751},
  {province: "Tianjin", total: 10.279, utility: 4.740, distributed: 5.538, households: 0.753},
  {province: "Tibet", total: 5.745, utility: 5.685, distributed: 0.060, households: 0.000},
  {province: "Xinjiang", total: 90.901, utility: 90.501, distributed: 0.401, households: 0.080},
  {province: "Yunnan", total: 54.861, utility: 49.646, distributed: 5.214, households: 3.638},
  {province: "Zhejiang", total: 64.294, utility: 11.453, distributed: 52.841, households: 6.128}
]
)}

function _layout(){return(
[
  {province: "Heilongjiang", col: 6, row: 1},

  {province: "Inner M.", col: 5, row: 2},
  {province: "Jilin", col: 6, row: 2},

  {province: "Beijing", col: 5, row: 3},
  {province: "Liaoning", col: 6, row: 3},

  {province: "Xinjiang", col: 0, row: 4},
  {province: "Gansu", col: 1, row: 4},
  {province: "Shanxi", col: 3, row: 4},
  {province: "Hebei", col: 4, row: 4},
  {province: "Tianjin", col: 5, row: 4},

  {province: "Tibet", col: 0, row: 5},
  {province: "Qinghai", col: 1, row: 5},
  {province: "Ningxia", col: 2, row: 5},
  {province: "Shaanxi", col: 3, row: 5},
  {province: "Henan", col: 4, row: 5},
  {province: "Shandong", col: 5, row: 5},

  {province: "Sichuan", col: 1, row: 6},
  {province: "Chongqing", col: 2, row: 6},
  {province: "Hubei", col: 3, row: 6},
  {province: "Anhui", col: 4, row: 6},
  {province: "Jiangsu", col: 5, row: 6},
  {province: "Shanghai", col: 6, row: 6},

  {province: "Yunnan", col: 1, row: 7},
  {province: "Guizhou", col: 2, row: 7},
  {province: "Hunan", col: 3, row: 7},
  {province: "Jiangxi", col: 4, row: 7},
  {province: "Zhejiang", col: 5, row: 7},

  {province: "Guangxi", col: 3, row: 8},
  {province: "Guangdong", col: 4, row: 8},
  {province: "Fujian", col: 5, row: 8},

  {province: "Hainan", col: 3, row: 9}
]
)}

function _boxes(layout,pv,settings){return(
layout
  .map(d => {
    const v = pv.find(x => x.province === d.province);
    if (!v) return null;

    const k = settings.boxScale;
    const r = settings.aspectRatio;

    const totalWidth = k * Math.sqrt(v.total * r);
    const totalHeight = k * Math.sqrt(v.total / r);

    const utilityWidth = k * Math.sqrt(v.utility * r);
    const utilityHeight = k * Math.sqrt(v.utility / r);

    return {
      ...d,
      ...v,
      anchorX: d.col * settings.xStep,
      baselineY: d.row * settings.yStep,
      totalWidth,
      totalHeight,
      utilityWidth,
      utilityHeight
    };
  })
  .filter(d => d)
)}

function _chart(settings,d3,boxes)
{
const {
  width, height, marginLeft, marginTop,
  plotOffsetX, plotOffsetY, labelOffset,
  title, subtitle, footer,
  colors
} = settings;

  const svg = d3.create("svg")
    .attr("viewBox", [0, 0, width, height])
    .style("background", colors.background);

  // One master group so the entire map can be nudged with margins.
  const g = svg.append("g").attr("transform", `translate(${marginLeft + plotOffsetX},${marginTop + plotOffsetY})`);

  const p = g.selectAll("g.province")
    .data(boxes)
    .join("g")
    .attr("class", "province");

  // Draw total PV rectangle first.
  // Fill it with the distributed color so that the unoccupied remainder
  // around the utility inset reads visually as distributed PV.
  p.append("rect")
    .attr("x", d => d.anchorX)
    .attr("y", d => d.baselineY - d.totalHeight)// SVG uses top-left coordinates, so subtract height
    .attr("width", d => d.totalWidth)
    .attr("height", d => d.totalHeight)
    .attr("fill", colors.distributed)
    .attr("stroke", colors.outline)
    .attr("stroke-width", 1.2)
    .attr("stroke-dasharray", "4,3");

  // Draw utility inset on top.
  // Because both rectangles share the same bottom-left anchor,
  // the utility box grows from the same origin as the total box.
  p.append("rect")
    .attr("x", d => d.anchorX)
    .attr("y", d => d.baselineY - d.utilityHeight)
    .attr("width", d => d.utilityWidth)
    .attr("height", d => d.utilityHeight)
    .attr("fill", colors.utility);

  // province label
  p.append("text")
    .attr("x", d => d.anchorX)
    .attr("y", d => d.baselineY + labelOffset)
    .attr("fill", colors.text)
    .style("font", "19px sans-serif")
    .text(d => d.province);

    // title
  svg.append("text")
    .attr("x", marginLeft)
    .attr("y", marginTop + 22)
    .attr("fill", colors.text)
    .style("font", "700 24px sans-serif")
    .text(title);

// subtitle (wrapped to two lines)
const subtitleText = svg.append("text")
  .attr("x", marginLeft)
  .attr("y", marginTop + 48)
  .attr("fill", colors.subtext)
  .style("font", "15px sans-serif");

subtitleText.append("tspan")
  .attr("x", marginLeft)
  .attr("dy", 0)
  .text("Schematic province boxes, where scale represents gigawatts; rectangle area represents total PV capacity.");

subtitleText.append("tspan")
  .attr("x", marginLeft)
  .attr("dy", 18)
  .text("Dark inset shows utility-scale PV, and the remaining area shows distributed PV.");

  // lplotOffsetYegend
const legendX = marginLeft;
const legendY = marginTop + 88;

svg.append("rect")
  .attr("x", legendX)
  .attr("y", legendY)
  .attr("width", 64)
  .attr("height", 38)
  .attr("fill", colors.distributed)
  .attr("stroke", colors.outline)
  .attr("stroke-width", 1.3)
  .attr("stroke-dasharray", "4,3");

svg.append("rect")
  .attr("x", legendX)
  .attr("y", legendY + 12)
  .attr("width", 34)
  .attr("height", 26)
  .attr("fill", colors.utility);

svg.append("text")
  .attr("x", legendX + 78)
  .attr("y", legendY + 13)
  .attr("fill", colors.text)
  .style("font", "15px sans-serif")
  .text("Outer box = total PV");

svg.append("text")
  .attr("x", legendX + 78)
  .attr("y", legendY + 33)
  .attr("fill", colors.text)
  .style("font", "15px sans-serif")
  .text("Dark inset = utility-scale PV");

svg.append("text")
  .attr("x", legendX + 78)
  .attr("y", legendY + 53)
  .attr("fill", colors.text)
  .style("font", "15px sans-serif")
  .text("Remaining area = distributed PV");

  // footer
  svg.append("text")
    .attr("x", marginLeft)
    .attr("y", height - 30)
    .attr("fill", colors.subtext)
    .style("font", "13px sans-serif")
    .text(footer);
  
  return svg.node();
}


export default function define(runtime, observer) {
  const main = runtime.module();
  main.variable(observer()).define(["md"], _1);
  main.variable(observer("d3")).define("d3", ["require"], _d3);
  main.variable(observer("settings")).define("settings", _settings);
  main.variable(observer("pv")).define("pv", _pv);
  main.variable(observer("layout")).define("layout", _layout);
  main.variable(observer("boxes")).define("boxes", ["layout","pv","settings"], _boxes);
  main.variable(observer("chart")).define("chart", ["settings","d3","boxes"], _chart);
  return main;
}
