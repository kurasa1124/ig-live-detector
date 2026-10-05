"""Build the thrift payload for the FBNS MQTToT connection (field order/types match MIT instagram_mqtt)."""
from __future__ import annotations

from dataclasses import dataclass, field as dc_field

from .thrift import ThriftWriter


@dataclass
class FbnsConnectConfig:
    client_identifier: str  # phoneId[:20]
    user_id: int = 0
    user_agent: str = ""
    client_capabilities: int = 183
    endpoint_capabilities: int = 128
    publish_format: int = 1
    no_automatic_foreground: bool = True
    make_user_available_in_foreground: bool = False
    device_id: str = ""
    is_initially_foreground: bool = False
    network_type: int = 1
    network_subtype: int = 0
    client_mqtt_session_id: int = 0
    subscribe_topics: list[int] = dc_field(default_factory=lambda: [76, 80, 231])
    client_type: str = "device_auth"
    app_id: int = 567310203415052
    device_secret: str = ""
    another_unknown: int = -1
    client_stack: int = 3
    password: str = ""


def build_fbns_connect_thrift(cfg: FbnsConnectConfig) -> bytes:
    w = ThriftWriter()
    w.string(1, cfg.client_identifier)
    w.struct(4)
    w.i64(1, cfg.user_id)
    w.string(2, cfg.user_agent)
    w.i64(3, cfg.client_capabilities)
    w.i64(4, cfg.endpoint_capabilities)
    w.i32(5, cfg.publish_format)
    w.boolean(6, cfg.no_automatic_foreground)
    w.boolean(7, cfg.make_user_available_in_foreground)
    w.string(8, cfg.device_id)
    w.boolean(9, cfg.is_initially_foreground)
    w.i32(10, cfg.network_type)
    w.i32(11, cfg.network_subtype)
    w.i64(12, cfg.client_mqtt_session_id)
    w.list_i32(14, cfg.subscribe_topics)
    w.string(15, cfg.client_type)
    w.i64(16, cfg.app_id)
    w.string(20, cfg.device_secret)
    w.i64(26, cfg.another_unknown)
    w.byte(21, cfg.client_stack)
    w.stop()  # end clientInfo struct
    w.string(5, cfg.password)
    w.stop()  # end top-level
    return w.result()
