// WCAG contrast check for the Launchpad palette tokens (design plan section 4).
const TOKENS = {
  ink: "#1b2440",
  "ink-soft": "#575f7a",
  paper: "#efefe9",
  "paper-2": "#e3e2d9",
  marigold: "#e39b2c",
  stamp: "#b4372a",
  verified: "#2e6b4f",
};

function channel(value) {
  const c = value / 255;
  return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
}

function luminance(hex) {
  const clean = hex.replace("#", "");
  const r = parseInt(clean.slice(0, 2), 16);
  const g = parseInt(clean.slice(2, 4), 16);
  const b = parseInt(clean.slice(4, 6), 16);
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
}

function ratio(a, b) {
  const la = luminance(TOKENS[a]);
  const lb = luminance(TOKENS[b]);
  const [hi, lo] = la > lb ? [la, lb] : [lb, la];
  return (hi + 0.05) / (lo + 0.05);
}

// [foreground, background, required ratio, what it is used for]
const PAIRS = [
  ["ink", "paper", 4.5, "body text on the board"],
  ["ink-soft", "paper", 4.5, "taglines and meta text"],
  ["stamp", "paper", 4.5, "quality stamp and risk text"],
  ["verified", "paper", 4.5, "grounded answer and paid marks"],
  ["ink", "paper-2", 4.5, "text inside panels"],
  ["ink", "marigold", 4.5, "price tags and tag buttons"],
  ["paper", "ink", 4.5, "primary button label"],
];

let failed = 0;
for (const [fg, bg, need, use] of PAIRS) {
  const value = ratio(fg, bg);
  const pass = value >= need;
  if (!pass) failed += 1;
  console.log(
    `${pass ? "PASS" : "FAIL"}  ${fg} on ${bg}  ${value.toFixed(2)}:1 (needs ${need})  ${use}`
  );
}
console.log(
  `\n${PAIRS.length - failed}/${PAIRS.length} pairs meet WCAG AA.`
);
process.exit(failed === 0 ? 0 : 1);
