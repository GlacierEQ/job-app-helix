(() => {
  const companySelect = document.getElementById("compiler-company");
  const roleSelect = document.getElementById("compiler-role");
  const depthSelect = document.getElementById("compiler-depth");
  const routeTitle = document.getElementById("compiler-route-title");
  const freshness = document.getElementById("compiler-freshness");
  const pressure = document.getElementById("compiler-pressure");
  const bottleneck = document.getElementById("compiler-bottleneck");
  const intervention = document.getElementById("compiler-intervention");
  const sources = document.getElementById("compiler-sources");
  const problemBoundary = document.getElementById("compiler-problem-boundary");
  const systemsRoot = document.getElementById("compiler-systems");

  if (
    !companySelect ||
    !roleSelect ||
    !depthSelect ||
    !routeTitle ||
    !freshness ||
    !pressure ||
    !bottleneck ||
    !intervention ||
    !sources ||
    !problemBoundary ||
    !systemsRoot
  ) {
    return;
  }

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
            .map((row) => (row && typeof row.system_id === "string" ? row.system_id : null))
            .filter(Boolean)
        : [];
    const routed = roleIds.filter((systemId) => allowed.has(systemId));
    return routed.length ? routed : Array.from(allowed);
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
      sources.appendChild(link);
    });
  };

  const renderSystems = (company, role, depth) => {
    clear(systemsRoot);
    const evidence = evidenceMap(company);
    const fits = fitMap(company, role);
    const ids = depthIds(company, role, depth);

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
      return;
    }

    ids.forEach((systemId) => {
      const row = evidence.get(systemId);
      if (!row) return;
      const fit = fits.get(systemId) || {};
      const card = appendText(
        systemsRoot,
        "article",
        "",
        "compiler-system-card",
      );
      const metrics = appendText(card, "div", "", "compiler-system-metrics");
      appendText(
        metrics,
        "span",
        typeof fit.fit_score === "number"
          ? `${Math.round(fit.fit_score)}% role fit`
          : "Role fit pending",
      );
      appendText(
        metrics,
        "span",
        typeof row.promotion_score === "number"
          ? `${Math.round(row.promotion_score)}/100 proof score`
          : "Evidence incomplete",
      );
      appendText(card, "h3", titleCase(systemId));

      const chips = appendText(card, "div", "", "capability-chips");
      (Array.isArray(row.capabilities) ? row.capabilities : [])
        .slice(0, 7)
        .forEach((capability) => {
          appendText(chips, "span", titleCase(capability), "capability-chip");
        });

      if (
        typeof row.source_repository === "string" &&
        row.source_repository.startsWith("GlacierEQ/")
      ) {
        const link = document.createElement("a");
        link.className = "text-link";
        link.href = `https://github.com/${row.source_repository}`;
        link.rel = "noopener noreferrer";
        link.textContent = "Inspect canonical source →";
        card.appendChild(link);
      }
    });
  };

  const render = (payload, company, preferredRole) => {
    const role = renderRoles(company, preferredRole || roleSelect.value);
    routeTitle.textContent = `${company.display_name || company.company_id} · ${
      role || "Role pending"
    }`;

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
    problemBoundary.textContent = `Dossier gate: ${
      company.dossier_next_gate || "not loaded"
    }`;

    renderSources(company);
    renderSystems(company, role, depthSelect.value);
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

      const companies = new Map(
        payload.company_projections
          .filter((row) => row && typeof row.company_id === "string")
          .map((row) => [row.company_id, row]),
      );
      const currentCompany = () => companies.get(companySelect.value);

      companySelect.addEventListener("change", () => {
        const company = currentCompany();
        if (company) render(payload, company, null);
      });
      roleSelect.addEventListener("change", () => {
        const company = currentCompany();
        if (!company) return;
        routeTitle.textContent = `${company.display_name || company.company_id} · ${
          roleSelect.value || "Role pending"
        }`;
        renderSystems(company, roleSelect.value, depthSelect.value);
      });
      depthSelect.addEventListener("change", () => {
        const company = currentCompany();
        if (company) {
          renderSystems(company, roleSelect.value, depthSelect.value);
        }
      });

      const initial =
        currentCompany() || payload.company_projections.find((row) => row);
      if (initial) {
        if (typeof initial.company_id === "string") {
          companySelect.value = initial.company_id;
        }
        render(payload, initial, roleSelect.value);
      }
    })
    .catch(() => {
      // Preserve the server-rendered fallback if projection fetch/validation fails.
    });
})();
