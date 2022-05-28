# Interfacing Maxima CAS with Python

## Setup

### Prerequisites

* Python Version >= `3.9`
* Maxima installed and added to PATH

### Install

```
pip install maxima_interface
```

## Example

```python
from maxima_interface import MaximaInterface

mi = MaximaInterface()
mi.raw_command("a: 1;")
result = mi.raw_command("a;")

print(result)
```
