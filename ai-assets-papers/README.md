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
