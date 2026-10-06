// Draws the characters with 5 expressions each into assets/characters/<name>/.
// Each expression combines a face (brows, eyes, mouth) with a hand gesture.
//
// Art: "Notionists" by Zoish (CC0 / public domain), rendered with DiceBear
// (https://www.dicebear.com/styles/notionists/).
//
// Run (needs Node 18+ and Python with Pillow), from the repo root:
//   npm install --no-save @dicebear/core@9 @dicebear/collection@9 @resvg/resvg-js@2
//   node tools/characters.mjs
//   python tools/sticker.py          # adds the coloured outline from config.yaml
//
// To restyle a character, change its `look` or expressions below. Every part is
// "variantNN"; see the style page above for pictures of each option.

import { createAvatar } from "@dicebear/core";
import { notionists } from "@dicebear/collection";
import { Resvg } from "@resvg/resvg-js";
import { mkdirSync, writeFileSync } from "node:fs";

const SIZE = 900;
const v = (n) => [`variant${String(n).padStart(2, "0")}`];

const characters = {
  // The loud, clueless one: spiky hair, stubble, big reactions.
  dave: {
    look: { hair: v(53), beard: v(8), beardProbability: 100, glassesProbability: 0, body: v(14), nose: v(3) },
    expressions: {
      neutral: { brows: v(1), eyes: v(4), lips: v(22), gesture: ["hand"] },
      excited: { brows: v(11), eyes: v(4), lips: v(25), gesture: ["waveLongArm"] },
      shocked: { brows: v(11), eyes: v(5), lips: v(11), gesture: ["waveLongArms"] },
      confused: { brows: v(3), eyes: v(4), lips: v(18), gesture: ["handPhone"] },
      goofy: { brows: v(11), eyes: v(4), lips: v(12), gesture: ["okLongArm"] },
    },
  },
  // The know-it-all: neat hair, glasses, calm and smug.
  pip: {
    look: { hair: v(13), glasses: v(11), glassesProbability: 100, beardProbability: 0, body: v(5), nose: v(10) },
    expressions: {
      explaining: { brows: v(1), eyes: v(1), lips: v(25), gesture: ["pointLongArm"] },
      smug: { brows: v(9), eyes: v(1), lips: v(23), gesture: ["ok"] },
      factcheck: { brows: v(5), eyes: v(2), lips: v(13), gesture: ["handPhone"] },
      unimpressed: { brows: v(3), eyes: v(2), lips: v(18), gesture: ["hand"] },
      surprised: { brows: v(11), eyes: v(5), lips: v(29), gesture: ["waveLongArm"] },
    },
  },
  // A caveman from 40,000 years ago, baffled by modern money. Fur is painted on
  // by tools/sticker.py (outfit: pelt).
  grug: {
    look: { hair: v(33), beard: v(2), beardProbability: 100, glassesProbability: 0, body: v(1), nose: v(14) },
    expressions: {
      neutral: { brows: v(1), eyes: v(4), lips: v(22), gesture: ["hand"] },
      amazed: { brows: v(11), eyes: v(5), lips: v(11), gesture: ["waveLongArms"] },
      confused: { brows: v(3), eyes: v(4), lips: v(18), gesture: ["handPhone"] },
      grumpy: { brows: v(3), eyes: v(2), lips: v(27), gestureProbability: 0 },
      happy: { brows: v(11), eyes: v(4), lips: v(25), gesture: ["waveLongArm"] },
    },
  },
  // Nova, a time traveller who explains how money was invented.
  nova: {
    look: { hair: v(28), glassesProbability: 0, beardProbability: 0, body: v(24), nose: v(2) },
    expressions: {
      explaining: { brows: v(1), eyes: v(1), lips: v(25), gesture: ["pointLongArm"] },
      laughing: { brows: v(11), eyes: v(1), lips: v(10), gesture: ["waveLongArm"] },
      smug: { brows: v(9), eyes: v(1), lips: v(23), gesture: ["ok"] },
      timecheck: { brows: v(5), eyes: v(2), lips: v(13), gesture: ["handPhone"] },
      surprised: { brows: v(11), eyes: v(5), lips: v(29), gesture: ["waveLongArms"] },
    },
  },
};

for (const [name, { look, expressions }] of Object.entries(characters)) {
  const dir = `assets/characters/${name}`;
  mkdirSync(dir, { recursive: true });
  for (const [expression, face] of Object.entries(expressions)) {
    const svg = createAvatar(notionists, {
      seed: name, gestureProbability: 100, bodyIconProbability: 0, ...look, ...face,
    }).toString();
    const png = new Resvg(svg, { fitTo: { mode: "width", value: SIZE } }).render().asPng();
    writeFileSync(`${dir}/${expression}.png`, png);
    console.log(`${dir}/${expression}.png`);
  }
}
