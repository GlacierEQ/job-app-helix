(() => {
  const companySelect = document.getElementById("compiler-company");
  const roleSelect = document.getElementById("compiler-role");
  const depthSelect = document.getElementById("compiler-depth");
  const proofRoot = document.getElementById("compiler-capability-proofs");
  const proofSummary = document.getElementById("compiler-capability-proof-summary");
  if (!companySelect || !roleSelect || !depthSelect || !proofRoot || !proofSummary) return;

  let companyMap = new Map();

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

  const rolePayload = (company, role) => {
    if (!company || !company.role_projection || !role) return null;
    const payload = company.role_projection[role];
    return payload && typeof payload === "object" ? payload : null;
  };

  const depthIds = (company, role, depth) => {
    const audience =
      company.audience_projection && Array.isArray(company.audience_projection[depth])
        ? company.audience_projection[depth]
        : [];
    const allowed = new Set(audience.filter((value) => typeof value === "string"));
    const payload = rolePayload(company, role);
    const roleIds =
      payload && Array.isArray(payload.systems)
        ? payload.systems
            .map((row) =>
              row && typeof row.system_id === "string" ? row.system_id : null,
            )
            .filter(Boolean)
        : [];
    const routed = roleIds.filter((systemId) => allowed.has(systemId));
    return new Set(routed.length ? routed : Array.from(allowed));
  };

  const routeCapabilities = (company, role, systemIds) => {
    const payload = rolePayload(company, role);
    const capabilities = new Set();
    if (payload && Array.isArray(payload.systems)) {
      payload.systems.forEach((row) => {
        if (
          !row ||
          typeof row.system_id !== "string" ||
          !systemIds.has(row.system_id) ||
          !Array.isArray(row.matched_capabilities)
        ) {
          return;
        }
        row.matched_capabilities.forEach((value) => {
          if (typeof value === "string") capabilities.add(value);
        });
      });
    }
    return capabilities;
  };

  const safeEvidencePath = (ref) => {
    if (typeof ref !== "string" || !ref || ref.startsWith("/") || ref.startsWith("\\")) {
      return null;
    }
    const normalized = ref.replaceAll("\\", "/");
    const segments = normalized.split("/");
    if (segments.some((segment) => !segment || segment === "." || segment === "..")) {
      return null;
    }
    return segments;
  };

  const evidenceHref = (proof, ref) => {
    const segments = safeEvidencePath(ref);
    if (
      !proof ||
      typeof proof.source_repository !== "string" ||
      !proof.source_repository.startsWith("GlacierEQ/") ||
      typeof proof.head_sha !== "string" ||
      !/^[0-9a-f]{40}$/.test(proof.head_sha) ||
      !segments
    ) {
      return null;
    }
    const encoded = segments.map(encodeURIComponent).join("/");
    return `https://github.com/${proof.source_repository}/blob/${proof.head_sha}/${encoded}`;
  };

  const appendLink = (parent, text, href, className) => {
    if (!href) return null;
    const link = document.createElement("a");
    if (className) link.className = className;
    link.href = href;
    link.rel = "noopener noreferrer";
    link.textContent = text;
    parent.appendChild(link);
    return link;
  };

  const renderEmpty = (message) => {
    clear(proofRoot);
    const card = appendText(
      proofRoot,
      "article",
      "",
      "capability-proof-card capability-proof-empty",
    );
    appendText(card, "span", "Proof boundary", "compiler-card-kicker");
    appendText(card, "h4", message);
    appendText(
      card,
      "p",
      "Helix does not synthesize a semantic donor packet when exact-head public proof is absent.",
      "capability-proof-copy",
    );
  };

  const renderProof = (proof, depth, roleCaps) => {
    const card = appendText(proofRoot, "article", "", "capability-proof-card");
    card.dataset.proofDepth = depth;
    const matched = roleCaps.has(proof.capability_id);
    appendText(
      card,
      "span",
      matched ? "Role-matched semantic donor" : "Company semantic donor",
      matched
        ? "compiler-card-kicker capability-proof-match"
        : "compiler-card-kicker",
    );
    appendText(card, "h4", titleCase(proof.capability_id));

    const donor = appendText(card, "div", "", "capability-proof-donor");
    appendText(
      donor,
      "strong",
      proof.source_repository.split("/").pop() || proof.source_repository,
    );
    appendText(donor, "span", titleCase(proof.admission_state));

    const receipts = Array.isArray(proof.proof_receipts) ? proof.proof_receipts : [];
    const evidence = Array.isArray(proof.evidence_refs) ? proof.evidence_refs : [];
    const trust = appendText(card, "div", "", "capability-proof-trust");
    appendText(trust, "span", `${receipts.length} exact-head check${receipts.length === 1 ? "" : "s"}`);
    appendText(trust, "span", `${evidence.length} source artifact${evidence.length === 1 ? "" : "s"}`);

    if (depth !== "recruiter") {
      const state = appendText(card, "dl", "", "capability-proof-state");
      appendText(state, "dt", "Proof state");
      appendText(state, "dd", titleCase(proof.proof_state));
      appendText(state, "dt", "Exact head");
      appendText(state, "dd", proof.head_sha.slice(0, 12));
    }

    if (depth === "senior_engineer") {
      const detail = appendText(card, "div", "", "capability-proof-detail");
      appendText(detail, "strong", "Evidence files", "capability-proof-label");
      const files = appendText(detail, "div", "", "capability-proof-links");
      evidence.slice(0, 4).forEach((ref) => {
        appendLink(files, ref, evidenceHref(proof, ref), "capability-proof-link");
      });

      appendText(detail, "strong", "Successful checks", "capability-proof-label");
      const checks = appendText(detail, "ul", "", "capability-proof-checks");
      receipts.slice(0, 5).forEach((receipt) => {
        if (!receipt || typeof receipt.name !== "string") return;
        const item = document.createElement("li");
        item.textContent = `${receipt.name} · #${receipt.id}`;
        checks.appendChild(item);
      });
    }

    const commitHref =
      typeof proof.source_repository === "string" &&
      proof.source_repository.startsWith("GlacierEQ/") &&
      typeof proof.head_sha === "string" &&
      /^[0-9a-f]{40}$/.test(proof.head_sha)
        ? `https://github.com/${proof.source_repository}/commit/${proof.head_sha}`
        : null;
    appendLink(card, "Inspect exact donor head →", commitHref, "text-link capability-proof-head-link");
  };

  const renderCurrent = () => {
    const company = companyMap.get(companySelect.value);
    if (!company) return;
    const role = roleSelect.value;
    const depth = depthSelect.value;
    const systemIds = depthIds(company, role, depth);
    const roleCaps = routeCapabilities(company, role, systemIds);
    const proofs = (Array.isArray(company.capability_proofs) ? company.capability_proofs : [])
      .filter(
        (proof) =>
          proof &&
          typeof proof.system_id === "string" &&
          systemIds.has(proof.system_id),
      )
      .sort((left, right) =>
        String(left.capability_id).localeCompare(String(right.capability_id)),
      );

    if (!proofs.length) {
      proofSummary.textContent = "No separately admitted semantic donor packet is required for this route.";
      renderEmpty("No exact-head semantic donor packet on this proof surface.");
      return;
    }

    clear(proofRoot);
    const systems = new Set(proofs.map((proof) => proof.system_id));
    const receiptCount = proofs.reduce(
      (total, proof) =>
        total + (Array.isArray(proof.proof_receipts) ? proof.proof_receipts.length : 0),
      0,
    );
    proofSummary.textContent = `${proofs.length} capability proof packet${proofs.length === 1 ? "" : "s"} · ${systems.size} public donor system${systems.size === 1 ? "" : "s"} · ${receiptCount} successful exact-head check${receiptCount === 1 ? "" : "s"}.`;
    proofs.slice(0, depth === "recruiter" ? 3 : 6).forEach((proof) =>
      renderProof(proof, depth, roleCaps),
    );
  };

  const observer = new MutationObserver(() => renderCurrent());
  observer.observe(companySelect, { childList: true });
  observer.observe(roleSelect, { childList: true });
  companySelect.addEventListener("change", renderCurrent);
  roleSelect.addEventListener("change", renderCurrent);
  depthSelect.addEventListener("change", renderCurrent);

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
        throw new Error("invalid capability proof projection");
      }
      companyMap = new Map(
        payload.company_projections
          .filter((company) => company && typeof company.company_id === "string")
          .map((company) => [company.company_id, company]),
      );
      renderCurrent();
    })
    .catch(() => {
      proofSummary.textContent = "Capability proof lens unavailable; no unsupported packet was synthesized.";
      renderEmpty("Capability proof data unavailable.");
    });
})();
