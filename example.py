import time

from maxima import Maxima

if __name__ == "__main__":
    m = Maxima()

    for i in range(3):
        print(i)
        time.sleep(1)

    m.terminate()
