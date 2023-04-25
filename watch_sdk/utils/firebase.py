import firebase_admin
from firebase_admin import credentials
from firebase_admin import auth

cred = credentials.Certificate(
    {
        "type": "service_account",
        "project_id": "taphealth",
        "private_key_id": "f5b7251010e0befa498c934bc02359f463188fb3",
        "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCzs1lWD16hTPP4\nITBhTH0guj0NEZF1p+9PwVrEteFAsZw9Bud/+4VdDlwifMJMph5+CtzjskPiFirh\nzLENtkQjIrpG1CmaybrMq4mxD/xWTGd8ZSsLsp6Pma/SCX1erqHXHr/lRNI+ahuY\nNV90SfuTqtQNtY5RlTeqd+64/od/zHbcW5uD2JtizydIEb/12mIQthMShlk2tZDY\nx+YaEj/XQY+UW3niuBfA3/EteGjjOxImYu5gsb39UQ690rqpL36EmHZA77cp/cI3\nEitWKXnkObG5jCcYQGw705uFrfrEl3a/guAo/Wdw/6rW8+FaEbA6Kc4iLajvBQ8I\nEC1EGcShAgMBAAECggEAALn8HViyCgcqZmH54WamBlXZBxQQPCMwitenzHZnFcY4\nT5JUW1tSGC/elp5/M0vISYQT/OMnLg/F7Mh4X9JAj5LCt5kyxP4K7PHGVYRQgaIz\n4Odj+kqmqfqn9EWxM6ENzvhnM/IAEP2TQ64usLLMOHNPDNwCF4z0MRgnYcpYbTLh\nSdWsqYhbxqyn7Q5N7csu1VfJeg+RqLAohc14iPP5Q88FqpEdntMlmnzagpSJ2FuH\nJMaP2iOIdA9iF1OEJkdxRMgwSiUQpNyPLXov8NMfnIaBkeO3RRxFUbnijNShRlB2\nNQJg642pyT/25hamQhEoVB7iCu5EWk+qAA53rCoQCQKBgQDnb8lYG4EWTFoSzRAl\nKbCoTaslOZ9+zPCLtz9nEf9P/stj2+p6SxCEzlwhh6ddf2pYU0ONIxn56DW0Brsz\nT6CRxTbwjXzk7OIFtZpeRzfH/bObi0A8zc9ad/a7+R+e9FMb5c9ZjJyxnN8UXbq6\nZ3MaANpzlHjjMyUKNZu44o8+3wKBgQDGxeAWTOPofXcFNzvinxBVsY5LweD9nrV7\nt4KKd+nPX4kpbdW40tFAtitNINALnc4D4vNAoxdnYnn6wSIeBa7zwZXr9rKVkLgN\n4gdxwyQFFJ6cj9u5b0PKBHwSG6xVxrESxU6whF+VhiX9QmBjrAWLqbr9Y/yLCRIL\nTzA+FWzsfwKBgQCOR5j+g5oufS361PqR/jlOnsESl4RITfGr0zI1SUkugrPDZlWW\nbUNwgfT94AmyXzyfpECpKeU0T9+EF4dKmi9armWCKVmY21Bwth56y0mtt3iNrWQG\nfXh2Y73Z/ePEsuvNANEiemFyh8BVIvJC2opWeCPUXnibJLwmtKJRXWc2/QKBgBlS\nigqtPveWTDxY3gMv2mfgV81k5KHKvzoEldfIEPw/In0ppemGyeuhiYCo5ngkYWNz\nXSPl4wxjqkB8rDkA5lndVpkZ84RETH5QRjyC7KrNBqvRU9+awhsRWTEBX4IJ7vMC\nOdUY+AhXb62E8DyiZI53UAAJ5dlcjXTtYKr4FclHAoGAHPMWQPEiq0bdqXnULeso\n20saVvkmDnfkE3KQHBJ0o3dh927fTBdox+cZ2M20UGMgrp4ujmqMhdu9UJkY58Yn\nNihO45LISm9sM3sdoXYfy4Mz0gdf1ZxTsqy1PkIpAzsWs0DRHg0YUVpRDKYlO/SZ\nKn9JAe8c3QQpZKFrAe7InM4=\n-----END PRIVATE KEY-----\n",
        "client_email": "firebase-adminsdk-1uv07@taphealth.iam.gserviceaccount.com",
        "client_id": "106694276624459499381",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-1uv07%40taphealth.iam.gserviceaccount.com",
    },
)

default_app = firebase_admin.initialize_app(cred)


def verify_firebase_token(auth_token):
    if not auth_token:
        return None
    try:
        decoded_token = auth.verify_id_token(auth_token)
    except Exception:
        return None

    try:
        decoded_token["uid"]
        return decoded_token["email"]
    except Exception:
        return None
