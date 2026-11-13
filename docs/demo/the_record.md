# The Record: The Week Checkout Came Back

WREL Release Radio | Storefront | 2026-10-26 to 2026-11-08

40 deploys | 109 main-branch builds (6 failed) | 1 incident

Every line the announcer reads comes from rules over this evidence. Same data, same broadcast.

## Days 1 to 4

> From Monday, October 26th through Thursday the 29th, fair skies over Storefront. 14 deploys went out, and all 33 builds on the main line came back clean. A team in step, ladies and gentlemen.

| Day | Date | Conditions | Evidence |
|---|---|---|---|
| 1 | 2026-10-26 | fair skies | all 8 main-branch runs passed; 3 deploys (catalog, checkout, search) |
| 2 | 2026-10-27 | fair skies | all 8 main-branch runs passed; 4 deploys (accounts, catalog, payments, search) |
| 3 | 2026-10-28 | fair skies | all 8 main-branch runs passed; 3 deploys (accounts, payments, search) |
| 4 | 2026-10-29 | fair skies | all 9 main-branch runs passed; 4 deploys (accounts, catalog, checkout, payments) |

## Days 5 to 6

> On Friday, October 30th and Saturday the 31st, the weather turned. 5 of 17 builds failed, and a flaky test called cart total rounding was heard stuttering in the wings. Rough going on the main line.

| Day | Date | Conditions | Evidence |
|---|---|---|---|
| 5 | 2026-10-30 | rough going | 3 of 9 main-branch runs failed; run r-0501 failed (accounts); run r-0502 failed (checkout); run r-0504 failed (search); flaky test_cart_total_rounding_b; 3 deploys (accounts, catalog, checkout) |
| 6 | 2026-10-31 | rough going | 2 of 8 main-branch runs failed; run r-0602 failed (catalog); run r-0608 failed (search); flaky test_cart_total_rounding_b; 2 deploys (catalog, checkout) |

## Day 7

> On Sunday, November 1st, not one deploy and not one build. A deploy freeze. All quiet on the main line.

| Day | Date | Conditions | Evidence |
|---|---|---|---|
| 7 | 2026-11-01 | freeze | deploy freeze: no deploys and no CI runs |

## Day 8

> On Monday, November 2nd, the crews were back at work. 3 deploys went out, and all 8 builds on the main line came back clean.

| Day | Date | Conditions | Evidence |
|---|---|---|---|
| 8 | 2026-11-02 | fair skies | all 8 main-branch runs passed; 3 deploys (accounts, payments, search) |

## Days 9 to 10

> We interrupt this program with an urgent bulletin. On Tuesday, November 3rd, at 10:12 Greenwich time, incident number 7 struck the checkout service. A rollback of checkout was ordered that afternoon. The error budget was burning at 2.3 times the safe rate. Stay tuned to this station for further developments. The storm held through Wednesday the 4th.

| Day | Date | Conditions | Evidence |
|---|---|---|---|
| 9 | 2026-11-03 | incident | INC-07 opened (checkout); rollback d-09rb (checkout); SLO burn 2.3x (over 1.0); 1 of 9 main-branch runs failed; run r-0904 failed (catalog); 2 deploys (accounts, payments) |
| 10 | 2026-11-04 | incident | INC-07 still open (checkout); SLO burn 1.6x (over 1.0); all 8 main-branch runs passed; flaky test_cart_total_rounding_b; 1 deploy (accounts) |

## Days 11 to 14

> And then, on Thursday, November 5th, after 50 long hours, incident number 7 was resolved. The all clear has sounded. In the 3 days that followed, 13 deploys went out, and all 26 builds came back clean.

| Day | Date | Conditions | Evidence |
|---|---|---|---|
| 11 | 2026-11-05 | all clear | INC-07 resolved after 50h; all 8 main-branch runs passed; 2 deploys (catalog, checkout) |
| 12 | 2026-11-06 | all clear | all 9 main-branch runs passed; 4 deploys (accounts, catalog, payments, search) |
| 13 | 2026-11-07 | all clear | all 8 main-branch runs passed; 4 deploys (accounts, checkout, payments, search) |
| 14 | 2026-11-08 | all clear | all 9 main-branch runs passed; 5 deploys (accounts, catalog, checkout, payments, search) |

Advisory only. A person decides what any of this means.
