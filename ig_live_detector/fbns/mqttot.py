"""MQTToT over TLS (pure Python, asyncio).

MQTToT = IG's MQTT 3 variant: the CONNECT protocol name is 'MQTToT' and CONNECT/CONNACK carry a payload.
The rest follows standard MQTT framing. Only what FBNS needs: connect / subscribe / publish / receive PUBLISH.
"""
from __future__ import annotations

import asyncio
import ssl
import struct
import zlib
from typing import Awaitable, Callable, Optional

# MQTT packet types
_CONNECT = 1
_CONNACK = 2
_PUBLISH = 3
_PUBACK = 4
_SUBSCRIBE = 8
_SUBACK = 9
_PINGREQ = 12
_PINGRESP = 13
_DISCONNECT = 14

# CONNECT flags: username(0x80) + password(0x40) + clean session(0x02)
_CONNECT_FLAGS = 0xC2


def _remaining_length(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        out.append(b | 0x80 if n else b)
        if not n:
            break
    return bytes(out)


def _mqtt_str(s) -> bytes:
    data = s.encode("utf-8") if isinstance(s, str) else s
    return struct.pack(">H", len(data)) + data


class MQTToTClient:
    def __init__(self) -> None:
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._pktid = 0
        self._keepalive = 60
        self._ping_task: Optional[asyncio.Task] = None
        self.on_message: Optional[Callable[[str, bytes], Awaitable[None]]] = None

    def _next_pktid(self) -> int:
        self._pktid = (self._pktid % 0xFFFF) + 1
        return self._pktid

    async def connect(self, host: str, port: int, keepalive: int, thrift_payload: bytes) -> bytes:
        """Open TLS, send the MQTToT CONNECT, return the CONNACK payload (device-auth data)."""
        self._keepalive = keepalive
        ctx = ssl.create_default_context()
        self._reader, self._writer = await asyncio.open_connection(host, port, ssl=ctx)

        vh = _mqtt_str("MQTToT") + bytes([3, _CONNECT_FLAGS]) + struct.pack(">H", keepalive)
        body = vh + zlib.compress(thrift_payload)
        self._writer.write(bytes([_CONNECT << 4]) + _remaining_length(len(body)) + body)
        await self._writer.drain()

        ptype, data, _ = await self._read_packet()
        if ptype != _CONNACK:
            raise RuntimeError(f"expected CONNACK, got packet type {ptype}")
        return_code = data[1]
        payload = b""
        if len(data) > 2:
            plen = struct.unpack(">H", data[2:4])[0]
            payload = data[4 : 4 + plen]
        if return_code != 0:
            raise RuntimeError(f"CONNACK return code {return_code}")
        return payload

    async def _read_exact(self, n: int) -> bytes:
        assert self._reader is not None
        return await self._reader.readexactly(n)

    async def _read_packet(self) -> tuple[int, bytes, int]:
        first = (await self._read_exact(1))[0]
        ptype = first >> 4
        flags = first & 0x0F
        mult = 1
        rl = 0
        while True:
            eb = (await self._read_exact(1))[0]
            rl += (eb & 0x7F) * mult
            if not (eb & 0x80):
                break
            mult *= 128
        data = await self._read_exact(rl) if rl else b""
        return ptype, data, flags

    async def subscribe(self, topic: str, qos: int = 0) -> None:
        assert self._writer is not None
        body = struct.pack(">H", self._next_pktid()) + _mqtt_str(topic) + bytes([qos])
        self._writer.write(bytes([(_SUBSCRIBE << 4) | 0x02]) + _remaining_length(len(body)) + body)
        await self._writer.drain()

    async def publish(self, topic: str, payload: bytes, qos: int = 1) -> None:
        assert self._writer is not None
        vh = _mqtt_str(topic)
        if qos > 0:
            vh += struct.pack(">H", self._next_pktid())
        body = vh + zlib.compress(payload)
        self._writer.write(bytes([(_PUBLISH << 4) | (qos << 1)]) + _remaining_length(len(body)) + body)
        await self._writer.drain()

    async def _ping_loop(self) -> None:
        assert self._writer is not None
        try:
            while True:
                await asyncio.sleep(max(10, self._keepalive // 2))
                try:
                    self._writer.write(bytes([_PINGREQ << 4, 0]))
                    await self._writer.drain()
                except Exception:
                    return  # connection is down; let the listen loop handle reconnect
        except asyncio.CancelledError:
            return

    async def listen(self) -> None:
        """Read loop: PUBLISH -> decompress -> on_message(topic, payload)."""
        self._ping_task = asyncio.create_task(self._ping_loop())
        try:
            while True:
                ptype, data, flags = await self._read_packet()
                if ptype == _PUBLISH:
                    qos = (flags >> 1) & 0x03
                    tlen = struct.unpack(">H", data[0:2])[0]
                    topic = data[2 : 2 + tlen].decode("utf-8", "replace")
                    idx = 2 + tlen
                    pktid = None
                    if qos > 0:
                        pktid = struct.unpack(">H", data[idx : idx + 2])[0]
                        idx += 2
                    payload = data[idx:]
                    # QoS>0 messages must be PUBACK'd, otherwise the server considers the link broken and drops it
                    if qos > 0 and pktid is not None and self._writer:
                        self._writer.write(bytes([_PUBACK << 4, 2]) + struct.pack(">H", pktid))
                        await self._writer.drain()
                    try:
                        payload = zlib.decompress(payload)
                    except Exception:
                        pass
                    if self.on_message:
                        await self.on_message(topic, payload)
                # ignore SUBACK / PUBACK / PINGRESP etc.
        finally:
            if self._ping_task:
                self._ping_task.cancel()

    async def disconnect(self) -> None:
        if self._writer:
            try:
                self._writer.write(bytes([_DISCONNECT << 4, 0]))
                await self._writer.drain()
                self._writer.close()
            except Exception:
                pass
