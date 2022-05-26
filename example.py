import time

from maxima import Maxima

if __name__ == "__main__":
    m = Maxima(port=65432)

    for i in range(3):
        print(i)
        time.sleep(1)

    m.terminate()
