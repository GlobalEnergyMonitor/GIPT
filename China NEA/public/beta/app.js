const DATA_PATH = "../data/scraped_wide.csv";

const EXCLUDED_PROVINCE_ROWS = new Set([
  "Total",
  "Xinjiang (Including Corps)"
]);

const CATEGORY_MAP = {
  "Total": "Total",
  "Utility-scale": "Utility-scale",
  "Total distributed": "Total distributed",
  "Households": "Households"
};

const GEM_PALETTE = {
  deepBlue: "#173f67",
  midBlue: "#4d8fba",
  darkGreen: "#148f77",
  mint: "#bfe8df",
  paleMint: "#e1f3ee",
  yellow: "#f2c14e",
  orange: "#e67e22",
  red: "#b8463f",
  grey: "#667085",
  lightGrey: "#d8d8d8"
};

const COLORS = {
  utility: GEM_PALETTE.darkGreen,
  nonHousehold: GEM_PALETTE.mint,
  household: GEM_PALETTE.yellow,
  distributed: GEM_PALETTE.mint,
  distributedUnsplit: "#7ecfbd",
  total: GEM_PALETTE.deepBlue,

  utilityShareVeryLow: GEM_PALETTE.paleMint,
  utilityShareLow: GEM_PALETTE.mint,
  utilityShareMidLow: "#7ecfbd",
  utilityShareMid: GEM_PALETTE.darkGreen,
  utilityShareMidHigh: GEM_PALETTE.midBlue,
  utilityShareHigh: GEM_PALETTE.deepBlue
};

const UTILITY_SHARE_SEGMENTED_COLORSCALE = [
  [0.000, COLORS.utilityShareVeryLow],
  [0.166, COLORS.utilityShareVeryLow],
  [0.167, COLORS.utilityShareLow],
  [0.333, COLORS.utilityShareLow],
  [0.334, COLORS.utilityShareMidLow],
  [0.500, COLORS.utilityShareMidLow],
  [0.501, COLORS.utilityShareMid],
  [0.666, COLORS.utilityShareMid],
  [0.667, COLORS.utilityShareMidHigh],
  [0.833, COLORS.utilityShareMidHigh],
  [0.834, COLORS.utilityShareHigh],
  [1.00, COLORS.utilityShareHigh]
];

const MAP_LAYOUT = [
  { area: "Heilongjiang", label: "Heilongjiang", col: 6, row: 1 },
  { area: "Inner Mongolia", label: "Inner M.", col: 5, row: 2 },
  { area: "Jilin", label: "Jilin", col: 6, row: 2 },
  { area: "Beijing", label: "Beijing", col: 5, row: 3 },
  { area: "Liaoning", label: "Liaoning", col: 6, row: 3 },
  { area: "Xinjiang", label: "Xinjiang", col: 0, row: 4 },
  { area: "Gansu", label: "Gansu", col: 1, row: 4 },
  { area: "Shanxi", label: "Shanxi", col: 3, row: 4 },
  { area: "Hebei", label: "Hebei", col: 4, row: 4 },
  { area: "Tianjin", label: "Tianjin", col: 5, row: 4 },
  { area: "Tibet", label: "Tibet", col: 0, row: 5 },
  { area: "Qinghai", label: "Qinghai", col: 1, row: 5 },
  { area: "Ningxia", label: "Ningxia", col: 2, row: 5 },
  { area: "Shaanxi", label: "Shaanxi", col: 3, row: 5 },
  { area: "Henan", label: "Henan", col: 4, row: 5 },
  { area: "Shandong", label: "Shandong", col: 5, row: 5 },
  { area: "Sichuan", label: "Sichuan", col: 1, row: 6 },
  { area: "Chongqing", label: "Chongqing", col: 2, row: 6 },
  { area: "Hubei", label: "Hubei", col: 3, row: 6 },
  { area: "Anhui", label: "Anhui", col: 4, row: 6 },
  { area: "Jiangsu", label: "Jiangsu", col: 5, row: 6 },
  { area: "Shanghai", label: "Shanghai", col: 6, row: 6 },
  { area: "Yunnan", label: "Yunnan", col: 1, row: 7 },
  { area: "Guizhou", label: "Guizhou", col: 2, row: 7 },
  { area: "Hunan", label: "Hunan", col: 3, row: 7 },
  { area: "Jiangxi", label: "Jiangxi", col: 4, row: 7 },
  { area: "Zhejiang", label: "Zhejiang", col: 5, row: 7 },
  { area: "Guangxi", label: "Guangxi", col: 3, row: 8 },
  { area: "Guangdong", label: "Guangdong", col: 4, row: 8 },
  { area: "Fujian", label: "Fujian", col: 5, row: 8 },
  { area: "Hainan", label: "Hainan", col: 3, row: 9 }
];

const MAP_SETTINGS = {
  width: 1000,
  height: 820,
  boxScale: 7.8,
  aspectRatio: 1.8,
  xStep: 120,
  yStep: 80,
  marginLeft: 30,
  marginTop: 6,
  labelOffset: 17,
  plotOffsetX: 0,
  plotOffsetY: -10,
  colors: {
    utility: COLORS.utility,
    distributed: COLORS.distributed,
    outline: "#9aa3af",
    text: "#2f3440",
    subtext: COLORS.grey,
    background: "#ffffff"
  }
};

const fmtGW = value => `${Number(value).toLocaleString(undefined, {
  maximumFractionDigits: 1
})} GW`;

const fmtPct = value => `${Number(value).toFixed(1)}%`;

const parseValue = value => {
  if (value === null || value === undefined) return null;
  const cleaned = String(value).replace(/,/g, "").trim();
  if (cleaned === "" || cleaned.toLowerCase() === "nan") return null;
  const n = Number(cleaned);
  return Number.isFinite(n) ? n : null;
};

const parseTimeLabel = col => `${col.slice(0, 4)}-${col.slice(4, 6)}`;

const getYear = col => Number(col.slice(0, 4));

const isYearEnd = col => col.endsWith("12");

let columnChartPeriodMode = "annual";
let columnChartContext = null;
let scatterProfileContext = null;
let scatterAnimationTimer = null;

Papa.parse(DATA_PATH, {
  download: true,
  header: true,
  skipEmptyLines: true,
  complete: results => {
    try {
      initialise(results.data);
    } catch (err) {
      console.error(err);
      document.querySelector("#data-status").textContent = "Error processing CSV";
    }
  },
  error: err => {
    console.error(err);
    document.querySelector("#data-status").textContent = "Could not load CSV";
  }
});

function initialise(rawRows) {
  const rows = rawRows
    .filter(row => row.Area && row.Category)
    .map(row => ({
      ...row,
      Area: row.Area.trim(),
      Category: CATEGORY_MAP[row.Category.trim()] || row.Category.trim()
    }));

  const timeCols = Object.keys(rows[0])
    .filter(col => /^\d{6}$/.test(col))
    .sort();

  const nationalTotalRow = rows.find(
    row => row.Area === "Total" && row.Category === "Total"
  );

  if (!nationalTotalRow) {
    throw new Error("Could not find national Total row.");
  }

  const availableTimeCols = timeCols.filter(col => parseValue(nationalTotalRow[col]) !== null);
  const annualCols = availableTimeCols.filter(isYearEnd);

  const latestCol = annualCols[annualCols.length - 1];
  const latestAvailableCol = availableTimeCols[availableTimeCols.length - 1];
  const startCol = annualCols[0];
  const baselineCol = annualCols.includes("202212") ? "202212" : annualCols[annualCols.length - 4];

  const lookup = buildLookup(rows);
  const national = makeAreaSeries("Total", annualCols, lookup);
  const provinces = getProvinceNames(rows);

  const latestProvinceRows = provinces
    .map(area => makeLatestProvinceRecord(area, latestCol, lookup))
    .filter(d => d.total !== null && d.total > 0)
    .sort((a, b) => b.total - a.total);

  const growthProvinceRows = provinces
    .map(area => makeGrowthRecord(area, baselineCol, latestCol, lookup))
    .filter(d => d.totalGrowth !== null)
    .sort((a, b) => b.totalGrowth - a.totalGrowth);

  updateStatus(rows, provinces, startCol, latestAvailableCol);
  renderStats(national, startCol, latestCol);
  renderBullets(national, latestProvinceRows, growthProvinceRows, baselineCol, latestCol);
  renderD3ProvinceMap(lookup, availableTimeCols, latestAvailableCol);
  renderCharts(
    national,
    latestProvinceRows,
    growthProvinceRows,
    lookup,
    annualCols,
    availableTimeCols,
    provinces
  );
  renderTables(
    latestProvinceRows,
    growthProvinceRows,
    national[national.length - 1].total,
    baselineCol,
    latestCol
  );
}

function buildLookup(rows) {
  const map = new Map();

  for (const row of rows) {
    map.set(`${row.Area}||${row.Category}`, row);
  }

  return map;
}

function getValue(area, category, col, lookup) {
  const row = lookup.get(`${area}||${category}`);
  return row ? parseValue(row[col]) : null;
}

function derivedNonHousehold(area, col, lookup) {
  const distributed = getValue(area, "Total distributed", col, lookup);
  const household = getValue(area, "Households", col, lookup);

  return splitDistributedCapacity(distributed, household).nonHousehold;
}

function splitDistributedCapacity(distributed, household) {
  if (distributed === null) {
    return {
      nonHousehold: null,
      distributedUnsplit: null,
      hasHouseholdBreakout: false
    };
  }

  if (household === null) {
    return {
      nonHousehold: null,
      distributedUnsplit: distributed,
      hasHouseholdBreakout: false
    };
  }

  return {
    nonHousehold: Math.max(0, distributed - household),
    distributedUnsplit: null,
    hasHouseholdBreakout: true
  };
}

function makeAreaSeries(area, cols, lookup) {
  return cols.map(col => {
    const total = getValue(area, "Total", col, lookup);
    const utility = getValue(area, "Utility-scale", col, lookup);
    const distributed = getValue(area, "Total distributed", col, lookup);
    const household = getValue(area, "Households", col, lookup);
    const distributedSplit = splitDistributedCapacity(distributed, household);

    return {
      col,
      year: getYear(col),
      label: parseTimeLabel(col),
      total,
      utility,
      distributed,
      household,
      nonHousehold: distributedSplit.nonHousehold,
      distributedUnsplit: distributedSplit.distributedUnsplit,
      hasHouseholdBreakout: distributedSplit.hasHouseholdBreakout
    };
  });
}

function getProvinceNames(rows) {
  return [...new Set(rows.map(row => row.Area))]
    .filter(area => !EXCLUDED_PROVINCE_ROWS.has(area))
    .sort();
}

function makeLatestProvinceRecord(area, latestCol, lookup) {
  const total = getValue(area, "Total", latestCol, lookup);
  const utility = getValue(area, "Utility-scale", latestCol, lookup);
  const distributed = getValue(area, "Total distributed", latestCol, lookup);
  const household = getValue(area, "Households", latestCol, lookup);
  const nonHousehold = derivedNonHousehold(area, latestCol, lookup);

  return {
    area,
    total,
    utility,
    distributed,
    household,
    nonHousehold,
    utilityShare: total && utility !== null ? utility / total : null,
    distributedShare: total && distributed !== null ? distributed / total : null,
    householdShareTotal: total && household !== null ? household / total : null,
    householdShareDistributed: distributed && household !== null ? household / distributed : null
  };
}

function makeGrowthRecord(area, startCol, endCol, lookup) {
  const startTotal = getValue(area, "Total", startCol, lookup);
  const endTotal = getValue(area, "Total", endCol, lookup);

  const startUtility = getValue(area, "Utility-scale", startCol, lookup);
  const endUtility = getValue(area, "Utility-scale", endCol, lookup);

  const startDistributed = getValue(area, "Total distributed", startCol, lookup);
  const endDistributed = getValue(area, "Total distributed", endCol, lookup);

  const startHousehold = getValue(area, "Households", startCol, lookup);
  const endHousehold = getValue(area, "Households", endCol, lookup);

  return {
    area,
    totalGrowth: diff(startTotal, endTotal),
    utilityGrowth: diff(startUtility, endUtility),
    distributedGrowth: diff(startDistributed, endDistributed),
    householdGrowth: diff(startHousehold, endHousehold)
  };
}

function diff(a, b) {
  if (a === null || b === null) return null;
  return b - a;
}

function safeChange(current, previous) {
  if (current === null || previous === null) return null;
  return current - previous;
}

function updateStatus(rows, provinces, startCol, latestCol) {
  document.querySelector("#data-status").textContent =
    `${rows.length} rows | ${provinces.length} province-level areas | ${parseTimeLabel(startCol)} to ${parseTimeLabel(latestCol)}`;
}

function renderStats(national, startCol, latestCol) {
  const first = national[0];
  const latest = national[national.length - 1];
  const prev = national[national.length - 2];

  const addition = latest.total - prev.total;
  const multiple = latest.total / first.total;

  document.querySelector("#stat-total").textContent = fmtGW(latest.total);
  document.querySelector("#stat-total-note").textContent =
    `${multiple.toFixed(1)}x end-${first.year} capacity`;

  document.querySelector("#stat-addition").textContent = `+${fmtGW(addition)}`;

  document.querySelector("#stat-distributed-share").textContent =
    fmtPct(100 * latest.distributed / latest.total);

  document.querySelector("#stat-household").textContent = fmtGW(latest.household);
}

function renderBullets(national, latestProvinceRows, growthProvinceRows, baselineCol, latestCol) {
  const bullets = [
    `<strong>China's solar PV buildout remains at record scale, even though the pace of acceleration has moderated.</strong> National additions rose from +216.9 GW in 2023 to +276.8 GW in 2024 and +314.2 GW in 2025, but the year-on-year increase in additions slowed from +130.8 GW to +59.9 GW and then +37.5 GW. Even so, the scale is extraordinary: China added more PV in 2025 alone than the country's entire installed solar fleet at end-2020 (253.2 GW).`,

    `<strong>Distributed PV has become a central growth driver.</strong> Distributed capacity rose from 10.3 GW in 2016 to 533.0 GW in 2025, lifting its share of national PV from 13.3% to 44.4%. In 2025, distributed additions slightly exceeded utility-scale additions: +158.2 GW versus +156.0 GW.`,

    `<strong>Households are substantial, but non-household systems are the larger distributed segment.</strong> At end-2025, household PV reached 205.8 GW, or 38.6% of distributed PV. Distributed non-household capacity was larger, at 327.2 GW.`,

    `<strong>Provincial growth now follows two main models: inland utility-scale expansion and eastern/central distributed rollout.</strong> At end-2025, large fleets included utility-dominated Xinjiang (90.9 GW) and distributed-heavy Shandong (94.8 GW), Jiangsu (89.7 GW), and Zhejiang (64.3 GW). Recent growth shows the same split, with utility-led increases in Xinjiang and Yunnan, and distributed-heavy growth in Jiangsu, Shandong, and Guangdong.`,

    `<strong>Several central and coastal provinces are now strongly distributed-led.</strong> In Henan, distributed PV reached 48.9 GW out of 55.7 GW total by end-2025. From end-2022 to end-2025, Henan added +31.8 GW of distributed PV versus only +0.5 GW of utility-scale capacity; similar patterns appear in Zhejiang, Guangdong, Anhui, and Jiangsu.`
  ];

  document.querySelector("#analysis-bullets").innerHTML = bullets
    .map(text => `<div class="bullet"><p>${text}</p></div>`)
    .join("");
}

function renderD3ProvinceMap(lookup, timeCols, latestCol) {
  if (!window.d3) {
    document.querySelector("#map-period-note").textContent = "D3 did not load.";
    return;
  }

  const slider = document.querySelector("#map-time-slider");
  const periodLabel = document.querySelector("#map-period-label");
  const periodNote = document.querySelector("#map-period-note");
  const container = d3.select("#d3-province-map");

  const settings = MAP_SETTINGS;
  const { width, height, marginLeft, marginTop, plotOffsetX, plotOffsetY, labelOffset, colors } = settings;

  container.selectAll("*").remove();

  const svg = container
    .append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("role", "img")
    .attr("aria-label", "Schematic map of China provincial solar PV capacity")
    .style("background", colors.background);

  svg.append("text")
    .attr("class", "map-svg-title")
    .attr("x", marginLeft)
    .attr("y", marginTop + 22)
    .attr("fill", colors.text)
    .style("font", "800 24px 'Plus Jakarta Sans', sans-serif");
    //.text("China's solar PV capacity by province and installation type");

  svg.append("text")
    .attr("class", "map-svg-period")
    .attr("x", marginLeft)
    .attr("y", marginTop + 34)
    .attr("fill", colors.subtext)
    .style("font", "700 15px 'Plus Jakarta Sans', sans-serif");

  const subtitleText = svg.append("text")
    .attr("x", marginLeft)
    .attr("y", marginTop + 58)
    .attr("fill", colors.subtext)
    .style("font", "15px 'Plus Jakarta Sans', sans-serif");

  subtitleText.append("tspan")
    .attr("x", marginLeft)
    .attr("dy", 0)
    .text("Schematic province boxes, where rectangle area represents total PV capacity in gigawatts.");

  subtitleText.append("tspan")
    .attr("x", marginLeft)
    .attr("dy", 18)
    .text("Dark inset shows utility-scale PV, and the remaining area shows distributed PV.");

  drawMapLegend(svg, settings);

  const mapGroup = svg.append("g")
    .attr("transform", `translate(${marginLeft + plotOffsetX},${marginTop + plotOffsetY})`);

  svg.append("text")
    .attr("x", marginLeft)
    .attr("y", height - 30)
    .attr("fill", colors.subtext)
    .style("font", "13px 'Plus Jakarta Sans', sans-serif")
    .text("Source: National Energy Administration. Province positions are schematic and do not represent exact geography.");

  slider.min = 0;
  slider.max = timeCols.length - 1;
  slider.step = 1;
  slider.value = Math.max(0, timeCols.indexOf(latestCol));

  document.querySelector("#map-slider-start").textContent = parseTimeLabel(timeCols[0]);
  document.querySelector("#map-slider-end").textContent = parseTimeLabel(timeCols[timeCols.length - 1]);

  const update = index => {
    const col = timeCols[index];
    const boxes = makeMapBoxes(col, lookup, settings);
    const missingCount = MAP_LAYOUT.length - boxes.length;

    periodLabel.textContent = parseTimeLabel(col);
    periodNote.textContent = missingCount
      ? `${missingCount} province box${missingCount === 1 ? "" : "es"} hidden because values are missing or zero for this period.`
      : "All mapped provinces have positive values for this period.";

    svg.select(".map-svg-period")
      .text(`Selected period: ${parseTimeLabel(col)}`);

    const province = mapGroup
      .selectAll("g.province")
      .data(boxes, d => d.area);

    province.exit()
      .transition()
      .duration(120)
      .style("opacity", 0)
      .remove();

    const provinceEnter = province.enter()
      .append("g")
      .attr("class", "province")
      .style("opacity", 0);

    provinceEnter.append("rect")
      .attr("class", "total-box")
      .attr("fill", colors.distributed)
      .attr("stroke", colors.outline)
      .attr("stroke-width", 1.2)
      .attr("stroke-dasharray", "4,3");

    provinceEnter.append("rect")
      .attr("class", "utility-box")
      .attr("fill", colors.utility);

    provinceEnter.append("text")
      .attr("class", "province-label")
      .attr("fill", colors.text)
      .style("font", "700 16px 'Plus Jakarta Sans', sans-serif")
      .text(d => d.label);

    provinceEnter.append("title");

    const provinceMerged = provinceEnter.merge(province);

    provinceMerged.transition()
      .duration(120)
      .style("opacity", 1);

    provinceMerged.select("rect.total-box")
      .transition()
      .duration(120)
      .attr("x", d => d.anchorX)
      .attr("y", d => d.baselineY - d.totalHeight)
      .attr("width", d => d.totalWidth)
      .attr("height", d => d.totalHeight);

    provinceMerged.select("rect.utility-box")
      .transition()
      .duration(120)
      .attr("x", d => d.anchorX)
      .attr("y", d => d.baselineY - d.utilityHeight)
      .attr("width", d => d.utilityWidth)
      .attr("height", d => d.utilityHeight);

    provinceMerged.select("text.province-label")
      .transition()
      .duration(120)
      .attr("x", d => d.anchorX)
      .attr("y", d => d.baselineY + labelOffset);

    provinceMerged.select("title")
      .text(d => [
        `${d.area} - ${parseTimeLabel(col)}`,
        `Total: ${fmtGW(d.total)}`,
        `Utility-scale: ${fmtGW(d.utility)} (${fmtPct(100 * d.utility / d.total)})`,
        `Distributed: ${fmtGW(d.distributed)} (${fmtPct(100 * d.distributed / d.total)})`
      ].join("\n"));
  };

  slider.addEventListener("input", event => {
    update(Number(event.target.value));
  });

  update(Number(slider.value));
}

function drawMapLegend(svg, settings) {
  const { marginLeft, marginTop, colors } = settings;
  const legendX = marginLeft;
  const legendY = marginTop + 92;

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
    .style("font", "15px 'Plus Jakarta Sans', sans-serif")
    .text("Outer box = total PV");

  svg.append("text")
    .attr("x", legendX + 78)
    .attr("y", legendY + 33)
    .attr("fill", colors.text)
    .style("font", "15px 'Plus Jakarta Sans', sans-serif")
    .text("Dark inset = utility-scale PV");

  svg.append("text")
    .attr("x", legendX + 78)
    .attr("y", legendY + 53)
    .attr("fill", colors.text)
    .style("font", "15px 'Plus Jakarta Sans', sans-serif")
    .text("Remaining area = distributed PV");
}

function makeMapBoxes(col, lookup, settings) {
  const k = settings.boxScale;
  const r = settings.aspectRatio;

  return MAP_LAYOUT
    .map(d => {
      const total = getValue(d.area, "Total", col, lookup);
      const utilityRaw = getValue(d.area, "Utility-scale", col, lookup);
      const distributedRaw = getValue(d.area, "Total distributed", col, lookup);

      if (total === null || utilityRaw === null || distributedRaw === null || total <= 0) {
        return null;
      }

      const utility = Math.max(0, Math.min(utilityRaw, total));
      const distributed = Math.max(0, distributedRaw);

      const totalWidth = k * Math.sqrt(total * r);
      const totalHeight = k * Math.sqrt(total / r);
      const utilityWidth = k * Math.sqrt(utility * r);
      const utilityHeight = k * Math.sqrt(utility / r);

      return {
        ...d,
        total,
        utility,
        distributed,
        anchorX: d.col * settings.xStep,
        baselineY: d.row * settings.yStep,
        totalWidth,
        totalHeight,
        utilityWidth,
        utilityHeight
      };
    })
    .filter(Boolean);
}

function renderCharts(national, latestProvinceRows, growthProvinceRows, lookup, annualCols, availableTimeCols, provinces) {
  columnChartContext = {
    lookup,
    annualCols,
    availableTimeCols,
    provinces
  };

  setupColumnChartPeriodToggle();
  setupAreaSelect("#area-stack-select", provinces, renderColumnCharts);
  setupAreaSelect("#area-additions-select", provinces, renderColumnCharts);
  renderColumnCharts();
  renderProvinceMix(latestProvinceRows);
  setupScatterTimeline(lookup, availableTimeCols, provinces);
}

function setupAreaSelect(selector, provinces, onChange) {
  const select = document.querySelector(selector);
  if (!select) return;

  const areas = ["Total", ...provinces];
  select.innerHTML = areas
    .map(area => `<option value="${area}">${area}</option>`)
    .join("");

  select.addEventListener("change", onChange);
  select.value = "Total";
}

function setupColumnChartPeriodToggle() {
  const buttons = [...document.querySelectorAll("[data-chart-period]")];
  if (!buttons.length) return;

  const syncButtons = () => {
    buttons.forEach(button => {
      button.classList.toggle("is-active", button.dataset.chartPeriod === columnChartPeriodMode);
    });
  };

  buttons.forEach(button => {
    button.addEventListener("click", () => {
      columnChartPeriodMode = button.dataset.chartPeriod;
      syncButtons();
      renderColumnCharts();
    });
  });

  syncButtons();
}

function activeColumnChartCols() {
  if (!columnChartContext) return [];
  return columnChartPeriodMode === "quarterly"
    ? columnChartContext.availableTimeCols
    : columnChartContext.annualCols;
}

function renderColumnCharts() {
  if (!columnChartContext) return;

  const cols = activeColumnChartCols();
  const stackArea = document.querySelector("#area-stack-select")?.value || "Total";
  const additionsArea = document.querySelector("#area-additions-select")?.value || "Total";

  renderNationalStack(
    makeAreaSeries(stackArea, cols, columnChartContext.lookup),
    stackArea,
    columnChartPeriodMode
  );
  renderAnnualAdditions(
    makeAreaSeries(additionsArea, cols, columnChartContext.lookup),
    additionsArea,
    columnChartPeriodMode
  );
}

function baseLayout(extra = {}) {
  return {
    font: {
      family: "Plus Jakarta Sans, sans-serif",
      size: 12,
      color: "#1f2933"
    },
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    margin: { l: 54, r: 24, t: 20, b: 54 },
    legend: {
      orientation: "h",
      y: -0.18
    },
    hovermode: "closest",
    ...extra
  };
}

function baseConfig() {
  return {
    responsive: true,
    displayModeBar: false
  };
}

function renderNationalStack(national, area = "Total", periodMode = "annual") {
  const x = national.map(d => periodMode === "quarterly" ? parseTimeLabel(d.col) : String(d.year));

  const traces = [
    {
      x,
      y: national.map(d => d.utility),
      name: "Utility-scale",
      type: "bar",
      marker: { color: COLORS.utility }
    },
    {
      x,
      y: national.map(d => d.distributedUnsplit),
      name: "Distributed total",
      type: "bar",
      marker: { color: COLORS.distributedUnsplit },
      hovertemplate: "%{x}<br>%{y:.1f} GW<br>Household split unavailable<extra></extra>"
    },
    {
      x,
      y: national.map(d => d.nonHousehold),
      name: "Distributed non-household",
      type: "bar",
      marker: { color: COLORS.nonHousehold }
    },
    {
      x,
      y: national.map(d => d.household),
      name: "Households",
      type: "bar",
      marker: { color: COLORS.household }
    }
  ];

  Plotly.newPlot("chart-national-stack", traces, baseLayout({
    barmode: "stack",
    title: {
      text: area,
      x: 0,
      xanchor: "left",
      font: {
        size: 14
      }
    },
    yaxis: {
      title: "GW",
      gridcolor: "#ebe8df",
      zerolinecolor: "#cfcabe"
    },
    xaxis: {
      title: "",
      tickangle: 0
    }
  }), baseConfig());
}

function renderAnnualAdditions(national, area = "Total", periodMode = "annual") {
  const additions = national.slice(1).map((d, i) => {
    const prev = national[i];
    const bothHaveHouseholdBreakout = d.hasHouseholdBreakout && prev.hasHouseholdBreakout;

    return {
      col: d.col,
      year: d.year,
      utility: safeChange(d.utility, prev.utility),
      distributedUnsplit: bothHaveHouseholdBreakout ? null : safeChange(d.distributed, prev.distributed),
      nonHousehold: bothHaveHouseholdBreakout ? safeChange(d.nonHousehold, prev.nonHousehold) : null,
      household: bothHaveHouseholdBreakout ? safeChange(d.household, prev.household) : null,
      total: safeChange(d.total, prev.total)
    };
  });

  const x = additions.map(d => periodMode === "quarterly" ? parseTimeLabel(d.col) : String(d.year));

  const traces = [
    {
      x,
      y: additions.map(d => d.utility),
      name: "Utility-scale",
      type: "bar",
      marker: { color: COLORS.utility }
    },
    {
      x,
      y: additions.map(d => d.distributedUnsplit),
      name: "Distributed total",
      type: "bar",
      marker: { color: COLORS.distributedUnsplit },
      hovertemplate: "%{x}<br>%{y:.1f} GW added<br>Household split unavailable<extra></extra>"
    },
    {
      x,
      y: additions.map(d => d.nonHousehold),
      name: "Distributed non-household",
      type: "bar",
      marker: { color: COLORS.nonHousehold }
    },
    {
      x,
      y: additions.map(d => d.household),
      name: "Households",
      type: "bar",
      marker: { color: COLORS.household }
    }
  ];

  Plotly.newPlot("chart-additions", traces, baseLayout({
    barmode: "stack",
    title: {
      text: area,
      x: 0,
      xanchor: "left",
      font: {
        size: 13
      }
    },
    yaxis: {
      title: "GW added",
      gridcolor: "#ebe8df",
      zerolinecolor: "#cfcabe"
    },
    xaxis: { title: "" },
    margin: { l: 48, r: 12, t: 10, b: 50 }
  }), baseConfig());
}

function renderProvinceMix(latestProvinceRows) {
  const top = latestProvinceRows.slice(0, 10).reverse();
  const y = top.map(d => d.area);

  const traces = [
    {
      y,
      x: top.map(d => d.utility),
      name: "Utility-scale",
      type: "bar",
      orientation: "h",
      marker: { color: COLORS.utility }
    },
    {
      y,
      x: top.map(d => d.nonHousehold),
      name: "Distributed non-household",
      type: "bar",
      orientation: "h",
      marker: { color: COLORS.nonHousehold }
    },
    {
      y,
      x: top.map(d => d.household),
      name: "Households",
      type: "bar",
      orientation: "h",
      marker: { color: COLORS.household }
    }
  ];

  Plotly.newPlot("chart-province-mix", traces, baseLayout({
    barmode: "stack",
    xaxis: {
      title: "GW",
      gridcolor: "#ebe8df",
      zerolinecolor: "#cfcabe"
    },
    yaxis: { automargin: true },
    margin: { l: 104, r: 12, t: 10, b: 50 }
  }), baseConfig());
}

function setupScatterTimeline(lookup, timeCols, provinces) {
  stopScatterAnimation();

  const slider = document.querySelector("#scatter-time-slider");
  const startLabel = document.querySelector("#scatter-slider-start");
  const endLabel = document.querySelector("#scatter-slider-end");
  const playButton = document.querySelector("#scatter-play-button");
  if (!slider || !timeCols.length) return;

  scatterProfileContext = {
    lookup,
    timeCols,
    provinces,
    maxTotal: maxProvinceTotal(provinces, timeCols, lookup)
  };

  slider.min = 0;
  slider.max = timeCols.length - 1;
  slider.step = 1;
  slider.value = timeCols.length - 1;

  if (startLabel) startLabel.textContent = parseTimeLabel(timeCols[0]);
  if (endLabel) endLabel.textContent = parseTimeLabel(timeCols[timeCols.length - 1]);

  slider.oninput = event => {
    stopScatterAnimation();
    updateScatterProfile(Number(event.target.value));
  };

  if (playButton) {
    playButton.onclick = () => {
      if (scatterAnimationTimer) {
        stopScatterAnimation();
      } else {
        startScatterAnimation();
      }
    };
  }

  updateScatterProfile(Number(slider.value), false);
}

function maxProvinceTotal(provinces, timeCols, lookup) {
  return Math.max(
    1,
    ...provinces.flatMap(area =>
      timeCols.map(col => getValue(area, "Total", col, lookup) || 0)
    )
  );
}

function startScatterAnimation() {
  if (!scatterProfileContext || scatterAnimationTimer) return;

  setScatterPlayState(true);
  scatterAnimationTimer = window.setInterval(() => {
    const slider = document.querySelector("#scatter-time-slider");
    if (!slider) {
      stopScatterAnimation();
      return;
    }

    const next = Number(slider.value) >= Number(slider.max)
      ? 0
      : Number(slider.value) + 1;

    slider.value = next;
    updateScatterProfile(next);
  }, 900);
}

function stopScatterAnimation() {
  if (scatterAnimationTimer) {
    window.clearInterval(scatterAnimationTimer);
    scatterAnimationTimer = null;
  }
  setScatterPlayState(false);
}

function setScatterPlayState(isPlaying) {
  const playButton = document.querySelector("#scatter-play-button");
  if (!playButton) return;

  playButton.textContent = isPlaying ? "Pause" : "Play";
  playButton.classList.toggle("is-active", isPlaying);
}

function updateScatterProfile(index, animate = true) {
  if (!scatterProfileContext) return;

  const { lookup, timeCols, provinces } = scatterProfileContext;
  const clampedIndex = Math.max(0, Math.min(index, timeCols.length - 1));
  const col = timeCols[clampedIndex];
  const previousCol = clampedIndex > 0 ? timeCols[clampedIndex - 1] : null;
  const data = makeScatterProfileRows(col, previousCol, lookup, provinces);

  const periodLabel = document.querySelector("#scatter-period-label");
  if (periodLabel) periodLabel.textContent = parseTimeLabel(col);

  const periodNote = document.querySelector("#scatter-period-note");
  if (periodNote) {
    const growthText = previousCol
      ? `growth since ${parseTimeLabel(previousCol)}`
      : "initial observed capacity";
    periodNote.textContent = `${data.length} provinces shown; bubble size shows ${growthText}.`;
  }

  renderScatter(data, col, previousCol, animate);
}

function makeScatterProfileRows(col, previousCol, lookup, provinces) {
  return provinces
    .map(area => {
      const record = makeLatestProvinceRecord(area, col, lookup);
      const previous = previousCol ? makeLatestProvinceRecord(area, previousCol, lookup) : null;
      return {
        ...record,
        growth: previous ? safeChange(record.total, previous.total) : record.total
      };
    })
    .filter(d => d.total > 0 && d.distributedShare !== null && d.utilityShare !== null);
}

function fmtHoverGW(value) {
  return value === null || value === undefined || Number.isNaN(value)
    ? "n/a"
    : `${Number(value).toFixed(1)} GW`;
}

function fmtHoverPct(value) {
  return value === null || value === undefined || Number.isNaN(value)
    ? "n/a"
    : `${Number(value).toFixed(1)}%`;
}

function renderScatter(data, col, previousCol, animate = true) {
  const growthLabel = previousCol
    ? `Growth since ${parseTimeLabel(previousCol)}`
    : "Initial observed capacity";
  const trace = {
    x: data.map(d => d.total),
    y: data.map(d => 100 * d.distributedShare),
    text: data.map(d => d.area),
    customdata: data.map(d => [
      fmtHoverGW(d.utility),
      fmtHoverGW(d.distributed),
      fmtHoverGW(d.household),
      fmtHoverGW(d.growth),
      fmtHoverPct(100 * d.utilityShare),
      parseTimeLabel(col),
      growthLabel
    ]),
    mode: "markers+text",
    type: "scatter",
    textposition: "top center",
    textfont: {
      size: 10,
      color: "#1f2933"
    },
    marker: {
      size: data.map(d => Math.max(9, Math.sqrt(Math.max(d.growth || 0, 0.15)) * 4.2)),
      color: data.map(d => d.utilityShare),
      cmin: 0,
      cmax: 1,
      colorscale: UTILITY_SHARE_SEGMENTED_COLORSCALE,
      showscale: true,
      opacity: 0.86,
      line: {
        width: 1,
        color: "#ffffff"
      },
      colorbar: {
        title: {
          text: "Utility<br>share",
          side: "right"
        },
        tickmode: "array",
        tickvals: [0.083, 0.25, 0.417, 0.583, 0.75, 0.917],
        ticktext: ["0-17%", "17-33%", "33-50%", "50-67%", "67-83%", "83-100%"],
        thickness: 18,
        len: 0.78,
        outlinewidth: 0
      }
    },
    hovertemplate:
      "<b>%{text}</b><br>" +
      "Period: %{customdata[5]}<br>" +
      "Total: %{x:.1f} GW<br>" +
      "Distributed share: %{y:.1f}%<br>" +
      "Utility share: %{customdata[4]}<br>" +
      "Utility-scale: %{customdata[0]}<br>" +
      "Distributed: %{customdata[1]}<br>" +
      "Households: %{customdata[2]}<br>" +
      "%{customdata[6]}: %{customdata[3]}<br>" +
      "<extra></extra>"
  };

  Plotly.react("chart-scatter", [trace], baseLayout({
    title: {
      text: parseTimeLabel(col),
      x: 0,
      xanchor: "left",
      font: {
        size: 14
      }
    },
    xaxis: {
      title: "Total PV capacity, GW",
      gridcolor: "#ebe8df",
      zerolinecolor: "#cfcabe",
      range: [0, scatterProfileContext.maxTotal * 1.08]
    },
    yaxis: {
      title: "Distributed share of total PV, %",
      gridcolor: "#ebe8df",
      zerolinecolor: "#cfcabe",
      range: [0, 100]
    },
    margin: { l: 64, r: 92, t: 34, b: 60 },
    transition: animate ? { duration: 450, easing: "cubic-in-out" } : undefined
  }), baseConfig());
}

function renderTables(latestProvinceRows, growthProvinceRows, nationalLatestTotal, baselineCol, latestCol) {
  const latestNote = document.querySelector("#table-latest-note");
  if (latestNote) {
    latestNote.textContent = `Top provinces at year-end ${getYear(latestCol)}.`;
  }

  const growthNote = document.querySelector("#table-growth-note");
  if (growthNote) {
    growthNote.textContent =
      `Capacity change from ${parseTimeLabel(baselineCol)} to year-end ${getYear(latestCol)}.`;
  }

  const latestRows = latestProvinceRows.slice(0, 15).map(d => ({
    Province: d.area,
    "Total GW": d.total,
    "Utility GW": d.utility,
    "Distributed GW": d.distributed,
    "Non-household distributed GW": d.nonHousehold,
    "Household GW": d.household,
    "Distributed share": 100 * d.distributedShare,
    "National share": 100 * d.total / nationalLatestTotal
  }));

  const growthRows = growthProvinceRows.slice(0, 15).map(d => ({
    Province: d.area,
    "Total growth GW": d.totalGrowth,
    "Utility growth GW": d.utilityGrowth,
    "Distributed growth GW": d.distributedGrowth,
    "Household growth GW": d.householdGrowth
  }));

  document.querySelector("#table-latest").innerHTML = makeTable(latestRows, {
    "Distributed share": value => fmtPct(value),
    "National share": value => fmtPct(value)
  });

  document.querySelector("#table-growth").innerHTML = makeTable(growthRows, {});
}

function makeTable(rows, customFormatters = {}) {
  if (!rows.length) return "<p>No rows available.</p>";

  const cols = Object.keys(rows[0]);

  const thead = `
    <thead>
      <tr>
        ${cols.map(col => `<th>${col}</th>`).join("")}
      </tr>
    </thead>
  `;

  const tbody = `
    <tbody>
      ${rows.map(row => `
        <tr>
          ${cols.map(col => `<td>${formatCell(row[col], col, customFormatters)}</td>`).join("")}
        </tr>
      `).join("")}
    </tbody>
  `;

  return `<table>${thead}${tbody}</table>`;
}

function formatCell(value, col, customFormatters) {
  if (value === null || value === undefined || Number.isNaN(value)) return "-";
  if (customFormatters[col]) return customFormatters[col](value);
  if (typeof value === "number") return value.toFixed(1);
  return value;
}


