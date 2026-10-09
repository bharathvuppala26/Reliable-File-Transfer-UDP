import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import socket
import struct
import threading
import os
import time
import random
import zlib

# ============================================================
# RELIABLE FILE TRANSFER SYSTEM OVER UDP
# Final-preview / learning version
# ============================================================

MAGIC = b"RUDP"
# magic(4) + type(1) + seq(4) + total(4) + crc(4)
HEADER = struct.Struct("!4sBIII")
DATA = 0
META = 1
DATA16 = 2
META16 = 3
ACK = b"ACK"

class ReliableUDPApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Reliable File Transfer System over UDP")
        self.root.geometry("950x650")
        self.root.minsize(850, 580)

        self.receiver_socket = None
        self.receiver_running = False
        self.send_lock = threading.Lock()

        self._build_ui()

    # ---------------- UI ----------------
    def _build_ui(self):
        title = tk.Label(
            self.root,
            text="RELIABLE FILE TRANSFER SYSTEM OVER UDP",
            font=("Segoe UI", 20, "bold")
        )
        title.pack(pady=(12, 2))

        subtitle = tk.Label(
            self.root,
            text="CRC Error Detection • ACK • Timeout • Retransmission • Packet Loss Simulation",
            font=("Segoe UI", 10)
        )
        subtitle.pack(pady=(0, 10))

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=8)

        self.sender_tab = ttk.Frame(self.notebook)
        self.receiver_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.sender_tab, text="  Sender (Client)  ")
        self.notebook.add(self.receiver_tab, text="  Receiver (Server)  ")

        self._build_sender()
        self._build_receiver()

        self.status_var = tk.StringVar(value="Ready")
        tk.Label(
            self.root,
            textvariable=self.status_var,
            anchor="w",
            relief="sunken",
            padx=8
        ).pack(fill="x", padx=12, pady=(0, 10))

    def _build_sender(self):
        frame = self.sender_tab
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(8, weight=1)

        ttk.Label(frame, text="File to send:").grid(row=0, column=0, sticky="w", padx=15, pady=10)
        self.file_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.file_var).grid(row=0, column=1, sticky="ew", padx=10, pady=10)
        ttk.Button(frame, text="Browse", command=self.browse_file).grid(row=0, column=2, padx=15, pady=10)

        ttk.Label(frame, text="Receiver IP:").grid(row=1, column=0, sticky="w", padx=15, pady=8)
        self.ip_var = tk.StringVar(value="127.0.0.1")
        ttk.Entry(frame, textvariable=self.ip_var, width=25).grid(row=1, column=1, sticky="w", padx=10, pady=8)

        ttk.Label(frame, text="Port:").grid(row=2, column=0, sticky="w", padx=15, pady=8)
        self.port_var = tk.StringVar(value="9000")
        ttk.Entry(frame, textvariable=self.port_var, width=25).grid(row=2, column=1, sticky="w", padx=10, pady=8)

        ttk.Label(frame, text="Packet size (bytes):").grid(row=3, column=0, sticky="w", padx=15, pady=8)
        self.packet_size_var = tk.StringVar(value="1024")
        ttk.Combobox(
            frame, textvariable=self.packet_size_var,
            values=["512", "1024", "2048", "4096"], state="readonly", width=22
        ).grid(row=3, column=1, sticky="w", padx=10, pady=8)

        ttk.Label(frame, text="CRC:").grid(row=4, column=0, sticky="w", padx=15, pady=8)
        self.crc_var = tk.StringVar(value="CRC-32")
        ttk.Combobox(
            frame, textvariable=self.crc_var,
            values=["CRC-32", "CRC-16-CCITT"], state="readonly", width=22
        ).grid(row=4, column=1, sticky="w", padx=10, pady=8)

        ttk.Label(frame, text="Timeout (seconds):").grid(row=5, column=0, sticky="w", padx=15, pady=8)
        self.timeout_var = tk.StringVar(value="0.7")
        ttk.Entry(frame, textvariable=self.timeout_var, width=25).grid(row=5, column=1, sticky="w", padx=10, pady=8)

        ttk.Label(frame, text="Simulated packet loss (%):").grid(row=6, column=0, sticky="w", padx=15, pady=8)
        self.loss_var = tk.StringVar(value="5")
        ttk.Entry(frame, textvariable=self.loss_var, width=25).grid(row=6, column=1, sticky="w", padx=10, pady=8)

        buttons = ttk.Frame(frame)
        buttons.grid(row=7, column=0, columnspan=3, sticky="w", padx=15, pady=10)
        ttk.Button(buttons, text="Start Transfer", command=self.start_transfer).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Clear Log", command=lambda: self.sender_log.delete("1.0", "end")).pack(side="left")

        stats = ttk.Frame(frame)
        stats.grid(row=8, column=0, columnspan=3, sticky="nsew", padx=15, pady=8)
        stats.columnconfigure(0, weight=1)
        stats.rowconfigure(1, weight=1)

        self.sender_progress = ttk.Progressbar(stats, maximum=100)
        self.sender_progress.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        self.sender_log = tk.Text(stats, height=15, wrap="word")
        self.sender_log.grid(row=1, column=0, sticky="nsew")

    def _build_receiver(self):
        frame = self.receiver_tab
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(6, weight=1)

        ttk.Label(frame, text="Listen Port:").grid(row=0, column=0, sticky="w", padx=15, pady=12)
        self.listen_port_var = tk.StringVar(value="9000")
        ttk.Entry(frame, textvariable=self.listen_port_var, width=25).grid(row=0, column=1, sticky="w", padx=10, pady=12)

        ttk.Label(frame, text="Save folder:").grid(row=1, column=0, sticky="w", padx=15, pady=8)
        self.save_var = tk.StringVar(value=os.path.join(os.getcwd(), "received_files"))
        ttk.Entry(frame, textvariable=self.save_var).grid(row=1, column=1, sticky="ew", padx=10, pady=8)
        ttk.Button(frame, text="Choose", command=self.choose_folder).grid(row=1, column=2, padx=15, pady=8)

        buttons = ttk.Frame(frame)
        buttons.grid(row=2, column=0, columnspan=3, sticky="w", padx=15, pady=10)
        ttk.Button(buttons, text="Start Receiver", command=self.start_receiver).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Stop Receiver", command=self.stop_receiver).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Clear Log", command=lambda: self.receiver_log.delete("1.0", "end")).pack(side="left")

        self.receiver_progress = ttk.Progressbar(frame, maximum=100)
        self.receiver_progress.grid(row=3, column=0, columnspan=3, sticky="ew", padx=15, pady=10)

        self.receiver_stats = tk.StringVar(value="No transfer yet.")
        ttk.Label(frame, textvariable=self.receiver_stats).grid(row=4, column=0, columnspan=3, sticky="w", padx=15, pady=5)

        self.receiver_log = tk.Text(frame, height=18, wrap="word")
        self.receiver_log.grid(row=6, column=0, columnspan=3, sticky="nsew", padx=15, pady=10)

    # ---------------- Helpers ----------------
    def log_sender(self, msg):
        self.root.after(0, lambda: (self.sender_log.insert("end", msg + "\n"), self.sender_log.see("end")))

    def log_receiver(self, msg):
        self.root.after(0, lambda: (self.receiver_log.insert("end", msg + "\n"), self.receiver_log.see("end")))

    def set_status(self, msg):
        self.root.after(0, lambda: self.status_var.set(msg))

    def browse_file(self):
        path = filedialog.askopenfilename()
        if path:
            self.file_var.set(path)

    def choose_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.save_var.set(path)

    def crc_value(self, data):
        if self.crc_var.get() == "CRC-16-CCITT":
            return self.crc16_ccitt(data)
        return zlib.crc32(data) & 0xffffffff

    @staticmethod
    def crc16_ccitt(data):
        crc = 0xFFFF
        for byte in data:
            crc ^= byte << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = ((crc << 1) ^ 0x1021) & 0xFFFF
                else:
                    crc = (crc << 1) & 0xFFFF
        return crc

    # ---------------- Receiver ----------------
    def start_receiver(self):
        if self.receiver_running:
            messagebox.showinfo("Receiver", "Receiver is already running.")
            return

        try:
            port = int(self.listen_port_var.get())
            os.makedirs(self.save_var.get(), exist_ok=True)
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(("0.0.0.0", port))
            sock.settimeout(1.0)
            self.receiver_socket = sock
            self.receiver_running = True
            self.log_receiver(f"[SERVER] Listening on UDP port {port}")
            self.set_status(f"Receiver running on port {port}")
            threading.Thread(target=self.receiver_loop, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Receiver Error", str(e))

    def stop_receiver(self):
        self.receiver_running = False
        if self.receiver_socket:
            try:
                self.receiver_socket.close()
            except:
                pass
            self.receiver_socket = None
        self.log_receiver("[SERVER] Receiver stopped.")
        self.set_status("Receiver stopped")

    def receiver_loop(self):
        meta = None
        chunks = {}
        expected_total = 0
        file_name = None
        transfer_id = None
        start_time = None
        received_count = 0

        while self.receiver_running:
            try:
                packet, addr = self.receiver_socket.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                break
            except Exception as e:
                self.log_receiver(f"[ERROR] {e}")
                continue

            if len(packet) < HEADER.size:
                continue

            magic, ptype, seq, total, sent_crc = HEADER.unpack(packet[:HEADER.size])
            if magic != MAGIC:
                continue

            payload = packet[HEADER.size:]
            calc_crc = self._receiver_crc(payload, sent_crc, ptype)

            # CRC check
            if calc_crc != sent_crc:
                self.log_receiver(f"[CRC ERROR] Packet {seq} rejected")
                continue

            use_crc16 = ptype in (DATA16, META16)
            is_meta = ptype in (META, META16)

            # Metadata packet
            if is_meta:
                try:
                    file_name = payload.decode("utf-8")
                    expected_total = total
                    chunks = {}
                    received_count = 0
                    start_time = time.time()
                    transfer_id = (addr, file_name)
                    self.log_receiver(f"[META] Receiving: {file_name} | packets={total}")
                    self.receiver_socket.sendto(ACK + struct.pack("!I", seq), addr)
                except Exception:
                    pass
                continue

            if ptype not in (DATA, DATA16):
                continue

            if expected_total == 0:
                expected_total = total

            # Duplicate packets are ACKed again
            if seq not in chunks:
                chunks[seq] = payload
                received_count += 1
                self.log_receiver(f"[RECV] Packet {seq}/{expected_total}")
            else:
                self.log_receiver(f"[DUPLICATE] Packet {seq}")

            try:
                self.receiver_socket.sendto(ACK + struct.pack("!I", seq), addr)
            except:
                pass

            percent = (received_count / expected_total * 100) if expected_total else 0
            self.root.after(0, lambda p=percent: self.receiver_progress.config(value=p))
            self.root.after(0, lambda r=received_count, t=expected_total:
                            self.receiver_stats.set(f"Packets received: {r}/{t}"))

            if expected_total and received_count >= expected_total:
                try:
                    safe_name = os.path.basename(file_name or "received_file")
                    out_path = os.path.join(self.save_var.get(), "received_" + safe_name)
                    with open(out_path, "wb") as f:
                        for i in range(expected_total):
                            f.write(chunks[i])

                    elapsed = max(time.time() - start_time, 0.001)
                    size = os.path.getsize(out_path)
                    speed = size / elapsed / 1024
                    self.log_receiver(f"[SUCCESS] File reconstructed: {out_path}")
                    self.log_receiver(f"[STATS] {size} bytes | {elapsed:.2f}s | {speed:.1f} KB/s")
                    self.set_status("File transfer completed successfully")
                    self.root.after(0, lambda: self.receiver_progress.config(value=100))

                    # Reset for next transfer
                    expected_total = 0
                    chunks = {}
                    file_name = None
                    received_count = 0
                except Exception as e:
                    self.log_receiver(f"[ERROR] Reconstruction failed: {e}")

    def _receiver_crc(self, data, sent_crc, ptype):
        if ptype in (DATA16, META16):
            return self.crc16_ccitt(data)
        return zlib.crc32(data) & 0xffffffff

    # ---------------- Sender ----------------
    def start_transfer(self):
        path = self.file_var.get().strip()
        if not path or not os.path.isfile(path):
            messagebox.showwarning("Sender", "Please choose a valid file.")
            return

        try:
            ip = self.ip_var.get().strip()
            port = int(self.port_var.get())
            packet_size = int(self.packet_size_var.get())
            timeout = float(self.timeout_var.get())
            loss = float(self.loss_var.get())

            if not (0 <= loss <= 100):
                raise ValueError("Packet loss must be between 0 and 100.")
        except Exception as e:
            messagebox.showerror("Input Error", str(e))
            return

        threading.Thread(
            target=self.send_file,
            args=(path, ip, port, packet_size, timeout, loss),
            daemon=True
        ).start()

    def send_file(self, path, ip, port, packet_size, timeout, loss):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)

        total_size = os.path.getsize(path)
        file_name = os.path.basename(path)

        with open(path, "rb") as f:
            data = f.read()

        chunks = [data[i:i+packet_size] for i in range(0, len(data), packet_size)]
        total = len(chunks)

        self.root.after(0, lambda: self.sender_progress.config(value=0))
        self.log_sender(f"[START] {file_name} | {total_size} bytes | {total} packets")
        self.log_sender(f"[CONFIG] UDP {ip}:{port} | {self.crc_var.get()} | loss simulation={loss}%")
        self.set_status("Transfer started")

        # Metadata packet
        meta_payload = file_name.encode("utf-8")
        meta_crc = self.crc_value(meta_payload)
        meta_type = META16 if self.crc_var.get() == "CRC-16-CCITT" else META
        meta_packet = HEADER.pack(MAGIC, meta_type, 0, total, meta_crc) + meta_payload

        try:
            self._send_reliably(sock, meta_packet, 0, ip, port, timeout, loss)
        except Exception as e:
            self.log_sender(f"[ERROR] Metadata transfer failed: {e}")
            sock.close()
            return

        sent = 0
        retransmissions = 0
        start = time.time()

        for seq, chunk in enumerate(chunks):
            crc = self.crc_value(chunk)
            data_type = DATA16 if self.crc_var.get() == "CRC-16-CCITT" else DATA
            packet = HEADER.pack(MAGIC, data_type, seq, total, crc) + chunk

            attempts = 0
            while True:
                attempts += 1

                # Simulate packet loss only for sending, not actual network.
                if random.random() >= loss / 100.0:
                    sock.sendto(packet, (ip, port))
                    self.log_sender(f"[SEND] Packet {seq}/{total-1}")
                else:
                    self.log_sender(f"[SIMULATED LOSS] Packet {seq}")

                try:
                    while True:
                        ack, _ = sock.recvfrom(1024)
                        if ack.startswith(ACK) and len(ack) >= 7:
                            ack_seq = struct.unpack("!I", ack[3:7])[0]
                            if ack_seq == seq:
                                self.log_sender(f"[ACK] Packet {seq}")
                                sent += 1
                                if attempts > 1:
                                    retransmissions += attempts - 1
                                percent = sent / total * 100
                                self.root.after(0, lambda p=percent: self.sender_progress.config(value=p))
                                break
                    break
                except socket.timeout:
                    self.log_sender(f"[TIMEOUT] Packet {seq} -> retransmitting")
                    continue

        elapsed = max(time.time() - start, 0.001)
        speed = total_size / elapsed / 1024

        self.log_sender("[SUCCESS] Transfer completed")
        self.log_sender(f"[STATS] Packets={total} | Retransmissions={retransmissions} | Time={elapsed:.2f}s | Speed={speed:.1f} KB/s")
        self.set_status("Transfer completed successfully")
        sock.close()

    def _send_reliably(self, sock, packet, seq, ip, port, timeout, loss):
        while True:
            if random.random() >= loss / 100.0:
                sock.sendto(packet, (ip, port))
                self.log_sender("[SEND] Metadata")
            else:
                self.log_sender("[SIMULATED LOSS] Metadata")
            try:
                while True:
                    ack, _ = sock.recvfrom(1024)
                    if ack.startswith(ACK) and len(ack) >= 7:
                        ack_seq = struct.unpack("!I", ack[3:7])[0]
                        if ack_seq == seq:
                            self.log_sender("[ACK] Metadata")
                            return
            except socket.timeout:
                self.log_sender("[TIMEOUT] Metadata -> retransmitting")

if __name__ == "__main__":
    root = tk.Tk()
    app = ReliableUDPApp(root)
    root.mainloop()
