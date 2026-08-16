// measure_texts.mjs
// Reads {width, height, texts:[{id, xml}]} from stdin, renders each <text> on a
// transparent canvas at its true position/rotation, and prints the ink AABB per id.
import { Resvg } from '@resvg/resvg-js';
import { PNG } from 'pngjs';

let input = '';
process.stdin.on('data', d => input += d);
process.stdin.on('end', () => {
  const job = JSON.parse(input);
  const out = {};
  for (const t of job.texts) {
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${job.width}" height="${job.height}" viewBox="0 0 ${job.width} ${job.height}">${t.xml}</svg>`;
    const r = new Resvg(svg, { fitTo: { mode: 'original' } });
    const png = PNG.sync.read(r.render().asPng());
    const { width, height, data } = png;
    let x0 = Infinity, y0 = Infinity, x1 = -1, y1 = -1;
    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const a = data[(y * width + x) * 4 + 3];
        if (a > 0) {
          if (x < x0) x0 = x;
          if (x > x1) x1 = x;
          if (y < y0) y0 = y;
          if (y > y1) y1 = y;
        }
      }
    }
    out[t.id] = (x0 === Infinity) ? null : [x0, y0, x1 + 1, y1 + 1];
  }
  process.stdout.write(JSON.stringify(out));
});
