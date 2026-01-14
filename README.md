# ConFuzz
ConFuzz is a novel LLM-driven Fuzzer designed for security testing the unsafe consumption APIs.  
This is a scientific prototype for my bachelor's thesis, to design and evaluate an LLM-driven fuzzer for consumer-side API security testing. 

## Usage
### ConFuzz
Run ConFuzz with the `qwen3:8b` Ollama model in 'auto' mode (run through all six scenarios after another): 
```shell
python3 main.py --strategy llm  --model qwen3:8b --auto
```
This is the result of ConFuzz running against the six scenario endpoints implemented in the [test-environment](./test-environment/endpoints.md):
![ConFuzz Example Results](assets/images/confuzz_example_1.png)

### Baseline
Run the baseline fuzzer with the [`custom.txt`](resources/lists/custom.txt) list in 'auto' mode:
```shell
python3 main.py --strategy baseline --auto
```
This is the result of the mutation-based baseline fuzzer that will be used for the comparative analysis with ConFuzz.
![Baseline Fuzzer Example Results](assets/images/baseline_fuzzer_example_2.png)

### Automatically Orchestrate the Evaluation
The [`autorun.py`](scripts/autorun.py) script can be used to orchestrate the runs for the empirical evaluation automatically. You can configure the strategy and model in the config. This will automatically execute ConFuzz with the configured options and store the resulting log files in the `evaluation/` directory for further analysis and evaluation. 

### Evaluation
Some commands and their results used in the empirical evaluation are [documented here](evaluation.md).

>[!warning]  
>ConFuzz is only effective for fuzzing the test environment due to a lack of a general feedback analysis engine.  
>In order to use it in other projects, either the [`detect_exploit()`](https://github.com/Ampferl/confuzz/blob/main/fuzzer/core/driver/trigger.py#L15) function must be adapted or a proper feedback analysis module must be implemented.
>In addition, the [driver configuration](https://github.com/Ampferl/confuzz/blob/main/fuzzer/core/driver/config.py) must be adapted to the host and endpoints to be fuzzed.

