# Routing Strategy Report
<!---
Keep your answers short, bullet points ok!
-->

**Candidate Name:** [Your Name]

**Date:** [Date]

## 1. Routing Idea

[Describe your adaptive routing strategy in 2-3 paragraphs. What is the core idea? Why did you choose this approach?]

## 2. Features/State Used

[Describe what information your router uses to make routing decisions. Examples:
- Current topology graph properties
- Historical topology patterns
- Packet characteristics (TTL, age, etc.)
- Node/link metrics
- ML features (if applicable)
]

## 3. When It Helps

[Describe scenarios or conditions where your adaptive routing performs better than baseline:
- Specific topology patterns
- Network conditions
- Traffic patterns
- Time periods
]

## 4. When It Fails

[Describe scenarios or conditions where your adaptive routing struggles:
- Edge cases
- Network conditions
- Limitations of your approach
]

## 5. Scaling Risks

[Discuss potential issues when scaling to:
- Larger constellations
- Higher traffic loads
- More complex scenarios
- Computational constraints
]

## 6. Implementation Notes

[Any additional implementation details, assumptions, or design decisions worth noting]

## 7. Results Summary

[Brief summary of your results:
- Delivery rate improvements (if any)
- Latency improvements (if any)
- Trade-offs observed
]

## 8. Constellation Scaling Analysis (REQUIRED)

[Document your scaling analysis results. This section is mandatory.]

### Configurations Tested

[Table or list of configurations tested:
- 4×4 (16 satellites)
- 6×6 (36 satellites)  
- 8×8 (64 satellites)
- Any additional sizes tested
]

### Performance Metrics by Network Size

[Present results in a table or chart:
- Delivery rate vs. network size
- Mean/median/p95 latency vs. network size
- Computation time/routing overhead vs. network size
- Comparison: adaptive vs. baseline at each size
]

### Observations

[Describe your findings:
- How does delivery rate change with network size?
- How does latency change?
- Does your routing strategy scale well computationally?
- At what point does performance degrade (if any)?
- Network density effects: too sparse vs. too dense
]

### Scaling Limits and Bottlenecks

[Identify any scaling issues:
- Computational bottlenecks
- Memory usage concerns
- Routing algorithm limitations
- Network topology constraints
]

### Recommendations

[Based on your analysis:
- Optimal constellation size for your routing strategy
- Trade-offs between more satellites vs. better routing
- When to use your adaptive router vs. baseline
- Suggestions for production deployment
]
