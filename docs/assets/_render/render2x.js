const fs = require('fs');
const { Resvg } = require('@resvg/resvg-js');
const jobs = [
  ['social-preview.svg', 'social-preview.png'],
  ['banner.svg', 'banner.png'],
];
for (const [inF, outF] of jobs) {
  const svg = fs.readFileSync(__dirname + '/../' + inF, 'utf-8');
  const r = new Resvg(svg, { fitTo: { mode: 'zoom', value: 2 } });
  const png = r.render().asPng();
  fs.writeFileSync(__dirname + '/../' + outF, png);
  console.log('rendered', outF, png.length, 'bytes');
}
