from typing import Iterable, Literal, Optional, Tuple, Union


def flatten(items):
    for x in items:
        if isinstance(x, Iterable) and not isinstance(x, (str, bytes)):
            for sub_x in flatten(x):
                yield sub_x
        else:
            yield x


def bytespop(
    b: Union[bytes, bytearray],
    q: int = 1,
    decode: Optional[str] = None,
    endian: Literal["little", "big"] = "little",
) -> Tuple[Union[int, str, bytearray], bytearray]:

    if isinstance(b, bytes):
        b = bytearray(b)

    ret = b[:q]

    b = b[q:]

    if decode == "utf8":
        return ret.decode("utf8"), b
    elif decode == "int":
        return int.from_bytes(ret, endian), b
    elif decode is None:
        return ret, b
    else:
        raise ValueError(f"Invalid decode type: {decode}")
