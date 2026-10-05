"""Golden-byte test: the Python thrift writer must match Node instagram_mqtt byte for byte."""
from ig_live_detector.fbns.connection import FbnsConnectConfig, build_fbns_connect_thrift

# Produced by Node instagram_mqtt's MQTToTConnection.toThrift() for the same config
GOLDEN = (
    "18146162636465666768696a303132333435363738393c16001807746573742d75"
    "6116ee0216800215021112180012150215001680a0abfe1929359801a001ce03180b"
    "6465766963655f617574681698a8b7b2e6fd810248006601032a0300180000"
)


def test_thrift_matches_node_golden():
    cfg = FbnsConnectConfig(
        client_identifier="abcdefghij0123456789",
        user_id=0,
        user_agent="test-ua",
        client_capabilities=183,
        endpoint_capabilities=128,
        publish_format=1,
        device_id="",
        network_type=1,
        network_subtype=0,
        client_mqtt_session_id=1700000000000 & 0xFFFFFFFF,
        subscribe_topics=[76, 80, 231],
        client_type="device_auth",
        app_id=567310203415052,
        device_secret="",
        another_unknown=-1,
        client_stack=3,
        password="",
    )
    assert build_fbns_connect_thrift(cfg).hex() == GOLDEN
