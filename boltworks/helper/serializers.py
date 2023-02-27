from typing import Any, Protocol, Union

import itsdangerous


"""
json, pickle, and dill all qualify as Serializable (in ascending order of heavyweightness)
"""
class Serializable(Protocol):
    def loads(self, data: bytes)->Any: ...
    def dumps(self, obj) -> bytes: ...

class SignedSerializer(Serializable):
    def __init__(self,serializer:Serializable,symmetric_key,max_age:Union[int,None]=3600*24*90):
        self._signer=itsdangerous.TimestampSigner(symmetric_key) if max_age else itsdangerous.Signer(symmetric_key)
        self._max_age=max_age
        self._serializer=serializer

    def dumps(self,obj:Any):
        serialized=self._serializer.dumps(obj)
        signed=self._signer.sign(serialized)
        return signed

    def loads(self,signed_serialized:bytes):
        unsigned=self._signer.unsign(signed_value=signed_serialized,max_age=self._max_age) if isinstance(self._signer,itsdangerous.TimestampSigner) else self._signer.unsign(signed_value=signed_serialized)
        return self._serializer.loads(unsigned)

    def __getstate__(self):
        raise Exception("serializing this class is not allowed, for security reasons")
