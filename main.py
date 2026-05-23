import os
import base64
from argon2.low_level import hash_secret_raw, Type
from cryptography.fernet import Fernet
from tkinter import Tk, Button, filedialog, Label, Entry, StringVar
from HMAC_integrity import init_hmac_auth, update_hmac_chunk, finalize_hmac

TIME_COST   = 3
MEMORY_COST = 64 * 1024
PARALLELISM = 2
HASH_LENGTH = 32
SALT_LENGTH = 16
HMAC_LENGTH = 32  # SHA256 digest = 32 bytes

saved_password = None


# ── Key generation ─────────────────────────────────────────

def get_fernet_key(password: str, salt: bytes) -> bytes:
    raw_key = hash_secret_raw(
        secret      = password.encode(),
        salt        = salt,
        time_cost   = TIME_COST,
        memory_cost = MEMORY_COST,
        parallelism = PARALLELISM,
        hash_len    = HASH_LENGTH,
        type        = Type.ID
    )
    return base64.urlsafe_b64encode(raw_key)


def get_hmac_key(password: str, salt: bytes) -> bytes:
    hmac_salt = bytes([b ^ 0xFF for b in salt])
    return hash_secret_raw(
        secret      = password.encode(),
        salt        = hmac_salt,
        time_cost   = TIME_COST,
        memory_cost = MEMORY_COST,
        parallelism = PARALLELISM,
        hash_len    = HASH_LENGTH,
        type        = Type.ID
    )


# ── HMAC Configuration ─────────────────────

def compute_hmac(data: bytes, hmac_key: bytes) -> bytes:
    hmac_obj = init_hmac_auth(hmac_key)
    update_hmac_chunk(hmac_obj, data)
    return finalize_hmac(hmac_obj)


def verify_hmac(data: bytes, tag: bytes, hmac_key: bytes):
    hmac_obj = init_hmac_auth(hmac_key)
    update_hmac_chunk(hmac_obj, data)
    hmac_obj.verify(tag) 

# ── GUI setup ──────────────────────────────────────────────

root = Tk()
root.title("Application de chiffrement")
root.geometry("500x500")

label = Label(root, text="No file selected")
label.pack(pady=10)

Label(root, text="Password:").pack()
password_var = StringVar()
password_entry = Entry(root, textvariable=password_var, show="*", width=30)
password_entry.pack(pady=5)

Label(root, text="Confirm Password:").pack()
confirm_var = StringVar()
confirm_entry = Entry(root, textvariable=confirm_var, show="*", width=30)
confirm_entry.pack(pady=5)

password_status = Label(root, text="", fg="gray")
password_status.pack(pady=2)

file_path = None


# ── Password ───────────────────────────────────────────────

def save_password():
    global saved_password
    password = password_var.get()
    confirm  = confirm_var.get()

    if not password:
        password_status.config(text="Please enter a password!", fg="red")
        return
    if password != confirm:
        password_status.config(text="Passwords do not match!", fg="red")
        return

    saved_password = password
    password_status.config(text="✔ Password saved", fg="green")
    password_var.set("")
    confirm_var.set("")


password_entry.bind("<Return>", lambda e: save_password())
confirm_entry.bind("<Return>",  lambda e: save_password())


def select_file():
    global file_path
    file_path = filedialog.askopenfilename()
    label.config(text=file_path if file_path else "No file selected")


# ── Encryption ─────────────────────────────────────────────
def encrypt():
    if not file_path:
        label.config(text="No file selected!")
        return
    if not saved_password:
        label.config(text="Please save a password first!")
        return

    os.makedirs("Encrypted", exist_ok=True)

    salt = os.urandom(SALT_LENGTH)

    fernet_key = get_fernet_key(saved_password, salt)
    hmac_key   = get_hmac_key(saved_password, salt)

    with open(file_path, 'rb') as f:
        data = f.read()

    # Fernet encryption
    encrypted = Fernet(fernet_key).encrypt(data)

    # HMAC =  salt + encrypted ciphertext
    protected_data = salt + encrypted
    tag = compute_hmac(protected_data, hmac_key)

    # Write salt + ciphertext + hmac
    enc_file_path = os.path.join("Encrypted", os.path.basename(file_path) + ".enc")
    with open(enc_file_path, 'wb') as out:
        out.write(protected_data + tag)

    label.config(text=f"Encrypted: {os.path.basename(file_path)}.enc")
    print(f"[OK] Encrypted + HMAC tag appended → {enc_file_path}")


# ── Decryption ─────────────────────────────────────────────

def decrypt():
    if not file_path:
        label.config(text="No file selected!")
        return
    if not saved_password:
        label.config(text="Please save a password first!")
        return

    os.makedirs("Decrypted", exist_ok=True)

    enc_path      = file_path if file_path.endswith(".enc") else os.path.join("Encrypted", os.path.basename(file_path) + ".enc")
    original_name = os.path.basename(enc_path[:-4])

    try:
        #raw = [ salt (16)  | fernet ciphertext  | hmac tag (32B) ]
        raw = open(enc_path, 'rb').read()

        tag            = raw[-HMAC_LENGTH:] #hmac tag 
        protected_data = raw[:-HMAC_LENGTH]   # salt + encrypted
        salt           = protected_data[:SALT_LENGTH] #First 16B 
        encrypted      = protected_data[SALT_LENGTH:]#Everything after salt 

        #Verify HMAC BEFORE decrypting
        hmac_key = get_hmac_key(saved_password, salt)
        verify_hmac(protected_data, tag, hmac_key)  

        #Fernet decryption
        fernet_key = get_fernet_key(saved_password, salt)
        decrypted  = Fernet(fernet_key).decrypt(encrypted)

    except ValueError as e:
        label.config(text="HMAC failed: file may be tampered or wrong password!")
        print(f"[ERROR] Integrity check failed: {e}")
        return
    except FileNotFoundError:
        label.config(text="Encrypted file not found!")
        return
    except Exception as e:
        label.config(text="Wrong password or corrupted file!")
        print(f"[ERROR] Decryption error: {e}")
        return

    open(os.path.join("Decrypted", original_name), 'wb').write(decrypted)
    label.config(text=f"Decrypted: {original_name}")
    print(f"[OK] Decrypted → Decrypted/{original_name}")


# ── Buttons ────────────────────────────────────────────────

Button(root, text="Save Password", command=save_password).pack(pady=5)
Button(root, text="Select File",   command=select_file).pack(pady=5)
Button(root, text="Encrypt",       command=encrypt).pack(pady=5)
Button(root, text="Decrypt",       command=decrypt).pack(pady=5)

root.mainloop()