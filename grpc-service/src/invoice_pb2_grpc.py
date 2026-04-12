# Vom gRPC-Python-Protokoll-Compiler erzeugt aus invoice.proto
"""Client- und Server-Klassen für den Rechnungs-gRPC-Dienst."""
import grpc

import invoice_pb2 as invoice__pb2

GRPC_GENERIERTE_VERSION = '1.80.0'
GRPC_VERSION = grpc.__version__
_version_nicht_unterstuetzt = False

try:
    from grpc._utilities import first_version_is_lower
    _version_nicht_unterstuetzt = first_version_is_lower(GRPC_VERSION, GRPC_GENERIERTE_VERSION)
except ImportError:
    _version_nicht_unterstuetzt = True

if _version_nicht_unterstuetzt:
    raise RuntimeError(
        f'Das installierte grpc-Paket hat Version {GRPC_VERSION},'
        + f' aber der generierte Code benötigt grpcio>={GRPC_GENERIERTE_VERSION}.'
        + f' Bitte grpcio auf >={GRPC_GENERIERTE_VERSION} aktualisieren'
        + f' oder grpcio-tools auf <={GRPC_VERSION} zurückstufen.'
    )


class RechnungsServiceStub(object):
    """Client-Stub für den RechnungsService."""

    def __init__(self, kanal):
        self.SpeichereRechnungsmetadaten = kanal.unary_unary(
                '/rechnung.RechnungsService/SpeichereRechnungsmetadaten',
                request_serializer=invoice__pb2.Rechnungsmetadaten.SerializeToString,
                response_deserializer=invoice__pb2.SpeicherAntwort.FromString,
                _registered_method=True)
        self.HoleRechnungsmetadaten = kanal.unary_unary(
                '/rechnung.RechnungsService/HoleRechnungsmetadaten',
                request_serializer=invoice__pb2.RechnungsAnfrage.SerializeToString,
                response_deserializer=invoice__pb2.Rechnungsmetadaten.FromString,
                _registered_method=True)


class RechnungsServiceServicer(object):
    """Server-Servicer-Basisklasse für den RechnungsService."""

    def SpeichereRechnungsmetadaten(self, request, context):
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Methode nicht implementiert!')
        raise NotImplementedError('Methode nicht implementiert!')

    def HoleRechnungsmetadaten(self, request, context):
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Methode nicht implementiert!')
        raise NotImplementedError('Methode nicht implementiert!')


def fuegeRechnungsServiceHinzu(servicer, server):
    methoden_handler = {
            'SpeichereRechnungsmetadaten': grpc.unary_unary_rpc_method_handler(
                    servicer.SpeichereRechnungsmetadaten,
                    request_deserializer=invoice__pb2.Rechnungsmetadaten.FromString,
                    response_serializer=invoice__pb2.SpeicherAntwort.SerializeToString,
            ),
            'HoleRechnungsmetadaten': grpc.unary_unary_rpc_method_handler(
                    servicer.HoleRechnungsmetadaten,
                    request_deserializer=invoice__pb2.RechnungsAnfrage.FromString,
                    response_serializer=invoice__pb2.Rechnungsmetadaten.SerializeToString,
            ),
    }
    allgemeiner_handler = grpc.method_handlers_generic_handler(
            'rechnung.RechnungsService', methoden_handler)
    server.add_generic_rpc_handlers((allgemeiner_handler,))
    server.add_registered_method_handlers('rechnung.RechnungsService', methoden_handler)
