from Crypto.Hash import HMAC, SHA256
import os 


def init_hmac_auth(key):
    
    hmac_object = HMAC.new(key,digestmod=SHA256)            
    
    return hmac_object

def update_hmac_chunk(hmac_object, encryption_chunk):
    
    hmac_object.update(encryption_chunk)
    
def finalize_hmac(hmac_object):
    
    hmac_signature = hmac_object.digest()
    
    return hmac_signature


def verify_file_integrity(file_path, key):
    
    file_size = os.path.getsize(file_path)
    
    if file_size < 48:
        raise ValueError("CRITICAL: The file is smaller than the size of a normal encrypted or corrupted file!")
        
    with open(file_path, "rb") as f:
        
        iv = f.read(16)
        
        f.seek(file_size - 32)
        original_tag = f.read(32)
        
    hmac_check = init_hmac_auth(key)
        
    chunks_size = 64 * 1024
    data_bytes_read = file_size - 16 - 32
    
    with open(file_path,"rb") as f:
        
        f.seek(16)
        
        encrypted_data = ""
        while data_bytes_read > 0:
            
            current_chunk_size = min(chunks_size, data_bytes_read)
            chunk = f.read(current_chunk_size)
            encrypted_data += chunk
            if not chunk:
                break
            
            hmac_check.update(chunk)
            
            data_bytes_read -= len(chunk)
        
    try:
        
        hmac_check.verify(original_tag)
        
        return iv, encrypted_data
    
    except ValueError:
        raise ValueError("CRITICAL ERROR: File Tampering Detected! Decryption Halted.")
        
    