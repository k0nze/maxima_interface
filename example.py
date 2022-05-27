from maxima_interface import MaximaInterface

if __name__ == "__main__":
    mi = MaximaInterface(port=65433, debug=True)
    """
    result = mi.raw_command("N:matrix([a,b],[c,d]);")
    result = mi.raw_command("O: invert(N);")
    result = mi.raw_command("a: 1/2;")
    result = mi.raw_command("ceiling(a);")
    result = mi.raw_command("floor(a);")
    result = mi.raw_command("a*a;")
    result = mi.raw_command("a**a;")
    result = mi.raw_command("b: 2*a+3;")
    result = mi.raw_command("b+a;")
    result = mi.raw_command("O+b;")
    """
    result = mi.raw_command("a: 1/2;")
    print(f"result={result}")
    mi.reset()
    result = mi.raw_command("a;")
    print(f"result={result}")
    mi.close()
