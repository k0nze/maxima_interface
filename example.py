import time

from maxima_interface import MaximaInterface

if __name__ == "__main__":
    mi = MaximaInterface(debug=True)

    for i in range(3):
        # print(i)
        time.sleep(1)

    mi.terminate()
