const pptxgen = require("pptxgenjs");
const path = require("path");
const out = path.join(__dirname, "PRESENTATION_SPECIAL_PROJECTS.pptx");

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.author = "GlacierEQ";
pres.title = "Special Projects — Multi-Domain Systems";
pres.subject = "SpaceX / xAI / multi-domain shark-laser offer";

// Charcoal aerospace palette
const BG = "0B0F14";
const CARD = "141A22";
const ICE = "C8D6E5";
const ACCENT = "E85D04"; // heat/reentry orange
const TEAL = "2A9D8F";
const WHITE = "FFFFFF";
const MUTED = "8B9AAB";

function addFooter(slide, n, total) {
  slide.addText(`GlacierEQ · Special Projects  ·  ${n}/${total}`, {
    x: 0.5, y: 5.25, w: 9, h: 0.25,
    fontSize: 10, fontFace: "Calibri", color: MUTED, margin: 0,
  });
}

const TOTAL = 10;

// 1 Title
{
  const s = pres.addSlide();
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 5.625, fill: { color: BG } });
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 0.18, h: 5.625, fill: { color: ACCENT } });
  s.addText("GLACIEREQ", {
    x: 0.6, y: 1.5, w: 8.5, h: 0.45,
    fontSize: 14, fontFace: "Consolas", color: TEAL, charSpacing: 4, margin: 0,
  });
  s.addText("Multi-domain systems.\nAgent OS. Physics-first\ncompute & aerospace software.", {
    x: 0.6, y: 2.0, w: 8.5, h: 1.8,
    fontSize: 28, fontFace: "Georgia", color: WHITE, bold: true, margin: 0,
  });
  s.addText("Shark-laser special projects  ·  not front-door pileup", {
    x: 0.6, y: 4.1, w: 8.5, h: 0.35,
    fontSize: 14, fontFace: "Calibri", color: ICE, italic: true, margin: 0,
  });
  addFooter(s, 1, TOTAL);
}

// 2 Positioning
{
  const s = pres.addSlide();
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 5.625, fill: { color: BG } });
  s.addText("Positioning", {
    x: 0.5, y: 0.35, w: 9, h: 0.5,
    fontSize: 28, fontFace: "Georgia", color: WHITE, bold: true, margin: 0,
  });
  const cards = [
    { t: "On-demand", d: "Open a hard problem; leave working systems + governance" },
    { t: "Multi-domain", d: "Agent OS · Colossus thermal · SpaceX helix · GPU · safety · cloud ops" },
    { t: "Honest", d: "No employment fiction. Portfolio motions. Measure or mark unknown." },
  ];
  cards.forEach((c, i) => {
    const y = 1.1 + i * 1.2;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: 0.5, y, w: 9, h: 1.05,
      fill: { color: CARD }, rectRadius: 0.08,
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y, w: 0.12, h: 1.05, fill: { color: i === 2 ? TEAL : ACCENT },
    });
    s.addText(c.t, {
      x: 0.85, y: y + 0.15, w: 8.4, h: 0.35,
      fontSize: 18, fontFace: "Georgia", color: ICE, bold: true, margin: 0,
    });
    s.addText(c.d, {
      x: 0.85, y: y + 0.5, w: 8.4, h: 0.4,
      fontSize: 14, fontFace: "Calibri", color: MUTED, margin: 0,
    });
  });
  addFooter(s, 2, TOTAL);
}

// 3 Operating stack
{
  const s = pres.addSlide();
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 5.625, fill: { color: BG } });
  s.addText("Operating level", {
    x: 0.5, y: 0.35, w: 9, h: 0.5,
    fontSize: 28, fontFace: "Georgia", color: WHITE, bold: true, margin: 0,
  });
  const layers = [
    { k: "L0", v: "token-saver · sequential thinking · humanizer" },
    { k: "OS", v: "AKOS · pro-code · mastermind · AZOP waves" },
    { k: "Motions", v: "Company-aligned helixes (SpaceX · xAI · NVIDIA · Anthropic · Microsoft)" },
    { k: "Hygiene", v: "Private-first · legal absolute lock · readiness scores 0–99" },
  ];
  layers.forEach((L, i) => {
    const x = 0.5 + (i % 2) * 4.6;
    const y = 1.15 + Math.floor(i / 2) * 1.7;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y, w: 4.35, h: 1.5, fill: { color: CARD }, rectRadius: 0.08,
    });
    s.addText(L.k, {
      x: x + 0.25, y: y + 0.25, w: 3.8, h: 0.35,
      fontSize: 16, fontFace: "Consolas", color: ACCENT, bold: true, margin: 0,
    });
    s.addText(L.v, {
      x: x + 0.25, y: y + 0.7, w: 3.8, h: 0.6,
      fontSize: 13, fontFace: "Calibri", color: ICE, margin: 0,
    });
  });
  addFooter(s, 3, TOTAL);
}

// 4 Flagship scores
{
  const s = pres.addSlide();
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 5.625, fill: { color: BG } });
  s.addText("Flagship demo readiness", {
    x: 0.5, y: 0.3, w: 9, h: 0.45,
    fontSize: 26, fontFace: "Georgia", color: WHITE, bold: true, margin: 0,
  });
  s.addText("Interview/demo score 0–99 · not flight certification", {
    x: 0.5, y: 0.75, w: 9, h: 0.3,
    fontSize: 12, fontFace: "Calibri", color: MUTED, italic: true, margin: 0,
  });
  const scores = [
    { n: "99", l: "xai-colossus-cooling" },
    { n: "97", l: "spacex-thermal-protection" },
    { n: "96", l: "colossus energy / nanosphere" },
    { n: "92", l: "orbital · telemetry" },
    { n: "91", l: "colossus-gateway" },
    { n: "88", l: "NVIDIA · Anthropic · pro-code" },
  ];
  scores.forEach((sc, i) => {
    const y = 1.15 + i * 0.6;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: 0.5, y, w: 1.2, h: 0.5, fill: { color: ACCENT }, rectRadius: 0.06,
    });
    s.addText(sc.n, {
      x: 0.5, y, w: 1.2, h: 0.5,
      fontSize: 18, fontFace: "Consolas", color: WHITE, bold: true,
      align: "center", valign: "middle", margin: 0,
    });
    s.addText(sc.l, {
      x: 1.9, y, w: 7.5, h: 0.5,
      fontSize: 16, fontFace: "Calibri", color: ICE, valign: "middle", margin: 0,
    });
  });
  addFooter(s, 4, TOTAL);
}

// 5 SpaceX
{
  const s = pres.addSlide();
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 5.625, fill: { color: BG } });
  s.addText("SpaceX — bottleneck → motion", {
    x: 0.5, y: 0.35, w: 9, h: 0.5,
    fontSize: 26, fontFace: "Georgia", color: WHITE, bold: true, margin: 0,
  });
  const rows = [
    ["Reentry / TPS", "spacex-thermal-protection (97)"],
    ["Launch cadence", "launch-sequencer · mission-control"],
    ["Telemetry / ground", "telemetry · ground-network"],
    ["Orbital / mission SW", "orbital-mechanics · mission-control"],
    ["Propulsion health", "propulsion-monitor"],
    ["Constellation mesh", "satellite-mesh"],
  ];
  rows.forEach((r, i) => {
    const y = 1.05 + i * 0.6;
    s.addText(r[0], {
      x: 0.5, y, w: 3.5, h: 0.5,
      fontSize: 14, fontFace: "Calibri", color: ACCENT, bold: true, valign: "middle", margin: 0,
    });
    s.addText(r[1], {
      x: 4.1, y, w: 5.4, h: 0.5,
      fontSize: 14, fontFace: "Consolas", color: ICE, valign: "middle", margin: 0,
    });
  });
  addFooter(s, 5, TOTAL);
}

// 6 xAI
{
  const s = pres.addSlide();
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 5.625, fill: { color: BG } });
  s.addText("xAI — Colossus-class", {
    x: 0.5, y: 0.35, w: 9, h: 0.5,
    fontSize: 26, fontFace: "Georgia", color: WHITE, bold: true, margin: 0,
  });
  const items = [
    { t: "Cooling 99", d: "Physics-first thermal core · exact SI · zone model" },
    { t: "Energy / Nano 96", d: "Power & nanosphere pillars" },
    { t: "Gateway 91", d: "MCP bridge for colossus orchestration" },
    { t: "Infra 80–88", d: "servers · security · colossus-2" },
  ];
  items.forEach((it, i) => {
    const x = 0.5 + (i % 2) * 4.6;
    const y = 1.15 + Math.floor(i / 2) * 1.75;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y, w: 4.35, h: 1.55, fill: { color: CARD }, rectRadius: 0.08,
    });
    s.addText(it.t, {
      x: x + 0.25, y: y + 0.3, w: 3.85, h: 0.4,
      fontSize: 18, fontFace: "Georgia", color: TEAL, bold: true, margin: 0,
    });
    s.addText(it.d, {
      x: x + 0.25, y: y + 0.85, w: 3.85, h: 0.5,
      fontSize: 13, fontFace: "Calibri", color: ICE, margin: 0,
    });
  });
  addFooter(s, 6, TOTAL);
}

// 7 NVIDIA Anthropic Microsoft
{
  const s = pres.addSlide();
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 5.625, fill: { color: BG } });
  s.addText("Elevated families", {
    x: 0.5, y: 0.35, w: 9, h: 0.5,
    fontSize: 26, fontFace: "Georgia", color: WHITE, bold: true, margin: 0,
  });
  const fam = [
    { co: "NVIDIA", sc: "88", d: "gpu-health · deep-reasoning\nsrc + tests + AKOS" },
    { co: "Anthropic", sc: "83–88", d: "safety-monitor · agent-coordinator\nPro-comet-agent" },
    { co: "Microsoft", sc: "80", d: "azure-ops multi-region\nlatency · error · cost" },
  ];
  fam.forEach((f, i) => {
    const x = 0.45 + i * 3.15;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y: 1.2, w: 3.0, h: 3.4, fill: { color: CARD }, rectRadius: 0.1,
    });
    s.addText(f.co, {
      x: x + 0.2, y: 1.5, w: 2.6, h: 0.4,
      fontSize: 18, fontFace: "Georgia", color: WHITE, bold: true, margin: 0,
    });
    s.addText(f.sc, {
      x: x + 0.2, y: 2.1, w: 2.6, h: 0.55,
      fontSize: 28, fontFace: "Consolas", color: ACCENT, bold: true, margin: 0,
    });
    s.addText(f.d, {
      x: x + 0.2, y: 2.9, w: 2.6, h: 1.3,
      fontSize: 13, fontFace: "Calibri", color: ICE, margin: 0,
    });
  });
  addFooter(s, 7, TOTAL);
}

// 8 AZOP
{
  const s = pres.addSlide();
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 5.625, fill: { color: BG } });
  s.addText("How I work — AZOP waves", {
    x: 0.5, y: 0.35, w: 9, h: 0.5,
    fontSize: 26, fontFace: "Georgia", color: WHITE, bold: true, margin: 0,
  });
  const steps = [
    { n: "1", t: "MICROWAVE", d: "Parallel explore\nread-only" },
    { n: "2", t: "CORE-THINK", d: "Parent synth\npointers only" },
    { n: "3", t: "VIPER", d: "Worktree\nimplement" },
    { n: "4", t: "VERIFY", d: "Tests + gates\nthen merge" },
  ];
  steps.forEach((st, i) => {
    const x = 0.45 + i * 2.4;
    s.addShape(pres.shapes.OVAL, {
      x: x + 0.85, y: 1.3, w: 0.55, h: 0.55, fill: { color: ACCENT },
    });
    s.addText(st.n, {
      x: x + 0.85, y: 1.3, w: 0.55, h: 0.55,
      fontSize: 16, fontFace: "Consolas", color: WHITE, bold: true,
      align: "center", valign: "middle", margin: 0,
    });
    if (i < 3) {
      s.addShape(pres.shapes.RIGHT_ARROW, {
        x: x + 1.9, y: 1.45, w: 0.35, h: 0.25,
        fill: { color: MUTED },
      });
    }
    s.addText(st.t, {
      x, y: 2.15, w: 2.2, h: 0.4,
      fontSize: 14, fontFace: "Consolas", color: TEAL, bold: true,
      align: "center", margin: 0,
    });
    s.addText(st.d, {
      x, y: 2.65, w: 2.2, h: 1.0,
      fontSize: 13, fontFace: "Calibri", color: ICE,
      align: "center", margin: 0,
    });
  });
  s.addText("Token-saver always on · legal never on hire surface · private-first", {
    x: 0.5, y: 4.3, w: 9, h: 0.4,
    fontSize: 13, fontFace: "Calibri", color: MUTED, italic: true, margin: 0,
  });
  addFooter(s, 8, TOTAL);
}

// 9 Demo path
{
  const s = pres.addSlide();
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 5.625, fill: { color: BG } });
  s.addText("15-minute live demo", {
    x: 0.5, y: 0.35, w: 9, h: 0.5,
    fontSize: 26, fontFace: "Georgia", color: WHITE, bold: true, margin: 0,
  });
  const demo = [
    "AKOS — governance & portfolio truth",
    "xai-colossus-cooling — physics walk (99)",
    "spacex-thermal-protection — reentry framing (97)",
    "nvidia-gpu-health or anthropic-safety-monitor (88)",
    "Honest assessment + SpaceX shark-laser showcase",
  ];
  demo.forEach((d, i) => {
    const y = 1.1 + i * 0.7;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: 0.5, y, w: 0.55, h: 0.55, fill: { color: TEAL }, rectRadius: 0.08,
    });
    s.addText(String(i + 1), {
      x: 0.5, y, w: 0.55, h: 0.55,
      fontSize: 18, fontFace: "Consolas", color: WHITE, bold: true,
      align: "center", valign: "middle", margin: 0,
    });
    s.addText(d, {
      x: 1.3, y, w: 8, h: 0.55,
      fontSize: 16, fontFace: "Calibri", color: ICE, valign: "middle", margin: 0,
    });
  });
  addFooter(s, 9, TOTAL);
}

// 10 Close
{
  const s = pres.addSlide();
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 5.625, fill: { color: BG } });
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 0.18, h: 5.625, fill: { color: ACCENT } });
  s.addText("Not claiming employment.\nClaiming systems you can walk.", {
    x: 0.6, y: 1.3, w: 8.8, h: 1.3,
    fontSize: 26, fontFace: "Georgia", color: WHITE, bold: true, margin: 0,
  });
  s.addText("Ask: special-projects / multi-domain on-demand seat\nGitHub: GlacierEQ  ·  Start: AKOS  ·  Flagship: cooling + thermal-protection", {
    x: 0.6, y: 2.9, w: 8.8, h: 1.0,
    fontSize: 15, fontFace: "Calibri", color: ICE, margin: 0,
  });
  s.addText("Resume: RESUME_GLACIEREQ_ELITE.md  ·  Scores: READINESS_SCORES.md", {
    x: 0.6, y: 4.3, w: 8.8, h: 0.35,
    fontSize: 12, fontFace: "Consolas", color: MUTED, margin: 0,
  });
  addFooter(s, 10, TOTAL);
}

pres.writeFile({ fileName: out }).then(() => console.log("wrote", out)).catch(e => { console.error(e); process.exit(1); });
