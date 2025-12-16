# Empirical Evaluation

![vulnerability_coverage_heatmap.png](assets/plots/vulnerability_coverage_heatmap.png)
![comparative_effectiveness.png](assets/plots/comparative_effectiveness.png)
![efficiency_vs_effectiveness.png](assets/plots/efficiency_vs_effectiveness.png)
- All GPT models are worse slower than 

## Models

### Deepseek R1
```shell
python3 ../scripts/eval.py -c deepseek-r1_1.5b/01,deepseek-r1_8b/01 --plot
```
![plot_deepseek.png](assets/plots/plot_deepseek.png)
#### 1.5b Quantization
![confuzz_deepseek-r1_1.5b.png](assets/images/confuzz_deepseek-r1_1.5b.png)
#### 8b Quantization
![confuzz_deepseek-r1_8b.png](assets/images/confuzz_deepseek-r1_8b.png)

### Qwen3
```shell
python3 ../scripts/eval.py -c qwen3_0.6b/01,qwen3_0.6b/02,qwen3_1.7b/01,qwen3_8b/01 --plot
```
![plot_qwen3.png](assets/plots/plot_qwen3.png)
#### 0.6b Quantization
![confuzz_qwen3_0.6b.png](assets/images/confuzz_qwen3_0.6b-v2.png)
#### 1.7b Quantization
![confuzz_qwen3_1.7b.png](assets/images/confuzz_qwen3_1.7b.png)
#### 8b Quantization
![confuzz_qwen3_8b.png](assets/images/confuzz_qwen3_8b.png)

### GPT-5
```shell
python3 ../scripts/eval.py -c gpt-5-nano/01,gpt-5-mini/01,gpt-5/01 --plot
```
![plot_gpt5.png](assets/plots/plot_gpt5.png)
#### Nano (predicted ~8b Quantization) (Reasoning: minimal)
![confuzz_gpt5-nano.png](assets/images/confuzz_gpt5-nano.png)
#### Mini (predicted ~27b Quantization) (Reasoning: minimal)
![confuzz_gpt5-mini.png](assets/images/confuzz_gpt5-mini.png)
#### Default (predicted ~57b Quantization) (Reasoning: minimal)
![confuzz_gpt5.png](assets/images/confuzz_gpt5.png)