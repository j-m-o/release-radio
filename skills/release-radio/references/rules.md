# The rules

The announcer never improvises. Each day is sorted by fixed rules, runs of the same kind of day become one segment and each segment is written from a template that only states facts in the data. Same data, same broadcast.

## Sorting a day

Checked in this order; the first that fits wins.

| Conditions | When |
| --- | --- |
| Freeze | No deploys, no rollbacks, no main-branch runs and no open incident |
| Incident | An incident is open and is not resolved that day |
| Rough going | At least one main-branch run failed |
| All clear | The day an incident resolves, and every clean day after it until the next incident |
| Fair skies | Everything else |

Feature branches are ignored: the station covers the main line.

## What the announcer says

| Segment | What it states |
| --- | --- |
| Sign on | The station, the system, the number of days, the title |
| Fair skies | The dates, the deploys and that every build came back clean |
| Rough going | The dates, failed builds out of total and the first flaky test by name |
| Freeze | The dates and that nothing shipped or built |
| Incident | An urgent bulletin: the date, the time in Greenwich time, the incident and the service, any rollback that day, the SLO burn rate if over 1.0 and how long the storm held |
| All clear | The resolution date, how many hours it took, then the deploys and builds in the days that followed |
| Sign off | Total deploys, builds and incidents, any missing source, good night |

The flourishes ("A team in step, ladies and gentlemen", "Rough going on the main line", "All quiet on the main line", "The all clear has sounded") are fixed per kind of day. They never add a fact.

## On the air

The WREL theme plays alone for a few seconds, then fades under the sign on. A station chime sounds before every urgent bulletin. The theme comes back under the sign off and plays the show out. The announcer is put through a narrow valve-radio filter with light crackle on the line.

## Missing data

A source that is missing or fails the data contract is left out. The sign off says which one was missing ("tonight's signal carried static") and nothing is guessed.

## Never

Names of people, guesses, numbers that are not in The Record.
