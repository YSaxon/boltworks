
#partially generated with codium.ai

import pickle
import itsdangerous
import pytest

from ..boltworks.helper.serializers import SignedSerializer

def test_serialize_and_sign():
    symmetric_key = "secret_key"
    data = {"name": "John", "last": "smith"}
    signed_serializer = SignedSerializer(pickle, symmetric_key)
    signed_data = signed_serializer.dumps(data)
    assert signed_data is not None

def test_deserialize_invalid_signature():
    symmetric_key = "secret_key"
    data = {"name": "John", "last": "smith"}
    signed_serializer = SignedSerializer(pickle, symmetric_key)
    signed_data = signed_serializer.dumps(data)
    # modify the signed data to make the signature invalid
    modified_signed_data = signed_data[:-1] + bytes(signed_data[-1] ^ 0xFF)
    with pytest.raises(itsdangerous.BadSignature):
        signed_serializer.loads(modified_signed_data)

def test_deserialize_expired_signature():
    symmetric_key = "secret_key"
    data = {"name": "John", "last": "smith"}
    # set max_age to 1 second for testing purposes
    signed_serializer = SignedSerializer(pickle, symmetric_key, max_age=1)
    signed_data = signed_serializer.dumps(data)
    # wait for max_age to expire
    import time
    time.sleep(2)
    with pytest.raises(itsdangerous.SignatureExpired):
        signed_serializer.loads(signed_data)

def test_deserialize_and_verify_with_different_object_same_key():
    symmetric_key = "secret_key"
    data = {"name": "John", "last": "smith"}
    signed_serializer = SignedSerializer(pickle, symmetric_key)
    signed_data = signed_serializer.dumps(data)
    
    signed_serializer2 = SignedSerializer(pickle, symmetric_key)
    deserialized_data = signed_serializer2.loads(signed_data)
    assert deserialized_data == data
    
def test_deserialize_and_verify_with_different_object_different_key():
    symmetric_key = "secret_key"
    data = {"name": "John", "last": "smith"}
    signed_serializer = SignedSerializer(pickle, symmetric_key)
    signed_data = signed_serializer.dumps(data)
    
    symmetric_key2 = "secret_key2"
    signed_serializer2 = SignedSerializer(pickle, symmetric_key2)
    with pytest.raises(itsdangerous.BadSignature):
        signed_serializer2.loads(signed_data)