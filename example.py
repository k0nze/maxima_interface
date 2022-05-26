import time
import os

from maxima_interface import MaximaInterface

if __name__ == "__main__":
    mi = MaximaInterface(port=65433, debug=True)
    # mi.raw_command("a: 1;")
    # mi.raw_command("b: 2;")
    result = mi.raw_command("a: 1;")
    print(f"result={result}")
    mi.close()
