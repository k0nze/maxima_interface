# Interfacing Maxima CAS with Python

## Setup

### Prerequisites

* Python Version >= `3.9`
* Maxima installed and added to PATH

```
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
pre-commit install
```

## Example

```python
from maxima_interface import MaximaInterface

mi = MaximaInterface()
mi.raw_command("a: 1;")
result = mi.raw_command("a;")

print(result)
```
