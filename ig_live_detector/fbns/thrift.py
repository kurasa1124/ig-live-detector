"""Thrift compact protocol writer (pure Python, clean-room from MIT instagram_mqtt logic).

Only the subset the FBNS MQTToT connect packet needs: binary/struct/i16/i32/i64/byte/bool/
list<i32>/list<binary>/map<binary,binary>, with compact field-delta encoding.
"""
from __future__ import annotations

# Thrift compact type codes
STOP = 0x00
TRUE = 0x01
FALSE = 0x02
BYTE = 0x03
I16 = 0x04
I32 = 0x05
I64 = 0x06
BINARY = 0x08
LIST = 0x09
MAP = 0x0B
STRUCT = 0x0C


def _zigzag(n: int, bits: int) -> int:
    """b-bit signed zigzag: (n<<1) ^ (n>>(bits-1)), result taken as an unsigned bits-wide value."""
    return ((n << 1) ^ (n >> (bits - 1))) & ((1 << bits) - 1)


class ThriftWriter:
    def __init__(self) -> None:
        self.buf = bytearray()
        self._field = 0
        self._stack: list[int] = []

    # ── low level ──
    def _byte(self, b: int) -> None:
        self.buf.append(b & 0xFF)

    def _varint(self, num: int) -> None:
        # num is always non-negative (a zigzag result or a length)
        while True:
            if num & ~0x7F == 0:
                self._byte(num)
                return
            self._byte((num & 0x7F) | 0x80)
            num >>= 7

    def _word(self, n: int) -> None:
        self._varint(_zigzag(n, 16))

    def _int(self, n: int) -> None:
        self._varint(_zigzag(n, 32))

    def _long(self, n: int) -> None:
        self._varint(_zigzag(n, 64))

    def _field_header(self, field: int, type_: int) -> None:
        delta = field - self._field
        if 0 < delta <= 15:
            self._byte((delta << 4) | type_)
        else:
            self._byte(type_)
            self._word(field)
        self._field = field

    def _str_direct(self, s: str) -> None:
        data = s.encode("utf-8")
        self._varint(len(data))
        self.buf.extend(data)

    # ── field types ──
    def string(self, field: int, s: str) -> "ThriftWriter":
        self._field_header(field, BINARY)
        self._str_direct(s)
        return self

    def boolean(self, field: int, b: bool) -> "ThriftWriter":
        self._field_header(field, TRUE if b else FALSE)
        return self

    def byte(self, field: int, n: int) -> "ThriftWriter":
        self._field_header(field, BYTE)
        self._byte(n)
        return self

    def i16(self, field: int, n: int) -> "ThriftWriter":
        self._field_header(field, I16)
        self._word(n)
        return self

    def i32(self, field: int, n: int) -> "ThriftWriter":
        self._field_header(field, I32)
        self._int(n)
        return self

    def i64(self, field: int, n: int) -> "ThriftWriter":
        self._field_header(field, I64)
        self._long(n)
        return self

    def list_i32(self, field: int, items: list[int]) -> "ThriftWriter":
        self._field_header(field, LIST)
        self._list_header(len(items), I32)
        for el in items:
            self._int(el)
        return self

    def list_binary(self, field: int, items: list[str]) -> "ThriftWriter":
        self._field_header(field, LIST)
        self._list_header(len(items), BINARY)
        for el in items:
            self._str_direct(el)
        return self

    def _list_header(self, size: int, elem_type: int) -> None:
        if size < 0x0F:
            self._byte((size << 4) | elem_type)
        else:
            self._byte(0xF0 | elem_type)
            self._varint(size)

    def map_binary(self, field: int, pairs: list[tuple[str, str]]) -> "ThriftWriter":
        self._field_header(field, MAP)
        if not pairs:
            self._byte(0)
        else:
            self._varint(len(pairs))
            self._byte((BINARY << 4) | BINARY)
            for k, v in pairs:
                self._str_direct(k)
                self._str_direct(v)
        return self

    def struct(self, field: int) -> "ThriftWriter":
        self._field_header(field, STRUCT)
        self._stack.append(self._field)
        self._field = 0
        return self

    def stop(self) -> "ThriftWriter":
        self._byte(STOP)
        if self._stack:
            self._field = self._stack.pop()
        return self

    def result(self) -> bytes:
        return bytes(self.buf)
