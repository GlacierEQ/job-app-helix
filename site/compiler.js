(() => {
  const companySelect = document.getElementById("compiler-company");
  const roleSelect = document.getElementById("compiler-role");
  const depthSelect = document.getElementById("compiler-depth");
  const routeTitle = document.getElementById("compiler-route-title");
  const routeSummary = document.getElementById("compiler-route-summary");
  const routeLink = document.getElementById("compiler-route-link");
  const freshness = document.getElementById("compiler-freshness");
  const pressure = document.getElementById("compiler-pressure");
  const bottleneck = document.getElementById("compiler-bottleneck");
  const intervention = document.getElementById("compiler-intervention");
  const sources = document.getElementById("compiler-sources");
  const capabilitiesRoot = document.getElementById("compiler-capabilities");
  const problemBoundary = document.getElementById("compiler-problem-boundary");
  const systemsRoot = document.getElementById("compiler-systems");
  const chainPressure = document.getElementById("compiler-chain-pressure");
  const chainCapability = document.getElementById("compiler-chain-capability");
  const chainSystems = document.getElementById("compiler-chain-systems");
  const chainProof = document.getElementById("compiler-chain-proof");

  const required = [
    companySelect,
    roleSelect,
    depthSelect,
    routeTitle,
    routeSummary,
    routeLink,
    freshness,
    pressure,
    bottleneck,
    intervention,
    sources,
    capabilitiesRoot,
    problemBoundary,
    systemsRoot,
    chainPressure,
    chainCapability,
    chainSystems,
    chainProof,
  ];
  if (required.some((node) => !node)) return;

  const DEPTH_LABELS = {
    recruiter: "Recruiter signal surface",
    company_reviewer: "Company intervention surface",
    senior_engineer: "Senior-engineer diligence surface",
  };

  const clear = (node) => {
    while (node.firstChild) node.removeChild(node.firstChild);
  };

  const titleCase = (value) =>
    String(value || "")
      .replaceAll("_", " ")
      .replaceAll("-", " ")
      .replace(/\b\w/g, (letter) => letter.toUpperCase());

  const appendText = (parent, tag, text, className) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    node.textContent = text;
    parent.appendChild(node);
    return node;
  };

  const evidenceMap = (company) =>
    new Map(
      (Array.isArray(company.ranked_evidence) ? company.ranked_evidence : [])
        .filter((row) => row && typeof row.system_id === "string")
        .map((row) => [row.system_id, row]),
    );

  const rolePayload = (company, role) => {
    if (!company.role_projection || !role) return null;
    const row = company.role_projection[role];
    return row && typeof row === "object" ? row : null;
  };

  const fitMap = (company, role) => {
    const payload = rolePayload(company, role);
    if (!payload || !Array.isArray(payload.systems)) return new Map();
    return new Map(
      payload.systems
        .filter((row) => row && typeof row.system_id === "string")
        .map((row) => [row.system_id, row]),
    );
  };

  const depthIds = (company, role, depth) => {
    const audience =
      company.audience_projection && Array.isArray(company.audience_projection[depth])
        ? company.audience_projection[depth]
        : [];
    const allowed = new Set(
      audience.filter((value) => typeof value === "string"),
    );
    const roleRow = rolePayload(company, role);
    const roleIds =
      roleRow && Array.isArray(roleRow.systems)
        ? roleRow.systems
            .map((row) =>
              row && typeof row.system_id === "string" ? row.system_id : null,
            )
            .filter(Boolean)
        : [];
    const routed = roleIds.filter((systemId) => allowed.has(systemId));
    return routed.length ? routed : Array.from(allowed);
  };

  const renderCompanies = (companies, preferredCompany) => {
    clear(companySelect);
    companies.forEach((company) => {
      const option = document.createElement("option");
      option.value = company.company_id;
      option.textContent = company.display_name || titleCase(company.company_id);
      companySelect.appendChild(option);
    });
    const ids = companies.map((company) => company.company_id);
    companySelect.value = ids.includes(preferredCompany)
      ? preferredCompany
      : ids[0] || "";
    return companySelect.value;
  };

  const renderRoles = (company, preferredRole) => {
    clear(roleSelect);
    const roles = Array.isArray(company.target_roles)
      ? company.target_roles.filter((role) => typeof role === "string")
      : [];
    if (!roles.length) {
      const option = document.createElement("option");
      option.value = "";
      option.textContent = "No role route";
      roleSelect.appendChild(option);
      return "";
    }
    roles.forEach((role) => {
      const option = document.createElement("option");
      option.value = role;
      option.textContent = role;
      roleSelect.appendChild(option);
    });
    roleSelect.value = roles.includes(preferredRole) ? preferredRole : roles[0];
    return roleSelect.value;
  };

  const renderSources = (company) => {
    clear(sources);
    const rows = Array.isArray(company.official_sources)
      ? company.official_sources
      : [];
    if (!rows.length) {
      appendText(
        sources,
        "span",
        "No refreshed public source is loaded.",
        "compiler-empty",
      );
      return;
    }
    rows.slice(0, 3).forEach((source) => {
      if (!source || typeof source.url !== "string") return;
      const link = document.createElement("a");
      link.href = source.url;
      link.rel = "noopener noreferrer";
      link.textContent =
        typeof source.title === "string" ? source.title : "Official source";
      if (typeof source.publisher === "string" && source.publisher) {
        link.setAttribute("aria-label", `${link.textContent} · ${source.publisher}`);
      }
      sources.appendChild(link);
    });
  };

  const renderCapabilities = (company, role, ids) => {
    clear(capabilitiesRoot);
    const payload = rolePayload(company, role);
    const fits = fitMap(company, role);
    const profile =
      payload && Array.isArray(payload.profile_capabilities)
        ? payload.profile_capabilities.filter((value) => typeof value === "string")
        : [];
    const matched = new Set();
    ids.forEach((systemId) => {
      const fit = fits.get(systemId);
      if (!fit || !Array.isArray(fit.matched_capabilities)) return;
      fit.matched_capabilities.forEach((capability) => {
        if (typeof capability === "string") matched.add(capability);
      });
    });

    const capabilities = profile.length
      ? profile
      : Array.from(matched).length
        ? Array.from(matched)
        : Array.isArray(company.capabilities)
          ? company.capabilities.filter((value) => typeof value === "string")
          : [];

    if (!capabilities.length) {
      appendText(
        capabilitiesRoot,
        "span",
        "Capability route not yet promoted.",
        "capability-chip capability-chip-muted",
      );
      chainCapability.textContent = "Capability mapping pending";
      return;
    }

    capabilities.slice(0, 10).forEach((capability) => {
      const chip = appendText(
        capabilitiesRoot,
        "span",
        titleCase(capability),
        matched.has(capability)
          ? "capability-chip capability-chip-match"
          : "capability-chip",
      );
      if (matched.has(capability)) chip.title = "Matched by promoted proof";
    });

    const strongest = Array.from(matched).slice(0, 2).map(titleCase);
    chainCapability.textContent = strongest.length
      ? strongest.join(" + ")
      : `${capabilities.length} mapped capabilities`;
  };

  const appendScore = (parent, label, value, className) => {
    const wrapper = appendText(parent, "div", "", "compiler-score");
    const row = appendText(wrapper, "div", "", "compiler-score-row");
    appendText(row, "span", label);
    appendText(
      row,
      "strong",
      typeof value === "number" ? `${Math.round(value)}` : "Pending",
    );
    const meter = document.createElement("meter");
    meter.min = 0;
    meter.max = 100;
    meter.value = typeof value === "number" ? Math.max(0, Math.min(100, value)) : 0;
    meter.className = className;
    meter.setAttribute(
      "aria-label",
      `${label}: ${typeof value === "number" ? Math.round(value) : "pending"}`,
    );
    wrapper.appendChild(meter);
  };

  const renderSystems = (company, role, depth) => {
    clear(systemsRoot);
    const evidence = evidenceMap(company);
    const fits = fitMap(company, role);
    const ids = depthIds(company, role, depth);
    const rendered = [];

    if (!ids.length) {
      const empty = appendText(
        systemsRoot,
        "article",
        "",
        "compiler-system-card compiler-system-empty",
      );
      appendText(empty, "h3", "No public proof promoted for this route yet.");
      appendText(
        empty,
        "p",
        "The compiler fails closed rather than filling the gap with an unsupported claim.",
      );
      chainSystems.textContent = "No public systems promoted";
      chainProof.textContent = "Fail-closed boundary held";
      renderCapabilities(company, role, []);
      return;
    }

    ids.forEach((systemId) => {
      const row = evidence.get(systemId);
      if (!row) return;
      const fit = fits.get(systemId) || {};
      rendered.push({ row, fit, systemId });

      const card = appendText(
        systemsRoot,
        "article",
        "",
        "compiler-system-card",
      );
      const sourceName =
        typeof row.source_repository === "string"
          ? row.source_repository.split("/").pop()
          : systemId;
      appendText(
        card,
        "span",
        row.promotion_state === "PROMOTED" ? "Source-bound proof donor" : "Public evidence donor",
        "compiler-card-kicker",
      );
      appendText(card, "h3", titleCase(sourceName || systemId));

      const scoreGrid = appendText(card, "div", "", "compiler-score-grid");
      appendScore(
        scoreGrid,
        "Role fit",
        typeof fit.fit_score === "number" ? fit.fit_score : null,
        "fit-meter",
      );
      appendScore(
        scoreGrid,
        "Proof",
        typeof row.promotion_score === "number" ? row.promotion_score : null,
        "proof-meter",
      );

      const matched =
        Array.isArray(fit.matched_capabilities) && fit.matched_capabilities.length
          ? fit.matched_capabilities
          : Array.isArray(row.capabilities)
            ? row.capabilities
            : [];
      const chips = appendText(card, "div", "", "capability-chips");
      matched.slice(0, 6).forEach((capability) => {
        if (typeof capability !== "string") return;
        appendText(chips, "span", titleCase(capability), "capability-chip");
      });

      if (
        typeof row.source_repository === "string" &&
        row.source_repository.startsWith("GlacierEQ/")
      ) {
        const link = document.createElement("a");
        link.className = "text-link compiler-source-link";
        link.href = `https://github.com/${row.source_repository}`;
        link.rel = "noopener noreferrer";
        link.textContent = "Inspect reference source →";
        card.appendChild(link);
      }
    });

    chainSystems.textContent = `${rendered.length} system${rendered.length === 1 ? "" : "s"} on this proof surface`;
    const proofScores = rendered
      .map(({ row }) => row.promotion_score)
      .filter((value) => typeof value === "number");
    chainProof.textContent = proofScores.length
      ? `Top proof ${Math.round(Math.max(...proofScores))}/100`
      : "Verification score pending";
    renderCapabilities(
      company,
      role,
      rendered.map(({ systemId }) => systemId),
    );
  };

  const updateRouteUrl = (company, role, depth) => {
    const params = new URLSearchParams();
    if (company && company.company_id) params.set("company", company.company_id);
    if (role) params.set("role", role);
    if (depth) params.set("depth", depth);
    const query = params.toString();
    const route = `${window.location.pathname}${query ? `?${query}` : ""}#compiler`;
    routeLink.href = route;
    if (window.history && typeof window.history.replaceState === "function") {
      window.history.replaceState(null, "", route);
    }
  };

  const renderRoute = (company, role) => {
    const depth = depthSelect.value;
    routeTitle.textContent = `${company.display_name || company.company_id} · ${
      role || "Role route pending"
    }`;
    routeSummary.textContent =
      company.recruiter_thesis ||
      company.operating_problem ||
      `${DEPTH_LABELS[depth] || "Evidence surface"} compiled from promoted public proof.`;

    const state = company.freshness_state
      ? titleCase(company.freshness_state)
      : "Not Loaded";
    freshness.textContent = company.research_as_of
      ? `${state} · research snapshot ${company.research_as_of}`
      : state;
    pressure.textContent =
      company.observed_operating_pressure ||
      "Source-backed operating pressure has not been loaded for this route.";
    bottleneck.textContent =
      company.inferred_bottleneck ||
      "No GlacierEQ bottleneck inference is promoted for this route.";
    intervention.textContent =
      company.application_move ||
      company.recruiter_thesis ||
      "No transferable intervention is promoted for this route.";
    problemBoundary.textContent = `${DEPTH_LABELS[depth] || "Evidence surface"} · dossier gate: ${
      company.dossier_next_gate || "not loaded"
    }`;
    chainPressure.textContent = company.display_name
      ? `${company.display_name} operating signal`
      : "Source-backed operating signal";

    renderSources(company);
    renderSystems(company, role, depth);
    updateRouteUrl(company, role, depth);
    document.title = `${company.display_name || company.company_id} · ${
      role || "Applied AI"
    } — Casey Barton`;
  };

  const renderCompany = (company, preferredRole) => {
    const role = renderRoles(company, preferredRole);
    renderRoute(company, role);
  };

  fetch("estate-projection.json", { credentials: "same-origin" })
    .then((response) => {
      if (!response.ok) throw new Error(`projection HTTP ${response.status}`);
      return response.json();
    })
    .then((payload) => {
      if (
        !payload ||
        payload.schema !== "glaciereq.estate-public-projection.v2" ||
        !Array.isArray(payload.company_projections)
      ) {
        throw new Error("invalid public estate projection");
      }

      const companies = payload.company_projections.filter(
        (row) => row && typeof row.company_id === "string",
      );
      if (!companies.length) throw new Error("empty public company projection");
      const companyMap = new Map(companies.map((row) => [row.company_id, row]));
      const params = new URLSearchParams(window.location.search);
      const requestedCompany = params.get("company") || "";
      const requestedRole = params.get("role") || "";
      const requestedDepth = params.get("depth") || "";
      if (Object.hasOwn(DEPTH_LABELS, requestedDepth)) {
        depthSelect.value = requestedDepth;
      }

      const initialCompanyId = renderCompanies(companies, requestedCompany);
      const currentCompany = () => companyMap.get(companySelect.value);
      const initial = companyMap.get(initialCompanyId) || companies[0];
      renderCompany(initial, requestedRole);

      companySelect.addEventListener("change", () => {
        const company = currentCompany();
        if (company) renderCompany(company, "");
      });
      roleSelect.addEventListener("change", () => {
        const company = currentCompany();
        if (company) renderRoute(company, roleSelect.value);
      });
      depthSelect.addEventListener("change", () => {
        const company = currentCompany();
        if (company) renderRoute(company, roleSelect.value);
      });
    })
    .catch(() => {
      freshness.textContent = "Static recruiter surface · compiler data unavailable";
      routeTitle.textContent = "Evidence compiler unavailable";
      routeSummary.textContent =
        "The static recruiter package remains available. No unsupported company route was synthesized.";
    });
})();
