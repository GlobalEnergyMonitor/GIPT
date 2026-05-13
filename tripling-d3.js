(async function () {
  async function loadData() {
    const response = await fetch("./tripling-d3-data.json");
    if (!response.ok) {
      throw new Error(`Could not load tripling-d3-data.json (${response.status})`);
    }
    return await response.json();
  }

  const mount = document.getElementById("renewable-d3-chart");
  const select = document.getElementById("d3-country-select");
  const explainer = document.getElementById("d3-explainer");

  if (!mount || !select || typeof d3 === "undefined") return;

  const data = await loadData();

  const DARK = "#002430";
  const PRE2030_COLOR = "#ca4a50";
  const UNKNOWN_COLOR = "#016b83";
  const LIGHT_TEXT = "#ffffff";
  const MUTED_TEXT = "#52606b";
  const TARGET_LIGHT = "#ffffff";
  const FONT = '"Plus Jakarta Sans", sans-serif';

  const W = 920;
  const MAX_SIDE = 240;

  const CATEGORY_START_X = 26;
  const RIGHT_MARGIN = 20;

  const VALUE_FONT = 12;
  const SMALL_VALUE_FONT = 11.25;
  const LABEL_FONT = 13.5;
  const ANNOT_FONT = 13;
  const LEGEND_FONT = 12.5;
  const FOOTER_FONT = 12.5;

  const FOOTER_LINE_1 = "Includes solar, wind, and non-pumped storage hydropower.";
  const FOOTER_LINE_2 = "Square area denotes total renewable capacity; color split shows pre-2030 versus unknown commissioning year.";

  function toNumber(value) {
    const n = Number(value);
    return Number.isFinite(n) ? n : 0;
  }

  function formatGW(value) {
    const n = toNumber(value);
    return `${n.toLocaleString(undefined, {
      maximumFractionDigits: n < 10 && n % 1 !== 0 ? 1 : 0
    })} GW`;
  }

  function formatSignedGW(value) {
    const n = toNumber(value);
    if (n === 0) return formatGW(0);
    return `${n > 0 ? "+" : "−"}${formatGW(Math.abs(n))}`;
  }

  function formatPercent(part, total) {
    const p = total > 0 ? (part / total) * 100 : 0;
    return `${p.toLocaleString(undefined, {
      maximumFractionDigits: p < 10 && p % 1 !== 0 ? 1 : 0
    })}%`;
  }

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, ch => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#039;"
    }[ch]));
  }

  function tooltipHTML({ title, rows }) {
    return `
      <div style="font-weight:700;margin-bottom:4px;">${escapeHtml(title)}</div>
      ${rows.map(row => `
        <div>
          <span style="color:${MUTED_TEXT};">${escapeHtml(row.label)}:</span>
          ${escapeHtml(row.value)}
        </div>
      `).join("")}
    `;
  }

  function normaliseStatusData(statusData = {}) {
    const pre2030 = toNumber(
      statusData.pre2030 ??
      statusData["pre-2030"] ??
      statusData.pre_2030 ??
      statusData.operating ??
      0
    );

    let unknown;

    if (
      statusData.unknown !== undefined ||
      statusData.post2030 !== undefined ||
      statusData["post-2030"] !== undefined
    ) {
      unknown = toNumber(
        statusData.unknown ??
        statusData.post2030 ??
        statusData["post-2030"] ??
        0
      );
    } else {
      const oldTotal = toNumber(statusData.total ?? 0);
      unknown = Math.max(0, oldTotal - pre2030);
    }

    return {
      pre2030,
      unknown,
      total: pre2030 + unknown
    };
  }

  function populateSelect() {
    select.innerHTML = "";
    Object.keys(data).forEach(name => {
      const option = document.createElement("option");
      option.value = name;
      option.textContent = name;
      select.appendChild(option);
    });
    select.value = Object.keys(data)[0];
  }

  function updateExplainer(d) {
    if (!explainer) return;

    const copy = d.explainer;
    const lines = Array.isArray(copy)
      ? copy
      : typeof copy === "string"
        ? [copy]
        : [copy?.line1, copy?.line2];

    const cleanedLines = lines
      .map(line => String(line || "").trim())
      .filter(Boolean);

    explainer.replaceChildren();

    if (!cleanedLines.length) {
      explainer.style.display = "none";
      return;
    }

    explainer.style.display = "block";
    cleanedLines.forEach(line => {
      const paragraph = document.createElement("p");
      paragraph.textContent = line;
      explainer.appendChild(paragraph);
    });
  }

  function draw(countryName) {
    mount.innerHTML = "";
    mount.style.position = "relative";

    const tooltip = d3.select(mount)
      .append("div")
      .attr("class", "d3-hover-tooltip")
      .style("position", "absolute")
      .style("display", "none")
      .style("pointer-events", "none")
      .style("z-index", "10")
      .style("max-width", "240px")
      .style("padding", "8px 10px")
      .style("background", "rgba(255, 255, 255, 0.96)")
      .style("border", "1px solid rgba(0, 36, 48, 0.18)")
      .style("box-shadow", "0 6px 20px rgba(0, 36, 48, 0.14)")
      .style("border-radius", "8px")
      .style("font-family", FONT)
      .style("font-size", "12px")
      .style("line-height", "1.35")
      .style("color", DARK);

    function showTooltip(event, html) {
      const rect = mount.getBoundingClientRect();

      tooltip
        .html(html)
        .style("display", "block");

      const node = tooltip.node();
      const pad = 8;

      let left = event.clientX - rect.left + 12;
      let top = event.clientY - rect.top + 12;

      const tooltipWidth = node.offsetWidth;
      const tooltipHeight = node.offsetHeight;

      if (left + tooltipWidth > rect.width - pad) {
        left = Math.max(pad, event.clientX - rect.left - tooltipWidth - 12);
      }

      if (top + tooltipHeight > rect.height - pad) {
        top = Math.max(pad, event.clientY - rect.top - tooltipHeight - 12);
      }

      tooltip
        .style("left", `${left}px`)
        .style("top", `${top}px`);
    }

    function hideTooltip() {
      tooltip.style("display", "none");
    }

    function bindTooltip(selection, html) {
      selection
        .style("cursor", "help")
        .on("mouseenter", event => showTooltip(event, html))
        .on("mousemove", event => showTooltip(event, html))
        .on("mouseleave", hideTooltip);
    }

    const d = data[countryName];

    updateExplainer(d);

    const categories = [
      { label: "Construction", ...normaliseStatusData(d.construction) },
      { label: "Pre-construction", ...normaliseStatusData(d.preConstruction) },
      { label: "Announced", ...normaliseStatusData(d.announced) }
    ];

    const combinedPre2030 = categories.reduce((s, c) => s + c.pre2030, 0);
    const combinedUnknown = categories.reduce((s, c) => s + c.unknown, 0);
    const combinedTotal = combinedPre2030 + combinedUnknown;

    const rawTriplingGap = toNumber(d.triplingGap || 0);
    const rawTriplingTotal = combinedTotal + rawTriplingGap;
    const triplingTotal = Math.max(0, rawTriplingTotal);

    const scaleDomainTotal = Math.max(
      combinedTotal,
      triplingTotal,
      ...categories.map(c => c.total)
    );

    const localScaleK = MAX_SIDE / Math.sqrt(scaleDomainTotal || 1);

    function gw2side(gw) {
      return Math.sqrt(Math.max(0, gw || 0)) * localScaleK;
    }

    const tripSide = gw2side(triplingTotal);
    const combinedSide = gw2side(combinedTotal);
    const combinedGroupSide = Math.max(tripSide, combinedSide);
    const maxTripSide = MAX_SIDE;

    categories.forEach(cat => {
      cat.outerSide = gw2side(cat.total);
    });

    const cx = W - RIGHT_MARGIN - combinedGroupSide;

    const totalCategoryWidth = categories.reduce((s, c) => s + c.outerSide, 0);
    const totalFreeSpace = cx - CATEGORY_START_X - totalCategoryWidth;
    const gap = Math.max(0, totalFreeSpace / 3);

    let runningX = CATEGORY_START_X;
    categories.forEach(cat => {
      cat.x = runningX;
      cat.centerX = cat.x + cat.outerSide / 2;
      runningX += cat.outerSide + gap;
    });

    const TOP_BAND = 58;
    const GAP_ABOVE_BOX = 18;
    const BASELINE_Y = TOP_BAND + GAP_ABOVE_BOX + maxTripSide;

    const BOTTOM_BAND = 128;
    const H = BASELINE_Y + BOTTOM_BAND;
    const FOOTER_Y = H - 20;

    const svg = d3.select(mount)
      .append("svg")
      .attr("viewBox", `0 0 ${W} ${H}`)
      .attr("preserveAspectRatio", "xMidYMin meet")
      .style("font-family", FONT);

    function addText({
      x, y, text, size = 11, fill = DARK, weight = 400,
      anchor = "start", style = "normal"
    }) {
      return svg.append("text")
        .attr("x", x)
        .attr("y", y)
        .attr("font-size", size)
        .attr("fill", fill)
        .attr("font-weight", weight)
        .attr("text-anchor", anchor)
        .attr("font-style", style)
        .style("font-family", FONT)
        .text(text);
    }

    function drawSegmentLabel({ x, y, width, side, value, fill, weight = 700, yOffset = 0 }) {
      if (value <= 0 || side < 34 || width < 34) return;

      const label = formatGW(value);

      if (width >= 54) {
        addText({
          x: x + 6,
          y: y + 16 + yOffset,
          text: label,
          size: VALUE_FONT,
          fill,
          weight
        });
      } else {
        addText({
          x: x + width / 2,
          y: y + 16 + yOffset,
          text: label,
          size: SMALL_VALUE_FONT,
          fill,
          weight,
          anchor: "middle"
        });
      }
    }

    function drawSplitSquare(x, pre2030GW, unknownGW, label) {
      const pre2030 = Math.max(0, toNumber(pre2030GW));
      const unknown = Math.max(0, toNumber(unknownGW));
      const total = pre2030 + unknown;

      const side = gw2side(total);
      const y = BASELINE_Y - side;

      const preWidth = total > 0 ? side * (pre2030 / total) : 0;
      const unknownWidth = Math.max(0, side - preWidth);

      if (side <= 0) {
        return { side, y, preWidth, unknownWidth, total };
      }

      if (preWidth > 0) {
        const preRect = svg.append("rect")
          .attr("x", x)
          .attr("y", y)
          .attr("width", preWidth)
          .attr("height", side)
          .attr("fill", PRE2030_COLOR);

        bindTooltip(preRect, tooltipHTML({
      title: `${label}: pre-2030 commissioning`,
          rows: [
            { label: "Capacity", value: formatGW(pre2030) },
            { label: "Share of total", value: formatPercent(pre2030, total) },
            { label: "Total", value: formatGW(total) }
          ]
        }));
      }

      if (unknownWidth > 0) {
        const unknownRect = svg.append("rect")
          .attr("x", x + preWidth)
          .attr("y", y)
          .attr("width", unknownWidth)
          .attr("height", side)
          .attr("fill", UNKNOWN_COLOR);

        bindTooltip(unknownRect, tooltipHTML({
      title: `${label}: unknown commissioning year`,
          rows: [
            { label: "Capacity", value: formatGW(unknown) },
            { label: "Share of total", value: formatPercent(unknown, total) },
            { label: "Total", value: formatGW(total) }
          ]
        }));
      }

      svg.append("rect")
        .attr("x", x)
        .attr("y", y)
        .attr("width", side)
        .attr("height", side)
        .attr("fill", "none")
        .attr("stroke", DARK)
        .attr("stroke-width", 0.8)
        .attr("opacity", 0.18)
        .style("pointer-events", "none");

      const preLabelVisible = pre2030 > 0 && side >= 34 && preWidth >= 34;
      const unknownLabelVisible = unknown > 0 && side >= 34 && unknownWidth >= 34;
      const staggerUnknownLabel = preLabelVisible && unknownLabelVisible && side >= 58 && preWidth < 86;

      drawSegmentLabel({
        x,
        y,
        width: preWidth,
        side,
        value: pre2030,
        fill: LIGHT_TEXT,
        weight: 700
      });

      drawSegmentLabel({
        x: x + preWidth,
        y,
        width: unknownWidth,
        side,
        value: unknown,
        fill: LIGHT_TEXT,
        weight: 700,
        yOffset: staggerUnknownLabel ? 16 : 0
      });

      return { side, y, preWidth, unknownWidth, total };
    }

    categories.forEach(cat => {
      drawSplitSquare(cat.x, cat.pre2030, cat.unknown, cat.label);

      addText({
        x: cat.centerX,
        y: BASELINE_Y + 26,
        text: cat.label,
        size: LABEL_FONT,
        fill: DARK,
        anchor: "middle"
      });
    });

    drawSplitSquare(
      cx,
      combinedPre2030,
      combinedUnknown,
      "Construction + Pre-construction + Announced"
    );

    const yTrip = BASELINE_Y - tripSide;
    const targetIsInside = rawTriplingGap < 0 && tripSide < combinedSide;

    let targetRect;

    if (targetIsInside) {
      svg.append("rect")
        .attr("x", cx)
        .attr("y", yTrip)
        .attr("width", tripSide)
        .attr("height", tripSide)
        .attr("fill", "none")
        .attr("stroke", DARK)
        .attr("stroke-width", 3.8)
        .attr("stroke-dasharray", "6,4")
        .attr("opacity", 0.55)
        .style("pointer-events", "none");

      targetRect = svg.append("rect")
        .attr("x", cx)
        .attr("y", yTrip)
        .attr("width", tripSide)
        .attr("height", tripSide)
        .attr("fill", "none")
        .attr("stroke", TARGET_LIGHT)
        .attr("stroke-width", 1.9)
        .attr("stroke-dasharray", "6,4")
        .attr("opacity", 0.98);
    } else {
      targetRect = svg.append("rect")
        .attr("x", cx)
        .attr("y", yTrip)
        .attr("width", tripSide)
        .attr("height", tripSide)
        .attr("fill", "none")
        .attr("stroke", DARK)
        .attr("stroke-width", 1.6)
        .attr("stroke-dasharray", "6,4")
        .attr("opacity", 0.75);
    }

    bindTooltip(targetRect, tooltipHTML({
      title: "2030 target comparison",
      rows: [
        {
          label: rawTriplingGap >= 0 ? "Additional capacity needed" : "Capacity above target",
          value: formatGW(Math.abs(rawTriplingGap))
        },
        { label: "Pipeline total", value: formatGW(combinedTotal) },
        { label: "Target level", value: formatGW(triplingTotal) },
        { label: "Difference", value: formatSignedGW(rawTriplingGap) }
      ]
    }));

    const outerTopY = BASELINE_Y - combinedSide;
    const outerRightX = cx + combinedSide;
    const targetRightX = cx + tripSide;

    const annotCX = targetIsInside
      ? cx + combinedSide / 2
      : cx + tripSide / 2;

    const annotY1 = 21;
    const annotY2 = 38;
    const lineStartY = 44;

    const gapAbs = Math.abs(rawTriplingGap).toLocaleString();

    const defaultLine1 = rawTriplingGap >= 0
      ? `+${gapAbs} GW for`
      : `${gapAbs} GW above`;

    const defaultLine2 = rawTriplingGap >= 0
      ? "tripling renewables"
      : "tripling requirement";

    const line1 = d.annotation?.line1 || defaultLine1;
    const line2 = d.annotation?.line2 || defaultLine2;

    const match = line1.match(/^([+\-−]?[\d,]+(?:\.\d+)?\s?GW)(.*)$/);

    const textEl = svg.append("text")
      .attr("x", annotCX)
      .attr("y", annotY1)
      .attr("font-size", ANNOT_FONT)
      .attr("fill", DARK)
      .attr("text-anchor", "middle")
      .style("font-family", FONT);

    if (match) {
      textEl.append("tspan")
        .attr("font-weight", 700)
        .text(match[1]);

      textEl.append("tspan")
        .attr("font-weight", 400)
        .text(match[2]);
    } else {
      textEl.text(line1);
    }

    addText({
      x: annotCX,
      y: annotY2,
      text: line2,
      size: ANNOT_FONT,
      fill: DARK,
      anchor: "middle"
    });

    function drawLeaderPath(pathD, highContrast = false) {
      if (highContrast) {
        svg.append("path")
          .attr("d", pathD)
          .attr("fill", "none")
          .attr("stroke", DARK)
          .attr("stroke-width", 3.4)
          .attr("stroke-linejoin", "round")
          .attr("stroke-linecap", "round")
          .attr("opacity", 0.38)
          .style("pointer-events", "none");

        svg.append("path")
          .attr("d", pathD)
          .attr("fill", "none")
          .attr("stroke", TARGET_LIGHT)
          .attr("stroke-width", 1.3)
          .attr("stroke-linejoin", "round")
          .attr("stroke-linecap", "round")
          .attr("opacity", 0.96)
          .style("pointer-events", "none");
      } else {
        svg.append("path")
          .attr("d", pathD)
          .attr("fill", "none")
          .attr("stroke", DARK)
          .attr("stroke-width", 1)
          .attr("stroke-linejoin", "round")
          .attr("stroke-linecap", "round")
          .attr("opacity", 0.55)
          .style("pointer-events", "none");
      }
    }

    if (targetIsInside) {
      const routeY = Math.max(lineStartY + 8, outerTopY - 10);
      const outsideX = outerRightX + 14;

      const pathD = [
        `M ${annotCX} ${lineStartY}`,
        `V ${routeY}`,
        `H ${outsideX}`,
        `V ${yTrip}`,
        `H ${targetRightX}`
      ].join(" ");

      drawLeaderPath(pathD, true);
    } else {
      const pathD = `M ${annotCX} ${lineStartY} V ${yTrip}`;
      drawLeaderPath(pathD, false);
    }

    ["Construction +", "Pre-construction +", "Announced"].forEach((line, i) => {
      addText({
        x: cx + combinedSide / 2,
        y: BASELINE_Y + 24 + i * 16,
        text: line,
        size: LABEL_FONT,
        fill: DARK,
        anchor: "middle"
      });
    });

    const refX = 6;
    const refY = 50;
    const refSide = 82;
    const refPreWidth = 36;
    const refUnknownWidth = refSide - refPreWidth;

    svg.append("rect")
      .attr("x", refX)
      .attr("y", refY)
      .attr("width", refPreWidth)
      .attr("height", refSide)
      .attr("fill", PRE2030_COLOR);

    svg.append("rect")
      .attr("x", refX + refPreWidth)
      .attr("y", refY)
      .attr("width", refUnknownWidth)
      .attr("height", refSide)
      .attr("fill", UNKNOWN_COLOR);

    svg.append("rect")
      .attr("x", refX)
      .attr("y", refY)
      .attr("width", refSide)
      .attr("height", refSide)
      .attr("fill", "none")
      .attr("stroke", DARK)
      .attr("stroke-width", 1.2)
      .attr("opacity", 0.75)
      .style("pointer-events", "none");

    const legLX = refX + refSide + 18;

    const preAnchorX = refX + refPreWidth / 2;
    const unknownAnchorX = refX + refPreWidth + refUnknownWidth / 2;

    const preLeaderY = refY - 26;
    const unknownLeaderY = refY - 6;

    svg.append("line")
      .attr("x1", preAnchorX)
      .attr("y1", refY)
      .attr("x2", preAnchorX)
      .attr("y2", preLeaderY)
      .attr("stroke", DARK)
      .attr("stroke-width", 0.8)
      .attr("opacity", 0.7);

    svg.append("line")
      .attr("x1", preAnchorX)
      .attr("y1", preLeaderY)
      .attr("x2", legLX)
      .attr("y2", preLeaderY)
      .attr("stroke", DARK)
      .attr("stroke-width", 0.8)
      .attr("opacity", 0.7);

    addText({
      x: legLX + 4,
      y: preLeaderY + 4,
      text: "Pre-2030 commissioning",
      size: LEGEND_FONT,
      fill: DARK
    });

    svg.append("line")
      .attr("x1", unknownAnchorX)
      .attr("y1", refY)
      .attr("x2", unknownAnchorX)
      .attr("y2", unknownLeaderY)
      .attr("stroke", DARK)
      .attr("stroke-width", 0.8)
      .attr("opacity", 0.7);

    svg.append("line")
      .attr("x1", unknownAnchorX)
      .attr("y1", unknownLeaderY)
      .attr("x2", legLX)
      .attr("y2", unknownLeaderY)
      .attr("stroke", DARK)
      .attr("stroke-width", 0.8)
      .attr("opacity", 0.7);

    addText({
      x: legLX + 4,
      y: unknownLeaderY + 4,
      text: "Unknown commissioning year",
      size: LEGEND_FONT,
      fill: DARK
    });

addText({
  x: 16,
  y: FOOTER_Y - 16,
  text: FOOTER_LINE_1,
  size: FOOTER_FONT,
  fill: MUTED_TEXT,
  style: "italic"
});

addText({
  x: 16,
  y: FOOTER_Y,
  text: FOOTER_LINE_2,
  size: FOOTER_FONT,
  fill: MUTED_TEXT,
  style: "italic"
});
  }

  populateSelect();
  draw(select.value);

  select.addEventListener("change", function () {
    draw(this.value);
  });

})();
