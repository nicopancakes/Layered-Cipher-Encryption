import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import numpy as np
import soundfile as sf
import os
from datetime import datetime
CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 !@#$%^&*()_+-=,./?;'\"[]{}<>"
CHAR_TO_IDX = {c: i for i, c in enumerate(CHARS)}
IDX_TO_CHAR = {i: c for i, c in enumerate(CHARS)}

class LCECore:
    @staticmethod
    def password_to_seed_layers(password: str):
        if not password.isdigit() or len(password) == 0 or len(password) > 5:
            return 42, 1
        return int(password) % 999999999, len(password)
    @staticmethod
    def encrypt_text(text: str, password: str) -> str:
        seed, _ = LCECore.password_to_seed_layers(password)
        np.random.seed(seed)
        shifts = np.random.randint(1, len(CHARS)-1, size=len(text))
        result = [IDX_TO_CHAR[(CHAR_TO_IDX.get(c, 0) + s) % len(CHARS)] if c in CHAR_TO_IDX else c 
                  for c, s in zip(text, shifts)]
        return ''.join(result)
    @staticmethod
    def decrypt_text(encrypted: str, password: str) -> str:
        seed, _ = LCECore.password_to_seed_layers(password)
        np.random.seed(seed)
        shifts = np.random.randint(1, len(CHARS)-1, size=len(encrypted))
        result = [IDX_TO_CHAR[(CHAR_TO_IDX.get(c, 0) - s) % len(CHARS)] if c in CHAR_TO_IDX else c 
                  for c, s in zip(encrypted, shifts)]
        return ''.join(result)
    @staticmethod
    def text_to_audio(text: str, password: str):
        seed, layers = LCECore.password_to_seed_layers(password)
        encrypted = LCECore.encrypt_text(text, password)
        audio = np.array([], dtype=np.float32)
        char_duration = 0.095
        np.random.seed(seed)
        for char in encrypted:
            if char not in CHAR_TO_IDX:
                silence = np.zeros(int(44100 * char_duration * layers))
                audio = np.concatenate((audio, silence))
                continue
            idx = CHAR_TO_IDX[char]
            for layer in range(layers):
                freq = 380 + idx * 22 + layer * 67
                t = np.linspace(0, char_duration, int(44100 * char_duration), False)
                tone = np.sin(2 * np.pi * freq * t) * 0.32
                audio = np.concatenate((audio, tone))
        
        audio = audio / np.max(np.abs(audio)) * 0.95
        return audio, encrypted, layers
    @staticmethod
    def audio_to_text(audio_path: str, password: str) -> str:
        try:
            audio, sr = sf.read(audio_path)
            if len(audio.shape) > 1:
                audio = np.mean(audio, axis=1)
            seed, layers = LCECore.password_to_seed_layers(password)
            char_samples = int(sr * 0.095)
            num_chars = len(audio) // (char_samples * layers)
            recovered = []
            np.random.seed(seed)
            for i in range(num_chars):
                start = i * char_samples * layers
                block = audio[start:start + char_samples * layers]
                best_idx = 0
                best_score = -999999
                for test_idx in range(len(CHARS)):
                    score = 0
                    for layer in range(layers):
                        seg = block[layer*char_samples:(layer+1)*char_samples]
                        fft = np.abs(np.fft.rfft(seg))
                        peak_freq = np.argmax(fft) * sr / len(seg)
                        expected = 380 + test_idx * 22 + layer * 67
                        score -= abs(peak_freq - expected)
                    if score > best_score:
                        best_score = score
                        best_idx = test_idx
                recovered.append(IDX_TO_CHAR[best_idx])
            
            encrypted = ''.join(recovered)
            return LCECore.decrypt_text(encrypted, password)
        except:
            return "Decoding Fail!"
class LCEApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("LCE v0.0.9")
        self.root.geometry("1000x680")
        self.root.configure(bg="#f0f0f0")
        
        self.current_file = None
        self.create_widgets()
    
    def create_widgets(self):
        top_frame = tk.Frame(self.root, bg="#f0f0f0", relief="raised", bd=1)
        top_frame.pack(fill="x")
        
        tk.Button(top_frame, text="Back", width=8, command=self.root.destroy).pack(side="left", padx=5, pady=5)
        tk.Button(top_frame, text="New", width=8, command=self.reset_fields).pack(side="left", padx=5, pady=5)
        tk.Label(top_frame, text="LCE v0.0.9", bg="#f0f0f0", font=("Segoe UI", 12, "bold")).pack(side="left", padx=20)
        enc_frame = tk.LabelFrame(self.root, text=" Encode Message ", font=("Segoe UI", 10, "bold"), bg="#f0f0f0")
        enc_frame.pack(fill="x", padx=15, pady=10)
        
        tk.Label(enc_frame, text="Message:", bg="#f0f0f0").pack(anchor="w", padx=10, pady=5)
        self.msg_entry = scrolledtext.ScrolledText(enc_frame, height=6, font=("Consolas", 10))
        self.msg_entry.pack(fill="x", padx=10, pady=5)
        
        tk.Label(enc_frame, text="Password (1-5 digits only):", bg="#f0f0f0").pack(anchor="w", padx=10)
        self.enc_pass = tk.Entry(enc_frame, font=("Consolas", 11), width=15)
        self.enc_pass.pack(anchor="w", padx=10, pady=5)
        
        tk.Button(enc_frame, text="Save As", font=("Segoe UI", 10, "bold"), 
                 bg="#e0e0e0", command=self.encode_and_save).pack(pady=12)
        
        dec_frame = tk.LabelFrame(self.root, text=" Decode Audio ", font=("Segoe UI", 10, "bold"), bg="#f0f0f0")
        dec_frame.pack(fill="x", padx=15, pady=10)
        
        btn_frame = tk.Frame(dec_frame, bg="#f0f0f0")
        btn_frame.pack(pady=8)
        tk.Button(btn_frame, text="Load Audio File", width=20, command=self.load_file).grid(row=0, column=0, padx=10)
        
        tk.Label(dec_frame, text="Password:", bg="#f0f0f0").pack(anchor="w", padx=15, pady=(10,5))
        self.dec_pass = tk.Entry(dec_frame, font=("Consolas", 11), width=15)
        self.dec_pass.pack(anchor="w", padx=15, pady=5)
        
        tk.Button(dec_frame, text="Decrypt Audio", font=("Segoe UI", 10, "bold"), 
                 bg="#e0e0e0", command=self.decrypt).pack(pady=12)
        
        tk.Label(dec_frame, text="Decrypted Message:", bg="#f0f0f0").pack(anchor="w", padx=15)
        self.result_box = scrolledtext.ScrolledText(dec_frame, height=8, font=("Consolas", 10))
        self.result_box.pack(fill="x", padx=15, pady=8)
        
        self.status = tk.Label(self.root, text="Ready", relief="sunken", anchor="w", bg="#e0e0e0")
        self.status.pack(side="bottom", fill="x")
    
    def encode_and_save(self):
        message = self.msg_entry.get("1.0", tk.END).strip()
        password = self.enc_pass.get().strip()
        
        if not message or not password:
            messagebox.showwarning("Input Required", "Please enter message and password")
            return
        
        default_name = f"LCE_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        save_path = filedialog.asksaveasfilename(
            initialfile=default_name,
            defaultextension=".wav",
            filetypes=[("WAV Audio File", "*.wav")]
        )
        
        if not save_path:
            return
        
        try:
            audio_data, _, layers = LCECore.text_to_audio(message, password)
            sf.write(save_path, audio_data, 44100)
            self.status.config(text=f"Saved: {os.path.basename(save_path)}  |  Layers: {layers}")
            messagebox.showinfo("Success", f"File saved successfully!\n\n{save_path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def load_file(self):
        path = filedialog.askopenfilename(filetypes=[("WAV Files", "*.wav")])
        if path:
            self.current_file = path
            self.status.config(text=f"Loaded: {os.path.basename(path)}")
    
    def decrypt(self):
        if not self.current_file:
            messagebox.showwarning("No File", "Please load an audio file first")
            return
        password = self.dec_pass.get().strip()
        if not password:
            messagebox.showwarning("Input Required", "Enter password")
            return
        
        self.status.config(text="Decrypting...")
        self.root.update()
        
        result = LCECore.audio_to_text(self.current_file, password)
        self.result_box.delete("1.0", tk.END)
        self.result_box.insert("1.0", result)
        self.status.config(text="Decryption Complete")
    
    def reset_fields(self):
        self.msg_entry.delete("1.0", tk.END)
        self.enc_pass.delete(0, tk.END)
        self.dec_pass.delete(0, tk.END)
        self.result_box.delete("1.0", tk.END)
        self.status.config(text="Ready")
    
    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = LCEApp()
    app.run()
