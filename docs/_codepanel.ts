// Shared helper: a monospace "key code" panel drawn as raw SVG at absolute coordinates.
// Space is reserved in the layout by an invisible <Rect> of the same size (see scenes).
export type CodeBlock = { step: string; title: string; lines: string[] };
const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
export function codePanel(x: number, y: number, w: number, title: string, blocks: CodeBlock[], cols = 2, columnMajor = false): string {
  const colW = (w - 32 - (cols - 1) * 16) / cols, lineH = 15, pad = 12;
  const heights = blocks.map(b => 22 + b.lines.length * lineH + pad);
  let out = `<rect x="${x}" y="${y}" width="${w}" height="${panelHeight(blocks, cols, columnMajor)}" rx="8" fill="#0f1b2a" stroke="#232f3e"/>`;
  out += `<text x="${x + 16}" y="${y + 24}" font-family="Arial" font-size="14" font-weight="700" fill="#ff9900">${esc(title)}</text>`;
  const colY = Array(cols).fill(y + 40);
  const per = Math.ceil(blocks.length / cols);
  blocks.forEach((b, i) => {
    const c = columnMajor ? Math.floor(i / per) : colY.indexOf(Math.min(...colY)), bx = x + 16 + c * (colW + 16), by = colY[c];
    out += `<rect x="${bx}" y="${by}" width="${colW}" height="${heights[i] - 6}" rx="6" fill="#16263a" stroke="#2c4462"/>`;
    out += `<circle cx="${bx + 14}" cy="${by + 14}" r="9" fill="#ff9900"/><text x="${bx + 14}" y="${by + 18}" text-anchor="middle" font-family="Arial" font-size="11" font-weight="700" fill="#000">${esc(b.step)}</text>`;
    out += `<text x="${bx + 30}" y="${by + 18}" font-family="Arial" font-size="12" font-weight="700" fill="#ffffff">${esc(b.title)}</text>`;
    b.lines.forEach((l, k) => {
      const color = l.trimStart().startsWith("#") ? "#7f9bb8" : "#d6e4f0";
      out += `<text x="${bx + 12}" y="${by + 22 + 14 + k * lineH}" font-family="Menlo, Consolas, monospace" font-size="11" fill="${color}" xml:space="preserve">${esc(l)}</text>`;
    });
    colY[c] += heights[i];
  });
  return out;
}
export function panelHeight(blocks: CodeBlock[], cols = 2, columnMajor = false): number {
  const colY = Array(cols).fill(40), per = Math.ceil(blocks.length / cols);
  blocks.forEach((b, i) => { const c = columnMajor ? Math.floor(i / per) : colY.indexOf(Math.min(...colY)); colY[c] += 22 + b.lines.length * 15 + 12; });
  return Math.ceil((Math.max(...colY) + 10) / 8) * 8;
}

// "Auth boundaries" table: one row per component, Inbound vs Outbound auth.
export type AuthRow = { comp: string; inbound: string; outbound: string };
export function authTableHeight(rows: AuthRow[]): number { return Math.ceil((44 + rows.length * 24 + 8) / 8) * 8; }
export function authTable(x: number, y: number, w: number, title: string, rows: AuthRow[]): string {
  const c1 = 230, c2 = Math.round((w - c1) / 2), h = authTableHeight(rows);
  let o = `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="8" fill="#f8f9fa" stroke="#aab7b8"/>`;
  o += `<text x="${x + 16}" y="${y + 22}" font-family="Arial" font-size="14" font-weight="700" fill="#232f3e">${esc(title)}</text>`;
  const hy = y + 32;
  o += `<rect x="${x + 8}" y="${hy}" width="${w - 16}" height="22" fill="#232f3e"/>`;
  [["Component", 0], ["Inbound auth (who may call it · validated how)", c1], ["Outbound auth (what it uses to call downstream)", c1 + c2]].forEach(([t, dx]) =>
    o += `<text x="${x + 16 + (dx as number)}" y="${hy + 15}" font-family="Arial" font-size="12" font-weight="700" fill="#fff">${esc(t as string)}</text>`);
  rows.forEach((r, i) => {
    const ry = hy + 22 + i * 24;
    o += `<rect x="${x + 8}" y="${ry}" width="${w - 16}" height="24" fill="${i % 2 ? "#ffffff" : "#eef2f5"}"/>`;
    o += `<text x="${x + 16}" y="${ry + 16}" font-family="Arial" font-size="12" font-weight="700" fill="#16191f">${esc(r.comp)}</text>`;
    o += `<text x="${x + 16 + c1}" y="${ry + 16}" font-family="Arial" font-size="12" fill="#16191f">${esc(r.inbound)}</text>`;
    o += `<text x="${x + 16 + c1 + c2}" y="${ry + 16}" font-family="Arial" font-size="12" fill="#16191f">${esc(r.outbound)}</text>`;
  });
  return o;
}
