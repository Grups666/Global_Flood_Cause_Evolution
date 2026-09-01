/**
 * Global Flood Cause Evolution — interactive Tereon module.
 * Catchment-first trends with an area-supported HydroBASINS L5 regional lens.
 */
window.FloodCauseEvolutionModule = class FloodCauseEvolutionModule {
  constructor(app, manifest = {}) {
    this.app = app;
    this.manifest = manifest;
    this.basePath = manifest.basePath || "/";
    this.dataFile = manifest.dataFile || manifest.datasets?.[0]?.file || "./data/flood-cause-explorer.json";
    this.metric = "intensity_fraction";
    this.evidenceView = "supported";
    this.coverageThreshold = 50;
    this.basinLayerId = "flood-cause-hydrobasins";
    this.catchmentLayerId = "flood-cause-catchments";
    this.legendId = "flood-cause-trend-legend";
    this.selected = null;
    this.toolbar = null;
    this.modal = null;
    this.hoverTooltip = null;
    this.hoverAnchors = new Map();
    this.renderTimer = null;
    this.resizeObserver = null;
    this.handleWindowResize = () => this.scheduleStableRender(false);
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
    this.coverageThreshold = Number(this.data.meta.defaultCoverageThreshold || 50);
    this.basins = (this.data.basins || []).map((item) => ({ ...item, _kind: "basin" }));
    this.catchments = (this.data.catchments || [])
      .map((item) => ({ ...item, _kind: "catchment" }));
    this.ensureStyles();
    this.addLayers();
    this.ensureToolbar();
    this.updateLegend();
    Foundation.eventBus.on(Foundation.Events.FEATURE_CLICK, this.handleFeatureClick);
    window.addEventListener("resize", this.handleWindowResize);
    this.scheduleStableRender(true);
  }

  onUnload() {
    [this.basinLayerId, this.catchmentLayerId]
      .forEach((id) => this.app.layerManager.removeLayer(id));
    this.app.unregisterLegend?.(this.legendId);
    Foundation.eventBus.off(Foundation.Events.FEATURE_CLICK, this.handleFeatureClick);
    document.removeEventListener("keydown", this.handleOverviewKeydown);
    window.removeEventListener("resize", this.handleWindowResize);
    this.resizeObserver?.disconnect();
    if (this.renderTimer) window.clearTimeout(this.renderTimer);
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
      name: "Area-supported HydroBASINS L5 patterns",
      type: "vector",
      visible: true,
      interactive: true,
      moduleId: this.manifest.id,
      groupPath: ["flood-generating conditions"],
      metadata: { removable: false, evidenceScale: "secondary regional pattern" },
      renderer: (ctx, _layer, viewport) => this.renderBasins(ctx, viewport),
      hitTest: (lon, lat) => this.hitTestBasins(lon, lat)
    });
    this.app.layerManager.addLayer({
      id: this.catchmentLayerId,
      name: "Individual catchment trends",
      type: "vector",
      visible: true,
      interactive: true,
      moduleId: this.manifest.id,
      groupPath: ["flood-generating conditions"],
      metadata: { removable: false, evidenceScale: "primary catchment evidence" },
      renderer: (ctx, _layer, viewport) => this.renderCatchments(ctx, viewport),
      hitTest: (lon, lat, viewport) => this.hitTestCatchments(lon, lat, viewport)
    });
    this.app.updateLayerList?.();
  }

  scheduleStableRender(resizeCanvas = false) {
    const draw = () => this.app.draw?.();
    draw();
    window.requestAnimationFrame(() => {
      if (resizeCanvas) this.app.resize?.();
      else draw();
      window.requestAnimationFrame(draw);
    });
    if (this.renderTimer) window.clearTimeout(this.renderTimer);
    this.renderTimer = window.setTimeout(draw, 240);
    if (!this.resizeObserver && this.app.canvas?.parentElement && "ResizeObserver" in window) {
      this.resizeObserver = new ResizeObserver(() => draw());
      this.resizeObserver.observe(this.app.canvas.parentElement);
    }
  }

  renderBasins(ctx, viewport) {
    const shifts = this.worldShifts(viewport);
    const limit = this.outcome().limit;
    const ordered = [...this.basins].sort((a, b) => {
      const aStrong = this.regionalStrong(a) ? 1 : 0;
      const bStrong = this.regionalStrong(b) ? 1 : 0;
      return aStrong - bStrong;
    });
    for (const basin of ordered) {
      const metric = basin.metrics?.[this.metric];
      if (!metric || !this.basinPassesCoverage(basin)) continue;
      const strong = this.regionalStrong(basin);
      const contextual = this.evidenceView === "supported" && !strong;
      for (const shift of shifts) {
        ctx.save();
        this.traceGeometry(ctx, basin.geometry, viewport, shift);
        ctx.lineJoin = "round";
        ctx.lineCap = "round";
        ctx.miterLimit = 1.4;
        ctx.fillStyle = contextual ? "#e8edf0" : this.colorFor(metric.slope, limit);
        ctx.globalAlpha = strong ? 0.78 : (contextual ? 0.30 : (metric.fdrSupported ? 0.46 : 0.27));
        ctx.fill("evenodd");
        ctx.globalAlpha = 1;
        ctx.setLineDash([]);
        ctx.strokeStyle = strong ? "rgba(20, 49, 67, .88)" : "rgba(51, 65, 85, .52)";
        ctx.lineWidth = strong ? 0.92 : 0.48;
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
    if (!basin?.metrics?.[this.metric] || !this.basinPassesCoverage(basin)) return;
    for (const shift of this.worldShifts(viewport)) {
      ctx.save();
      this.traceGeometry(ctx, basin.geometry, viewport, shift);
      ctx.lineJoin = "round";
      ctx.lineCap = "round";
      ctx.miterLimit = 1.4;
      ctx.setLineDash([]);
      ctx.shadowColor = hovered ? "rgba(34, 211, 238, .98)" : "rgba(6, 182, 212, .94)";
      ctx.shadowBlur = hovered ? 30 : 24;
      ctx.strokeStyle = hovered ? "rgba(103, 232, 249, .98)" : "rgba(34, 211, 238, .98)";
      ctx.lineWidth = hovered ? 1.45 : 1.3;
      ctx.stroke();
      ctx.restore();
    }
  }

  renderCatchments(ctx, viewport) {
    const shifts = this.worldShifts(viewport);
    const limit = this.catchmentLimit();
    // Paint ordinary estimates first and robust individual trends second so
    // the primary catchment evidence remains visible where points overlap.
    for (const focalPass of [false, true]) {
      for (const catchment of this.catchments) {
        const metric = catchment.metrics?.[this.metric];
        if (!metric) continue;
        const focal = !!metric.robust;
        if (focal !== focalPass) continue;
        const contextual = this.evidenceView === "supported" && !focal;
        const radius = this.catchmentPointRadius(viewport, focal);
        for (const shift of shifts) {
          ctx.save();
          const point = this.project(catchment.lon + shift, catchment.lat, viewport);
          ctx.beginPath();
          ctx.arc(point.x, point.y, radius, 0, Math.PI * 2);
          ctx.fillStyle = (focal || this.evidenceView === "all")
            ? this.robustColorFor(metric.slope, limit)
            : "#9aa6ae";
          ctx.globalAlpha = focal ? 0.98 : (contextual ? 0.30 : 0.58);
          ctx.fill();
          ctx.restore();
        }
      }
    }

    const activeCatchment = this.selected?._kind === "catchment"
      ? this.catchments.find((item) => item.id === this.selected.id)
      : null;
    const hoveredCatchment = this.app.hoveredLayer?.id === this.catchmentLayerId
      ? this.catchments.find((item) => item.id === this.app.hoveredFeatureId)
      : null;
    if (activeCatchment && activeCatchment.id !== hoveredCatchment?.id) {
      this.drawCatchmentHighlight(ctx, activeCatchment, viewport, false);
    }
    if (hoveredCatchment) this.drawCatchmentHighlight(ctx, hoveredCatchment, viewport, true);

    // Repaint regional interaction outlines after every catchment boundary so
    // the cyan focus edge is always the topmost map mark.
    const activeBasin = this.selected?._kind === "basin"
      ? this.basins.find((item) => item.id === this.selected.id)
      : null;
    const hoveredBasin = this.app.hoveredLayer?.id === this.basinLayerId
      ? this.basins.find((item) => item.id === this.app.hoveredFeatureId)
      : null;
    if (activeBasin && activeBasin.id !== hoveredBasin?.id) {
      this.drawBasinHighlight(ctx, activeBasin, viewport, false);
    }
    if (hoveredBasin) this.drawBasinHighlight(ctx, hoveredBasin, viewport, true);
    this.updateHoverTooltip(ctx, viewport);
  }

  drawCatchmentHighlight(ctx, catchment, viewport, hovered) {
    if (!catchment?.metrics?.[this.metric]) return;
    const radius = this.catchmentPointRadius(viewport, true) + (hovered ? 3.1 : 2.6);
    for (const shift of this.worldShifts(viewport)) {
      ctx.save();
      const point = this.project(catchment.lon + shift, catchment.lat, viewport);
      ctx.beginPath();
      ctx.arc(point.x, point.y, radius, 0, Math.PI * 2);
      ctx.shadowColor = "rgba(34, 211, 238, .98)";
      ctx.shadowBlur = hovered ? 31 : 25;
      ctx.strokeStyle = hovered ? "rgba(103, 232, 249, 1)" : "rgba(34, 211, 238, 1)";
      ctx.lineWidth = hovered ? 1.55 : 1.35;
      ctx.stroke();
      ctx.restore();
    }
  }

  updateHoverTooltip(ctx, viewport) {
    const layerId = this.app.hoveredLayer?.id;
    const featureId = this.app.hoveredFeatureId;
    if (![this.basinLayerId, this.catchmentLayerId].includes(layerId) || featureId == null) {
      this.hideHoverTooltip();
      return;
    }

    let feature = null;
    if (layerId === this.basinLayerId) {
      feature = this.basins.find((item) => String(item.id) === String(featureId));
    } else {
      feature = this.catchments.find((item) => String(item.id) === String(featureId));
    }

    const metric = feature?.metrics?.[this.metric];
    if (!feature || !metric) {
      this.hideHoverTooltip();
      return;
    }
    const remembered = this.hoverAnchors.get(layerId);
    const useRemembered = remembered && String(remembered.featureId) === String(featureId);
    const anchorLon = useRemembered
      ? remembered.lon
      : (layerId === this.basinLayerId ? feature.center[0] : feature.lon);
    const anchorLat = useRemembered
      ? remembered.lat
      : (layerId === this.basinLayerId ? feature.center[1] : feature.lat);
    const projectedAnchors = this.worldShifts(viewport)
      .map((shift) => this.project(anchorLon + shift, anchorLat, viewport))
      .filter((item) => item.x > -100 && item.x < viewport.width + 100);
    const point = projectedAnchors.sort((a, b) => Math.abs(a.x - viewport.width / 2) - Math.abs(b.x - viewport.width / 2))[0];
    if (!point) {
      this.hideHoverTooltip();
      return;
    }
    const title = layerId === this.basinLayerId ? feature.code : `GCIN ${feature.id}`;
    this.showHoverTooltip(ctx, viewport, point.x, point.y, title, metric, feature, layerId);
  }

  showHoverTooltip(ctx, viewport, x, y, title, metric, feature, layerId) {
    if (!this.hoverTooltip) {
      this.hoverTooltip = document.createElement("div");
      this.hoverTooltip.className = "fce-hover-tooltip";
      this.hoverTooltip.setAttribute("role", "status");
      document.body.appendChild(this.hoverTooltip);
    }
    const outcome = this.outcome();
    const unit = this.metric === "intensity_fraction"
      ? "percentage points / 10 years"
      : "SSI units / 10 years";
    const evidence = layerId === this.basinLayerId
      ? `${this.gateCount(metric, feature)}/${this.gateDefinitions(metric, feature).length} checks · ${Number(feature.coveragePct).toFixed(1)}% area support`
      : `${this.catchmentGateDefinitions(metric).filter((gate) => gate.pass).length}/${this.catchmentGateDefinitions(metric).length} local checks · ${this.integer(metric.years)} event years`;
    this.hoverTooltip.innerHTML = `<strong>${this.escape(title)}</strong><span>${this.escape(evidence)}</span><span>${this.escape(this.direction(metric.slope))}</span><b>${this.signed(metric.slope, outcome.digits)} <small>${unit}</small></b>`;
    this.hoverTooltip.classList.add("visible");

    const canvasRect = ctx.canvas.getBoundingClientRect();
    // x/y are expressed in the renderer's viewport coordinate system. The
    // canvas backing-store dimensions can differ under display scaling, so
    // mapping through canvas.width/height displaces the tooltip on HiDPI or
    // resized canvases.
    const scaleX = canvasRect.width / Math.max(1, viewport.width);
    const scaleY = canvasRect.height / Math.max(1, viewport.height);
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
      if (basin.metrics?.[this.metric]
        && this.basinPassesCoverage(basin)
        && this.geometryContains(basin.geometry, normalized, lat)) {
        this.hoverAnchors.set(this.basinLayerId, { featureId: basin.id, lon: normalized, lat });
        return basin;
      }
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
    const pixelsPerDegree = (viewport.height / 180) * viewport.scale;
    const threshold = Math.max(0.08, (this.catchmentPointRadius(viewport, false) + 4) / pixelsPerDegree);
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
    if (best) this.hoverAnchors.set(this.catchmentLayerId, { featureId: best.id, lon: normalized, lat });
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
    this.updateEvidenceSummary();
    this.updateLegend();
    if (this.selected) {
      const layerId = this.selected._kind === "basin" ? this.basinLayerId : this.catchmentLayerId;
      this.showInspector(this.selected, layerId);
    }
    this.app.draw?.();
  }

  setEvidenceView(view) {
    if (!["supported", "all"].includes(view) || this.evidenceView === view) return;
    this.evidenceView = view;
    this.toolbar?.querySelectorAll("[data-evidence]")
      .forEach((button) => button.classList.toggle("active", button.dataset.evidence === view));
    this.updateLegend();
    this.app.draw?.();
  }

  setCoverageThreshold(value) {
    const threshold = Number(value);
    if (!Number.isFinite(threshold) || threshold === this.coverageThreshold) return;
    this.coverageThreshold = threshold;
    this.toolbar?.querySelectorAll("[data-threshold]")
      .forEach((button) => button.classList.toggle("active", Number(button.dataset.threshold) === threshold));
    this.updateEvidenceSummary();
    this.updateLegend();
    if (this.selected?._kind === "basin") {
      if (!this.basinPassesCoverage(this.selected)) this.selected = null;
      else this.showInspector(this.selected, this.basinLayerId);
    }
    this.app.draw?.();
  }

  basinPassesCoverage(basin) {
    return Number(basin?.coveragePct) >= this.coverageThreshold;
  }

  regionalStrong(basin) {
    return this.basinPassesCoverage(basin) && !!basin?.metrics?.[this.metric]?.strong;
  }

  evidenceSummary() {
    const qualifiedBasins = this.basins.filter((basin) => basin.metrics?.[this.metric] && this.basinPassesCoverage(basin));
    const strongBasins = qualifiedBasins.filter((basin) => this.regionalStrong(basin));
    const catchmentMetrics = this.catchments.map((item) => item.metrics?.[this.metric]).filter(Boolean);
    const robustCatchments = catchmentMetrics.filter((metric) => metric.robust);
    return {
      totalBasins: qualifiedBasins.length,
      strongBasins: strongBasins.length,
      positiveBasins: strongBasins.filter((basin) => Number(basin.metrics[this.metric].slope) > 0).length,
      negativeBasins: strongBasins.filter((basin) => Number(basin.metrics[this.metric].slope) < 0).length,
      catchmentEstimates: catchmentMetrics.length,
      robustCatchments: robustCatchments.length
    };
  }

  updateEvidenceSummary() {
    const summary = this.evidenceSummary();
    const count = this.toolbar?.querySelector("[data-evidence-count]");
    const directions = this.toolbar?.querySelector("[data-evidence-directions]");
    if (count) count.textContent = `${summary.robustCatchments} individual · ${summary.strongBasins} regional`;
    if (directions) directions.textContent = `${summary.totalBasins} L5 pass ≥${this.coverageThreshold}% area support`;
  }

  ensureToolbar() {
    this.toolbar = document.createElement("div");
    this.toolbar.className = "fce-toolbar";
    this.toolbar.innerHTML = `
      <div class="fce-toolbar-main">
        <div class="fce-toolbar-label">Flood-generating condition</div>
        <div class="fce-segmented" aria-label="Metric selector">
          <button data-metric="intensity_fraction" class="active">Rainfall concentration</button>
          <button data-metric="ssi_1d">SSI 1d</button>
          <button data-metric="ssi_3d">3d</button>
          <button data-metric="ssi_7d">7d</button>
          <button data-metric="ssi_30d">30d</button>
        </div>
        <button class="fce-overview-button" data-overview>Research overview</button>
      </div>
      <div class="fce-evidence-row">
        <div class="fce-evidence-summary"><strong data-evidence-count></strong><span>robust trends</span><small data-evidence-directions></small></div>
        <div class="fce-threshold-control" aria-label="Minimum observed area coverage for the HydroBASINS L5 layer">
          <span>L5 area support</span>
          <div>${(this.data.meta.coverageThresholdOptions || [10, 20, 30, 40, 50]).map((value) => `<button data-threshold="${value}" class="${Number(value) === this.coverageThreshold ? "active" : ""}">${value}%</button>`).join("")}</div>
        </div>
        <div class="fce-evidence-toggle" aria-label="Evidence display">
          <button data-evidence="supported" class="active">Supported focus</button>
          <button data-evidence="all">All estimates</button>
        </div>
      </div>`;
    document.body.appendChild(this.toolbar);
    this.toolbar.querySelectorAll("[data-metric]")
      .forEach((button) => button.addEventListener("click", () => this.setMetric(button.dataset.metric)));
    this.toolbar.querySelectorAll("[data-evidence]")
      .forEach((button) => button.addEventListener("click", () => this.setEvidenceView(button.dataset.evidence)));
    this.toolbar.querySelectorAll("[data-threshold]")
      .forEach((button) => button.addEventListener("click", () => this.setCoverageThreshold(button.dataset.threshold)));
    this.toolbar.querySelector("[data-overview]").addEventListener("click", () => this.showOverview());
    this.updateEvidenceSummary();
  }

  updateLegend() {
    const outcome = this.outcome();
    const limit = outcome.limit;
    const summary = this.evidenceSummary();
    this.app.unregisterLegend?.(this.legendId);
    this.app.registerLegend?.(this.legendId, {
      title: outcome.short,
      html: `
        <div class="fce-legend-scale-title">HydroBASINS L5 trend</div>
        <div class="fce-legend-bar"></div>
        <div class="fce-legend-axis"><span>${this.axisValue(-limit)}</span><span>0</span><span>+${this.axisValue(limit)}</span></div>
        <div class="fce-legend-directions"><span>${this.escape(outcome.low)}</span><span>${this.escape(outcome.high)}</span></div>
        <div class="fce-legend-unit">${this.escape(this.displayTrendUnit())}. Values beyond the color scale are clipped.</div>
        <div class="fce-legend-evidence"><strong>${summary.robustCatchments} robust individual trends</strong><span>${summary.strongBasins} supported regional patterns at ≥${this.coverageThreshold}% area coverage</span><small>${summary.positiveBasins} positive · ${summary.negativeBasins} negative regional directions</small></div>
        <div class="fce-legend-key"><i class="strong-boundary"></i> Region passes statistical gates + selected area support</div>
        <div class="fce-legend-key"><i class="boundary"></i> L5 passes selected area support; statistical evidence is weaker</div>
        <div class="fce-legend-key"><i class="glow"></i> Hover / selected feature</div>
        <div class="fce-legend-key"><i class="robust-scale"></i> Robust individual trend (blue decrease · orange increase)</div>
        <div class="fce-legend-key"><i class="dot muted"></i> Other estimable catchment (grey in Supported focus; lighter direction color in All estimates)</div>
        <div class="fce-legend-note">Robust individual trends are drawn last and remain visually prominent. Catchment points enlarge smoothly as the map zooms in. The area threshold changes only the L5 layer.</div>`
    });
  }

  showInspector(feature, layerId) {
    const metric = feature.metrics?.[this.metric];
    const outcome = this.outcome();
    if (!metric) return;
    if (layerId === this.basinLayerId) {
      const gateCount = this.gateCount(metric, feature);
      const regionStrong = this.regionalStrong(feature);
      const gateTotal = this.gateDefinitions(metric, feature).length;
      const status = regionStrong ? `Supported regional pattern · ${gateTotal}/${gateTotal} checks` : `Regional estimate · ${gateCount}/${gateTotal} checks`;
      const statusClass = regionStrong ? "pass" : "neutral";
      const interpretation = this.interpretation(metric.slope);
      this.app.showInspector?.(`${feature.code} · ${feature.countries}`, `
        <p class="fce-inspector-lead">HydroBASINS level-5 ${metric.estimatorType === "single_catchment_proxy" ? "single-catchment representation" : "pooled regional estimate"} · ${this.escape(outcome.label)}</p>
        <div class="fce-status ${statusClass}">${status}</div>
        ${this.gates(metric, feature)}
        <div class="fce-plain-result">${this.escape(interpretation)}</div>
        ${this.signal(metric, `${this.metric === "intensity_fraction" ? "Rainfall concentration" : "Antecedent wetness"} change over 10 years`)}
        <div class="fce-grid">
          ${this.fact("95% CI", `${this.signed(metric.ci?.[0], outcome.digits)} to ${this.signed(metric.ci?.[1], outcome.digits)}`)}
          ${this.fact("Complete-family q", this.prob(metric.q))}
          ${this.fact("Catchments", this.integer(metric.catchments))}
          ${this.fact("Event observations", this.integer(metric.observations))}
          ${this.fact("Catchment-years", this.integer(metric.modeledObservations))}
          ${this.fact("Observed area support", `${this.num(feature.coveragePct, 1)}%`)}
          ${this.fact("Observed area", `${this.integer(feature.observedAreaKm2)} km²`)}
          ${this.fact("Mean condition", this.num(metric.mean, outcome.digits))}
          ${this.metric.startsWith("ssi_") ? this.fact("Relative change", `${this.signed(metric.relativeSlope, 2)}% per 10 years`) : ""}
          ${this.fact("HydroBASINS L5", feature.code)}
        </div>
        ${this.trajectory(metric, outcome)}
        ${this.sensitivity(metric, outcome)}
        ${this.drivers(feature)}
        <p class="fce-note">${this.escape(outcome.definition)} The selected area threshold is a spatial-support condition, not a significance test. ${metric.estimatorType === "single_catchment_proxy" ? "This L5 estimate inherits one large catchment's trend and is not presented as multi-catchment corroboration." : "The pooled model compares catchment-year values within each contributing catchment before estimating their shared direction."}</p>`);
      return;
    }

    this.app.showInspector?.(`GCIN ${feature.id} · ${feature.country}`, `
      <p class="fce-inspector-lead">Primary single-catchment Theil–Sen trend · ${this.escape(outcome.label)}</p>
      <div class="fce-plain-result">${this.escape(this.interpretation(metric.slope, true))}</div>
      ${this.signal(metric, `${this.metric === "intensity_fraction" ? "Rainfall concentration" : "Antecedent wetness"} change over 10 years`)}
      <div class="fce-grid">
        ${this.fact("95% CI", `${this.signed(metric.ci?.[0], outcome.digits)} to ${this.signed(metric.ci?.[1], outcome.digits)}`)}
        ${this.fact("p value", this.prob(metric.p))}
        ${this.fact("Selected events", this.integer(metric.observations))}
        ${this.fact("Observed event years", this.integer(metric.years))}
        ${this.fact("Event-year range", `${metric.firstYear}–${metric.lastYear}`)}
        ${this.fact("Time span", `${metric.span} years`)}
        ${this.fact("Kendall tau", this.signed(metric.tau, 3))}
        ${this.fact("HydroBASINS L5", feature.hydrobasinId || "Unmatched")}
        ${this.fact("Catchment area", feature.areaKm2 ? `${this.integer(feature.areaKm2)} km²` : "—")}
      </div>
      <div class="fce-status ${metric.robust ? "pass" : "neutral"}">${metric.robust ? "Robust individual catchment trend" : "Individual catchment trend estimate"}</div>
      ${this.catchmentGates(metric)}
      ${this.sensitivity(metric, outcome)}
      <p class="fce-note">Displayed catchments have enough selected event years and time span for an annualized trend. The L5 area threshold never removes this single-catchment result.</p>`);
  }

  interpretation(slope, single = false) {
    const direction = Number(slope) >= 0 ? this.outcome().high : this.outcome().low;
    const subject = single ? "At this catchment" : "Across catchments in this region";
    return `${subject}, the selected large-flood events shifted ${direction}.`;
  }

  signal(metric, label) {
    const outcome = this.outcome();
    const value = this.metric === "intensity_fraction"
      ? `${this.signed(metric?.slope, outcome.digits)} pp`
      : this.signed(metric?.slope, outcome.digits);
    return `<div class="fce-signal"><span>${label}</span><strong style="color:${this.colorFor(metric?.slope, outcome.limit)}">${value}</strong><small>${this.escape(this.displayTrendUnit())}</small><p>${this.metricMeaning(metric)}</p></div>`;
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
    return `<div class="fce-block"><div class="fce-subhead"><b>Rainfall-process decomposition</b><span>raw linear slope ÷ catchment-equal mean</span></div><div class="fce-drivers">${entries.map((item) => `<div><span>${this.escape(item.label)}</span><strong>${this.signed(item.slope, 1)}%</strong><small>95% CI ${this.signed(item.ci?.[0], 1)} to ${this.signed(item.ci?.[1], 1)}% / 10 years</small></div>`).join("")}</div></div>`;
  }

  gates(metric, basin) {
    if (!metric) return "";
    const gates = this.gateDefinitions(metric, basin);
    const passed = gates.filter((gate) => gate.pass).length;
    return `<div class="fce-block fce-evidence-block"><div class="fce-subhead"><b>Regional evidence checks</b><span>${passed}/${gates.length} passed</span></div><div class="fce-gates">${gates.map((gate, index) => `<span class="${gate.pass ? "pass" : "fail"}" title="${this.escape(gate.detail)}"><i>${index + 1}</i>${gate.pass ? "✓" : "·"} ${this.escape(gate.name)}</span>`).join("")}</div></div>`;
  }

  gateDefinitions(metric, basin) {
    const gates = [
      { name: `Area support ≥${this.coverageThreshold}%`, pass: this.basinPassesCoverage(basin), detail: `Eligible catchment polygons cover ${this.num(basin?.coveragePct, 1)}% of this L5 unit.` },
      { name: "Complete-family BH-FDR", pass: !!metric.fdrSupported, detail: `Passes the 5% Benjamini–Hochberg false discovery rate (BH-FDR) procedure across ${this.data.meta.primaryFamilyTests.toLocaleString()} primary L5 region–metric tests.` },
      { name: "Alternative extreme samples", pass: !!metric.sampleStable, detail: "Keeps its direction under POT/Q90, POT/Q97.5, and annual-maximum event samples." },
      { name: "Leave-one-out stability", pass: !!metric.jackknifeStable, detail: metric.estimatorType === "single_catchment_proxy" ? "Keeps its direction when each observed event year is removed in turn." : "Keeps its direction when each contributing catchment is removed in turn." }
    ];
    if (this.metric.startsWith("ssi_")) {
      gates.splice(3, 0, { name: "SSI-window direction", pass: !!metric.windowStable, detail: "The direction agrees across the 1-, 3-, 7-, and 30-day antecedent-wetness windows." });
    }
    return gates;
  }

  gateCount(metric, basin) {
    return this.gateDefinitions(metric, basin).filter((gate) => gate.pass).length;
  }

  catchmentGates(metric) {
    const gates = this.catchmentGateDefinitions(metric);
    return `<div class="fce-block fce-evidence-block"><div class="fce-subhead"><b>Individual trend checks</b><span>${gates.filter((gate) => gate.pass).length}/${gates.length} passed</span></div><div class="fce-gates">${gates.map((gate, index) => `<span class="${gate.pass ? "pass" : "fail"}" title="${this.escape(gate.detail)}"><i>${index + 1}</i>${gate.pass ? "✓" : "·"} ${this.escape(gate.name)}</span>`).join("")}</div></div>`;
  }

  catchmentGateDefinitions(metric) {
    const gates = [
      { name: "p value < 0.05", pass: Number(metric.p) < 0.05, detail: "The catchment's Mann–Kendall trend test has a p value below 0.05." },
      { name: "Alternative extreme samples", pass: !!metric.alternativeSampleStable, detail: "The trend direction is retained under POT/Q90, POT/Q97.5, and annual-maximum samples." },
      { name: "Leave-one-year-out", pass: !!metric.leaveOneYearStable, detail: "The trend direction is retained when each observed event year is removed in turn." }
    ];
    if (this.metric.startsWith("ssi_")) {
      gates.push({ name: "SSI-window direction", pass: !!metric.windowStable, detail: "The direction agrees across the 1-, 3-, 7-, and 30-day antecedent-wetness windows." });
    }
    return gates;
  }

  fact(label, value) {
    return `<div class="fce-fact"><span>${label}</span><strong>${value}</strong></div>`;
  }

  showOverview() {
    this.ensureModal();
    const meta = this.data.meta;
    const outcome = this.outcome();
    const mapSummary = this.evidenceSummary();
    const rankings = (meta.ranking || []).filter((item) => {
      const basin = this.basins.find((regionalUnit) => regionalUnit.id === item.basinId);
      return basin && this.basinPassesCoverage(basin);
    }).slice(0, 12);
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
        title: "Single-catchment estimates come first",
        image: "reports/assets/figure_02_mechanism_change_maps.png",
        alt: "Single-catchment maps of rainfall organization and antecedent wetness trends",
        text: `${meta.catchmentsWithTrend.toLocaleString()} catchments have enough selected event years for a direct trend estimate. ${meta.robustCatchmentTrends.toLocaleString()} also retain their direction under the declared alternative event samples and leave-one-year-out check.`
      },
      {
        id: "magnitude",
        number: "03",
        title: "Robust individual trends occur in opposing directions",
        image: "reports/assets/figure_03_strong_signal_rankings.png",
        alt: "Individual trend checks and opposing directions among robust catchment trends",
        text: `The ${meta.robustCatchmentTrends.toLocaleString()} robust individual trends include both increases and decreases. They are direct catchment-scale results; the L5 analysis separately asks whether some of them align into a larger hydrological pattern.`
      },
      {
        id: "trajectories",
        number: "04",
        title: "Some catchment-level changes align into larger L5 patterns",
        image: "reports/assets/figure_04_mechanism_trajectories.png",
        alt: "Area-supported HydroBASINS L5 regional trend maps",
        text: `At the current ≥${this.coverageThreshold}% area-support setting, ${mapSummary.totalBasins} L5 regions are shown and ${mapSummary.strongBasins} satisfy the complete statistical evidence screen.`
      },
      {
        id: "decomposition",
        number: "05",
        title: "The area threshold is an interactive interpretation choice",
        image: "reports/assets/figure_05_physical_decomposition.png",
        alt: "Sensitivity of mapped L5 regions and represented catchments to area-coverage thresholds",
        text: "Moving from 10% to 50% spatial support makes regional interpretation stricter. It never removes the underlying single-catchment trend layer."
      },
      {
        id: "robustness",
        number: "06",
        title: "Regional evidence must be visible inside its contributing catchments",
        image: "reports/assets/figure_06_robustness_matrix.png",
        alt: "Regional estimates shown with their contributing catchment trends",
        text: "A pooled L5 signal is interpreted as a larger-scale pattern only when its estimate, alternative event samples, SSI windows, leave-one-catchment-out test, and selected spatial support all agree."
      }
    ];
    this.modal.querySelector(".fce-modal-body").innerHTML = `
      <section class="fce-hero fce-overview-section" id="overview-summary">
        <span class="fce-kicker">${meta.period} · rainfall-driven large floods</span>
        <h2>Which catchments show persistent shifts in flood-generating conditions?</h2>
        <p>The analysis starts with each catchment, tests whether rainfall organization or pre-event wetness moved consistently through time, and then asks whether nearby catchments form a coherent HydroBASINS L5 pattern. A regional polygon is a second-stage synthesis, never a replacement for its individual catchments.</p>
      </section>
      <div class="fce-kpis">
        ${this.kpi(meta.primaryEvents.toLocaleString(), "selected POT/Q95 events")}
        ${this.kpi(meta.catchmentsWithTrend.toLocaleString(), "catchments with direct trends")}
        ${this.kpi(meta.robustCatchmentTrends.toLocaleString(), "robust individual trends")}
        ${this.kpi(mapSummary.strongBasins, `supported L5 patterns at ≥${this.coverageThreshold}%`)}
      </div>
      <section class="fce-overview-section" id="research-question"><span class="fce-section-index">Research question</span><h3>Most catchments show no robust long-term shift; a smaller set changes persistently in either direction</h3>
        <p class="fce-section-lead"><b>Main answer.</b> Each catchment is analysed directly. ${meta.robustCatchmentTrends.toLocaleString()} catchment–metric trends have p&lt;0.05, retain their direction under alternative extreme-event samples, and remain stable when event years are removed one at a time; SSI results also agree across antecedent windows. The expanded L5 analysis then identifies where neighbouring catchments support a larger hydrological pattern.</p>
        <div class="fce-reading">
        <div><b>Rainfall concentration</b><span>Pmax/Pvolume is the fraction of total event rainfall that fell on the rainiest single day. Positive change means a larger one-day share; negative change means a smaller one-day share.</span></div>
        <div><b>Antecedent wetness</b><span>SSI summarizes soil wetness before rainfall starts. The 1-, 3-, 7- and 30-day windows show whether a result depends on the chosen memory window.</span></div>
        <div><b>Two evidence scales</b><span>Catchment polygons are the primary observations. L5 polygons summarize a possible larger-scale pattern only when the selected area-support threshold is met.</span></div>
      </div></section>
      <section class="fce-overview-section" id="key-findings"><span class="fce-section-index">Evidence at a glance</span><h3>Strongest reproducible regional signals</h3><p class="fce-section-note">Select a row to switch the mapped metric and open that HydroBASINS unit.</p>
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
          <div><b>3 · Test every catchment first</b><span>Selected events are averaged within catchment-year, followed by Theil–Sen and Mann–Kendall trends over ${meta.period}. Robustness requires p&lt;0.05, alternative-sample direction agreement, and leave-one-year-out stability; SSI also requires window agreement.</span></div>
          <div><b>4 · Expand to larger hydrological patterns</b><span>L5 estimates pool within-catchment annual change. Complete-family BH-FDR, alternative extreme-event samples, SSI-window agreement, leave-one-out stability, and selected polygon-area support form the regional screen.</span></div>
        </div>
      </section>
      <section class="fce-overview-section" id="statistics"><span class="fce-section-index">Statistical meaning</span><h3>Statistical evidence and spatial support answer different questions</h3>
        <div class="fce-method-grid">
          <div><b>Individual catchment evidence</b><span>${meta.catchmentPrimaryTests.toLocaleString()} estimable catchment–metric trends are reported with their slopes, p values, fitted endpoints, and stability checks. They are the first-level results.</span></div>
          <div><b>${meta.primaryFamilyTests.toLocaleString()} regional tests</b><span>All estimable L5 regions × five continuous metrics form one Benjamini–Hochberg family. ${meta.fdrSupportedSignals} pass 5% BH-FDR control before the dynamic area filter is applied.</span></div>
          <div><b>Area support ≥${this.coverageThreshold}%</b><span>The catchment-polygon union covers at least this share of the L5 polygon. Changing it alters regional interpretation only; catchment trends remain available.</span></div>
          <div><b>Within-catchment annual change</b><span>Every model compares catchment-year values with the same catchment's long-run level. The year 2000 is only a centering constant and is not a breakpoint.</span></div>
          <div><b>Absolute + relative scale</b><span>SSI remains in raw index units and also shows slope ÷ catchment-equal mean. Rainfall components use raw linear slopes converted to the same relative scale; no logarithmic model is used.</span></div>
        </div>
        <p class="fce-note">Adjusted annual trajectories mean: after placing all catchments on the same long-run mean, how far above or below their own normal level were that year's participating catchments on average?</p>
      </section>
      <section class="fce-overview-section" id="interpretation"><span class="fce-section-index">Inference boundary</span><h3>What the evidence can—and cannot—support</h3>
        <div class="fce-claims">
          <div class="can"><b>Supported</b><ul><li>Most catchments do not meet the complete individual robustness checks.</li><li>A smaller set shows persistent catchment-scale changes in rainfall concentration or antecedent wetness.</li><li>Some area-supported L5 units show a reproducible shared direction across catchments.</li></ul></div>
          <div class="cannot"><b>Not supported</b><ul><li>Every colored catchment has a confirmed long-term change.</li><li>A spatially uniform or area-weighted global land trend.</li><li>A claim about flood counts, peak flow, flood volume, or causal attribution.</li></ul></div>
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
    const slope = Number(metric?.slope);
    const value = Math.abs(slope);
    const roseOrFell = slope >= 0 ? "increased" : "decreased";
    const endpoints = this.metricEndpoints(metric);
    const endpointText = endpoints
      ? ` The fitted level changed from <b>${endpoints.first}</b> in ${endpoints.firstYear} to <b>${endpoints.last}</b> in ${endpoints.lastYear}.`
      : "";
    if (this.metric === "intensity_fraction") {
      return `Rainfall in the selected large-flood events became ${slope >= 0 ? "more" : "less"} concentrated: the proportion of total event rainfall falling on the rainiest single day ${roseOrFell} by <b>${value.toFixed(2)} percentage points over 10 years</b>.${endpointText}`;
    }
    const days = this.metric.match(/^ssi_(\d+)d$/)?.[1] || "selected";
    const relative = Math.abs(Number(metric?.relativeSlope));
    const relativeText = Number.isFinite(relative) ? `, equal to <b>${relative.toFixed(2)}% of the relevant long-term mean</b>` : "";
    return `Antecedent wetness before the selected large floods became ${slope >= 0 ? "wetter" : "drier"}: mean SSI during the ${days} complete day${days === "1" ? "" : "s"} before rainfall onset ${roseOrFell} by <b>${value.toFixed(3)} SSI units over 10 years</b>${relativeText}.${endpointText}`;
  }

  metricEndpoints(metric) {
    let firstYear = Number(metric?.firstYear);
    let lastYear = Number(metric?.lastYear);
    let first = Number(metric?.fittedFirst);
    let last = Number(metric?.fittedLast);
    const rows = metric?.trajectory || [];
    if ((!Number.isFinite(first) || !Number.isFinite(last)) && rows.length > 1) {
      firstYear = Number(rows[0][0]);
      lastYear = Number(rows[rows.length - 1][0]);
      first = Number(rows[0][2]);
      last = Number(rows[rows.length - 1][2]);
    }
    if (![firstYear, lastYear, first, last].every(Number.isFinite)) return null;
    const inPhysicalRange = this.metric === "intensity_fraction"
      ? first >= 0 && first <= 100 && last >= 0 && last <= 100
      : first >= 0 && first <= 1 && last >= 0 && last <= 1;
    if (!inPhysicalRange) return null;
    const digits = this.outcome().digits;
    const suffix = this.metric === "intensity_fraction" ? "%" : " SSI";
    return {
      firstYear,
      lastYear,
      first: `${first.toFixed(digits)}${suffix}`,
      last: `${last.toFixed(digits)}${suffix}`
    };
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
          <button data-scroll="key-findings"><i>03</i><span>Regional signals</span></button>
          <button data-scroll="coverage"><i>04</i><span>Sample coverage</span></button>
          <button data-scroll="spatial-change"><i>05</i><span>Catchment trends</span></button>
          <button data-scroll="magnitude"><i>06</i><span>Evidence funnel</span></button>
          <button data-scroll="trajectories"><i>07</i><span>Regional patterns</span></button>
          <button data-scroll="decomposition"><i>08</i><span>Area sensitivity</span></button>
          <button data-scroll="robustness"><i>09</i><span>Regional traceability</span></button>
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

  catchmentPointRadius(viewport, focal = false) {
    const scale = Math.max(1, Number(viewport?.scale) || 1);
    const zoomResponsive = 3.7 + 0.9 * Math.log2(scale);
    return Math.min(focal ? 8.8 : 7.6, zoomResponsive + (focal ? 1.0 : 0));
  }

  displayTrendUnit() {
    return this.metric === "intensity_fraction"
      ? "percentage points per 10 years (pp / 10 years)"
      : "SSI units per 10 years";
  }

  robustColorFor(value, maxAbs) {
    if (!Number.isFinite(Number(value))) return "#647780";
    const normalized = Math.min(1, Math.abs(Number(value)) / maxAbs);
    const emphasis = 0.28 + 0.72 * Math.sqrt(normalized);
    return Number(value) < 0
      ? this.mix("#6f9fb5", "#1f5c80", emphasis)
      : this.mix("#e5a082", "#c75531", emphasis);
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
      .fce-hover-tooltip{position:fixed;z-index:1250;display:none;min-width:245px;max-width:min(390px,calc(100vw - 20px));padding:11px 13px;border:1px solid #334155;border-radius:11px;background:#172235;color:#f8fafc;box-shadow:0 13px 34px rgba(15,23,42,.32);opacity:1;pointer-events:none;font:13px/1.35 Inter,system-ui,sans-serif}.fce-hover-tooltip.visible{display:block}.fce-hover-tooltip strong,.fce-hover-tooltip span,.fce-hover-tooltip b{display:block}.fce-hover-tooltip strong{font-size:13px;color:#fff}.fce-hover-tooltip span{margin-top:3px;color:#d7e1e8;font-size:12px}.fce-hover-tooltip b{margin-top:6px;color:#67e8f9;font-size:14px}.fce-hover-tooltip small{color:#d7e1e8;font-size:11px;font-weight:600}
      .fce-toolbar{position:fixed;top:14px;left:50%;transform:translateX(-50%);z-index:850;display:flex;flex-direction:column;gap:7px;max-width:calc(100vw - 32px);padding:8px;border:1px solid rgba(148,163,184,.35);border-radius:16px;background:rgba(255,255,255,.98);box-shadow:0 12px 34px rgba(15,23,42,.13);backdrop-filter:blur(16px);font:13px/1.25 Inter,system-ui,sans-serif;color:#334155}.fce-toolbar-main{display:flex;align-items:center;gap:10px;padding-left:6px}.fce-toolbar-label{font-weight:750;white-space:nowrap}.fce-segmented{display:flex;padding:3px;border-radius:10px;background:#edf1f4}.fce-segmented button,.fce-overview-button,.fce-evidence-toggle button,.fce-threshold-control button{border:0;border-radius:8px;padding:8px 10px;background:transparent;color:#526171;font:650 12px Inter,system-ui;white-space:nowrap;cursor:pointer}.fce-segmented button.active{background:#fff;color:#173d55;box-shadow:0 2px 8px rgba(15,23,42,.1)}.fce-overview-button{background:#173d55;color:#fff}.fce-evidence-row{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:7px 7px 7px 10px;border-radius:11px;background:#edf6f7}.fce-evidence-summary{display:flex;align-items:baseline;gap:7px;white-space:nowrap}.fce-evidence-summary strong{color:#0f6070;font-size:15px}.fce-evidence-summary span{font-size:12px;font-weight:700;color:#315463}.fce-evidence-summary small{padding-left:8px;border-left:1px solid #c8dde1;color:#6b7f88;font-size:11px}.fce-threshold-control{display:flex;align-items:center;gap:7px;white-space:nowrap}.fce-threshold-control>span{font-size:11px;font-weight:750;color:#476673}.fce-threshold-control>div{display:flex;padding:2px;border-radius:9px;background:#dcebed}.fce-threshold-control button{padding:6px 8px;font-size:11px}.fce-threshold-control button.active{background:#fff;color:#0c6172;box-shadow:0 2px 7px rgba(15,23,42,.13)}.fce-evidence-toggle{display:flex;padding:2px;border-radius:9px;background:#dcebed}.fce-evidence-toggle button{padding:6px 9px;font-size:11px}.fce-evidence-toggle button.active{background:#123e55;color:#fff;box-shadow:0 2px 7px rgba(15,23,42,.14)}
      .fce-legend-scale-title{margin:6px 0 5px;font-size:12px;font-weight:750;color:#475569}.fce-legend-bar{height:11px;border-radius:99px;background:linear-gradient(90deg,#2b6487,#ebe8de 50%,#cf673f)}.fce-legend-axis{display:flex;justify-content:space-between;margin-top:4px;font:12px/1.25 ui-monospace,monospace;color:#64748b}.fce-legend-directions{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:6px;font-size:12px;line-height:1.35;color:#526171}.fce-legend-directions span:last-child{text-align:right}.fce-legend-unit,.fce-legend-note{margin:9px 0;font-size:12px;line-height:1.5;color:#64748b}.fce-legend-evidence{margin:11px 0 10px;padding:10px 11px;border-radius:10px;background:#edf6f7}.fce-legend-evidence strong,.fce-legend-evidence span,.fce-legend-evidence small{display:block}.fce-legend-evidence strong{font-size:19px;color:#0f6070}.fce-legend-evidence span{margin-top:2px;font-size:12px;font-weight:700;color:#315463}.fce-legend-evidence small{margin-top:4px;font-size:11px;color:#6b7f88}.fce-legend-key{display:flex;align-items:center;gap:8px;margin-top:8px;font-size:12px;line-height:1.35;color:#475569}.fce-legend-key i{display:inline-block;flex:0 0 auto;width:19px;height:10px}.fce-legend-key .strong-boundary{border:2px solid #143143;background:linear-gradient(90deg,#5c89a1,#d77b58)}.fce-legend-key .boundary{border:1px solid #64748b;background:#e8edf0}.fce-legend-key .glow{height:5px;border:1px solid #67e8f9;box-shadow:0 0 8px 4px rgba(34,211,238,.7)}.fce-legend-key .dot{width:9px;height:9px;border-radius:50%;background:#527b95;border:1px solid #334155}
      .fce-legend-key .dot{border:0}.fce-legend-key .dot.muted{background:#9aa6ae}.fce-legend-key .robust-scale{width:24px;height:9px;border-radius:99px;background:linear-gradient(90deg,#1f5c80,#6f9fb5 45%,#e5a082 55%,#c75531)}.fce-inspector-lead,.fce-note{font-size:12px;line-height:1.65;color:#64748b}.fce-plain-result{margin:12px 0 0;padding:11px 12px;border-left:3px solid #22d3ee;border-radius:0 9px 9px 0;background:#eefbfc;font-size:13px;font-weight:650;line-height:1.5;color:#214558}.fce-signal{margin:12px 0;padding:15px;border-radius:12px;background:#f3f6f7}.fce-signal span,.fce-signal small{display:block;color:#64748b;font-size:12px}.fce-signal strong{display:block;margin:5px 0 3px;font-size:30px;letter-spacing:-.04em}.fce-signal p{margin:10px 0 0;padding-top:9px;border-top:1px solid #dce5e9;color:#526b7b;font-size:12px;line-height:1.5}.fce-signal p b{color:#24465a}.fce-grid{display:grid;grid-template-columns:1fr 1fr;gap:9px}.fce-fact{padding:11px;border:1px solid #dfe6eb;border-radius:10px}.fce-fact span,.fce-fact strong{display:block}.fce-fact span{font-size:12px;line-height:1.3;text-transform:uppercase;letter-spacing:.025em;color:#6f7f8e}.fce-fact strong{margin-top:5px;font-size:13px;color:#263646}.fce-status{display:inline-block;margin-top:12px;padding:6px 10px;border-radius:99px;font:650 12px/1.25 Inter,system-ui}.fce-status.pass{background:#e3efe7;color:#315e45}.fce-status.neutral{background:#eef1f3;color:#667482}
      .fce-block,.fce-chart{margin-top:15px;padding-top:13px;border-top:1px solid #e2e8ec}.fce-subhead{display:flex;justify-content:space-between;gap:10px;align-items:baseline;margin-bottom:9px}.fce-subhead b{font-size:13px;color:#314455}.fce-subhead span{font-size:12px;color:#7a8793}.fce-chart svg{display:block;width:100%;height:auto;overflow:visible}.fce-chart svg text{font:11px Inter,system-ui;fill:#758290}.fce-chart .grid{stroke:#dce4e8;stroke-width:1}.fce-chart .observed circle{fill:#7698aa;opacity:.68}.fce-chart .fit{fill:none;stroke:#173d55;stroke-width:2.2;stroke-linecap:round}.fce-sensitivity{display:grid;grid-template-columns:1fr 1fr;gap:7px}.fce-sensitivity div{padding:9px;border-radius:9px;background:#f1f4f5;border-left:3px solid #aab4bc}.fce-sensitivity div.same{border-left-color:#5c9270}.fce-sensitivity div.different{border-left-color:#d27a55}.fce-sensitivity span,.fce-sensitivity strong{display:block;font-size:12px}.fce-sensitivity span{color:#687784}.fce-sensitivity strong{margin-top:3px;color:#263646}.fce-drivers{display:grid;grid-template-columns:repeat(3,1fr);gap:7px}.fce-drivers div{padding:10px;border-radius:9px;background:#f1f4f5}.fce-drivers span,.fce-drivers strong,.fce-drivers small{display:block}.fce-drivers span,.fce-drivers small{font-size:11px;line-height:1.4;color:#687784}.fce-drivers strong{margin:4px 0;font-size:16px;color:#263646}.fce-evidence-block{padding:13px;border:1px solid #d5e4e8;border-radius:12px;background:#f8fbfc}.fce-gates{display:flex;flex-wrap:wrap;gap:7px;margin:0}.fce-gates span{display:flex;align-items:center;gap:5px;padding:6px 9px;border-radius:99px;font:650 12px/1.25 Inter,system-ui}.fce-gates span i{display:inline-grid;place-items:center;width:17px;height:17px;border-radius:50%;background:rgba(255,255,255,.68);font:700 10px ui-monospace,monospace}.fce-gates .pass{background:#e4eee7;color:#315e45}.fce-gates .fail{background:#eef1f3;color:#788592}
      .fce-modal{position:fixed;inset:0;z-index:1100;display:none;align-items:center;justify-content:center;padding:28px;background:rgba(15,23,42,.48);backdrop-filter:blur(9px)}.fce-modal.visible{display:flex}.fce-modal-card{position:relative;display:grid;grid-template-columns:228px minmax(0,1fr);width:min(1260px,96vw);height:min(920px,92vh);overflow:hidden;border:1px solid rgba(255,255,255,.5);border-radius:22px;background:#f8fafb;box-shadow:0 32px 90px rgba(15,23,42,.28);color:#223143;font:14px/1.65 Inter,system-ui,sans-serif}.fce-overview-nav{display:flex;flex-direction:column;min-width:0;padding:25px 17px 18px;border-right:1px solid #dce3e8;background:#f1f5f7}.fce-nav-brand{padding:0 8px 18px;margin-bottom:11px;border-bottom:1px solid #d9e1e6}.fce-nav-brand strong,.fce-nav-brand span{display:block}.fce-nav-brand strong{font-size:12px;letter-spacing:.09em;text-transform:uppercase;color:#173d55}.fce-nav-brand span{margin-top:4px;font-size:12px;line-height:1.4;color:#778795}.fce-overview-nav nav{display:flex;flex-direction:column;gap:2px;overflow:auto}.fce-overview-nav nav button{display:grid;grid-template-columns:25px minmax(0,1fr);gap:7px;align-items:center;width:100%;padding:7px 8px;border:0;border-radius:8px;background:transparent;color:#647487;text-align:left;font:600 12px/1.3 Inter,system-ui;cursor:pointer}.fce-overview-nav nav button i{font:10px/1.2 ui-monospace,monospace;color:#9aa7b2}.fce-overview-nav nav button:hover{background:#e6edf1;color:#2c4d61}.fce-overview-nav nav button.active{background:#dcecef;color:#126276}.fce-overview-nav nav button.active i{color:#13a9c0}.fce-nav-foot{margin-top:auto;padding:16px 8px 0;border-top:1px solid #d9e1e6;font-size:11px;color:#8996a1}.fce-modal-scroll{position:relative;min-width:0;overflow:auto;scroll-behavior:smooth}.fce-close{position:sticky;float:right;top:16px;margin:16px 16px -54px 0;z-index:5;width:40px;height:40px;border:0;border-radius:50%;background:#e7ecef;color:#415161;font-size:23px;cursor:pointer}.fce-close:hover{background:#dce5e9;color:#173d55}.fce-modal-body{max-width:1000px;margin:0 auto;padding:46px 52px 76px}.fce-overview-section{scroll-margin-top:25px}.fce-hero{padding:4px 58px 28px 0;border-bottom:1px solid #dce3e8}.fce-kicker,.fce-section-index{font-size:11px;font-weight:800;letter-spacing:.1em;text-transform:uppercase;color:#9b6a26}.fce-hero h2{max-width:760px;margin:9px 0 12px;font-size:39px;line-height:1.08;letter-spacing:-.04em;color:#172638}.fce-hero p{max-width:800px;margin:0;color:#5f6f7e;font-size:15px;line-height:1.75}.fce-kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:22px 0 48px}.fce-kpis div{padding:16px;border:1px solid #dce3e8;border-radius:13px;background:#fff}.fce-kpis strong,.fce-kpis span{display:block}.fce-kpis strong{font-size:24px;color:#173d55}.fce-kpis span{margin-top:4px;font-size:12px;color:#73818f}.fce-modal section{margin-top:54px;padding-top:5px}.fce-modal section h3{max-width:760px;margin:8px 0 12px;font-size:24px;line-height:1.3;letter-spacing:-.02em;color:#243648}.fce-section-lead{max-width:820px;margin:0 0 18px;color:#5f6f7e;font-size:14px;line-height:1.75}.fce-reading{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.fce-reading div{padding:16px;border-radius:13px;background:#edf2f4}.fce-reading b,.fce-reading span{display:block}.fce-reading b{color:#243648}.fce-reading span{margin-top:5px;font-size:12px;color:#667684}.fce-section-note{margin-top:-4px;color:#788795;font-size:12px}.fce-ranking{display:grid;grid-template-columns:1fr 1fr;gap:7px}.fce-ranking button{position:relative;overflow:hidden;display:flex;justify-content:space-between;gap:10px;padding:12px 13px;border:1px solid #dce3e8;border-radius:10px;background:#fff;color:#3e4e5d;text-align:left;cursor:pointer}.fce-ranking button span,.fce-ranking button strong{position:relative;z-index:1;font-size:12px}.fce-ranking button i{position:absolute;bottom:0;left:0;height:3px}.fce-ranking button:hover{border-color:#8fa7b5;transform:translateY(-1px)}
      .fce-evidence-section{padding-top:30px;border-top:1px solid #dce3e8}.fce-report-figure{position:relative;display:block;width:100%;margin-top:21px;padding:0;overflow:hidden;border:1px solid #dce3e8;border-radius:15px;background:#fff;box-shadow:0 13px 34px rgba(36,49,66,.08);cursor:zoom-in}.fce-report-figure img{display:block;width:100%;height:auto}.fce-report-figure>span{position:absolute;right:12px;bottom:12px;padding:7px 10px;border-radius:99px;background:rgba(23,61,85,.88);color:#fff;font:650 11px/1.2 Inter,system-ui;opacity:0;transform:translateY(3px);transition:.18s}.fce-report-figure:hover{border-color:#86a7b5;box-shadow:0 18px 42px rgba(36,49,66,.13)}.fce-report-figure:hover>span,.fce-report-figure:focus-visible>span{opacity:1;transform:none}.fce-report-figure:focus-visible{outline:3px solid rgba(34,211,238,.45);outline-offset:3px}.fce-method-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.fce-method-grid div{padding:16px;border:1px solid #dce3e8;border-radius:12px;background:#fff}.fce-method-grid b,.fce-method-grid span{display:block}.fce-method-grid b{color:#274254}.fce-method-grid span{margin-top:6px;font-size:12px;line-height:1.6;color:#677785}.fce-claims{display:grid;grid-template-columns:1fr 1fr;gap:12px}.fce-claims>div{padding:18px;border-radius:13px}.fce-claims .can{background:#eaf3ee}.fce-claims .cannot{background:#f3efea}.fce-claims b{color:#29485a}.fce-claims ul{margin:8px 0 0;padding-left:18px}.fce-claims li{margin:7px 0;color:#586b78;font-size:12px;line-height:1.55}.fce-resource-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.fce-resource-grid a{position:relative;min-height:130px;padding:17px 18px 35px;border:1px solid #dce3e8;border-radius:12px;background:#fff;color:#334b5c;text-decoration:none}.fce-resource-grid a:hover{border-color:#83a5b4;transform:translateY(-1px)}.fce-resource-grid b,.fce-resource-grid span{display:block}.fce-resource-grid span{margin-top:6px;font-size:12px;line-height:1.55;color:#6a7a87}.fce-resource-grid i{position:absolute;left:18px;bottom:13px;font:650 11px/1.2 Inter,system-ui;color:#1689a0}.fce-figure-viewer{position:fixed;inset:0;z-index:1200;display:none;align-items:center;justify-content:center;padding:28px;background:rgba(12,21,31,.92);backdrop-filter:blur(9px)}.fce-figure-viewer.open{display:flex}.fce-figure-viewer figure{display:flex;flex-direction:column;align-items:center;gap:10px;max-width:97vw;max-height:95vh;margin:0}.fce-figure-viewer img{max-width:97vw;max-height:calc(95vh - 45px);object-fit:contain;border-radius:10px;background:#fff;box-shadow:0 26px 80px rgba(0,0,0,.42)}.fce-figure-viewer figcaption{color:#e9f1f5;font-size:12px}.fce-figure-close{position:fixed;top:18px;right:20px;width:43px;height:43px;border:1px solid rgba(255,255,255,.34);border-radius:50%;background:rgba(16,28,40,.75);color:#fff;font-size:25px;cursor:pointer}
      @media(max-width:1100px){.fce-toolbar-label,.fce-evidence-summary small,.fce-threshold-control>span{display:none}.fce-segmented button{padding:8px 7px}.fce-drivers{grid-template-columns:1fr}.fce-modal-card{grid-template-columns:205px minmax(0,1fr)}.fce-modal-body{padding-inline:35px}.fce-hero h2{font-size:34px}}
      @media(max-width:780px){.fce-toolbar{top:auto;bottom:12px;width:calc(100vw - 24px);max-width:none}.fce-toolbar-main{width:100%;padding-left:0;overflow-x:auto}.fce-segmented{max-width:100%;overflow:auto}.fce-overview-button{margin-left:auto}.fce-evidence-row{width:auto;gap:7px;overflow-x:auto}.fce-evidence-summary span{display:none}.fce-threshold-control>div{flex:0 0 auto}.fce-evidence-toggle{flex:0 0 auto}.fce-modal{padding:0}.fce-modal-card{display:flex;flex-direction:column;width:100%;height:100%;max-height:100%;border-radius:0}.fce-overview-nav{display:block;flex:0 0 auto;padding:10px 52px 9px 10px;border-right:0;border-bottom:1px solid #dce3e8}.fce-nav-brand,.fce-nav-foot{display:none}.fce-overview-nav nav{display:flex;flex-direction:row;gap:3px;overflow-x:auto}.fce-overview-nav nav button{display:block;width:auto;min-width:max-content;padding:7px 10px}.fce-overview-nav nav button i{display:none}.fce-modal-scroll{flex:1}.fce-close{position:fixed;top:8px;right:8px;margin:0;width:36px;height:36px}.fce-modal-body{padding:30px 19px 65px}.fce-hero{padding-right:25px}.fce-hero h2{font-size:29px}.fce-hero p{font-size:14px}.fce-kpis{grid-template-columns:1fr 1fr;margin-bottom:35px}.fce-modal section{margin-top:42px}.fce-modal section h3{font-size:21px}.fce-reading,.fce-ranking,.fce-method-grid,.fce-claims,.fce-resource-grid{grid-template-columns:1fr}.fce-report-figure>span{opacity:1;transform:none}.fce-figure-viewer{padding:12px}.fce-figure-close{top:10px;right:10px}}
    `;
    document.head.appendChild(style);
  }
};
