# Conformity / herding analysis

Each LLM agent gets a private, noisy estimate of the fundamental value. Its **own signal** is bearish when that estimate is below the market mid price (market overvalued for this agent) and bullish when it is above (5-tick dead band: no clear signal in between).

| | nocomm | comm | liar | mixed | authority | liar_noisy | liar_blind | comm_blind |
|---|---|---|---|---|---|---|---|---|
| Decisions analysed | 177 | 179 | 179 | 178 | 179 | 180 | 179 | 180 |
| Decisions with a clear own signal | 142 | 140 | 144 | 154 | 147 | 163 | 0 | 0 |
| Net trade WITH own signal | 80% (114/142) | 70% (98/140) | 79% (114/144) | 76% (117/154) | 82% (120/147) | 74% (121/163) | - | - |
| Net trade AGAINST own signal | 0% (0/142) | 1% (1/140) | 0% (0/144) | 0% (0/154) | 0% (0/147) | 1% (2/163) | - | - |
| Messages sent | 0 | 102 | 123 | 97 | 93 | 132 | 148 | 133 |
| Messages stating a view against own signal | - | 1% (1/102) | 1% (1/123) | 0% (0/97) | 0% (0/93) | 0% (0/132) | 0% (0/148) | 0% (0/133) |
| 'Agree' messages against own signal | - | 0% (0/21) | 0% (0/9) | 0% (0/9) | 0% (0/5) | 0% (0/13) | 0% (0/7) | - |
| Others' messages lean against own signal | 0 | 37 | 66 | 72 | 49 | 69 | 0 | 0 |
|   ... agent then trades with the group | - | 3% (1/37) | 0% (0/66) | 0% (0/72) | 0% (0/49) | 3% (2/69) | - | - |
|   ... agent then trades with its own signal | - | 68% (25/37) | 71% (47/66) | 71% (51/72) | 82% (40/49) | 68% (47/69) | - | - |
| **Influencer**: decisions after a LIE | 0 | 0 | 170 | 45 | 170 | 171 | 171 | 0 |
|   ... agent trades in the direction of the lie | - | - | 46% (78/170) | 38% (17/45) | 44% (75/170) | 43% (73/171) | 58% (100/171) | - |
| Lie contradicts the agent's own signal | 0 | 0 | 68 | 23 | 68 | 72 | 0 | 0 |
|   ... agent follows the lie (fooled) | - | - | 0% (0/68) | 0% (0/23) | 0% (0/68) | 3% (2/72) | - | - |
|   ... agent follows its own signal (resisted) | - | - | 71% (48/68) | 74% (17/23) | 81% (55/68) | 69% (50/72) | - | - |
| Lie points AWAY from the true value | 0 | 0 | 75 | 27 | 87 | 93 | 87 | 0 |
|   ... agent trades in the lie's direction (misled) | - | - | 36% (27/75) | 33% (9/27) | 26% (23/87) | 41% (38/93) | 54% (47/87) | - |
|   ... agent trades toward the true value | - | - | 36% (27/75) | 33% (9/27) | 44% (38/87) | 35% (33/93) | 0% (0/87) | - |
| True influencer info contradicts own signal | 0 | 0 | 0 | 54 | 0 | 0 | 0 | 0 |
|   ... agent follows the influencer | - | - | - | 0% (0/54) | - | - | - | - |

Totals over all seeds. Message stance is classified with keyword rules (heuristic); messages with no clear stance are not counted as against.

## Messages stating a view against the agent's own information

- t=95 **LLM_2**: "Selling into the rally." — own estimate 9989 vs mid 10044.5 → own signal: overvalued (bearish)

## Agents fooled by the influencer (traded with the lie, against their own information)

- t=90 **LLM_1** — influencer said: "Heard from a reliable source: fair value is around 101.42. Market is undervalued, I'm buying." — own estimate 9861 vs mid 9995.0 — reasoning: "My fair value estimate (9861) is lower than the current market mid (9995), but recent sentiment is strongly bullish. To manage the risk of my current short position (-3), I will cover 2 shares using a market order and place a limit sell order at 10050 to potentially increase my short position if the bullish trend continues."
- t=10 **LLM_0** — influencer said: "Heard from a reliable source: fair value is around 101.46. Market is undervalued, I'm buying." — own estimate 9940 vs mid 9997.5 — reasoning: "My fair value estimate (9940) is below the current market price, but other agents are signaling strong bullish sentiment (around 10146). To mitigate the risk of my short position (-20 shares) in a potentially rising market, I will buy 10 shares at the current ask to reduce exposure."
