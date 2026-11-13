---
name: release-radio
description: Turns two weeks of a team's delivery data into WREL's Release Hour, a 1940s radio broadcast. A vintage announcer reads a release report written by fixed rules from deploys, CI runs, incidents, rollbacks and SLO burn, with an urgent bulletin for each incident, a jazz-age theme to open and close and The Record citing the evidence for every line. Outputs an offline player page, the script, a live-read cue sheet and The Record, plus a mixed broadcast WAV when a voice is provided (ElevenLabs or one recorded read). Use for a release retro, a sprint review, a talk or "how did the last two weeks go?"
---

# Release Radio

Good evening, ladies and gentlemen. Release Radio puts your last two weeks on the air as WREL's Release Hour: a 1940s announcer reads the release report, the theme plays it in and out and a chime sounds before every urgent bulletin.

The broadcast sits on top of the evidence, never instead of it. Every line comes from a rule over the data, and The Record shows the evidence behind it.

## When to use

- A retro, sprint review or leadership update where a dashboard would get skimmed.
- A talk about delivery health that needs a moment people remember.
- Someone asks "how did the last two weeks go?" and should hear the answer.

## Run

Read-only and Python standard library only. The ElevenLabs API step is optional and the only network call.

```bash
python scripts/radio.py demo --out radio                              # the bundled fictional storefront
python scripts/radio.py play --data DIR --out radio                   # your data
python scripts/radio.py play --data DIR --out radio --voice-file read.wav           # one recorded read of script.txt
python scripts/radio.py play --data DIR --out radio --voice elevenlabs --voice-id ID  # ElevenLabs API, needs ELEVENLABS_API_KEY
python scripts/check_data.py DIR                                      # check gathered data first
```

Options: `--days 14`, `--as-of 2026-11-08T22:00:00Z` (both can also come from `manifest.json`), `--theme your_theme.wav`.

| Output | What it is |
| --- | --- |
| `player.html` | One offline page: the radio, the broadcast with captions, a day-by-day timeline that lights up as each day is read, the script cards and The Record |
| `broadcast.wav`, `cues.json` | The mixed broadcast and what is on the air when (when a voice is provided) |
| `script.txt` | The whole script, one paragraph per segment, for one recorded read |
| `script.md` | A cue sheet for reading it live, with theme and chime cues |
| `the_record.md` | Every segment, every day and the evidence behind it |
| `score.json`, `script.json` | The sorted days and the script, as data |

Without a voice, the player plays the theme and the browser's own voice reads the script.

## A real announcer

- **Through an ElevenLabs connector in chat:** generate `script.txt` as one read in a vintage announcer voice (for example Clyde, the vintage male radio announcer in the ElevenLabs library), convert it to WAV and pass it as `--voice-file`. The mixer splits it at the paragraph pauses and checks every piece against its word count.
- **Through the API:** `--voice elevenlabs --voice-id ID` with `ELEVENLABS_API_KEY`. Only the script text is sent. It goes one segment per call and each segment is cached.

## The rules

Full table in `references/rules.md`. In short: each day is a freeze, an incident, rough going, the all clear or fair skies; runs of the same kind of day become one segment; each segment states only facts from the data, plus a fixed period flourish.

## Gathering (agents gather, rules decide)

Pull raw records through the connectors you have (GitHub for deployments and Actions runs, your incident tool, your observability tool for SLO burn) into the files in `references/data-contract.md`. Never write or edit the script, sort a day or compute a number yourself: the engine does. Record where each file came from in `manifest.json` under `provenance`.

Never name people. Deploys, runs and incidents belong to services.

## Human in the loop

The broadcast is advisory. Show the player, the script and The Record before sharing them anywhere, and end with "Draft, pending human review."
