test1 = {
    "a": 1,
    "b": 1
}
def gen_enumirate_text(counters:list) -> str:
    length = len(counters)
    if length < 2:
        return counters[0]
    if length < 3:
        return counters[0] + ' и ' + counters[1]
    else:
        return ", ".join(counters [:length - 1]) + ' и ' + counters[length - 1]


print(gen_enumirate_text(['1', '2', '3', '4']))