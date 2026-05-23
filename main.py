import os
import base64
import threading
import customtkinter as ctk
from argon2.low_level import hash_secret_raw, Type
from cryptography.fernet import Fernet
from tkinter import filedialog, messagebox
from HMAC_integrity import init_hmac_auth, update_hmac_chunk, finalize_hmac

# --- Fixed Specifications Constants ---
TIME_COST   = 3
MEMORY_COST = 64 * 1024
PARALLELISM = 2
HASH_LENGTH = 32
SALT_LENGTH = 16
HMAC_LENGTH = 32  # SHA256 digest = 32 bytes
CHUNK_SIZE  = 64 * 1024  # Max 64KB chunks to prevent RAM crash

# Global variables tracking operational states
saved_password = None
file_path = None

# --- CustomTkinter UI Theme Setup ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# --- Backend Cryptographic Key Generation Engine ---
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

# --- Refactored Streaming HMAC Functions ---
def compute_hmac_streaming(protected_file_path: str, hmac_key: bytes) -> bytes:
    """Streams a file to generate an HMAC without loading it completely into RAM."""
    hmac_obj = init_hmac_auth(hmac_key)
    with open(protected_file_path, 'rb') as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            update_hmac_chunk(hmac_obj, chunk)
    return finalize_hmac(hmac_obj)

# --- UI Application Window Class ---
class SecureCryptoApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Aegis File Cryptosystem")
        self.geometry("600x560")
        self.resizable(False, False)
        
        self.create_widgets()

    def create_widgets(self):
        # Header Application Brand
        self.title_label = ctk.CTkLabel(self, text="🛡️ AEGIS SECURITY INTERFACE", font=ctk.CTkFont(size=18, weight="bold"))
        self.title_label.pack(pady=(20, 5))
        
        self.sub_label = ctk.CTkLabel(self, text="AES-256 (Fernet) + HMAC-SHA256 Multi-Threaded Streamer", font=ctk.CTkFont(size=12, slant="italic"), text_color="gray")
        self.sub_label.pack(pady=(0, 15))

        # Main Layout Window Container
        self.container = ctk.CTkFrame(self)
        self.container.pack(fill="both", expand=True, padx=25, pady=10)

        # 1. Target File Handling Context
        self.file_title = ctk.CTkLabel(self.container, text="Target File Path:", font=ctk.CTkFont(weight="bold"))
        self.file_title.pack(anchor="w", padx=20, pady=(15, 2))
        
        self.file_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.file_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        self.file_entry = ctk.CTkEntry(self.file_frame, placeholder_text="No file selected...", width=380)
        self.file_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.file_btn = ctk.CTkButton(self.file_frame, text="Browse", width=90, command=self.select_file)
        self.file_btn.pack(side="right")

        # 2. Authentication Password Credentials Entry Fields
        self.pass_title = ctk.CTkLabel(self.container, text="Authentication Token:", font=ctk.CTkFont(weight="bold"))
        self.pass_title.pack(anchor="w", padx=20, pady=(5, 2))

        self.pass_entry = ctk.CTkEntry(self.container, show="*", placeholder_text="Enter encryption password...")
        self.pass_entry.pack(fill="x", padx=20, pady=2)

        self.confirm_entry = ctk.CTkEntry(self.container, show="*", placeholder_text="Confirm your password...")
        self.confirm_entry.pack(fill="x", padx=20, pady=5)

        # Status output line tracking password confirmations
        self.pwd_status = ctk.CTkLabel(self.container, text="", font=ctk.CTkFont(size=12))
        self.pwd_status.pack(pady=2)

        self.save_pwd_btn = ctk.CTkButton(self.container, text="Save & Register Password", fg_color="#3A3A3A", hover_color="#2B2B2B", command=self.save_password)
        self.save_pwd_btn.pack(fill="x", padx=20, pady=(0, 15))

        # 3. Dedicated Real-Time Progress Metric Widgets (Your Primary Assignment)
        self.progress_label = ctk.CTkLabel(self.container, text="System Idle", font=ctk.CTkFont(size=12))
        self.progress_label.pack(pady=(10, 2))

        self.progress_bar = ctk.CTkProgressBar(self.container)
        self.progress_bar.pack(fill="x", padx=20, pady=(0, 15))
        self.progress_bar.set(0)

        # 4. Global Structural Control Execution Buttons
        self.action_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.action_frame.pack(fill="x", padx=25, pady=(10, 20))

        self.encrypt_btn = ctk.CTkButton(self.action_frame, text="ENCRYPT", fg_color="#A83232", hover_color="#822525", font=ctk.CTkFont(weight="bold"), command=lambda: self.launch_worker_thread("encrypt"))
        self.encrypt_btn.pack(side="left", expand=True, fill="x", padx=(0, 10))

        self.decrypt_btn = ctk.CTkButton(self.action_frame, text="DECRYPT", fg_color="#2E7D32", hover_color="#1B5E20", font=ctk.CTkFont(weight="bold"), command=lambda: self.launch_worker_thread("decrypt"))
        self.decrypt_btn.pack(side="right", expand=True, fill="x", padx=(10, 0))

    # --- Structural Layout Actions Management ---
    def select_file(self):
        global file_path
        file_path = filedialog.askopenfilename()
        if file_path:
            self.file_entry.delete(0, "end")
            self.file_entry.insert(0, file_path)
            self.progress_bar.set(0)
            self.progress_label.configure(text="Ready to process selected file.", text_color="white")

    def save_password(self):
        global saved_password
        password = self.pass_entry.get()
        confirm = self.confirm_entry.get()

        if not password:
            self.pwd_status.configure(text="Please enter a password!", text_color="#FF4444")
            return
        if password != confirm:
            self.pwd_status.configure(text="Passwords do not match!", text_color="#FF4444")
            return

        saved_password = password
        self.pwd_status.configure(text="✔ Password securely registered for sessions", text_color="#44FF44")
        self.pass_entry.delete(0, "end")
        self.confirm_entry.delete(0, "end")

    def update_progress(self, bytes_processed, total_size):
        
        if total_size == 0:
            ratio = 0
        else:
            ratio = bytes_processed / total_size
            
        self.progress_bar.set(ratio)
        percentage = int(ratio * 100)
        self.progress_label.configure(text=f"Processing status: {percentage}% ({bytes_processed // (1024*1024)} MB / {total_size // (1024*1024)} MB)")
        self.update_idletasks()

    def set_ui_lockstate(self, locked):
        state = "disabled" if locked else "normal"
        self.file_btn.configure(state=state)
        self.save_pwd_btn.configure(state=state)
        self.encrypt_btn.configure(state=state)
        self.decrypt_btn.configure(state=state)

    def launch_worker_thread(self, mode):
       
        if not file_path:
            messagebox.showerror("Error", "No file selected!")
            return
        if not saved_password:
            messagebox.showerror("Error", "Please configure and register a secure session password first!")
            return
            
        # Edge Case 3: Empty File Pre-processing validations
        if os.path.getsize(file_path) == 0:
            messagebox.showwarning("Empty File Warning", "Processing cancelled: Selected target file contains 0 Bytes.")
            return

        self.set_ui_lockstate(True)
        worker = threading.Thread(target=self.process_cryptography_stream, args=(mode,))
        worker.daemon = True
        worker.start()

    # --- Refactored Non-Blocking Streaming Crypto Engine Execution Loop ---
    def process_cryptography_stream(self, mode):
        global file_path
        try:
            total_size = os.path.getsize(file_path)
            bytes_processed = 0
            
            if mode == "encrypt":
                os.makedirs("Encrypted", exist_ok=True)
                salt = os.urandom(SALT_LENGTH)
                
                fernet_key = get_fernet_key(saved_password, salt)
                hmac_key = get_hmac_key(saved_password, salt)
                fernet = Fernet(fernet_key)
                
                enc_file_path = os.path.join("Encrypted", os.path.basename(file_path) + ".enc")
                temp_protected_path = enc_file_path + ".tmp"
                
                # Write salt and stream blocks into temporary container file
                with open(file_path, 'rb') as source, open(temp_protected_path, 'wb') as dest:
                    dest.write(salt)
                    while True:
                        chunk = source.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        
                        # Process chunks to maintain small system RAM usage footprint
                        encrypted_chunk = fernet.encrypt(chunk)
                        # Prepend length of sub-token chunk to let decrypt stream loop split it safely later
                        dest.write(len(encrypted_chunk).to_bytes(4, byteorder='big') + encrypted_chunk)
                        
                        bytes_processed += len(chunk)
                        self.update_progress(bytes_processed, total_size)
                
                # Dynamic calculated streaming update across overall file layout blocks for final signature placement
                self.progress_label.configure(text="Generating authenticated HMAC validation seal...", text_color="#A83232")
                tag = compute_hmac_streaming(temp_protected_path, hmac_key)
                
                # Finalize assembly target deployment signature appending operations
                with open(temp_protected_path, 'ab') as dest:
                    dest.write(tag)
                    
                if os.path.exists(enc_file_path):
                    os.remove(enc_file_path)
                os.rename(temp_protected_path, enc_file_path)
                
                messagebox.showinfo("Success", f"File encrypted successfully!\nSaved to: {enc_file_path}")

            elif mode == "decrypt":
                os.makedirs("Decrypted", exist_ok=True)
                enc_path = file_path if file_path.endswith(".enc") else os.path.join("Encrypted", os.path.basename(file_path) + ".enc")
                
                # Edge Case 4: Preserve and smooth extract initial name configuration tags
                original_name = os.path.basename(enc_path[:-4])
                out_path = os.path.join("Decrypted", original_name)
                
                enc_total_size = os.path.getsize(enc_path)
                
                # Stream verify the signature first to prevent padding oracle processing risks
                self.progress_label.configure(text="Running integrity authentication validation routines...", text_color="#2E7D32")
                
                with open(enc_path, 'rb') as f:
                    salt = f.read(SALT_LENGTH)
                    f.seek(enc_total_size - HMAC_LENGTH)
                    tag = f.read(HMAC_LENGTH)
                
                # Isolation configuration slice read out definitions
                hmac_key = get_hmac_key(saved_password, salt)
                hmac_obj = init_hmac_auth(hmac_key)
                
                # Read structural layout block payload minus trailing tag parameters
                with open(enc_path, 'rb') as f:
                    protected_bytes_left = enc_total_size - HMAC_LENGTH
                    while protected_bytes_left > 0:
                        read_len = min(CHUNK_SIZE, protected_bytes_left)
                        chunk = f.read(read_len)
                        update_hmac_chunk(hmac_obj, chunk)
                        protected_bytes_left -= read_len
                
                # Edge Case 2: Catches bit-tampering before writing anything to disk
                hmac_obj.verify(tag)
                
                # Proceeding with Stream Decryption
                fernet_key = get_fernet_key(saved_password, salt)
                fernet = Fernet(fernet_key)
                
                with open(enc_path, 'rb') as source, open(out_path, 'wb') as dest:
                    source.seek(SALT_LENGTH) # Skip initial salt position block data
                    bytes_to_read = enc_total_size - SALT_LENGTH - HMAC_LENGTH
                    
                    while bytes_to_read > 0:
                        chunk_len_bytes = source.read(4)
                        if not chunk_len_bytes:
                            break
                        chunk_len = int.from_bytes(chunk_len_bytes, byteorder='big')
                        
                        encrypted_chunk = source.read(chunk_len)
                        decrypted_chunk = fernet.decrypt(encrypted_chunk)
                        dest.write(decrypted_chunk)
                        
                        # Use raw file advancement bounds metrics mapping to update UI calculation sliders
                        bytes_processed += (4 + chunk_len)
                        self.update_progress(bytes_processed, enc_total_size - SALT_LENGTH - HMAC_LENGTH)
                        bytes_to_read -= (4 + chunk_len)
                        
                messagebox.showinfo("Success", f"Integrity Verified! File decrypted successfully.\nSaved to: {out_path}")

        except ValueError:
            # Edge Case 2 Handler: Trap tampered bits safely without application crashes
            messagebox.showerror("Security Threat Intercepted", "Cryptographic Validation Failure!\nFile may have been altered by an attacker or an invalid signature key/password was entered.")
        except FileNotFoundError:
            messagebox.showerror("IO Error", "The designated resource target could not be found.")
        except Exception as e:
            messagebox.showerror("Decryption Failed", "Decryption error occurred. Key mismatch or data structure payload is corrupted.")
            print(f"[DEBUG LOG] Internal error breakdown details: {str(e)}")
        finally:
            self.set_ui_lockstate(False)
            self.progress_label.configure(text="Operation Cycle Finished.", text_color="white")

if __name__ == "__main__":
    app = SecureCryptoApp()
    app.mainloop()