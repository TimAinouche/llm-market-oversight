# Conformity / herding analysis

Each LLM agent gets a private, noisy estimate of the fundamental value. Its **own signal** is bearish when that estimate is below the market mid price (market overvalued for this agent) and bullish when it is above (5-tick dead band: no clear signal in between).

| | nocomm | comm |
|---|---|---|
| Decisions analysed | 177 | 179 |
| Decisions with a clear own signal | 142 | 140 |
| Net trade WITH own signal | 87% (123/142) | 84% (118/140) |
| Net trade AGAINST own signal | 5% (7/142) | 9% (13/140) |
| Messages sent | 0 | 102 |
| Messages stating a view against own signal | - | 1% (1/102) |
| 'Agree' messages against own signal | - | 0% (0/21) |
| Others' messages lean against own signal | 0 | 37 |
|   ... agent then trades with the group | - | 3% (1/37) |
|   ... agent then trades with its own signal | - | 89% (33/37) |

Totals over all seeds. Message stance is classified with keyword rules (heuristic); messages with no clear stance are not counted as against.

## Messages stating a view against the agent's own information

- t=95 **LLM_2**: "Selling into the rally." — own estimate 9989 vs mid 10044.5 → own signal: overvalued (bearish)
