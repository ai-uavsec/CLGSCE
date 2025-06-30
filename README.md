# Large Language Model-Driven Closed-Loop UAV Operation with Semantic Observations

This repository

## Setup

### AirSim Setup

1. Install [AirSim](https://github.com/microsoft/AirSim).

2. Download pre-build AiSim environment ["Releases"](https://github.com/Microsoft/AirSim/releases), recommend using "Block".

### OpenAI Setup

Please make sure you have set the `OPENAI_API_KEY` environment variable, if not:

```bash
export OPENAI_API_KEY="your_openai_api_key"
```

### Python

1. Install AirSim Python library [AirSim Python APIs](https://microsoft.github.io/AirSim/apis/).

2. This project is tested under python `3.9`.

---

## Instructions

1. Open AirSim "block" or other "pre-built" environment, make sure the environment has a clear space for drone flight.

2. run python file.

   ```bash
   python CLGSCE.py -m NL -t advanced
   ```

---

## Citation

```

```

---

## License

This project is licensed under the Apache-2.0 License - see the [LICENSE](LICENSE) file for details.
