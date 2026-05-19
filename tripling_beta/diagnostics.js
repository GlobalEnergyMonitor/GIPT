(function () {
  document.addEventListener("DOMContentLoaded", initDiagnostics);

  const PATHS = {
    iea: "./iea.csv",
    indevAnnual: "./indev_annual.csv",
    indevTotal: "./indev_total.csv",
    triplingAdditions: "./tripling_additions.csv",
    baseAssumptions: "./risk_pipeline/base_assumptions.csv",
    geoMultipliers: "./risk_pipeline/geography_multipliers.csv",
    annualStatusDateKnown: "./risk_pipeline/simulated_annual_additions_by_status_date_known_summary.csv",
    annualTotalByTechnology: "./risk_pipeline/simulated_annual_additions_total_by_technology_summary.csv",
    windowStatus: "./risk_pipeline/simulated_2026_2030_additions_by_status_summary.csv",
    windowStatusDateKnown: "./risk_pipeline/simulated_2026_2030_additions_by_status_date_known_summary.csv",
    windowTotalByTechnology: "./risk_pipeline/simulated_2026_2030_additions_total_by_technology_summary.csv"
  };

  const TECHNOLOGIES = [
    { label: "Utility-scale solar", csv: "Utility-scale solar", model: "utility-scale solar" },
    { label: "Onshore wind", csv: "Onshore wind", model: "onshore wind" },
    { label: "Offshore wind", csv: "Offshore wind", model: "offshore wind" },
    { label: "Hydropower", csv: "Hydro", model: "hydropower" }
  ];

  const SCENARIO_ORDER = ["low", "central", "high"];
  const STATUS_ORDER = ["construction", "pre-construction", "announced"];
  const STATUS_LABELS = {
    "construction": "Construction",
    "pre-construction": "Pre-construction",
    "announced": "Announced"
  };
  const CATEGORY_ORDER = ["Construction", "Pre-construction", "Announced", "Total"];

  const COLORS = {
    historical: "#173f67",
    construction: "#3b82f6",
    "pre-construction": "#93c5fd",
    announced: "#dbeafe",
    known: "#3b82f6",
    unknown: "#f59e0b",
    rawUnknown: "#dbeafe",
    tripling: "#dc2626",
    range: "#111827",
    iqr: "rgba(255, 255, 255, 0.86)"
  };

  const state = {
    ieaRows: [],
    indevAnnualRows: [],
    indevTotalRows: [],
    triplingRows: [],
    baseRows: [],
    geoRows: [],
    annualStatusDateKnownRows: [],
    annualTotalByTechnologyRows: [],
    windowStatusRows: [],
    windowStatusDateKnownRows: [],
    windowTotalByTechnologyRows: []
  };

  function cleanText(value) {
    return String(value ?? "").trim();
  }

  function normalise(value) {
    return cleanText(value).toLowerCase();
  }

  function toNumber(value) {
    const n = Number(value);
    return Number.isFinite(n) ? n : 0;
  }

  function fmt(value, digits = 1) {
    const n = toNumber(value);
    return n.toLocaleString(undefined, {
      maximumFractionDigits: digits,
      minimumFractionDigits: 0
    });
  }

  function selectedTechnology() {
    const select = document.getElementById("diagnostic-technology-select");
    return TECHNOLOGIES.find(tech => tech.csv === select.value) || TECHNOLOGIES[0];
  }

  function selectedScenario() {
    return document.getElementById("diagnostic-scenario-select").value || "central";
  }

  function riskMode() {
    return Boolean(document.getElementById("diagnostic-risk-toggle")?.checked);
  }

  function firstColumnValue(row) {
    return cleanText(row[""] || row["Unnamed: 0"] || row.Technology || row.technology);
  }

  function statusFromRow(row) {
    return normalise(row.Status || row.status || row.index);
  }

  function yearColumns(rows) {
    if (!rows.length) return [];

    return Object.keys(rows[0])
      .filter(col => !["", "Unnamed: 0", "Technology", "technology", "Status", "status"].includes(col))
      .map(col => ({ col, year: Number(String(col).replace(".0", "")) }))
      .filter(d => Number.isFinite(d.year))
      .sort((a, b) => a.year - b.year);
  }

  function buildRawCumulativeData(tech) {
    const rows = state.indevTotalRows.filter(row => firstColumnValue(row) === tech.csv);
    const byStatus = new Map();

    rows.forEach(row => {
      const rawStatus = cleanText(row.index || row.Status || row.status);
      const statusKey = rawStatus.toLowerCase();
      const label =
        statusKey === "construction" ? "Construction" :
        statusKey === "pre-construction" ? "Pre-construction" :
        statusKey === "announced" ? "Announced" :
        statusKey === "total" ? "Total" :
        rawStatus;

      const known = toNumber(row["pre-2030"] ?? row.pre2030 ?? row.known);
      const unknown = toNumber(row.unknown ?? row.Unknown);
      byStatus.set(label, { category: label, known, unknown, total: known + unknown });
    });

    return CATEGORY_ORDER.map(category => byStatus.get(category) || {
      category,
      known: 0,
      unknown: 0,
      total: 0
    });
  }

  function buildRiskCumulativeData(tech, scenario) {
    const byStatus = new Map();

    state.windowStatusDateKnownRows.forEach(row => {
      if (normalise(row.scenario) !== scenario || normalise(row.model_technology) !== tech.model) return;

      const status = normalise(row.status);
      const dateKnown = normalise(row.date_known);
      if (!STATUS_ORDER.includes(status) || !["known", "unknown"].includes(dateKnown)) return;

      if (!byStatus.has(status)) {
        byStatus.set(status, { known: 0, unknown: 0 });
      }
      byStatus.get(status)[dateKnown] += toNumber(row.p50_mw) / 1000;
    });

    const rangeByStatus = new Map();
    state.windowStatusRows.forEach(row => {
      if (normalise(row.scenario) !== scenario || normalise(row.model_technology) !== tech.model) return;
      rangeByStatus.set(normalise(row.status), quantileRow(row));
    });

    const totalRangeRow = state.windowTotalByTechnologyRows.find(row =>
      normalise(row.scenario) === scenario && normalise(row.model_technology) === tech.model
    );

    const rows = STATUS_ORDER.map(status => {
      const values = byStatus.get(status) || { known: 0, unknown: 0 };
      return {
        category: STATUS_LABELS[status],
        status,
        known: values.known,
        unknown: values.unknown,
        total: values.known + values.unknown,
        range: rangeByStatus.get(status)
      };
    });

    rows.push({
      category: "Total",
      status: "total",
      known: rows.reduce((sum, row) => sum + row.known, 0),
      unknown: rows.reduce((sum, row) => sum + row.unknown, 0),
      total: rows.reduce((sum, row) => sum + row.total, 0),
      range: totalRangeRow ? quantileRow(totalRangeRow) : null
    });

    return rows;
  }

  function quantileRow(row) {
    return {
      p10: toNumber(row.p10_mw) / 1000,
      p25: toNumber(row.p25_mw) / 1000,
      p50: toNumber(row.p50_mw) / 1000,
      p75: toNumber(row.p75_mw) / 1000,
      p90: toNumber(row.p90_mw) / 1000
    };
  }

  function triplingSeries(tech) {
    return state.triplingRows
      .map(row => ({
        year: Number(row.Year || row.year || row[""]),
        value: toNumber(row[tech.csv])
      }))
      .filter(d => Number.isFinite(d.year))
      .sort((a, b) => a.year - b.year);
  }

  function triplingTotal(tech) {
    return triplingSeries(tech).reduce((sum, d) => sum + d.value, 0);
  }

  function rangeShapesHorizontal(rows, yValues) {
    const shapes = [];

    rows.forEach((row, index) => {
      if (!row.range) return;
      const y = yValues[index] + 0.32;
      const boxHalfHeight = 0.075;

      shapes.push({
        type: "line",
        xref: "x",
        yref: "y",
        x0: row.range.p10,
        x1: row.range.p90,
        y0: y,
        y1: y,
        line: { color: COLORS.range, width: 1.1 }
      });

      shapes.push({
        type: "rect",
        xref: "x",
        yref: "y",
        x0: row.range.p25,
        x1: row.range.p75,
        y0: y - boxHalfHeight,
        y1: y + boxHalfHeight,
        fillcolor: COLORS.iqr,
        line: { color: COLORS.range, width: 1 }
      });

      shapes.push({
        type: "line",
        xref: "x",
        yref: "y",
        x0: row.range.p50,
        x1: row.range.p50,
        y0: y - boxHalfHeight,
        y1: y + boxHalfHeight,
        line: { color: COLORS.range, width: 1.4 }
      });
    });

    return shapes;
  }

  function drawCumulativeChart() {
    const tech = selectedTechnology();
    const scenario = selectedScenario();
    const isRisk = riskMode();
    const data = isRisk ? buildRiskCumulativeData(tech, scenario) : buildRawCumulativeData(tech);
    const yValues = data.map((_, i) => i);
    const knownValues = data.map(d => d.known);
    const unknownValues = data.map(d => d.unknown);
    const triplingWindowTotal = triplingTotal(tech);
    const maxRange = Math.max(0, ...data.map(d => d.range?.p90 || 0));
    const xMax = Math.max(1, ...data.map(d => d.total), maxRange, triplingWindowTotal) * 1.14;
    const shapes = [];

    if (triplingWindowTotal > 0) {
      shapes.push({
        type: "line",
        xref: "x",
        yref: "paper",
        x0: triplingWindowTotal,
        x1: triplingWindowTotal,
        y0: 0,
        y1: 1,
        line: { color: COLORS.tripling, width: 2, dash: "dash" }
      });
    }

    shapes.push(...(isRisk ? rangeShapesHorizontal(data, yValues) : []));

    const traces = [
      {
        type: "bar",
        orientation: "h",
        y: yValues,
        x: knownValues,
        name: isRisk ? "Known start year, risk-adjusted p50" : "Pre-2030 commissioning",
        marker: { color: COLORS.known },
        hovertemplate: "%{customdata}<br>%{x:.1f} GW<extra></extra>",
        customdata: data.map(d => `${d.category}: ${isRisk ? "known start year p50" : "pre-2030 commissioning"}`)
      },
      {
        type: "bar",
        orientation: "h",
        y: yValues,
        x: unknownValues,
        name: isRisk ? "Unknown start year, risk-adjusted p50" : "Unknown commissioning year",
        marker: { color: isRisk ? COLORS.unknown : COLORS.rawUnknown },
        hovertemplate: "%{customdata}<br>%{x:.1f} GW<extra></extra>",
        customdata: data.map(d => `${d.category}: ${isRisk ? "unknown start year p50" : "unknown commissioning year"}`)
      }
    ];

    const annotations = triplingWindowTotal > 0 ? [{
      x: triplingWindowTotal,
      y: 0.76,
      xref: "x",
      yref: "paper",
      text: "2026-2030 additions<br>consistent with tripling",
      showarrow: false,
      xanchor: triplingWindowTotal > xMax * 0.75 ? "right" : "left",
      xshift: triplingWindowTotal > xMax * 0.75 ? -8 : 8,
      align: "left",
      font: { size: 10, color: COLORS.tripling }
    }] : [];

    Plotly.react("diagnostic-cumulative-chart", traces, {
      font: { family: "Plus Jakarta Sans, sans-serif", color: "#17233a" },
      paper_bgcolor: "#ffffff",
      plot_bgcolor: "#ffffff",
      margin: { l: 112, r: 18, t: 36, b: 44 },
      barmode: "stack",
      bargap: 0.38,
      hovermode: "closest",
      legend: {
        orientation: "h",
        x: 0,
        y: 1.08,
        xanchor: "left",
        yanchor: "bottom",
        font: { size: 10 }
      },
      xaxis: {
        title: "GW",
        range: [0, xMax],
        gridcolor: "#e5e7eb",
        zeroline: false
      },
      yaxis: {
        tickmode: "array",
        tickvals: yValues,
        ticktext: data.map(d => d.category),
        autorange: "reversed"
      },
      shapes,
      annotations
    }, {
      responsive: true,
      displaylogo: false
    });
  }

  function buildHistoricalData(tech) {
    return state.ieaRows
      .map(row => ({
        year: Number(row[""] || row["Unnamed: 0"] || row.Year || row.year),
        value: toNumber(row[tech.csv])
      }))
      .filter(d => d.year >= 2015 && d.year <= 2025 && Number.isFinite(d.year))
      .sort((a, b) => a.year - b.year);
  }

  function buildRawAnnualStatusData(tech) {
    const rows = state.indevAnnualRows.filter(row => firstColumnValue(row) === tech.csv);
    const cols = yearColumns(rows);
    const maps = new Map();
    STATUS_ORDER.forEach(status => maps.set(status, new Map()));

    rows.forEach(row => {
      const status = statusFromRow(row);
      if (!maps.has(status)) return;
      cols.forEach(({ col, year }) => {
        maps.get(status).set(year, toNumber(row[col]));
      });
    });

    return maps;
  }

  function buildRiskAnnualStatusData(tech, scenario) {
    const maps = new Map();
    STATUS_ORDER.forEach(status => maps.set(status, new Map()));
    const unknownMap = new Map();

    state.annualStatusDateKnownRows.forEach(row => {
      if (normalise(row.scenario) !== scenario || normalise(row.model_technology) !== tech.model) return;
      const year = Number(row.year);
      const status = normalise(row.status);
      const dateKnown = normalise(row.date_known);
      const value = toNumber(row.p50_mw) / 1000;

      if (year < 2026 || year > 2030 || !STATUS_ORDER.includes(status)) return;

      if (dateKnown === "known") {
        maps.get(status).set(year, (maps.get(status).get(year) || 0) + value);
      } else if (dateKnown === "unknown") {
        unknownMap.set(year, (unknownMap.get(year) || 0) + value);
      }
    });

    return { maps, unknownMap };
  }

  function annualRangeByYear(tech, scenario) {
    const map = new Map();
    state.annualTotalByTechnologyRows.forEach(row => {
      if (normalise(row.scenario) !== scenario || normalise(row.model_technology) !== tech.model) return;
      map.set(Number(row.year), quantileRow(row));
    });
    return map;
  }

  function cloneAnnualStatusData(statusData) {
    const maps = new Map();
    STATUS_ORDER.forEach(status => {
      maps.set(status, new Map(statusData.maps.get(status) || []));
    });

    return {
      maps,
      unknownMap: new Map(statusData.unknownMap || [])
    };
  }

  function alignRiskAnnualBarsToTotalP50(statusData, rangeMap, years) {
    const aligned = cloneAnnualStatusData(statusData);

    years.forEach(year => {
      const targetTotal = rangeMap.get(year)?.p50;
      if (!Number.isFinite(targetTotal) || targetTotal <= 0) return;

      const componentTotal = STATUS_ORDER.reduce((sum, status) => {
        return sum + (aligned.maps.get(status).get(year) || 0);
      }, 0) + (aligned.unknownMap.get(year) || 0);

      if (componentTotal <= 0) return;

      const scale = targetTotal / componentTotal;

      STATUS_ORDER.forEach(status => {
        const map = aligned.maps.get(status);
        if (map.has(year)) {
          map.set(year, map.get(year) * scale);
        }
      });

      if (aligned.unknownMap.has(year)) {
        aligned.unknownMap.set(year, aligned.unknownMap.get(year) * scale);
      }
    });

    return aligned;
  }

  function annualRangeShapes(rangeMap) {
    const shapes = [];

    rangeMap.forEach((range, year) => {
      if (year < 2026 || year > 2030) return;
      const x = year + 0.28;
      const boxHalfWidth = 0.075;

      shapes.push({
        type: "line",
        xref: "x",
        yref: "y",
        x0: x,
        x1: x,
        y0: range.p10,
        y1: range.p90,
        line: { color: COLORS.range, width: 1.1 }
      });

      shapes.push({
        type: "rect",
        xref: "x",
        yref: "y",
        x0: x - boxHalfWidth,
        x1: x + boxHalfWidth,
        y0: range.p25,
        y1: range.p75,
        fillcolor: COLORS.iqr,
        line: { color: COLORS.range, width: 1 }
      });

      shapes.push({
        type: "line",
        xref: "x",
        yref: "y",
        x0: x - boxHalfWidth,
        x1: x + boxHalfWidth,
        y0: range.p50,
        y1: range.p50,
        line: { color: COLORS.range, width: 1.4 }
      });
    });

    return shapes;
  }

  function valuesForYears(map, years) {
    return years.map(year => map.get(year) ?? null);
  }

  function drawAnnualChart() {
    const tech = selectedTechnology();
    const scenario = selectedScenario();
    const isRisk = riskMode();
    const historical = buildHistoricalData(tech);
    const tripling = triplingSeries(tech);
    const futureYears = [2026, 2027, 2028, 2029, 2030];
    const chartYears = [...new Set([
      ...historical.map(d => d.year),
      ...futureYears,
      ...tripling.map(d => d.year)
    ])].sort((a, b) => a - b);

    const historicalMap = new Map(historical.map(d => [d.year, d.value]));
    const triplingMap = new Map(tripling.map(d => [d.year, d.value]));
    const rawStatusData = isRisk
      ? buildRiskAnnualStatusData(tech, scenario)
      : { maps: buildRawAnnualStatusData(tech), unknownMap: new Map() };
    const rangeMap = isRisk ? annualRangeByYear(tech, scenario) : new Map();
    const statusData = isRisk
      ? alignRiskAnnualBarsToTotalP50(rawStatusData, rangeMap, futureYears)
      : rawStatusData;

    const traces = [
      {
        type: "bar",
        x: historical.map(d => d.year),
        y: historical.map(d => d.value),
        name: "Historical additions",
        marker: { color: COLORS.historical },
        hovertemplate: "%{x}: %{y:.1f} GW<extra>Historical additions</extra>"
      },
      {
        type: "bar",
        x: futureYears,
        y: valuesForYears(statusData.maps.get("construction"), futureYears),
        name: "Construction, known start year p50",
        marker: { color: COLORS.construction },
        hovertemplate: "%{x}: %{y:.1f} GW<extra>Construction</extra>"
      },
      {
        type: "bar",
        x: futureYears,
        y: valuesForYears(statusData.maps.get("pre-construction"), futureYears),
        name: "Pre-construction, known start year p50",
        marker: { color: COLORS["pre-construction"] },
        hovertemplate: "%{x}: %{y:.1f} GW<extra>Pre-construction</extra>"
      },
      {
        type: "bar",
        x: futureYears,
        y: valuesForYears(statusData.maps.get("announced"), futureYears),
        name: "Announced, known start year p50",
        marker: { color: COLORS.announced },
        hovertemplate: "%{x}: %{y:.1f} GW<extra>Announced</extra>"
      }
    ];

    if (isRisk) {
      traces.push({
        type: "bar",
        x: futureYears,
        y: valuesForYears(statusData.unknownMap, futureYears),
        name: "Unknown start year, risk-adjusted p50",
        marker: {
          color: COLORS.unknown,
          line: { color: "rgba(23, 63, 103, 0.24)", width: 1 }
        },
        hovertemplate: "%{x}: %{y:.1f} GW<extra>Unknown start year p50</extra>"
      });
    }

    traces.push({
      type: "scatter",
      mode: "lines+markers",
      x: chartYears,
      y: chartYears.map(year => triplingMap.has(year) ? triplingMap.get(year) : null),
      name: "Tripling pathway additions",
      line: { color: COLORS.tripling, width: 2, dash: "dash" },
      marker: { color: COLORS.tripling, size: 5 },
      connectgaps: false,
      hovertemplate: "%{x}: %{y:.1f} GW<extra>Tripling pathway additions</extra>"
    });

    const totals = chartYears.map(year => {
      const knownTotal = STATUS_ORDER.reduce((sum, status) => {
        return sum + (statusData.maps.get(status).get(year) || 0);
      }, 0);
      return (historicalMap.get(year) || 0) + knownTotal + (statusData.unknownMap.get(year) || 0);
    });
    const yMax = Math.max(
      1,
      ...totals,
      ...tripling.map(d => d.value),
      ...[...rangeMap.values()].map(d => d.p90)
    ) * 1.14;

    Plotly.react("diagnostic-annual-chart", traces, {
      font: { family: "Plus Jakarta Sans, sans-serif", color: "#17233a" },
      paper_bgcolor: "#ffffff",
      plot_bgcolor: "#ffffff",
      margin: { l: 56, r: 20, t: 48, b: 48 },
      barmode: "stack",
      bargap: 0.32,
      hovermode: "x unified",
      legend: {
        orientation: "h",
        x: 0,
        y: 1.08,
        xanchor: "left",
        yanchor: "bottom",
        font: { size: 10 }
      },
      xaxis: {
        tickmode: "linear",
        dtick: 5,
        range: [2014.4, 2030.8],
        showgrid: false,
        zeroline: false
      },
      yaxis: {
        title: "GW",
        range: [0, yMax],
        gridcolor: "#e5e7eb",
        zeroline: false
      },
      shapes: isRisk ? annualRangeShapes(rangeMap) : []
    }, {
      responsive: true,
      displaylogo: false
    });
  }

  function renderTable(targetId, rows, captionId, captionText) {
    const target = document.getElementById(targetId);
    const caption = document.getElementById(captionId);
    if (!target) return;

    target.replaceChildren();
    if (caption) caption.textContent = captionText;

    if (!rows.length) {
      const empty = document.createElement("p");
      empty.className = "empty-state";
      empty.textContent = "No rows available for the selected scenario.";
      target.appendChild(empty);
      return;
    }

    const columns = Object.keys(rows[0]);
    const table = document.createElement("table");
    table.className = "assumption-table";

    const thead = document.createElement("thead");
    const headRow = document.createElement("tr");
    columns.forEach(column => {
      const th = document.createElement("th");
      th.textContent = column;
      headRow.appendChild(th);
    });
    thead.appendChild(headRow);
    table.appendChild(thead);

    const tbody = document.createElement("tbody");
    rows.forEach(row => {
      const tr = document.createElement("tr");
      columns.forEach(column => {
        const td = document.createElement("td");
        const rawValue = row[column];
        const n = Number(rawValue);
        if (rawValue !== "" && Number.isFinite(n)) {
          td.className = "numeric";
          td.textContent = n.toLocaleString(undefined, { maximumFractionDigits: 4 });
        } else {
          td.textContent = rawValue;
        }
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    target.appendChild(table);
  }

  function updateTables() {
    const scenario = selectedScenario();
    const baseRows = state.baseRows.filter(row => normalise(row.scenario) === scenario);
    const geoRows = state.geoRows.filter(row => normalise(row.scenario) === scenario);

    renderTable(
      "base-assumptions-table",
      baseRows,
      "base-assumptions-caption",
      `${scenario} scenario, ${baseRows.length} rows`
    );
    renderTable(
      "geography-multipliers-table",
      geoRows,
      "geography-multipliers-caption",
      `${scenario} scenario, ${geoRows.length} rows`
    );
  }

  function updateAll() {
    updateTables();
    drawCumulativeChart();
    drawAnnualChart();
  }

  function populateControls() {
    const technologySelect = document.getElementById("diagnostic-technology-select");
    const scenarioSelect = document.getElementById("diagnostic-scenario-select");
    const riskToggle = document.getElementById("diagnostic-risk-toggle");

    technologySelect.replaceChildren();
    TECHNOLOGIES.forEach(tech => {
      const option = document.createElement("option");
      option.value = tech.csv;
      option.textContent = tech.label;
      technologySelect.appendChild(option);
    });
    technologySelect.value = TECHNOLOGIES[0].csv;
    technologySelect.disabled = false;

    const scenarios = [...new Set(state.baseRows.map(row => normalise(row.scenario)).filter(Boolean))]
      .sort((a, b) => {
        const ai = SCENARIO_ORDER.indexOf(a);
        const bi = SCENARIO_ORDER.indexOf(b);
        return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi) || a.localeCompare(b);
      });

    scenarioSelect.replaceChildren();
    scenarios.forEach(scenario => {
      const option = document.createElement("option");
      option.value = scenario;
      option.textContent = scenario[0].toUpperCase() + scenario.slice(1);
      scenarioSelect.appendChild(option);
    });
    scenarioSelect.value = scenarios.includes("central") ? "central" : scenarios[0];
    scenarioSelect.disabled = false;

    technologySelect.addEventListener("change", updateAll);
    scenarioSelect.addEventListener("change", updateAll);
    riskToggle?.addEventListener("change", updateAll);
  }

  async function initDiagnostics() {
    if (!window.d3 || !window.Plotly) {
      console.error("D3 and Plotly are required for diagnostics.");
      return;
    }

    const [
      iea,
      indevAnnual,
      indevTotal,
      triplingAdditions,
      baseAssumptions,
      geoMultipliers,
      annualStatusDateKnown,
      annualTotalByTechnology,
      windowStatus,
      windowStatusDateKnown,
      windowTotalByTechnology
    ] = await Promise.all([
      d3.csv(PATHS.iea),
      d3.csv(PATHS.indevAnnual),
      d3.csv(PATHS.indevTotal),
      d3.csv(PATHS.triplingAdditions),
      d3.csv(PATHS.baseAssumptions),
      d3.csv(PATHS.geoMultipliers),
      d3.csv(PATHS.annualStatusDateKnown),
      d3.csv(PATHS.annualTotalByTechnology),
      d3.csv(PATHS.windowStatus),
      d3.csv(PATHS.windowStatusDateKnown),
      d3.csv(PATHS.windowTotalByTechnology)
    ]);

    Object.assign(state, {
      ieaRows: iea,
      indevAnnualRows: indevAnnual,
      indevTotalRows: indevTotal,
      triplingRows: triplingAdditions,
      baseRows: baseAssumptions,
      geoRows: geoMultipliers,
      annualStatusDateKnownRows: annualStatusDateKnown,
      annualTotalByTechnologyRows: annualTotalByTechnology,
      windowStatusRows: windowStatus,
      windowStatusDateKnownRows: windowStatusDateKnown,
      windowTotalByTechnologyRows: windowTotalByTechnology
    });

    populateControls();
    updateAll();
  }
})();
