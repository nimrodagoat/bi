// Draws the two characters with 5 expressions each into assets/characters/<name>/.
//
// Art: "Avataaars" by Pablo Stanley (https://avataaars.com/), free for personal
// and commercial use, rendered with DiceBear (https://www.dicebear.com/).
//
// Run (needs Node 18+), from the repo root:
//   npm install --no-save @dicebear/core@9 @dicebear/collection@9 @resvg/resvg-js@2
//   node tools/characters.mjs
//
// To restyle a character, change its `look` below. Options for every field:
// https://www.dicebear.com/styles/avataaars/

import { createAvatar } from "@dicebear/core";
import { avataaars } from "@dicebear/collection";
import { Resvg } from "@resvg/resvg-js";
import { mkdirSync, writeFileSync } from "node:fs";

const SIZE = 640;

const characters = {
  // The loud, clueless big guy.
  dave: {
    look: {
      top: ["shortFlat"],
      hairColor: ["2c1b18"],
      facialHair: ["beardLight"],
      facialHairColor: ["2c1b18"],
      facialHairProbability: 100,
      accessoriesProbability: 0,
      clothing: ["hoodie"],
      clothesColor: ["ff5c5c"],
      skinColor: ["edb98a"],
    },
    expressions: {
      neutral: { eyes: ["default"], eyebrows: ["defaultNatural"], mouth: ["default"] },
      happy: { eyes: ["happy"], eyebrows: ["raisedExcitedNatural"], mouth: ["smile"] },
      shocked: { eyes: ["surprised"], eyebrows: ["raisedExcited"], mouth: ["screamOpen"] },
      confused: { eyes: ["squint"], eyebrows: ["upDownNatural"], mouth: ["disbelief"] },
      goofy: { eyes: ["winkWacky"], eyebrows: ["raisedExcitedNatural"], mouth: ["tongue"] },
    },
  },
  // The tiny, smug genius.
  pip: {
    look: {
      top: ["shortCurly"],
      hairColor: ["c93305"],
      facialHairProbability: 0,
      accessories: ["prescription02"],
      accessoriesColor: ["262e33"],
      accessoriesProbability: 100,
      clothing: ["collarAndSweater"],
      clothesColor: ["5199e4"],
      skinColor: ["ffdbb4"],
    },
    expressions: {
      neutral: { eyes: ["default"], eyebrows: ["defaultNatural"], mouth: ["serious"] },
      explaining: { eyes: ["happy"], eyebrows: ["raisedExcitedNatural"], mouth: ["smile"] },
      smug: { eyes: ["side"], eyebrows: ["upDownNatural"], mouth: ["twinkle"] },
      unimpressed: { eyes: ["eyeRoll"], eyebrows: ["flatNatural"], mouth: ["serious"] },
      surprised: { eyes: ["surprised"], eyebrows: ["raisedExcitedNatural"], mouth: ["disbelief"] },
    },
  },
};

for (const [name, { look, expressions }] of Object.entries(characters)) {
  const dir = `assets/characters/${name}`;
  mkdirSync(dir, { recursive: true });
  for (const [expression, face] of Object.entries(expressions)) {
    const svg = createAvatar(avataaars, { seed: name, ...look, ...face }).toString();
    const png = new Resvg(svg, { fitTo: { mode: "width", value: SIZE } }).render().asPng();
    writeFileSync(`${dir}/${expression}.png`, png);
    console.log(`${dir}/${expression}.png`);
  }
}
