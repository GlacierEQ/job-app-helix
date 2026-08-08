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
  const claimCeiling = document.getElementById("compiler-claim-ceiling");
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
    !claimCeiling ||
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
      .replace(/\b\w/g, (letter) => letter.toUpperCase());

  const appendText = (parent, tag, text, className) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    node.textContent = text;
    parent.appendChild(node);
    return node;
  };

  const canonicalSystems = (payload) =>
    new Map(
      (Array.isArray(payload.systems) ? payload.systems : [])
        .filter((row) => row && typeof row.system_id === "string")
        .map((row) => [row.system_id, row]),
    );

  const companySystems = (company) =>
    new Map(
      (Array.isArray(company.systems) ? company.systems : [])
        .filter((row) => row && typeof row.system_id === "string")
        .map((row) => [row.system_id, row]),
    );

  const roleData = (company, role) => {
    if (!company.role_projection || !role) return null;
    const row = company.role_projection[role];
    return row && typeof row === "object" ? row : null;
  };

  const fitBySystem = (company, role) => {
    const row = roleData(company, role);
    const map = new Map();
    if (!row || !Array.isArray(row.systems)) return map;
    row.systems.forEach((system) => {
      if (system && typeof system.system_id === "string") {
        map.set(system.system_id, system);
      }
    });
    return map;
  };

  const selectedSystemIds = (company, role, depth) => {
    const audience =
      company.audience_projection && Array.isArray(company.audience_projection[depth])
        ? company.audience_projection[depth]
        : [];
    const allowed = new Set(
      audience.filter((value) => typeof value === "string"),
    );
    const roleRow = roleData(company, role);
    const roleIds =
      roleRow && Array.isArray(roleRow.systems)
        ? roleRow.systems
            .map((row) => (row && typeof row.system_id === "string" ? row.system_id : null))
            .filter(Boolean)
        : [];
    const routed = roleIds.filter((systemId) => allowed.has(systemId));
    if (routed.length) return routed;
    return Array.from(allowed);
  };

  const renderSources = (intelligence) => {
    clear(sources);
    const rows =
      intelligence && Array.isArray(intelligence.official_sources)
        ? intelligence.official_sources
        : [];
    if (!rows.length) {
      appendText(
        sources,
        "span",
        "Source-backed company intelligence not loaded.",
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

  const renderSystems = (payload, company, role, depth) => {
    clear(systemsRoot);
    const globalSystems = canonicalSystems(payload);
    const scopedSystems = companySystems(company);
    const fitMap = fitBySystem(company, role);
    const ids = selectedSystemIds(company, role, depth);

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
      const global = globalSystems.get(systemId) || {};
      const scoped = scopedSystems.get(systemId) || {};
      const fit = fitMap.get(systemId) || {};
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

      const score = scoped.promotion_score;
      appendText(
        metrics,
        "span",
        score && score.complete === true && typeof score.score === "number"
          ? `${Math.round(score.score)}/100 proof score`
          : "Evidence incomplete",
      );

      appendText(card, "h3", titleCase(systemId));
      const chips = appendText(card, "div", "", "capability-chips");
      (Array.isArray(scoped.capabilities) ? scoped.capabilities : [])
        .slice(0, 7)
        .forEach((capability) => {
          appendText(chips, "span", titleCase(capability), "capability-chip");
        });

      if (
        typeof global.canonical_repository === "string" &&
        global.canonical_repository.startsWith("GlacierEQ/")
      ) {
        const link = document.createElement("a");
        link.className = "text-link";
        link.href = `https://github.com/${global.canonical_repository}`;
        link.rel = "noopener noreferrer";
        link.textContent = "Inspect canonical source →";
        card.appendChild(link);
      }
    });
  };

  const render = (payload, company, preferredRole) => {
    const role = renderRoles(company, preferredRole || roleSelect.value);
    const intelligence =
      company.intelligence && typeof company.intelligence === "object"
        ? company.intelligence
        : null;

    routeTitle.textContent = `${company.display_name || company.company_id} · ${
      role || "Role pending"
    }`;

    const state = intelligence?.freshness_state
      ? titleCase(intelligence.freshness_state)
      : "Not Loaded";
    freshness.textContent = intelligence?.research_as_of
      ? `${state} · research snapshot ${intelligence.research_as_of}`
      : state;

    pressure.textContent =
      intelligence?.observed_current_pressure ||
      "Source-backed operating pressure has not been loaded for this route.";
    bottleneck.textContent =
      intelligence?.inferred_bottleneck ||
      "No GlacierEQ bottleneck inference is promoted for this route.";
    intervention.textContent =
      intelligence?.application_move ||
      company.recruiter_thesis ||
      "No transferable intervention is promoted for this route.";
    claimCeiling.textContent = `Claim ceiling: ${
      company.claim_ceiling || "alignment only"
    }`;

    renderSources(intelligence);
    renderSystems(payload, company, role, depthSelect.value);
  };

  fetch("estate-projection.json", { credentials: "same-origin" })
    .then((response) => {
      if (!response.ok) throw new Error(`projection HTTP ${response.status}`);
      return response.json();
    })
    .then((payload) => {
      if (
        !payload ||
        payload.schema !== "glaciereq.public-portfolio-projection.v2" ||
        !Array.isArray(payload.companies)
      ) {
        throw new Error("invalid public projection");
      }
      const companyMap = new Map(
        payload.companies
          .filter((row) => row && typeof row.company_id === "string")
          .map((row) => [row.company_id, row]),
      );

      const currentCompany = () => companyMap.get(companySelect.value);

      companySelect.addEventListener("change", () => {
        const company = currentCompany();
        if (company) render(payload, company, null);
      });
      roleSelect.addEventListener("change", () => {
        const company = currentCompany();
        if (company) {
          routeTitle.textContent = `${company.display_name || company.company_id} · ${
            roleSelect.value || "Role pending"
          }`;
          renderSystems(payload, company, roleSelect.value, depthSelect.value);
        }
      });
      depthSelect.addEventListener("change", () => {
        const company = currentCompany();
        if (company) {
          renderSystems(payload, company, roleSelect.value, depthSelect.value);
        }
      });

      const initial = currentCompany() || payload.companies.find(Boolean);
      if (initial) {
        if (initial.company_id && companyMap.has(initial.company_id)) {
          companySelect.value = initial.company_id;
        }
        render(payload, initial, roleSelect.value);
      }
    })
    .catch(() => {
      // Server-rendered fallback remains intact when the same-origin projection
      // cannot be fetched or validated.
    });
})();
