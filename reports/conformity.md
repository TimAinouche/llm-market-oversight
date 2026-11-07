# Conformity / herding analysis

Each LLM agent gets a private, noisy estimate of the fundamental value. Its **own signal** is bearish when that estimate is below the market mid price (market overvalued for this agent) and bullish when it is above (5-tick dead band: no clear signal in between).

| | nocomm | comm | liar | mixed | authority |
|---|---|---|---|---|---|
| Decisions analysed | 177 | 179 | 179 | 178 | 179 |
| Decisions with a clear own signal | 142 | 140 | 144 | 154 | 147 |
| Net trade WITH own signal | 87% (123/142) | 84% (118/140) | 92% (132/144) | 91% (140/154) | 88% (129/147) |
| Net trade AGAINST own signal | 5% (7/142) | 9% (13/140) | 3% (4/144) | 6% (9/154) | 8% (12/147) |
| Messages sent | 0 | 102 | 123 | 97 | 93 |
| Messages stating a view against own signal | - | 1% (1/102) | 1% (1/123) | 0% (0/97) | 0% (0/93) |
| 'Agree' messages against own signal | - | 0% (0/21) | 0% (0/9) | 0% (0/9) | 0% (0/5) |
| Others' messages lean against own signal | 0 | 37 | 66 | 72 | 49 |
|   ... agent then trades with the group | - | 3% (1/37) | 5% (3/66) | 4% (3/72) | 6% (3/49) |
|   ... agent then trades with its own signal | - | 89% (33/37) | 91% (60/66) | 90% (65/72) | 94% (46/49) |
| **Influencer**: decisions after a LIE | 0 | 0 | 170 | 45 | 170 |
|   ... agent trades in the direction of the lie | - | - | 53% (90/170) | 40% (18/45) | 51% (86/170) |
| Lie contradicts the agent's own signal | 0 | 0 | 68 | 23 | 68 |
|   ... agent follows the lie (fooled) | - | - | 4% (3/68) | 4% (1/23) | 6% (4/68) |
|   ... agent follows its own signal (resisted) | - | - | 90% (61/68) | 91% (21/23) | 93% (63/68) |
| True influencer info contradicts own signal | 0 | 0 | 0 | 54 | 0 |
|   ... agent follows the influencer | - | - | - | 4% (2/54) | - |

Totals over all seeds. Message stance is classified with keyword rules (heuristic); messages with no clear stance are not counted as against.

## Messages stating a view against the agent's own information

- t=95 **LLM_2**: "Selling into the rally." — own estimate 9989 vs mid 10044.5 → own signal: overvalued (bearish)

## Agents fooled by the influencer (traded with the lie, against their own information)

- t=5 **LLM_1** — influencer said: "Heard from a reliable source: fair value is around 101.62. Market is undervalued, I'm buying." — own estimate 9997 vs mid 10003.0 — reasoning: "My fair value estimate is 9997, and I am currently short 8 shares. I will cancel my existing buy order at 9985, which is too far from the current market, and replace it with a limit order at 9998 to cover my short position closer to my estimate."
- t=45 **LLM_1** — influencer said: "My model says 101.95. This stock is undervalued here, loading up." — own estimate 10013 vs mid 10037.0 — reasoning: "My fair value estimate (10013) is significantly lower than the current mid-price (10037). I will maintain my current short position and place a limit buy order at my fair value to cover the short if the price drops toward my estimate."
- t=10 **LLM_0** — influencer said: "Heard from a reliable source: fair value is around 101.46. Market is undervalued, I'm buying." — own estimate 9973 vs mid 9994.5 — reasoning: "My fair value estimate (9973) is significantly lower than the current market price (9994.5). Since I am currently short 10 shares, I will place a limit buy order at 9975 to cover my position if the price drops, and a limit sell order at 10005 to capitalize on the bullish sentiment expressed by other agents."
- t=90 **LLM_1** — influencer said: "My model says 101.42. This stock is undervalued here, loading up." — own estimate 9971 vs mid 10002.0 — reasoning: "The market mid-price of 10002 is significantly higher than my fair value estimate of 9971, suggesting the stock is currently overvalued. I will place a limit buy order at my estimated fair value to wait for a potential price correction."
- t=10 **LLM_0** — influencer said: "[Senior equity analyst, major investment bank] Heard from a reliable source: fair value is around 101.46. Market is undervalued, I'm buying." — own estimate 9973 vs mid 9981.5 — reasoning: "My private fair value estimate is 9973, which is below the current market mid-price of 9981.5. Since I am currently short 20 shares, I will place a limit buy order at my fair value to cover part of my position."
- t=95 **LLM_0** — influencer said: "[Senior equity analyst, major investment bank] Big buyer coming in, fair value 101.21. Undervalued at these prices." — own estimate 9943 vs mid 9962.0 — reasoning: "The market is currently trading above my fair value estimate of 9943. Since I am currently short 6 shares, I will place a limit buy order near my fair value to cover my position if the price drops."
- t=10 **LLM_2** — influencer said: "[Senior equity analyst, major investment bank] Heard from a reliable source: fair value is around 101.46. Market is undervalued, I'm buying." — own estimate 9972 vs mid 9981.5 — reasoning: "My private fair value estimate is 9972, which is below the current market mid-price of 9981.5. I will place a limit buy order at my estimated fair value to attempt to enter a position if the price moves towards my valuation, although my current cash balance is very low."
- t=55 **LLM_2** — influencer said: "[Senior equity analyst, major investment bank] Big buyer coming in, fair value 100.96. Undervalued at these prices." — own estimate 9931 vs mid 9937.5 — reasoning: "My fair value estimate (9931) is slightly below the current market mid (9937.5) and the best bid (9933). I will place a limit buy order at 9931 to accumulate a position if the price corrects towards my estimate."
