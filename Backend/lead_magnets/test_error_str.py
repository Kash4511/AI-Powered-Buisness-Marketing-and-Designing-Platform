try:
    l = []
    print(l[0])
except IndexError as e:
    print(f"IndexError str(e): '{str(e)}'")

try:
    raise Exception(0)
except Exception as e:
    print(f"Exception(0) str(e): '{str(e)}'")
