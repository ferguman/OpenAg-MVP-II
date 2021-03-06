from base64 import standard_b64encode
from datetime import datetime, timezone
from hashlib import sha256
from jose import jws 
from requests import post
from time import time
from uuid import uuid4

from python.logger import get_sub_logger 
from python.encryption.nacl_fop import decrypt

from config import device_id, hmac_secret_key_b64_cipher, fop_jose_id

# Note: This module uses JWT security (via jose).  Paseto is another system for implemeting token based security.

logger = get_sub_logger(__name__)

def extract_timestamp(path_name) -> 'timestamp':

    dt = path_name.split("/")[-1].split(".")[0]

    return datetime(int(dt[0:4]), int(dt[4:6]), int(dt[6:8]), 
                    hour=int(dt[9:11]), minute=int(dt[12:14]), second=int(dt[15:17]), tzinfo=timezone.utc).timestamp()


# Make the JWT claim set
def claim_info(file_hash, time_stamp, camera_id):

    #- TBD: Time delivers seconds since unix epoch. Not all systems have the same epoch start date.  There
    #- may be a better way to time stamp the claims.
    issue_time = int(time())

    # See RFC 7519
    return {'iss':device_id,                 #Issuer -> This mvp is the issuer. Use it's secret key to authenticate.
            'aud':fop_jose_id,               #Audience -> identifies the cloud provider that will receive this claim.
            'exp':issue_time + 60,           #Expiration Time
            'sub':camera_id,                 #Subject -> This mvp's camera is the subject
            'nbf':issue_time - 60,           #Not Before Time
            'iat':issue_time,                #Issued At
            'jti':str(uuid4()),              #JWT ID -> Don't accept duplicates by jti
            'file_dt':time_stamp,
            'file_hash':file_hash}

def get_file_hash(path_name):

    m = sha256()
    with open(path_name, 'rb') as f:
        for line in f:
            m.update(line)
            
    return standard_b64encode(m.digest()).decode('utf-8')

def get_jws(path_name, camera_id):
    """ create a jws token
        hmac_secret_key_b64_cipher - A 64 byte random value shared between the JWT client and the JWT server.
    """

    return jws.sign(claim_info(get_file_hash(path_name), extract_timestamp(path_name), camera_id), 
                    decrypt(hmac_secret_key_b64_cipher),
                    algorithm='HS256')

def upload_camera_image(path_name, url, camera_id):

    with open(path_name, 'rb') as f:
        r = post('{}'.format(url), 
                 data={'auth_method':'JWS', 'auth_data':get_jws(path_name, camera_id)}, 
                 files={'file':f}) 

    result = r.content.decode('utf-8')
    if result != 'ok':
        logger.error('Image upload error, server response -> {}'.format(result))
