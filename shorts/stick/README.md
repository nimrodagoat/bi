# Stickman stories

Animated stick-figure survival series ("format: stickman" in the queue). Each
video is one day of a series: a hook, the series title card, numbered rules,
an inventory count, a radio broadcast, a map, a tense walk, and a two-option
cliffhanger ("comment below") ending on "follow for day N+1". A counter in the
corner shows the day, the clock, the place and how much light is left.

Everything is drawn by code (cairo) and the sound effects and low drone are
generated (`sound.py`); the narrator is Kokoro (Edge as backup), voiced one
sentence at a time so captions stay in sync. Preview one entry quickly:
`python -m shorts preview ID`.

## Queue entry

```yaml
- id: blackout-day-2
  format: stickman
  series: BLACKOUT          # title card / end card name
  day_label: NIGHT          # optional: count NIGHT 1, 2... instead of DAY
  day: 2
  place: APT 6B             # shown under the clock until a shot changes it
  title: "..."
  tags: [...]
  shots:
    - scene: room           # see scenes below
      time: "9:14 PM"       # clock; small jumps to the next shot tick by
      light: 82             # the meter (0-100), or [from, to] across the shot
      meter_label: WARMTH   # optional; the meter is called LIGHT unless set (also on the entry)
      rule: {n: 4, text: Never answer}   # big rule card, then it shrinks to the top
      say: "One or more sentences. Pauses come from the punctuation..."
```

`say` can also be a list mixing narration and radio lines:
`[ "At midnight, the radio crackles.", {radio: "Shelter at the stadium."} ]`.

Cues (when something happens) are a word the narrator says in that shot
(`cue: batteries`), seconds (`2.5`), a share (`"40%"`) or `"end-1"`.

## Scenes and their options

- `room`: apartment. `furniture: false` (empty room / shop), `monitors: true` (security
  office wall of screens instead of the window), `desk`, `door: false`, `clock`,
  `mannequins: [{x, facing, turn: cue}]` (pale figures that snap round at the cue), `dark` (0-1), `you: {x, to, action, move, then, light, aim, facing, go, arrive}`,
  `creatures: [{x, facing, cue, action, scale, to}]`, `lamp`, `door_open`,
  `barricade: true | {start, end, remove}`, `window`, `picture`, `on_air: on|off|flicker` (or `[[state, cue], ...]`: a radio studio's ON AIR sign).
- `hallway`: corridor seen from the door. `lights: on|off|flicker|dying` (`off: cue` for dying),
  `dark`, `rolling: {from, to}` (a flashlight rolling away), `figures: [{who: creature|person, z, x, cue, to_z}]`,
  `open_doors: [0, 3]`, `marks` (drag marks).
- `peephole`: the hallway through a peephole (same options).
- `cctv`: a security-camera monitor showing another scene: `view: {scene: hallway, ...}`,
  `cam: CAM 03`, `src_y` (which part of the view), `zoom`, `glitch: cue`.
  Hallway `shops: true` turns the doors into mall shop windows with signs.
- `inventory`: `items: [{icon, count, label, cue}]` (icons: battery, candle, matches,
  flashlight, can, bottle, key), `total: {text, cue}`.
- `radio`: `on: cue`; radio lines in `say` get teal captions and a radio sound. `radio_label` (any shot) replaces
  the "EMERGENCY BROADCAST · RADIO" tag shown while a radio line plays (e.g. `INTERCOM`).
- `map`: blueprint map. `route: [[x, y], ...]` (0-1), `route_cue`, `route_end`, `target: {label, cue}`,
  `bracket: {label, cue}`, `lamps: {cue}` (street lights going dead), `danger: [{x, y, r, cue}]`,
  `x_marks: [{x, y, cue}]`, `stops: [{x, y, label, cue, ghost, left}]` (named stations; `ghost` = red).
- `street`: side-scrolling night street. `pace: walk|run`, `speed`, `offset`, `stop: cue`,
  `lurkers: N` (creatures that back away from the beam), `chasers: {n, cue}`,
  `counter: [{text, label, cue}]` (big numbers passing by), `eyes: {cue, n}`.
- `closeup`: `object: flashlight|phone|alarm`.
- `train`: inside a subway car, seen from the side. `passengers: [{x, sit, color, coat, asleep, stare, cue, fade, turn}]`
  (`coat: true` = the man in the grey coat), `next: "NEXT: CANAL"` (or `[[text, cue], ...]`) on the sign over the door,
  `lights: on|flicker|off|dying` (or `[[state, cue], ...]`), `stop: cue` (brakes), `start: cue`, `parked: true`,
  `speed`, `station: {name, color, sign, flicker, people: [{x, facing, turn, stare, coat}]}` (the platform slides in as
  the train stops), `doors: {open, close}`, `tunnel_eyes: N`, `eyes_cue`, `you` (`action: sit` works), `creatures`.
- `tunnel`: the driver's view down the tunnel, with the dashboard and a speed gauge. `speed`, `stop`, `start`, `parked`,
  `signal: red|green|yellow` (or `[[colour, cue], ...]`), `next`, `station: {name, park, flicker, people: [{dz, x, turn, stare, coat}]}`,
  `figures` (like the hallway's; they stand still so the train closes in), `headlights: false`, `dies`/`flicker`/`relight`.
- `title`: series name + day over the previous picture.
- `choice`: `question`, `options: [{text, cue}, {text, cue}]`, `base: {a scene to show behind}`.
- `endcard`: "follow for day N+1"; flips to the next day at the end. `final: true` on the
  last part: "THE END?" and "follow for a new story".

Hallway colours: `wall`, `floor`, `carpet`, `ceiling`, `exit_color` (e.g. a garage or a
stadium tunnel); a `who: person` figure can have `stare: true` (shining eyes).
Street: `floodlights: cue` (bright lights ahead), `dawn: true` (sunrise sky), `rooftop: true`,
`people: [{x, action, cue, fade, facing, drift}]` (other people). Closeup flashlight: `eyes: N`, `eyes_cue`.

Any shot: `recap: true` (shows PREVIOUSLY; use it for the opening line of parts 2+), `snow: {n, speed, wind}` (or `snow: true`), `fog: {top: 0.6, rise: [0.8, 0.5], cue, density, color}` (rolling fog), `flicker: cue`, `relight: cue`, `dies: cue` (the flashlight fails), `heartbeat: cue`,
`shake_at: [cue]`, `camera: {zoom: [1, 1.1], focus: [x, y], shift}`, `hold` (extra seconds),
`sfx: [{name: knock|boom|hit|click|whoosh|tick, at: cue, gain}]`, `no_hud`.
