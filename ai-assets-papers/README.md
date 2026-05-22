# Research Papers

A collection of foundational papers in large language model architecture and efficient fine-tuning.

---

## 1. Attention Is All You Need
**Vaswani et al., 2017 — Google Brain / Google Research**

The paper that introduced the **Transformer architecture**, replacing recurrent and convolutional networks with a model built entirely on self-attention. The Transformer uses multi-head scaled dot-product attention to capture dependencies across input and output sequences in parallel, making it significantly faster to train than RNN-based models.

Key contributions:
- **Scaled Dot-Product Attention** and **Multi-Head Attention** as core building blocks
- Encoder-decoder architecture with positional encodings (no recurrence)
- Achieved state-of-the-art BLEU scores on WMT 2014 English-German (28.4) and English-French (41.8) translation tasks at a fraction of prior training costs

> This paper laid the groundwork for virtually all modern large language models, including BERT, GPT, and their descendants.

📄 [arXiv:1706.03762](https://arxiv.org/abs/1706.03762)

---

## 2. LoRA: Low-Rank Adaptation of Large Language Models
**Hu et al., 2021 — Microsoft Corporation**

Introduces **LoRA**, a parameter-efficient fine-tuning method for large pre-trained language models. Rather than updating all model weights during adaptation, LoRA freezes the original weights and injects small trainable **rank decomposition matrices** (A and B) into each Transformer layer. At inference time, these can be merged back into the base weights, adding zero latency.

Key contributions:
- Reduces trainable parameters by up to **10,000×** compared to full fine-tuning (e.g., 350GB → 35MB checkpoints on GPT-3 175B)
- Cuts GPU memory requirements by up to **3×** during training
- Matches or exceeds full fine-tuning quality on RoBERTa, DeBERTa, GPT-2, and GPT-3 benchmarks
- No additional inference latency (unlike adapter-based methods)
- Empirically shows that weight update matrices have a very low "intrinsic rank," justifying the approach

> LoRA has become one of the most widely used techniques for fine-tuning large models efficiently, and is the basis for many practical LLM customization workflows today.

📄 [arXiv:2106.09685](https://arxiv.org/abs/2106.09685) | 💻 [GitHub](https://github.com/microsoft/LoRA)

---
 
## 3. Chain-of-Thought Prompting Elicits Reasoning in Large Language Models
**Wei et al., 2022 — Google Research, Brain Team**
 
Explores how generating a **chain of thought** — a series of intermediate reasoning steps — significantly improves the ability of large language models to perform complex reasoning. The method requires no fine-tuning: a few chain-of-thought demonstrations are simply provided as exemplars in the prompt.
 
Key contributions:
- Introduces **chain-of-thought prompting**, where few-shot exemplars include step-by-step reasoning alongside questions and answers
- Demonstrates striking empirical gains across arithmetic, commonsense, and symbolic reasoning benchmarks
- Shows that chain-of-thought reasoning is an **emergent ability of model scale** — benefits only appear reliably at ~100B+ parameters
- PaLM 540B with just eight chain-of-thought exemplars achieves state-of-the-art accuracy on the GSM8K math word problem benchmark, surpassing even fine-tuned GPT-3 with a verifier
- Establishes that the approach is robust across different annotators, exemplar orderings, and prompt styles
> Chain-of-thought prompting has become a foundational prompting technique, demonstrating that the reasoning capabilities of large language models can be unlocked simply through carefully constructed prompts — no gradient updates required.
 
📄 [arXiv:2201.11903](https://arxiv.org/abs/2201.11903)

---
 
## 4. Direct Preference Optimization: Your Language Model is Secretly a Reward Model
**Rafailov et al., 2023 — Stanford University / CZ Biohub**
 
Introduces **Direct Preference Optimization (DPO)**, a simpler alternative to Reinforcement Learning from Human Feedback (RLHF) for aligning language models with human preferences. DPO identifies a mathematical mapping between reward functions and optimal policies, allowing the standard RLHF objective to be optimized with a simple binary cross-entropy loss — no reinforcement learning required.
 
Key contributions:
- Derives a **closed-form reparameterization** of the reward model in terms of the policy itself, eliminating the need for an explicit, standalone reward model
- Replaces the complex PPO-based RLHF pipeline with a single **classification loss**, making training stable and computationally lightweight — no sampling from the LM during fine-tuning
- Proves that the DPO reparameterization covers all reward equivalence classes under the Bradley-Terry and Plackett-Luce preference models, losing no generality
- Outperforms PPO-based RLHF on sentiment control, and matches or exceeds it on summarization (61% vs. 57% win rate on TL;DR) and single-turn dialogue, using models up to 6B parameters
- Validated with both GPT-4 automated evaluation and a human study, showing GPT-4 judgments correlate with human preferences as reliably as inter-human agreement
> DPO has become a widely adopted technique for preference-based fine-tuning, significantly lowering the barrier to aligning language models with human feedback without the instability and complexity of reinforcement learning.
 
📄 [arXiv:2305.18290](https://arxiv.org/abs/2305.18290)

---
 
## 5. Lost in the Middle: How Language Models Use Long Contexts
**Liu et al., 2023 — Stanford University / UC Berkeley / Samaya AI**
 
Investigates how well language models actually use the long input contexts they can accept, by running controlled experiments on multi-document question answering and key-value retrieval. The central finding is that performance follows a **U-shaped curve** based on where relevant information sits in the context: models are best at using information at the very beginning or end of their input, and significantly worse when it falls in the middle.
 
Key contributions:
- Demonstrates a consistent **U-shaped (primacy + recency bias) performance curve** across GPT-3.5-Turbo, Claude-1.3, MPT-30B-Instruct, and LongChat-13B — for example, GPT-3.5-Turbo's multi-document QA accuracy drops over 20% in the worst case, falling *below* its closed-book (no-context) performance of 56.1%
- Shows that **extended-context models are not necessarily better** at using context than their standard counterparts — GPT-3.5-Turbo and GPT-3.5-Turbo (16K) exhibit nearly identical position-dependent performance curves when context fits both windows
- Finds that **encoder-decoder models** (Flan-UL2, Flan-T5-XXL) are relatively robust to position changes within their training-time sequence length, but develop the same U-shaped degradation beyond it
- Demonstrates that **query-aware contextualization** (placing the query both before and after the documents) largely solves the synthetic key-value retrieval task but provides minimal benefit for real multi-document QA
- Establishes that the U-shaped curve is present in base models (pre-instruction fine-tuning), and that the effect only emerges at sufficient scale — Llama-2 7B models show recency bias only, while 13B and 70B models exhibit both primacy and recency bias
- Shows in an open-domain QA case study that **reader performance saturates well before retriever recall** — using 50 retrieved documents instead of 20 improves accuracy by only ~1–1.5%
> This paper introduced a widely-cited evaluation lens for long-context models, establishing that a large context window is not the same as effective use of that window — and that the "lost in the middle" phenomenon is a fundamental challenge for retrieval-augmented and long-document applications.
 
📄 [arXiv:2307.03172](https://arxiv.org/abs/2307.03172)

---
 
## 6. ReAct: Synergizing Reasoning and Acting in Language Models
**Yao et al., 2023 — Princeton University / Google Research, Brain Team**
 
Introduces **ReAct**, a prompting paradigm that interleaves verbal reasoning traces and task-specific actions in large language models, enabling them to both think through problems and interact with external environments in a unified loop. Rather than treating reasoning (chain-of-thought) and acting (tool use) as separate capabilities, ReAct combines them so each informs the other: reasoning guides what actions to take, and observations from actions update the reasoning.
 
Key contributions:
- Proposes the **ReAct framework**, which augments the model's action space with a language "thought" action — a free-form reasoning step that updates context without affecting the environment, enabling goal decomposition, progress tracking, exception handling, and commonsense inference mid-trajectory
- On knowledge-intensive tasks (HotPotQA, FEVER), ReAct reduces hallucination compared to chain-of-thought alone by grounding reasoning in retrieved Wikipedia facts; combining ReAct with chain-of-thought self-consistency achieves the best overall prompting results (35.1 EM on HotPotQA, 64.6% on FEVER with PaLM-540B)
- On interactive decision-making benchmarks, ReAct dramatically outperforms action-only baselines with as few as **1–2 in-context examples**: 71% vs. 45% success rate on ALFWorld, and a **10% absolute improvement** in success rate on WebShop over the best imitation + reinforcement learning baseline trained on 10k+ examples
- Demonstrates that **finetuning amplifies the advantage**: PaLM-8B finetuned with just 3,000 ReAct trajectories outperforms all PaLM-62B prompting methods, and PaLM-62B finetuned ReAct outperforms all PaLM-540B prompting baselines
- Shows that ReAct trajectories are **human-interpretable and controllable** — humans can inspect reasoning steps and directly edit thoughts mid-trajectory to correct model behavior, a form of lightweight human-in-the-loop collaboration not possible with action-only or pure RL methods
> ReAct established the Thought–Action–Observation loop as a foundational pattern for LLM agents, directly influencing the design of agentic frameworks like LangChain and the broader field of tool-augmented and autonomous LLM systems.
 
📄 [arXiv:2210.03629](https://arxiv.org/abs/2210.03629) | 🌐 [Project Page](https://react-lm.github.io/)

---
 
## 7. Training Language Models to Follow Instructions with Human Feedback
**Ouyang et al., 2022 — OpenAI**
 
Introduces **InstructGPT**, a method for aligning language models with user intent by fine-tuning GPT-3 using **Reinforcement Learning from Human Feedback (RLHF)**. The core insight is that scaling model size does not inherently improve alignment — a much smaller model trained on human preferences can be more helpful and truthful than a far larger untuned model.
 
Key contributions:
- A three-step training pipeline: **(1) supervised fine-tuning (SFT)** on human demonstrations, **(2) reward model (RM) training** from human preference rankings, and **(3) PPO-based RL** to optimize against the reward model
- A 1.3B InstructGPT model is preferred by human labelers over the 175B GPT-3 baseline, demonstrating that alignment can be more cost-effective than scaling
- InstructGPT produces roughly **half the hallucination rate** of GPT-3 on closed-domain tasks (21% vs. 41%), and scores higher on the TruthfulQA benchmark
- Introduces the **PPO-ptx** variant, which mixes pretraining gradients into RL fine-tuning to mitigate the "alignment tax" — performance regressions on public NLP benchmarks like SQuAD and HellaSwag
- Demonstrates generalization: InstructGPT follows instructions in non-English languages and answers questions about code, despite these being rare in the fine-tuning data
- Surfaces key limitations: the model still makes simple mistakes, can be manipulated into harmful outputs by explicit prompting, and is aligned to a specific (non-representative) group of labelers
> InstructGPT established the RLHF recipe that became the foundation for ChatGPT and most subsequent instruction-following language models, and remains one of the most influential works on practical LLM alignment.
 
📄 [arXiv:2203.02155](https://arxiv.org/abs/2203.02155)