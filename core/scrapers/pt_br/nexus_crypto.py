import base64
import hashlib
import json

CRYPTO_SECRET = b"OrionNexus2025CryptoKey!Secure"
NUM_KEYS = 5

class KeyData:
    def __init__(self, key):
        self.key = key
        self.sbox = [0] * 256
        self.rsbox = [0] * 256

keys = []
initialized = False

def _initialize():
    global initialized, keys
    if initialized:
        return
    
    for i in range(NUM_KEYS):
        pattern = f"_orion_key_{i}_v2_".encode('utf-8') + CRYPTO_SECRET
        hex_key = hashlib.sha256(pattern).hexdigest()
        key_bytes = bytes.fromhex(hex_key)
        
        kd = KeyData(key_bytes)
        _init_sbox_for_key(kd)
        keys.append(kd)
        
    initialized = True

def _init_sbox_for_key(kd):
    key = kd.key
    for i in range(256):
        kd.sbox[i] = i
        
    j = 0
    for i in range(256):
        j = (j + kd.sbox[i] + key[i % len(key)]) % 256
        kd.sbox[i], kd.sbox[j] = kd.sbox[j], kd.sbox[i]
        
    for i in range(256):
        kd.rsbox[kd.sbox[i]] = i

def _rotate_right(byte, shift):
    s = shift % 8
    return ((byte >> s) | (byte << (8 - s))) & 0xFF

def decrypt(key_index, base64_data):
    _initialize()
    if key_index < 0 or key_index >= NUM_KEYS:
        raise ValueError(f"Invalid key index: {key_index}")
        
    kd = keys[key_index]
    key = kd.key
    rsbox = kd.rsbox
    
    input_bytes = bytearray(base64.b64decode(base64_data))
    output = bytearray(len(input_bytes))
    key_len = len(key)
    
    for i in range(len(input_bytes) - 1, -1, -1):
        b = input_bytes[i]
        
        if i > 0:
            b ^= input_bytes[i - 1]
        else:
            b ^= key[key_len - 1]
            
        b = rsbox[b]
        rot_amount = ((key[(i + 3) % key_len] + (i & 0xFF)) & 0xFF) % 7 + 1
        b = _rotate_right(b, rot_amount)
        b ^= key[i % key_len]
        
        output[i] = b
        
    return output.decode('utf-8')

def decrypt_response(body_text):
    try:
        data = json.loads(body_text)
        if 'v' in data and 'd' in data:
            v = data['v']
            if v == 1 or v == 2:
                key_index = 0 if v == 1 else data.get('k', 0)
                decrypted = decrypt(key_index, data['d'])
                return json.loads(decrypted)
        return data
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Erro ao decodificar Nexus: {e}")
        return None
