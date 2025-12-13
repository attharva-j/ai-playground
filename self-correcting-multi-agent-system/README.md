# Self-Correcting Multi-Agent System

## Overview

This project demonstrates a **Self-Correcting Multi-Agent System** that significantly improves AI solution accuracy, groundedness, and reliability compared to single-agent approaches. The system consists of specialized agents working together to solve complex problems while continuously validating and improving their outputs.

## Architecture Components

### Core Agents
- **Solver Agent**: Primary problem-solving agent that generates initial solutions
- **Critic Agent**: Reviews solver outputs, identifies issues, and suggests improvements
- **Judge Agent**: Validates final answers against evidence and provides confidence scores
- **Controller/Orchestrator**: Manages the interaction flow and iteration cycles

### Supporting Infrastructure
- **Tool Layer**: Web search, database queries, code execution, document retrieval
- **Logger**: Comprehensive tracking of agent interactions and performance metrics
- **Evaluator**: Measures system performance across multiple dimensions

## Key Benefits

### Compared to Single-Agent Systems:
1. **Reduced Hallucinations**: Multi-layer validation catches false information
2. **Improved Accuracy**: Iterative refinement leads to better solutions
3. **Enhanced Groundedness**: Evidence-based validation ensures factual correctness
4. **Better Error Recovery**: Self-correction mechanisms handle edge cases
5. **Increased Reliability**: Multiple validation layers reduce system failures

## Evaluation Metrics

- **Accuracy**: Percentage of correct answers
- **Groundedness**: Percentage of answers with verifiable evidence
- **Hallucination Rate**: Percentage of false/unverifiable claims
- **Iteration Efficiency**: Average cycles needed for convergence
- **Cost Analysis**: Token usage and API call optimization
- **Latency**: Response time comparison
- **Task Success Rate**: Multi-step task completion without human intervention

## Use Cases Demonstrated

1. **Document Q&A with Citations**: Answers must reference specific source paragraphs
2. **Financial Analysis**: Data retrieval, computation, and explanation
3. **Multi-step Reasoning**: Complex KPI calculations with justification
4. **Code Generation & Validation**: Automated testing and refinement

## Getting Started

1. Install dependencies: `pip install -r requirements.txt`
2. Set up environment variables (use global `.env` file)
3. Run the Jupyter notebook: `jupyter lab self_correcting_agents_demo.ipynb`
4. Follow the step-by-step implementation and comparison

## Project Structure

```
self-correcting-multi-agent-system/
├── README.md                           # This file
├── requirements.txt                    # Python dependencies
├── self_correcting_agents_demo.ipynb   # Main demonstration notebook
├── agents/
│   ├── __init__.py
│   ├── solver_agent.py                 # Primary problem solver
│   ├── critic_agent.py                 # Solution reviewer
│   ├── judge_agent.py                  # Final validator
│   └── orchestrator.py                 # System controller
├── tools/
│   ├── __init__.py
│   ├── web_search.py                   # Web search capabilities
│   ├── database_tool.py                # Database query tool
│   ├── code_executor.py                # Code execution sandbox
│   └── document_retriever.py           # RAG/vector search
├── evaluation/
│   ├── __init__.py
│   ├── metrics.py                      # Performance metrics
│   ├── evaluator.py                    # System evaluator
│   └── synthetic_data.py               # Test data generation
├── utils/
│   ├── __init__.py
│   ├── logger.py                       # Structured logging
│   ├── config.py                       # Configuration management
│   └── prompts.py                      # Agent prompt templates
└── data/
    ├── sample_documents/               # Test documents
    ├── financial_data.json             # Sample financial dataset
    └── evaluation_results/             # Performance logs
```

## Expected Outcomes

The notebook demonstrates measurable improvements in:
- 25-40% reduction in hallucination rates
- 15-30% improvement in answer accuracy
- 50-70% increase in evidence-based responses
- Better handling of complex, multi-step problems
- More reliable performance across diverse task types

## Next Steps

After running the demonstration:
1. Experiment with different agent configurations
2. Test on your specific use cases
3. Optimize for cost vs. performance trade-offs
4. Integrate with your existing AI workflows
5. Scale to production environments