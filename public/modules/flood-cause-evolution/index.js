/**
 * Global Flood Cause Evolution — interactive Tereon module.
 * Continuous flood-generating-condition trends at HydroBASINS L5 and catchment scales.
 */
window.FloodCauseEvolutionModule = class FloodCauseEvolutionModule {
  constructor(app, manifest = {}) {
    this.app = app;
    this.manifest = manifest;
    this.basePath = manifest.basePath || "/";
    this.dataFile = manifest.dataFile || manifest.datasets?.[0]?.file || "./data/flood-cause-explorer.json";
    this.metric = "intensity_fraction";
    this.basinLayerId = "flood-cause-hydrobasins";
    this.catchmentLayerId = "flood-cause-catchments";
    this.legendId = "flood-cause-trend-legend";
    this.selected = null;
    this.toolbar = null;
    this.modal = null;
    this.hoverTooltip = null;
    this.handleFeatureClick = (payload) => {
      if (![this.basinLayerId, this.catchmentLayerId].includes(payload.layer?.id)) return;
      this.selected = payload.feature;
      this.showInspector(payload.feature, payload.layer.id);
      this.app.draw?.();
    };
    this.handleOverviewKeydown = (event) => {
      if (event.key !== "Escape") return;
      if (this.modal?.querySelector(".fce-figure-viewer.open")) this.closeOverviewFigure();
      else if (this.modal?.classList.contains("visible")) this.closeOverview();
    };
  }

  async onLoad() {
    const response = await fetch(this.resolve(this.dataFile));
    if (!response.ok) throw new Error(`Unable to load flood-cause data (${response.status})`);
    this.data = await response.json();
    this.basins = (this.data.basins || []).map((item) => ({ ...item, _kind: "basin" }));
    this.catchments = (this.data.catchments || []).map((item) => ({ ...item, _kind: "catchment" }));
    this.ensureStyles();
    this.addLayers();
    this.ensureToolbar();
    this.updateLegend();
    Foundation.eventBus.on(Foundation.Events.FEATURE_CLICK, this.handleFeatureClick);
    this.app.draw?.();
  }

  onUnload() {
    [this.basinLayerId, this.catchmentLayerId]
      .forEach((id) => this.app.layerManager.removeLayer(id));
    this.app.unregisterLegend?.(this.legendId);
    Foundation.eventBus.off(Foundation.Events.FEATURE_CLICK, this.handleFeatureClick);
    document.removeEventListener("keydown", this.handleOverviewKeydown);
    this.toolbar?.remove();
    this.modal?.remove();
    this.hoverTooltip?.remove();
  }

  getLayerIds() {
    return [this.basinLayerId, this.catchmentLayerId];
  }

  resolve(path) {
    if (/^https?:\/\//i.test(path) || path.startsWith("/")) return path;
    return this.basePath + path.replace(/^\.\//, "");
  }

  addLayers() {
    this.app.layerManager.addLayer({
      id: this.basinLayerId,
      name: "HydroBASINS L5 regions",
      type: "vector",
      visible: true,
      interactive: true,
      moduleId: this.manifest.id,
      groupPath: ["flood-generating conditions"],
      metadata: { removable: false, evidenceScale: "multi-catchment region" },
      renderer: (ctx, _layer, viewport) => this.renderBasins(ctx, viewport),
      hitTest: (lon, lat) => this.hitTestBasins(lon, lat)
    });
    this.app.layerManager.addLayer({
      id: this.catchmentLayerId,
      name: "Eligible individual catchments",
      type: "vector",
      visible: true,
      interactive: true,
      moduleId: this.manifest.id,
      groupPath: ["flood-generating conditions"],
      metadata: { removable: false, evidenceScale: "single catchment" },
      renderer: (ctx, _layer, viewport) => this.renderCatchments(ctx, viewport),
      hitTest: (lon, lat, viewport) => this.hitTestCatchments(lon, lat, viewport)
    });
    this.app.updateLayerList?.();
  }

  renderBasins(ctx, viewport) {
    const shifts = this.worldShifts(viewport);
    const limit = this.outcome().limit;
    for (const basin of this.basins) {
      const metric = basin.metrics?.[this.metric];
      if (!metric) continue;
      for (const shift of shifts) {
        ctx.save();
        this.traceGeometry(ctx, basin.geometry, viewport, shift);
        ctx.lineJoin = "round";
        ctx.lineCap = "round";
        ctx.miterLimit = 1.4;
        ctx.fillStyle = this.colorFor(metric.slope, limit);
        ctx.globalAlpha = metric.strong ? 0.84 : 0.68;
        ctx.fill("evenodd");
        ctx.globalAlpha = 1;
        ctx.setLineDash([]);
        ctx.strokeStyle = "rgba(15, 23, 42, .72)";
        ctx.lineWidth = 0.72;
        ctx.stroke();
        ctx.restore();
      }
    }

    const activeBasin = this.selected?._kind === "basin"
      ? this.basins.find((basin) => basin.id === this.selected.id)
      : null;
    const hoveredBasin = this.app.hoveredLayer?.id === this.basinLayerId
      ? this.basins.find((basin) => basin.id === this.app.hoveredFeatureId)
      : null;
    if (activeBasin && activeBasin.id !== hoveredBasin?.id) {
      this.drawBasinHighlight(ctx, activeBasin, viewport, false);
    }
    if (hoveredBasin) {
      this.drawBasinHighlight(ctx, hoveredBasin, viewport, true);
    }
    this.updateHoverTooltip(ctx, viewport);
  }

  drawBasinHighlight(ctx, basin, viewport, hovered) {
    if (!basin?.metrics?.[this.metric]) return;
    for (const shift of this.worldShifts(viewport)) {
      ctx.save();
      this.traceGeometry(ctx, basin.geometry, viewport, shift);
      ctx.lineJoin = "round";
      ctx.lineCap = "round";
      ctx.miterLimit = 1.4;
      ctx.setLineDash([]);
      ctx.shadowColor = hovered ? "rgba(34, 211, 238, .98)" : "rgba(6, 182, 212, .94)";
      ctx.shadowBlur = hovered ? 28 : 22;
      ctx.strokeStyle = hovered ? "rgba(103, 232, 249, .98)" : "rgba(34, 211, 238, .98)";
      ctx.lineWidth = hovered ? 1.2 : 1.15;
      ctx.stroke();
      ctx.restore();
    }
  }

  renderCatchments(ctx, viewport) {
    const base = (viewport.height / 180) * viewport.scale;
    const shifts = this.worldShifts(viewport);
    const limit = this.catchmentLimit();
    for (const catchment of this.catchments) {
      const metric = catchment.metrics?.[this.metric];
      if (!metric) continue;
      const hovered = this.app.hoveredLayer?.id === this.catchmentLayerId && this.app.hoveredFeatureId === catchment.id;
      const active = this.selected?._kind === "catchment" && this.selected.id === catchment.id;
      for (const shift of shifts) {
        const x = viewport.width / 2 + (catchment.lon + shift) * base + viewport.offsetX;
        const y = viewport.height / 2 - catchment.lat * base + viewport.offsetY;
        if (x < -9 || x > viewport.width + 9 || y < -9 || y > viewport.height + 9) continue;
        const radius = active ? 4.7 : Math.max(1.8, Math.min(3.35, 1.5 + Math.sqrt(viewport.scale) * 0.5));
        ctx.save();
        ctx.beginPath();
        ctx.arc(x, y, radius, 0, Math.PI * 2);
        ctx.fillStyle = this.colorFor(metric.slope, limit);
        ctx.globalAlpha = 0.82;
        ctx.fill();
        ctx.globalAlpha = 1;
        if (hovered || active) {
          ctx.shadowColor = hovered ? "rgba(34, 211, 238, .98)" : "rgba(6, 182, 212, .94)";
          ctx.shadowBlur = hovered ? 22 : 17;
          ctx.strokeStyle = "rgba(103, 232, 249, .98)";
          ctx.lineWidth = 1.15;
        } else {
          ctx.strokeStyle = metric.fdrSupported ? "rgba(15, 23, 42, .9)" : "rgba(15, 23, 42, .42)";
          ctx.lineWidth = metric.fdrSupported ? 1.05 : 0.5;
        }
        ctx.stroke();
        ctx.restore();
      }
    }
    this.updateHoverTooltip(ctx, viewport);
  }

  updateHoverTooltip(ctx, viewport) {
    const layerId = this.app.hoveredLayer?.id;
    const featureId = this.app.hoveredFeatureId;
    if (![this.basinLayerId, this.catchmentLayerId].includes(layerId) || featureId == null) {
      this.hideHoverTooltip();
      return;
    }

    let feature = null;
    let point = null;
    if (layerId === this.basinLayerId) {
      feature = this.basins.find((item) => String(item.id) === String(featureId));
      if (feature) {
        const candidates = this.worldShifts(viewport)
          .map((shift) => this.project(feature.center[0] + shift, feature.center[1], viewport))
          .filter((item) => item.x > -100 && item.x < viewport.width + 100);
        point = candidates.sort((a, b) => Math.abs(a.x - viewport.width / 2) - Math.abs(b.x - viewport.width / 2))[0];
      }
    } else {
      feature = this.catchments.find((item) => String(item.id) === String(featureId));
      if (feature) {
        const base = (viewport.height / 180) * viewport.scale;
        const candidates = this.worldShifts(viewport).map((shift) => ({
          x: viewport.width / 2 + (feature.lon + shift) * base + viewport.offsetX,
          y: viewport.height / 2 - feature.lat * base + viewport.offsetY
        })).filter((item) => item.x > -20 && item.x < viewport.width + 20);
        point = candidates.sort((a, b) => Math.abs(a.x - viewport.width / 2) - Math.abs(b.x - viewport.width / 2))[0];
      }
    }

    const metric = feature?.metrics?.[this.metric];
    if (!feature || !metric || !point) {
      this.hideHoverTooltip();
      return;
    }
    const title = layerId === this.basinLayerId ? feature.code : `GCIN ${feature.id}`;
    this.showHoverTooltip(ctx, point.x, point.y, title, metric);
  }

  showHoverTooltip(ctx, x, y, title, metric) {
    if (!this.hoverTooltip) {
      this.hoverTooltip = document.createElement("div");
      this.hoverTooltip.className = "fce-hover-tooltip";
      this.hoverTooltip.setAttribute("role", "status");
      document.body.appendChild(this.hoverTooltip);
    }
    const outcome = this.outcome();
    const unit = this.metric === "intensity_fraction"
      ? "percentage points / decade"
      : "SSI units / decade";
    this.hoverTooltip.innerHTML = `<strong>${this.escape(title)}</strong><span>${this.escape(this.direction(metric.slope))}</span><b>${this.signed(metric.slope, outcome.digits)} <small>${unit}</small></b>`;
    this.hoverTooltip.classList.add("visible");

    const canvasRect = ctx.canvas.getBoundingClientRect();
    const scaleX = canvasRect.width / ctx.canvas.width;
    const scaleY = canvasRect.height / ctx.canvas.height;
    const anchorX = canvasRect.left + x * scaleX;
    const anchorY = canvasRect.top + y * scaleY;
    const width = this.hoverTooltip.offsetWidth;
    const height = this.hoverTooltip.offsetHeight;
    let left = anchorX + 14;
    let top = anchorY - height - 14;
    if (left + width > window.innerWidth - 10) left = anchorX - width - 14;
    if (top < 10) top = anchorY + 14;
    left = Math.max(10, Math.min(left, window.innerWidth - width - 10));
    top = Math.max(10, Math.min(top, window.innerHeight - height - 10));
    this.hoverTooltip.style.left = `${Math.round(left)}px`;
    this.hoverTooltip.style.top = `${Math.round(top)}px`;
  }

  hideHoverTooltip() {
    this.hoverTooltip?.classList.remove("visible");
  }

  worldShifts(viewport) {
    const base = (viewport.height / 180) * viewport.scale;
    const left = (-viewport.width / 2 - viewport.offsetX) / base;
    const right = (viewport.width / 2 - viewport.offsetX) / base;
    const shifts = [];
    for (let segment = Math.floor(left / 360) - 1; segment <= Math.ceil(right / 360) + 1; segment += 1) {
      shifts.push(segment * 360);
    }
    return shifts;
  }

  traceGeometry(ctx, geometry, viewport, shift) {
    ctx.beginPath();
    const polygons = geometry.type === "Polygon" ? [geometry.coordinates] : geometry.coordinates;
    for (const polygon of polygons) {
      for (const ring of polygon) {
        ring.forEach(([lon, lat], index) => {
          const point = this.project(lon + shift, lat, viewport);
          if (index === 0) ctx.moveTo(point.x, point.y);
          else ctx.lineTo(point.x, point.y);
        });
        ctx.closePath();
      }
    }
  }

  project(lon, lat, viewport) {
    const base = (viewport.height / 180) * viewport.scale;
    return {
      x: viewport.width / 2 + lon * base + viewport.offsetX,
      y: viewport.height / 2 - lat * base + viewport.offsetY
    };
  }

  hitTestBasins(lon, lat) {
    const normalized = ((lon + 180) % 360 + 360) % 360 - 180;
    for (let index = this.basins.length - 1; index >= 0; index -= 1) {
      const basin = this.basins[index];
      if (basin.metrics?.[this.metric] && this.geometryContains(basin.geometry, normalized, lat)) return basin;
    }
    return null;
  }

  geometryContains(geometry, lon, lat) {
    const polygons = geometry.type === "Polygon" ? [geometry.coordinates] : geometry.coordinates;
    return polygons.some((polygon) => this.ringContains(polygon[0], lon, lat)
      && !polygon.slice(1).some((ring) => this.ringContains(ring, lon, lat)));
  }

  ringContains(ring, lon, lat) {
    let inside = false;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i, i += 1) {
      const [xi, yi] = ring[i];
      const [xj, yj] = ring[j];
      if ((yi > lat) !== (yj > lat) && lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) inside = !inside;
    }
    return inside;
  }

  hitTestCatchments(lon, lat, viewport) {
    const normalized = ((lon + 180) % 360 + 360) % 360 - 180;
    const threshold = Math.max(0.08, 8 / ((viewport.height / 180) * viewport.scale));
    let best = null;
    let distance = Infinity;
    for (const catchment of this.catchments) {
      if (!catchment.metrics?.[this.metric]) continue;
      const current = Math.hypot(this.lonDistance(normalized, catchment.lon), lat - catchment.lat);
      if (current < threshold && current < distance) {
        best = catchment;
        distance = current;
      }
    }
    return best;
  }

  lonDistance(a, b) {
    let value = a - b;
    while (value > 180) value -= 360;
    while (value < -180) value += 360;
    return value;
  }

  setMetric(metric) {
    if (!this.data.meta.outcomes[metric]) return;
    this.metric = metric;
    this.toolbar?.querySelectorAll("[data-metric]")
      .forEach((button) => button.classList.toggle("active", button.dataset.metric === metric));
    this.updateLegend();
    if (this.selected) {
      const layerId = this.selected._kind === "basin" ? this.basinLayerId : this.catchmentLayerId;
      this.showInspector(this.selected, layerId);
    }
    this.app.draw?.();
  }

  ensureToolbar() {
    this.toolbar = document.createElement("div");
    this.toolbar.className = "fce-toolbar";
    this.toolbar.innerHTML = `
      <div class="fce-toolbar-label">Flood-generating condition</div>
      <div class="fce-segmented" aria-label="Metric selector">
        <button data-metric="intensity_fraction" class="active">Rainfall concentration</button>
        <button data-metric="ssi_1d">SSI 1d</button>
        <button data-metric="ssi_3d">3d</button>
        <button data-metric="ssi_7d">7d</button>
        <button data-metric="ssi_30d">30d</button>
      </div>
      <button class="fce-overview-button" data-overview>Research overview</button>`;
    document.body.appendChild(this.toolbar);
    this.toolbar.querySelectorAll("[data-metric]")
      .forEach((button) => button.addEventListener("click", () => this.setMetric(button.dataset.metric)));
    this.toolbar.querySelector("[data-overview]").addEventListener("click", () => this.showOverview());
  }

  updateLegend() {
    const outcome = this.outcome();
    const limit = outcome.limit;
    this.app.unregisterLegend?.(this.legendId);
    this.app.registerLegend?.(this.legendId, {
      title: outcome.short,
      html: `
        <div class="fce-legend-scale-title">HydroBASINS L5 trend</div>
        <div class="fce-legend-bar"></div>
        <div class="fce-legend-axis"><span>${this.axisValue(-limit)}</span><span>0</span><span>+${this.axisValue(limit)}</span></div>
        <div class="fce-legend-directions"><span>${this.escape(outcome.low)}</span><span>${this.escape(outcome.high)}</span></div>
        <div class="fce-legend-unit">${this.escape(outcome.unit)}. Values beyond the color scale are clipped.</div>
        <div class="fce-legend-key"><i class="boundary"></i> Eligible L5 region (≥${this.data.meta.minimumCatchments} catchments)</div>
        <div class="fce-legend-key"><i class="glow"></i> Hover / selected feature</div>
        <div class="fce-legend-key"><i class="dot"></i> Eligible individual catchment</div>
        <div class="fce-legend-note">Strong evidence is identified in the inspector; color alone is not a significance claim.</div>`
    });
  }

  showInspector(feature, layerId) {
    const metric = feature.metrics?.[this.metric];
    const outcome = this.outcome();
    if (!metric) return;
    if (layerId === this.basinLayerId) {
      const status = metric.strong ? "Strong regional evidence" : "Eligible regional estimate";
      const statusClass = metric.strong ? "pass" : "neutral";
      const interpretation = this.interpretation(metric.slope);
      this.app.showInspector?.(`${feature.code} · ${feature.countries}`, `
        <p class="fce-inspector-lead">HydroBASINS level-5 multi-catchment estimate · ${this.escape(outcome.label)}</p>
        <div class="fce-status ${statusClass}">${status}</div>
        <div class="fce-plain-result">${this.escape(interpretation)}</div>
        ${this.signal(metric, "Change per decade")}
        <div class="fce-grid">
          ${this.fact("95% CI", `${this.signed(metric.ci?.[0], outcome.digits)} to ${this.signed(metric.ci?.[1], outcome.digits)}`)}
          ${this.fact("Complete-family q", this.prob(metric.q))}
          ${this.fact("Catchments", this.integer(metric.catchments))}
          ${this.fact("Event observations", this.integer(metric.observations))}
          ${this.fact("Mean condition", this.num(metric.mean, outcome.digits))}
          ${this.metric.startsWith("ssi_") ? this.fact("Relative change", `${this.signed(metric.relativeSlope, 2)}% per decade`) : ""}
          ${this.fact("HydroBASINS L5", feature.code)}
        </div>
        ${this.trajectory(metric, outcome)}
        ${this.sensitivity(metric, outcome)}
        ${this.drivers(feature)}
        ${this.gates(metric)}
        <p class="fce-note">${this.escape(outcome.definition)} Every mapped region contains at least ${this.data.meta.minimumCatchments} contributing catchments; the model controls their stable differences.</p>`);
      return;
    }

    this.app.showInspector?.(`GCIN ${feature.id} · ${feature.country}`, `
      <p class="fce-inspector-lead">Eligible single-catchment Theil–Sen trend · ${this.escape(outcome.label)}</p>
      <div class="fce-plain-result">${this.escape(this.interpretation(metric.slope, true))}</div>
      ${this.signal(metric, "Catchment change per decade")}
      <div class="fce-grid">
        ${this.fact("95% CI", `${this.signed(metric.ci?.[0], outcome.digits)} to ${this.signed(metric.ci?.[1], outcome.digits)}`)}
        ${this.fact("Catchment-family q", this.prob(metric.q))}
        ${this.fact("Selected events", this.integer(metric.observations))}
        ${this.fact("Observed event years", this.integer(metric.years))}
        ${this.fact("Event-year range", `${metric.firstYear}–${metric.lastYear}`)}
        ${this.fact("Time span", `${metric.span} years`)}
        ${this.fact("Kendall tau", this.signed(metric.tau, 3))}
        ${this.fact("HydroBASINS L5", feature.hydrobasinId || "Unmatched")}
      </div>
      <div class="fce-status ${metric.fdrSupported ? "pass" : "neutral"}">${metric.fdrSupported ? "Passes catchment-level 5% FDR" : "Does not pass catchment-level 5% FDR"}</div>
      <p class="fce-note">Only catchments with at least 10 selected POT/Q95 events spanning at least 20 years are displayed. Single-catchment points give local context; the multi-catchment HydroBASINS layer is the primary spatial evidence.</p>`);
  }

  interpretation(slope, single = false) {
    const direction = Number(slope) >= 0 ? this.outcome().high : this.outcome().low;
    const subject = single ? "At this catchment" : "Across catchments in this region";
    return `${subject}, the selected large-flood events shifted ${direction}.`;
  }

  signal(metric, label) {
    const outcome = this.outcome();
    return `<div class="fce-signal"><span>${label}</span><strong style="color:${this.colorFor(metric?.slope, outcome.limit)}">${this.signed(metric?.slope, outcome.digits)}</strong><small>${this.escape(outcome.unit)}</small><p>${this.metricMeaning(metric)}</p></div>`;
  }

  trajectory(metric, outcome) {
    const rows = metric?.trajectory || [];
    if (rows.length < 2) return "";
    const width = 320;
    const height = 150;
    const pad = { left: 35, right: 10, top: 14, bottom: 25 };
    const values = rows.flatMap((row) => [Number(row[1]), Number(row[2])]).filter(Number.isFinite);
    let min = Math.min(...values);
    let max = Math.max(...values);
    const spread = Math.max(max - min, outcome.group === "Antecedent wetness" ? 0.02 : 2);
    min -= spread * 0.12;
    max += spread * 0.12;
    const x = (year) => pad.left + ((year - rows[0][0]) / Math.max(1, rows[rows.length - 1][0] - rows[0][0])) * (width - pad.left - pad.right);
    const y = (value) => pad.top + ((max - value) / (max - min)) * (height - pad.top - pad.bottom);
    const fit = rows.map((row, index) => `${index ? "L" : "M"}${x(row[0]).toFixed(1)},${y(row[2]).toFixed(1)}`).join(" ");
    const dots = rows.map((row) => `<circle cx="${x(row[0]).toFixed(1)}" cy="${y(row[1]).toFixed(1)}" r="2.2"><title>${row[0]}: ${this.num(row[1], outcome.digits)} · ${row[4]} events</title></circle>`).join("");
    return `<div class="fce-chart"><div class="fce-subhead"><b>Continuous-time trajectory</b><span>adjusted annual mean + fitted trend</span></div>
      <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Annual trajectory from ${rows[0][0]} to ${rows[rows.length - 1][0]}">
        <line class="grid" x1="${pad.left}" x2="${width - pad.right}" y1="${y(min).toFixed(1)}" y2="${y(min).toFixed(1)}"/>
        <line class="grid" x1="${pad.left}" x2="${width - pad.right}" y1="${y(max).toFixed(1)}" y2="${y(max).toFixed(1)}"/>
        <text x="${pad.left}" y="${height - 6}">${rows[0][0]}</text><text x="${width - pad.right}" y="${height - 6}" text-anchor="end">${rows[rows.length - 1][0]}</text>
        <text x="${pad.left - 5}" y="${y(max).toFixed(1) + 4}" text-anchor="end">${this.num(max, outcome.digits)}</text>
        <text x="${pad.left - 5}" y="${y(min).toFixed(1) + 4}" text-anchor="end">${this.num(min, outcome.digits)}</text>
        <g class="observed">${dots}</g><path class="fit" d="${fit}"/>
      </svg></div>`;
  }

  sensitivity(metric, outcome) {
    const entries = Object.entries(metric?.sensitivities || {});
    if (!entries.length) return "";
    return `<div class="fce-block"><div class="fce-subhead"><b>Extreme-sample sensitivity</b><span>same metric, alternative samples</span></div><div class="fce-sensitivity">${entries.map(([name, value]) => {
      const available = Number.isFinite(Number(value));
      const same = available && Math.sign(Number(value)) === Math.sign(Number(metric.slope));
      return `<div class="${available ? (same ? "same" : "different") : "missing"}"><span>${this.escape(name)}</span><strong>${this.signed(value, outcome.digits)}</strong></div>`;
    }).join("")}</div></div>`;
  }

  drivers(feature) {
    if (this.metric !== "intensity_fraction") return "";
    const entries = Object.values(feature.drivers || {});
    if (!entries.length) return "";
    return `<div class="fce-block"><div class="fce-subhead"><b>Rainfall-process decomposition</b><span>raw linear slope ÷ catchment-equal mean</span></div><div class="fce-drivers">${entries.map((item) => `<div><span>${this.escape(item.label)}</span><strong>${this.signed(item.slope, 1)}%</strong><small>95% CI ${this.signed(item.ci?.[0], 1)} to ${this.signed(item.ci?.[1], 1)}% / decade</small></div>`).join("")}</div></div>`;
  }

  gates(metric) {
    if (!metric) return "";
    const gates = [
      ["Complete-family FDR", metric.fdrSupported],
      [`≥${this.data.meta.minimumCatchments} catchments`, metric.catchments >= this.data.meta.minimumCatchments],
      ["Extreme-sample direction", metric.sampleStable],
      ["SSI-window direction", metric.windowStable],
      ["Leave-one-catchment-out", metric.jackknifeStable]
    ];
    return `<div class="fce-gates">${gates.map(([name, pass]) => `<span class="${pass ? "pass" : "fail"}">${pass ? "✓" : "·"} ${name}</span>`).join("")}</div>`;
  }

  fact(label, value) {
    return `<div class="fce-fact"><span>${label}</span><strong>${value}</strong></div>`;
  }

  showOverview() {
    this.ensureModal();
    const meta = this.data.meta;
    const outcome = this.outcome();
    const rankings = (meta.ranking || []).slice(0, 12);
    const figures = [
      {
        id: "coverage",
        number: "01",
        title: "The evidence base is broad, but not spatially uniform",
        image: "reports/assets/figure_01_sample_coverage.png",
        alt: "Coverage of the eligible long-record catchments and the primary POT/Q95 sample",
        text: `Long-record screening leaves ${meta.primaryCatchments.toLocaleString()} catchments and ${meta.primaryEvents.toLocaleString()} selected events. Europe and North America are much denser than Asia, so “global” refers to the observed network rather than an area-weighted land surface.`
      },
      {
        id: "spatial-change",
        number: "02",
        title: "Changes separate into opposing local directions",
        image: "reports/assets/figure_02_mechanism_change_maps.png",
        alt: "HydroBASINS level-5 maps of rainfall organization and antecedent wetness trends",
        text: `${meta.eligibleHydrobasins} eligible HydroBASINS L5 regions contain both positive and negative shifts. The primary result is this local spatial heterogeneity—not a single global mean direction.`
      },
      {
        id: "magnitude",
        number: "03",
        title: "The strongest local shifts are large enough to interpret",
        image: "reports/assets/figure_03_strong_signal_rankings.png",
        alt: "Ranked strong-evidence regional trends in rainfall concentration and antecedent wetness",
        text: `${meta.strongByMetric?.intensity_fraction || 0} strong rainfall-concentration signals span −2.54 to +2.92 percentage points per decade. Strong SSI signals also occur in both wetter and drier directions across the 1–30 day windows.`
      },
      {
        id: "trajectories",
        number: "04",
        title: "Continuous trajectories show how conditions moved through time",
        image: "reports/assets/figure_04_mechanism_trajectories.png",
        alt: "Continuous-time trajectories for representative HydroBASINS regions",
        text: "Annual adjusted means and fitted trends retain the full 1982–2019 record. They show sustained movement without inventing a calendar breakpoint or reducing the result to an early-versus-late contrast."
      },
      {
        id: "decomposition",
        number: "05",
        title: "Rainfall components give the ratio a physical reading",
        image: "reports/assets/figure_05_physical_decomposition.png",
        alt: "Physical decomposition of rainfall-concentration changes into maximum daily rain, event total, and duration",
        text: "Changes in Pmax/Pvolume are read alongside maximum daily rainfall, event rainfall total, and duration. This distinguishes increasingly concentrated events from longer, volume-dominated events while avoiding a causal attribution claim."
      },
      {
        id: "robustness",
        number: "06",
        title: "Strong signals survive alternative definitions of a large flood",
        image: "reports/assets/figure_06_robustness_matrix.png",
        alt: "Sensitivity matrix across annual maxima, POT/Q90, declustered POT/Q95, and POT/Q97.5 samples",
        text: "Annual maxima, POT/Q90, 10-day-declustered POT/Q95, and POT/Q97.5 provide independent stress tests. The reported strong signals retain their direction across all four alternatives."
      }
    ];
    this.modal.querySelector(".fce-modal-body").innerHTML = `
      <section class="fce-hero fce-overview-section" id="overview-summary">
        <span class="fce-kicker">${meta.period} · rainfall-driven large floods</span>
        <h2>Where did flood-generating conditions move—and how?</h2>
        <p>This project asks how the conditions producing large rainfall-driven floods changed through time. It follows whether event rainfall became more concentrated or more prolonged, and whether the land before the event became wetter or drier. Opposing local changes are retained instead of being averaged into one global direction.</p>
      </section>
      <div class="fce-kpis">
        ${this.kpi(meta.primaryEvents.toLocaleString(), "selected POT/Q95 events")}
        ${this.kpi(meta.primaryCatchments.toLocaleString(), "eligible catchments")}
        ${this.kpi(meta.eligibleHydrobasins, "mapped L5 regions")}
        ${this.kpi(meta.strongEvidenceBasins, "regions with strong evidence")}
      </div>
      <section class="fce-overview-section" id="research-question"><span class="fce-section-index">Research question</span><h3>The target is a process trajectory, not a flood-count trend</h3>
        <p class="fce-section-lead"><b>Main answer.</b> The observed network does not support one uniform global direction. It supports reproducible, directionally opposed changes in the generating conditions of large floods within ${meta.strongEvidenceBasins} smaller hydrological regions.</p>
        <div class="fce-reading">
        <div><b>Rainfall organization</b><span>Pmax/Pvolume measures how much of an event's rain fell in its wettest day. Positive change means more concentrated rainfall; negative change means more prolonged, volume-dominated rainfall.</span></div>
        <div><b>Antecedent wetness</b><span>SSI summarizes soil wetness before rainfall starts. The 1-, 3-, 7- and 30-day windows show whether a result depends on the chosen memory window.</span></div>
        <div><b>Two spatial layers</b><span>Colored polygons pool neighboring catchments within HydroBASINS L5. Points retain eligible single-catchment trends for local inspection.</span></div>
      </div></section>
      <section class="fce-overview-section" id="key-findings"><span class="fce-section-index">Evidence at a glance</span><h3>Strongest reproducible local signals</h3><p class="fce-section-note">Select a row to switch the mapped metric and open that HydroBASINS unit.</p>
        <div class="fce-ranking">${rankings.map((item) => {
          const definition = meta.outcomes[item.metric];
          return `<button data-basin="${item.basinId}" data-outcome="${item.metric}"><span>${this.escape(item.code)} · ${this.escape(definition.short)}</span><strong>${this.signed(item.slope, definition.digits)}</strong><i style="width:${Math.min(100, item.score * 100)}%;background:${this.colorFor(item.slope, definition.limit)}"></i></button>`;
        }).join("")}</div>
      </section>
      ${figures.map((figure) => this.overviewFigure(figure)).join("")}
      <section class="fce-overview-section" id="methods"><span class="fce-section-index">Analysis design</span><h3>Selection, description, and inference are kept separate</h3>
        <div class="fce-method-grid">
          <div><b>1 · Select large floods</b><span>The primary population is catchment-specific POT/Q95. Flood-peak magnitude selects events; it does not assign their generating condition.</span></div>
          <div><b>2 · Preserve continuous descriptors</b><span>Rainfall organization and four antecedent-wetness windows remain continuous before any summary or evidence grade is applied.</span></div>
          <div><b>3 · Estimate continuous time trends</b><span>HydroBASINS L5 fixed-effect models compare within-catchment change over ${meta.period} while controlling stable differences among catchments.</span></div>
          <div><b>4 · Stress-test the direction</b><span>Every region first clears the single ≥${meta.minimumCatchments}-catchment rule; strong evidence then combines complete-family FDR, four extreme-event populations, leave-one-catchment-out stability, and SSI-window agreement.</span></div>
        </div>
      </section>
      <section class="fce-overview-section" id="statistics"><span class="fce-section-index">Statistical meaning</span><h3>One regional threshold and one declared multiple-testing family</h3>
        <div class="fce-method-grid">
          <div><b>≥${meta.minimumCatchments} catchments</b><span>This is the only regional inclusion threshold. Smaller L5 units are not mapped. Twenty is a conservative lower design bound for conventional catchment-clustered inference, not a theorem of exact finite-sample validity.</span></div>
          <div><b>${meta.primaryFamilyTests} primary tests</b><span>${meta.eligibleHydrobasins} L5 regions × five continuous metrics form one Benjamini–Hochberg family. ${meta.fdrSupportedSignals} pass 5% False Discovery Rate control; testing each at unadjusted p&lt;0.05 would yield about ${(meta.primaryFamilyTests * .05).toFixed(1)} chance positives if all nulls were true.</span></div>
          <div><b>Within-catchment change</b><span>Fixed effects compare every catchment with its own long-run baseline. The year 2000 is only a centering constant and is not a breakpoint.</span></div>
          <div><b>Absolute + relative scale</b><span>SSI remains in raw index units and also shows slope ÷ catchment-equal mean. Rainfall components use raw linear slopes converted to the same relative scale; no logarithmic model is used.</span></div>
        </div>
        <p class="fce-note">Adjusted annual trajectories mean: after placing all catchments on the same long-run mean, how far above or below their own normal level were that year's participating catchments on average?</p>
      </section>
      <section class="fce-overview-section" id="interpretation"><span class="fce-section-index">Inference boundary</span><h3>What the evidence can—and cannot—support</h3>
        <div class="fce-claims">
          <div class="can"><b>Supported</b><ul><li>Generating conditions changed reproducibly in some smaller hydrological regions.</li><li>Local rainfall-organization changes reach several percentage points per decade.</li><li>Wetness shifts occur in both wetter and drier directions and persist across 1–30 day windows.</li></ul></div>
          <div class="cannot"><b>Not supported</b><ul><li>A spatially uniform or area-weighted global land trend.</li><li>A claim about flood counts, peak flow, or flood volume themselves.</li><li>Direct attribution to climate change, land use, or engineering controls.</li></ul></div>
        </div>
        <p class="fce-note">Current map metric: <b>${this.escape(outcome.label)}</b> — ${this.escape(outcome.definition)} Primary sample: ${this.escape(meta.primarySample)}.</p>
      </section>
      <section class="fce-overview-section" id="resources"><span class="fce-section-index">Project materials</span><h3>Read, audit, and reproduce the study</h3>
        <p class="fce-section-lead">The overview is the reading spine; the links below expose the complete report, definitions, scientific positioning, quality checks, results, and executable workflow without duplicating them into disconnected pages.</p>
        <div class="fce-resource-grid">
          ${this.overviewResource("Complete browser report", "Long-form Chinese report with all figures and click-to-enlarge reading.", this.resolve("reports/global_flood_cause_evolution.html"))}
          ${this.overviewResource("English technical report", "Complete English methods, formulas, results, limitations, and reproducibility record.", "https://github.com/Grups666/Global_Flood_Cause_Evolution/blob/main/reports/global_flood_cause_evolution_en.md")}
          ${this.overviewResource("Analysis protocol", "Population, metrics, continuous-time models, spatial inference, and evidence grades.", "https://github.com/Grups666/Global_Flood_Cause_Evolution/blob/main/docs/methods/analysis_protocol.md")}
          ${this.overviewResource("Data dictionary", "Source assets, derived event features, samples, and result tables.", "https://github.com/Grups666/Global_Flood_Cause_Evolution/blob/main/docs/methods/data_dictionary.md")}
          ${this.overviewResource("Literature and positioning", "Why event selection, continuous process dimensions, and local heterogeneity matter.", "https://github.com/Grups666/Global_Flood_Cause_Evolution/blob/main/docs/background/literature_review.md")}
          ${this.overviewResource("Validation report", "Recalculation, figure, record-eligibility, web-data, and reproducibility checks.", "https://github.com/Grups666/Global_Flood_Cause_Evolution/blob/main/docs/quality/validation_report.md")}
          ${this.overviewResource("Results and code", "Generated tables, analysis scripts, figure code, and the complete execution entry point.", "https://github.com/Grups666/Global_Flood_Cause_Evolution")}
        </div>
      </section>`;
    this.modal.classList.add("visible");
    const scroll = this.modal.querySelector(".fce-modal-scroll");
    scroll.scrollTop = 0;
    this.syncOverviewNav();
    this.modal.querySelectorAll("[data-basin]").forEach((button) => button.addEventListener("click", () => {
      this.setMetric(button.dataset.outcome);
      const basin = this.basins.find((item) => item.id === button.dataset.basin);
      if (basin) {
        this.selected = basin;
        this.closeOverview();
        this.showInspector(basin, this.basinLayerId);
        this.app.draw?.();
      }
    }));
    this.modal.querySelectorAll("[data-figure]").forEach((button) => button.addEventListener("click", () => {
      this.openOverviewFigure(button.dataset.figure, button.dataset.alt);
    }));
  }

  metricMeaning(metric) {
    const value = Math.abs(Number(metric?.slope));
    const direction = Number(metric?.slope) >= 0 ? "increases" : "decreases";
    if (this.metric === "intensity_fraction") {
      return `Wettest-day share of event rainfall ${direction} by <b>${value.toFixed(2)} percentage points over 10 years</b>.`;
    }
    const relative = Math.abs(Number(metric?.relativeSlope));
    const relativeText = Number.isFinite(relative) ? `, equal to <b>${relative.toFixed(2)}% of this region's catchment-equal mean</b>` : "";
    return `Mean pre-event soil wetness ${direction} by <b>${value.toFixed(3)} SSI units over 10 years</b>${relativeText}.`;
  }

  ensureModal() {
    if (this.modal) return;
    this.modal = document.createElement("div");
    this.modal.className = "fce-modal";
    this.modal.innerHTML = `<div class="fce-modal-card">
      <aside class="fce-overview-nav">
        <div class="fce-nav-brand"><strong>Research overview</strong><span>Global Flood Cause Evolution</span></div>
        <nav aria-label="Research overview sections">
          <button data-scroll="overview-summary" class="active"><i>01</i><span>Summary</span></button>
          <button data-scroll="research-question"><i>02</i><span>Research question</span></button>
          <button data-scroll="key-findings"><i>03</i><span>Key signals</span></button>
          <button data-scroll="coverage"><i>04</i><span>Sample coverage</span></button>
          <button data-scroll="spatial-change"><i>05</i><span>Spatial changes</span></button>
          <button data-scroll="magnitude"><i>06</i><span>Local magnitude</span></button>
          <button data-scroll="trajectories"><i>07</i><span>Trajectories</span></button>
          <button data-scroll="decomposition"><i>08</i><span>Physical reading</span></button>
          <button data-scroll="robustness"><i>09</i><span>Robustness</span></button>
          <button data-scroll="methods"><i>10</i><span>Methods</span></button>
          <button data-scroll="statistics"><i>11</i><span>Statistical meaning</span></button>
          <button data-scroll="interpretation"><i>12</i><span>Inference boundary</span></button>
          <button data-scroll="resources"><i>13</i><span>Project materials</span></button>
        </nav>
        <div class="fce-nav-foot">1982–2019 · verified record</div>
      </aside>
      <div class="fce-modal-scroll"><button class="fce-close" aria-label="Close overview">×</button><div class="fce-modal-body"></div></div>
    </div>
    <div class="fce-figure-viewer" aria-hidden="true"><button class="fce-figure-close" aria-label="Close enlarged figure">×</button><figure><img alt=""><figcaption></figcaption></figure></div>`;
    document.body.appendChild(this.modal);
    this.modal.querySelector(".fce-close").addEventListener("click", () => this.closeOverview());
    this.modal.addEventListener("click", (event) => { if (event.target === this.modal) this.closeOverview(); });
    this.modal.querySelectorAll("[data-scroll]").forEach((button) => button.addEventListener("click", () => {
      const target = this.modal.querySelector(`#${button.dataset.scroll}`);
      const scroll = this.modal.querySelector(".fce-modal-scroll");
      if (target && scroll) scroll.scrollTo({ top: target.offsetTop - 20, behavior: "smooth" });
    }));
    this.modal.querySelector(".fce-modal-scroll").addEventListener("scroll", () => this.syncOverviewNav(), { passive: true });
    this.modal.querySelector(".fce-figure-close").addEventListener("click", () => this.closeOverviewFigure());
    this.modal.querySelector(".fce-figure-viewer").addEventListener("click", (event) => {
      if (event.target.classList.contains("fce-figure-viewer")) this.closeOverviewFigure();
    });
    document.addEventListener("keydown", this.handleOverviewKeydown);
  }

  closeOverview() {
    this.closeOverviewFigure();
    this.modal?.classList.remove("visible");
  }

  overviewFigure(figure) {
    const src = this.resolve(figure.image);
    return `<section class="fce-overview-section fce-evidence-section" id="${figure.id}">
      <span class="fce-section-index">Figure ${figure.number}</span><h3>${this.escape(figure.title)}</h3>
      <p class="fce-section-lead">${this.escape(figure.text)}</p>
      <button class="fce-report-figure" data-figure="${this.escape(src)}" data-alt="${this.escape(figure.alt)}" aria-label="Open Figure ${figure.number} at full size">
        <img src="${this.escape(src)}" alt="${this.escape(figure.alt)}" loading="lazy"><span>Click to enlarge</span>
      </button>
    </section>`;
  }

  overviewResource(title, description, href) {
    return `<a href="${this.escape(href)}" target="_blank" rel="noopener"><b>${this.escape(title)}</b><span>${this.escape(description)}</span><i>Open ↗</i></a>`;
  }

  syncOverviewNav() {
    if (!this.modal?.classList.contains("visible")) return;
    const scroll = this.modal.querySelector(".fce-modal-scroll");
    const sections = [...this.modal.querySelectorAll(".fce-overview-section")];
    if (!scroll || !sections.length) return;
    let current = sections[0];
    const anchor = scroll.scrollTop + 120;
    sections.forEach((section) => { if (section.offsetTop <= anchor) current = section; });
    this.modal.querySelectorAll("[data-scroll]").forEach((button) => {
      button.classList.toggle("active", button.dataset.scroll === current.id);
    });
  }

  openOverviewFigure(src, alt) {
    const viewer = this.modal?.querySelector(".fce-figure-viewer");
    if (!viewer) return;
    const image = viewer.querySelector("img");
    image.src = src;
    image.alt = alt || "Research figure";
    viewer.querySelector("figcaption").textContent = alt || "";
    viewer.classList.add("open");
    viewer.setAttribute("aria-hidden", "false");
  }

  closeOverviewFigure() {
    const viewer = this.modal?.querySelector(".fce-figure-viewer");
    if (!viewer) return;
    viewer.classList.remove("open");
    viewer.setAttribute("aria-hidden", "true");
    viewer.querySelector("img")?.removeAttribute("src");
  }

  kpi(value, label) {
    return `<div><strong>${value}</strong><span>${label}</span></div>`;
  }

  outcome() {
    return this.data.meta.outcomes[this.metric];
  }

  direction(value) {
    return Number(value) >= 0 ? this.outcome().high : this.outcome().low;
  }

  catchmentLimit() {
    if (this.metric === "intensity_fraction") return 15;
    return 0.04;
  }

  axisValue(value) {
    return Math.abs(value) < 0.1 ? Number(value).toFixed(3) : Number(value).toFixed(1).replace(/\.0$/, "");
  }

  integer(value) {
    return Number.isFinite(Number(value)) ? Number(value).toLocaleString() : "—";
  }

  num(value, digits = 2) {
    return Number.isFinite(Number(value)) ? Number(value).toFixed(digits) : "—";
  }

  prob(value) {
    return Number.isFinite(Number(value)) ? (Number(value) < 0.001 ? "<0.001" : Number(value).toFixed(3)) : "—";
  }

  signed(value, digits = 2) {
    return Number.isFinite(Number(value)) ? `${Number(value) > 0 ? "+" : ""}${Number(value).toFixed(digits)}` : "—";
  }

  escape(value) {
    const div = document.createElement("div");
    div.textContent = value == null ? "" : String(value);
    return div.innerHTML;
  }

  colorFor(value, maxAbs) {
    if (!Number.isFinite(Number(value))) return "#aeb8c2";
    const t = Math.max(-1, Math.min(1, Number(value) / maxAbs));
    return t < 0 ? this.mix("#2b6487", "#ebe8de", t + 1) : this.mix("#ebe8de", "#cf673f", t);
  }

  mix(a, b, t) {
    const parse = (hex) => [1, 3, 5].map((index) => parseInt(hex.slice(index, index + 2), 16));
    const aa = parse(a);
    const bb = parse(b);
    return `rgb(${aa.map((value, index) => Math.round(value + (bb[index] - value) * t)).join(",")})`;
  }

  ensureStyles() {
    if (document.getElementById("fce-styles")) return;
    const style = document.createElement("style");
    style.id = "fce-styles";
    style.textContent = `
      .panel-section-header{font-size:13px}.module-item,.layer-item,.layer-expandable,.layer-sublayer,.map-display-option{font-size:13px}.legend-card{font-size:12px;padding:13px 14px}.legend-title{font-size:14px}.inspector-title{font-size:16px}.inspector-body{font-size:13px;line-height:1.55}
      .fce-hover-tooltip{position:fixed;z-index:1095;display:none;min-width:245px;max-width:min(390px,calc(100vw - 20px));padding:11px 13px;border:1px solid #334155;border-radius:11px;background:#172235;color:#f8fafc;box-shadow:0 13px 34px rgba(15,23,42,.32);opacity:1;pointer-events:none;font:13px/1.35 Inter,system-ui,sans-serif}.fce-hover-tooltip.visible{display:block}.fce-hover-tooltip strong,.fce-hover-tooltip span,.fce-hover-tooltip b{display:block}.fce-hover-tooltip strong{font-size:13px;color:#fff}.fce-hover-tooltip span{margin-top:3px;color:#d7e1e8;font-size:12px}.fce-hover-tooltip b{margin-top:6px;color:#67e8f9;font-size:14px}.fce-hover-tooltip small{color:#d7e1e8;font-size:11px;font-weight:600}
      .fce-toolbar{position:fixed;top:14px;left:50%;transform:translateX(-50%);z-index:850;display:flex;align-items:center;gap:10px;max-width:calc(100vw - 32px);padding:9px 10px 9px 14px;border:1px solid rgba(148,163,184,.35);border-radius:14px;background:rgba(255,255,255,.95);box-shadow:0 10px 30px rgba(15,23,42,.12);backdrop-filter:blur(16px);font:13px/1.25 Inter,system-ui,sans-serif;color:#334155}.fce-toolbar-label{font-weight:750;white-space:nowrap}.fce-segmented{display:flex;padding:3px;border-radius:10px;background:#edf1f4}.fce-segmented button,.fce-overview-button{border:0;border-radius:8px;padding:8px 10px;background:transparent;color:#526171;font:650 12px Inter,system-ui;white-space:nowrap;cursor:pointer}.fce-segmented button.active{background:#fff;color:#173d55;box-shadow:0 2px 8px rgba(15,23,42,.1)}.fce-overview-button{background:#173d55;color:#fff}
      .fce-legend-scale-title{margin:6px 0 5px;font-size:12px;font-weight:750;color:#475569}.fce-legend-bar{height:11px;border-radius:99px;background:linear-gradient(90deg,#2b6487,#ebe8de 50%,#cf673f)}.fce-legend-axis{display:flex;justify-content:space-between;margin-top:4px;font:12px/1.25 ui-monospace,monospace;color:#64748b}.fce-legend-directions{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:6px;font-size:12px;line-height:1.35;color:#526171}.fce-legend-directions span:last-child{text-align:right}.fce-legend-unit,.fce-legend-note{margin:9px 0;font-size:12px;line-height:1.5;color:#64748b}.fce-legend-key{display:flex;align-items:center;gap:8px;margin-top:8px;font-size:12px;line-height:1.35;color:#475569}.fce-legend-key i{display:inline-block;flex:0 0 auto;width:19px;height:10px}.fce-legend-key .boundary{border:1px solid #172235;background:#d8d3c7}.fce-legend-key .glow{height:5px;border:1px solid #67e8f9;box-shadow:0 0 8px 4px rgba(34,211,238,.7)}.fce-legend-key .dot{width:9px;height:9px;border-radius:50%;background:#527b95;border:1px solid #334155}
      .fce-inspector-lead,.fce-note{font-size:12px;line-height:1.65;color:#64748b}.fce-plain-result{margin:12px 0 0;padding:11px 12px;border-left:3px solid #22d3ee;border-radius:0 9px 9px 0;background:#eefbfc;font-size:13px;font-weight:650;line-height:1.5;color:#214558}.fce-signal{margin:12px 0;padding:15px;border-radius:12px;background:#f3f6f7}.fce-signal span,.fce-signal small{display:block;color:#64748b;font-size:12px}.fce-signal strong{display:block;margin:5px 0 3px;font-size:30px;letter-spacing:-.04em}.fce-signal p{margin:10px 0 0;padding-top:9px;border-top:1px solid #dce5e9;color:#526b7b;font-size:12px;line-height:1.5}.fce-signal p b{color:#24465a}.fce-grid{display:grid;grid-template-columns:1fr 1fr;gap:9px}.fce-fact{padding:11px;border:1px solid #dfe6eb;border-radius:10px}.fce-fact span,.fce-fact strong{display:block}.fce-fact span{font-size:12px;line-height:1.3;text-transform:uppercase;letter-spacing:.025em;color:#6f7f8e}.fce-fact strong{margin-top:5px;font-size:13px;color:#263646}.fce-status{display:inline-block;margin-top:12px;padding:6px 10px;border-radius:99px;font:650 12px/1.25 Inter,system-ui}.fce-status.pass{background:#e3efe7;color:#315e45}.fce-status.neutral{background:#eef1f3;color:#667482}
      .fce-block,.fce-chart{margin-top:15px;padding-top:13px;border-top:1px solid #e2e8ec}.fce-subhead{display:flex;justify-content:space-between;gap:10px;align-items:baseline;margin-bottom:9px}.fce-subhead b{font-size:13px;color:#314455}.fce-subhead span{font-size:12px;color:#7a8793}.fce-chart svg{display:block;width:100%;height:auto;overflow:visible}.fce-chart svg text{font:11px Inter,system-ui;fill:#758290}.fce-chart .grid{stroke:#dce4e8;stroke-width:1}.fce-chart .observed circle{fill:#7698aa;opacity:.68}.fce-chart .fit{fill:none;stroke:#173d55;stroke-width:2.2;stroke-linecap:round}.fce-sensitivity{display:grid;grid-template-columns:1fr 1fr;gap:7px}.fce-sensitivity div{padding:9px;border-radius:9px;background:#f1f4f5;border-left:3px solid #aab4bc}.fce-sensitivity div.same{border-left-color:#5c9270}.fce-sensitivity div.different{border-left-color:#d27a55}.fce-sensitivity span,.fce-sensitivity strong{display:block;font-size:12px}.fce-sensitivity span{color:#687784}.fce-sensitivity strong{margin-top:3px;color:#263646}.fce-drivers{display:grid;grid-template-columns:repeat(3,1fr);gap:7px}.fce-drivers div{padding:10px;border-radius:9px;background:#f1f4f5}.fce-drivers span,.fce-drivers strong,.fce-drivers small{display:block}.fce-drivers span,.fce-drivers small{font-size:11px;line-height:1.4;color:#687784}.fce-drivers strong{margin:4px 0;font-size:16px;color:#263646}.fce-gates{display:flex;flex-wrap:wrap;gap:7px;margin:14px 0}.fce-gates span{padding:6px 9px;border-radius:99px;font:650 12px/1.25 Inter,system-ui}.fce-gates .pass{background:#e4eee7;color:#315e45}.fce-gates .fail{background:#eef1f3;color:#788592}
      .fce-modal{position:fixed;inset:0;z-index:1100;display:none;align-items:center;justify-content:center;padding:28px;background:rgba(15,23,42,.48);backdrop-filter:blur(9px)}.fce-modal.visible{display:flex}.fce-modal-card{position:relative;display:grid;grid-template-columns:228px minmax(0,1fr);width:min(1260px,96vw);height:min(920px,92vh);overflow:hidden;border:1px solid rgba(255,255,255,.5);border-radius:22px;background:#f8fafb;box-shadow:0 32px 90px rgba(15,23,42,.28);color:#223143;font:14px/1.65 Inter,system-ui,sans-serif}.fce-overview-nav{display:flex;flex-direction:column;min-width:0;padding:25px 17px 18px;border-right:1px solid #dce3e8;background:#f1f5f7}.fce-nav-brand{padding:0 8px 18px;margin-bottom:11px;border-bottom:1px solid #d9e1e6}.fce-nav-brand strong,.fce-nav-brand span{display:block}.fce-nav-brand strong{font-size:12px;letter-spacing:.09em;text-transform:uppercase;color:#173d55}.fce-nav-brand span{margin-top:4px;font-size:12px;line-height:1.4;color:#778795}.fce-overview-nav nav{display:flex;flex-direction:column;gap:2px;overflow:auto}.fce-overview-nav nav button{display:grid;grid-template-columns:25px minmax(0,1fr);gap:7px;align-items:center;width:100%;padding:7px 8px;border:0;border-radius:8px;background:transparent;color:#647487;text-align:left;font:600 12px/1.3 Inter,system-ui;cursor:pointer}.fce-overview-nav nav button i{font:10px/1.2 ui-monospace,monospace;color:#9aa7b2}.fce-overview-nav nav button:hover{background:#e6edf1;color:#2c4d61}.fce-overview-nav nav button.active{background:#dcecef;color:#126276}.fce-overview-nav nav button.active i{color:#13a9c0}.fce-nav-foot{margin-top:auto;padding:16px 8px 0;border-top:1px solid #d9e1e6;font-size:11px;color:#8996a1}.fce-modal-scroll{position:relative;min-width:0;overflow:auto;scroll-behavior:smooth}.fce-close{position:sticky;float:right;top:16px;margin:16px 16px -54px 0;z-index:5;width:40px;height:40px;border:0;border-radius:50%;background:#e7ecef;color:#415161;font-size:23px;cursor:pointer}.fce-close:hover{background:#dce5e9;color:#173d55}.fce-modal-body{max-width:1000px;margin:0 auto;padding:46px 52px 76px}.fce-overview-section{scroll-margin-top:25px}.fce-hero{padding:4px 58px 28px 0;border-bottom:1px solid #dce3e8}.fce-kicker,.fce-section-index{font-size:11px;font-weight:800;letter-spacing:.1em;text-transform:uppercase;color:#9b6a26}.fce-hero h2{max-width:760px;margin:9px 0 12px;font-size:39px;line-height:1.08;letter-spacing:-.04em;color:#172638}.fce-hero p{max-width:800px;margin:0;color:#5f6f7e;font-size:15px;line-height:1.75}.fce-kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:22px 0 48px}.fce-kpis div{padding:16px;border:1px solid #dce3e8;border-radius:13px;background:#fff}.fce-kpis strong,.fce-kpis span{display:block}.fce-kpis strong{font-size:24px;color:#173d55}.fce-kpis span{margin-top:4px;font-size:12px;color:#73818f}.fce-modal section{margin-top:54px;padding-top:5px}.fce-modal section h3{max-width:760px;margin:8px 0 12px;font-size:24px;line-height:1.3;letter-spacing:-.02em;color:#243648}.fce-section-lead{max-width:820px;margin:0 0 18px;color:#5f6f7e;font-size:14px;line-height:1.75}.fce-reading{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.fce-reading div{padding:16px;border-radius:13px;background:#edf2f4}.fce-reading b,.fce-reading span{display:block}.fce-reading b{color:#243648}.fce-reading span{margin-top:5px;font-size:12px;color:#667684}.fce-section-note{margin-top:-4px;color:#788795;font-size:12px}.fce-ranking{display:grid;grid-template-columns:1fr 1fr;gap:7px}.fce-ranking button{position:relative;overflow:hidden;display:flex;justify-content:space-between;gap:10px;padding:12px 13px;border:1px solid #dce3e8;border-radius:10px;background:#fff;color:#3e4e5d;text-align:left;cursor:pointer}.fce-ranking button span,.fce-ranking button strong{position:relative;z-index:1;font-size:12px}.fce-ranking button i{position:absolute;bottom:0;left:0;height:3px}.fce-ranking button:hover{border-color:#8fa7b5;transform:translateY(-1px)}
      .fce-evidence-section{padding-top:30px;border-top:1px solid #dce3e8}.fce-report-figure{position:relative;display:block;width:100%;margin-top:21px;padding:0;overflow:hidden;border:1px solid #dce3e8;border-radius:15px;background:#fff;box-shadow:0 13px 34px rgba(36,49,66,.08);cursor:zoom-in}.fce-report-figure img{display:block;width:100%;height:auto}.fce-report-figure>span{position:absolute;right:12px;bottom:12px;padding:7px 10px;border-radius:99px;background:rgba(23,61,85,.88);color:#fff;font:650 11px/1.2 Inter,system-ui;opacity:0;transform:translateY(3px);transition:.18s}.fce-report-figure:hover{border-color:#86a7b5;box-shadow:0 18px 42px rgba(36,49,66,.13)}.fce-report-figure:hover>span,.fce-report-figure:focus-visible>span{opacity:1;transform:none}.fce-report-figure:focus-visible{outline:3px solid rgba(34,211,238,.45);outline-offset:3px}.fce-method-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.fce-method-grid div{padding:16px;border:1px solid #dce3e8;border-radius:12px;background:#fff}.fce-method-grid b,.fce-method-grid span{display:block}.fce-method-grid b{color:#274254}.fce-method-grid span{margin-top:6px;font-size:12px;line-height:1.6;color:#677785}.fce-claims{display:grid;grid-template-columns:1fr 1fr;gap:12px}.fce-claims>div{padding:18px;border-radius:13px}.fce-claims .can{background:#eaf3ee}.fce-claims .cannot{background:#f3efea}.fce-claims b{color:#29485a}.fce-claims ul{margin:8px 0 0;padding-left:18px}.fce-claims li{margin:7px 0;color:#586b78;font-size:12px;line-height:1.55}.fce-resource-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.fce-resource-grid a{position:relative;min-height:130px;padding:17px 18px 35px;border:1px solid #dce3e8;border-radius:12px;background:#fff;color:#334b5c;text-decoration:none}.fce-resource-grid a:hover{border-color:#83a5b4;transform:translateY(-1px)}.fce-resource-grid b,.fce-resource-grid span{display:block}.fce-resource-grid span{margin-top:6px;font-size:12px;line-height:1.55;color:#6a7a87}.fce-resource-grid i{position:absolute;left:18px;bottom:13px;font:650 11px/1.2 Inter,system-ui;color:#1689a0}.fce-figure-viewer{position:fixed;inset:0;z-index:1200;display:none;align-items:center;justify-content:center;padding:28px;background:rgba(12,21,31,.92);backdrop-filter:blur(9px)}.fce-figure-viewer.open{display:flex}.fce-figure-viewer figure{display:flex;flex-direction:column;align-items:center;gap:10px;max-width:97vw;max-height:95vh;margin:0}.fce-figure-viewer img{max-width:97vw;max-height:calc(95vh - 45px);object-fit:contain;border-radius:10px;background:#fff;box-shadow:0 26px 80px rgba(0,0,0,.42)}.fce-figure-viewer figcaption{color:#e9f1f5;font-size:12px}.fce-figure-close{position:fixed;top:18px;right:20px;width:43px;height:43px;border:1px solid rgba(255,255,255,.34);border-radius:50%;background:rgba(16,28,40,.75);color:#fff;font-size:25px;cursor:pointer}
      @media(max-width:1100px){.fce-toolbar-label{display:none}.fce-segmented button{padding:8px 7px}.fce-drivers{grid-template-columns:1fr}.fce-modal-card{grid-template-columns:205px minmax(0,1fr)}.fce-modal-body{padding-inline:35px}.fce-hero h2{font-size:34px}}
      @media(max-width:780px){.fce-toolbar{top:auto;bottom:12px;max-width:calc(100vw - 24px);flex-wrap:wrap;justify-content:center}.fce-segmented{max-width:100%;overflow:auto}.fce-modal{padding:0}.fce-modal-card{display:flex;flex-direction:column;width:100%;height:100%;max-height:100%;border-radius:0}.fce-overview-nav{display:block;flex:0 0 auto;padding:10px 52px 9px 10px;border-right:0;border-bottom:1px solid #dce3e8}.fce-nav-brand,.fce-nav-foot{display:none}.fce-overview-nav nav{display:flex;flex-direction:row;gap:3px;overflow-x:auto}.fce-overview-nav nav button{display:block;width:auto;min-width:max-content;padding:7px 10px}.fce-overview-nav nav button i{display:none}.fce-modal-scroll{flex:1}.fce-close{position:fixed;top:8px;right:8px;margin:0;width:36px;height:36px}.fce-modal-body{padding:30px 19px 65px}.fce-hero{padding-right:25px}.fce-hero h2{font-size:29px}.fce-hero p{font-size:14px}.fce-kpis{grid-template-columns:1fr 1fr;margin-bottom:35px}.fce-modal section{margin-top:42px}.fce-modal section h3{font-size:21px}.fce-reading,.fce-ranking,.fce-method-grid,.fce-claims,.fce-resource-grid{grid-template-columns:1fr}.fce-report-figure>span{opacity:1;transform:none}.fce-figure-viewer{padding:12px}.fce-figure-close{top:10px;right:10px}}
    `;
    document.head.appendChild(style);
  }
};
