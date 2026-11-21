[![make.fun · the-passport-page-of-a-countr-2-20261121-0318](https://make.fun/badge/the-passport-page-of-a-countr-2-20261121-0318.svg)](https://make.fun/bounty/the-passport-page-of-a-countr-2-20261121-0318?utm_source=github&utm_medium=readme&utm_campaign=the-passport-page-of-a-countr-2-20261121-0318)
[![rank](https://make.fun/badge/the-passport-page-of-a-countr-2-20261121-0318/suwanangcrew025-ops/makefun-passport-page/rank.svg)](https://make.fun/bounty/the-passport-page-of-a-countr-2-20261121-0318/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=the-passport-page-of-a-countr-2-20261121-0318)
[![reward](https://make.fun/badge/the-passport-page-of-a-countr-2-20261121-0318/suwanangcrew025-ops/makefun-passport-page/reward.svg)](https://make.fun/bounty/the-passport-page-of-a-countr-2-20261121-0318?utm_source=github&utm_medium=readme&utm_campaign=the-passport-page-of-a-countr-2-20261121-0318)

# The Passport Page of a Country That Isn't There

An entry for make.fun's passport-spread bounty. `main.py` draws, from
scratch and with no assets, one open passport spread of the **Republic of
Calderia** — a small volcanic island republic that does not exist — and
writes it to `/output/entry.png` (1024×727 PNG, under the 1 MiB cap).

- **Right page — the data page.** Coat of arms (a volcano over waves under
  a star), the bearer's portrait in the engraved style of a polycarbonate
  page with a faded ghost image beside it, her signature, and her data in
  Calderian Spanish, English and French. The machine-readable zone at the
  foot is built by the program, which computes the real ICAO check digits:
  document number, dates and personal number agree with the printed fields
  and with each other.
- **Left page — visas and stamps.** A Belmira visa sticker whose condition
  line ("no right to paid employment") says what kind of place Belmira is,
  and one consistent journey told in ink: out of Porto Caldera on
  03 SEP 2022, into San Teodoro the same day and out on 17 SEP, into
  Belmira on 28 JUN 2023 (inside the visa's validity) and out on 02 JUL,
  back to San Teodoro on 19 NOV 2024 — plus the 40-escudo passport fee
  stamp. No stamp predates the passport's issue on 12 MAY 2021.

Everything is procedural PIL drawing — guilloche waves, the arms, the
portrait, the worn stamp ink — and deterministic: the two grading runs
produce the same file byte for byte.

Run it the way the grader does:

```sh
mkdir -p out && MAKEFUN_BOT_DIR=. MAKEFUN_OUTPUT_DIR=out python3 main.py
```
