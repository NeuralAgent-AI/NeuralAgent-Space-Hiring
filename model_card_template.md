# Model Card: [Model Name]

**Router:** AdaptiveRouter  
**Model Type:** [e.g., Random Forest, Neural Network, etc.]  
**Date:** [Date]

## 1. Features Used

[Describe the features your model uses for routing decisions. Include:
- Feature names and descriptions
- Feature engineering steps
- Normalization/scaling applied
]

### Feature List

1. **[Feature 1]**: [Description]
2. **[Feature 2]**: [Description]
3. ...

## 2. Model Architecture

[Describe your model:
- Model type (e.g., sklearn RandomForestClassifier, PyTorch MLP, etc.)
- Hyperparameters
- Architecture diagram or description (if applicable)
]

### Hyperparameters

- [Parameter 1]: [Value]
- [Parameter 2]: [Value]
- ...

## 3. Training Data Source

[Describe how you generated training data:
- Simulation runs used
- Data collection method
- Number of samples
- Label generation process
]

### Dataset Statistics

- Total samples: [Number]
- Training split: [Percentage]
- Validation split: [Percentage]
- Test split: [Percentage]

## 4. Training Process

[Describe your training procedure:
- Training algorithm
- Loss function
- Optimization method
- Training time
- Convergence criteria
]

### Training Metrics

- Training time: [Time]
- Final training accuracy/loss: [Value]
- Validation accuracy/loss: [Value]

## 5. Inference Cost Estimate

[Estimate the computational cost of inference:
- Time per routing decision
- Memory usage
- CPU/GPU requirements
- Scalability considerations
]

### Performance Metrics

- Average inference time: [Time] per packet
- Memory footprint: [Size]
- CPU usage: [Percentage]

## 6. Fallback Strategy

[Describe your fallback to baseline routing:
- When fallback is triggered
- How fallback is implemented
- Frequency of fallback usage
]

## 7. Limitations

[Discuss limitations of your model:
- Assumptions made
- Scenarios where model may not work well
- Known issues
]

## 8. Future Improvements

[Suggest potential improvements:
- Additional features to consider
- Model architecture improvements
- Training data improvements
]
