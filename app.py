import socket
import threading
import zlib
import os
import time
import random
import base64
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


# ============================================================
# RELIABLE FILE TRANSFER SYSTEM OVER UDP
# Single-file GUI version
#
# Concepts:
# UDP
# CRC-32
# ACK
# Timeout
# Retransmission
# Packet Loss Simulation
# ============================================================


class ReliableUDPApp:

    def __init__(self, root):
        self.root = root
        self.root.title("Reliable File Transfer System over UDP")
        self.root.geometry("1100x750")

        self.receiver_running = False
        self.receiver_socket = None

        self.create_variables()
        self.create_gui()

    # ========================================================
    # VARIABLES
    # ========================================================

    def create_variables(self):

        self.file_path = tk.StringVar()

        self.receiver_ip = tk.StringVar(value="127.0.0.1")
        self.port = tk.StringVar(value="9000")

        self.packet_size = tk.StringVar(value="1024")
        self.crc_type = tk.StringVar(value="CRC-32")

        self.timeout = tk.StringVar(value="1.0")
        self.packet_loss = tk.StringVar(value="5")

        self.listen_port = tk.StringVar(value="9000")

        self.save_folder = tk.StringVar(
            value=os.path.join(
                os.path.expanduser("~"),
                "Downloads",
                "received_files"
            )
        )

    # ========================================================
    # GUI
    # ========================================================

    def create_gui(self):

        # ---------------- MAIN TITLE ----------------

        title = tk.Label(
            self.root,
            text="RELIABLE FILE TRANSFER SYSTEM OVER UDP",
            font=("Arial", 24, "bold")
        )

        title.pack(pady=(20, 5))

        subtitle = tk.Label(
            self.root,
            text="CRC Error Detection • ACK • Timeout • Retransmission • Packet Loss Simulation",
            font=("Arial", 11)
        )

        subtitle.pack(pady=(0, 15))

        # ---------------- NOTEBOOK ----------------

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=15, pady=5)

        sender_tab = ttk.Frame(notebook)
        receiver_tab = ttk.Frame(notebook)

        notebook.add(sender_tab, text="Sender (Client)")
        notebook.add(receiver_tab, text="Receiver (Server)")

        self.create_sender_tab(sender_tab)
        self.create_receiver_tab(receiver_tab)

    # ========================================================
    # SENDER GUI
    # ========================================================

    def create_sender_tab(self, frame):

        # File

        tk.Label(
            frame,
            text="File to send:",
            font=("Arial", 11)
        ).grid(row=0, column=0, padx=15, pady=12, sticky="w")

        tk.Entry(
            frame,
            textvariable=self.file_path,
            width=90
        ).grid(row=0, column=1, padx=5, pady=12)

        tk.Button(
            frame,
            text="Browse",
            command=self.browse_file
        ).grid(row=0, column=2, padx=10)

        # Receiver IP

        tk.Label(
            frame,
            text="Receiver IP:",
            font=("Arial", 11)
        ).grid(row=1, column=0, padx=15, pady=8, sticky="w")

        tk.Entry(
            frame,
            textvariable=self.receiver_ip,
            width=25
        ).grid(row=1, column=1, sticky="w", padx=5)

        # Port

        tk.Label(
            frame,
            text="Port:",
            font=("Arial", 11)
        ).grid(row=2, column=0, padx=15, pady=8, sticky="w")

        tk.Entry(
            frame,
            textvariable=self.port,
            width=25
        ).grid(row=2, column=1, sticky="w", padx=5)

        # Packet size

        tk.Label(
            frame,
            text="Packet size (bytes):",
            font=("Arial", 11)
        ).grid(row=3, column=0, padx=15, pady=8, sticky="w")

        packet_box = ttk.Combobox(
            frame,
            textvariable=self.packet_size,
            values=["256", "512", "1024", "2048", "4096"],
            width=22,
            state="readonly"
        )

        packet_box.grid(row=3, column=1, sticky="w", padx=5)

        # CRC

        tk.Label(
            frame,
            text="CRC:",
            font=("Arial", 11)
        ).grid(row=4, column=0, padx=15, pady=8, sticky="w")

        crc_box = ttk.Combobox(
            frame,
            textvariable=self.crc_type,
            values=["CRC-32"],
            width=22,
            state="readonly"
        )

        crc_box.grid(row=4, column=1, sticky="w", padx=5)

        # Timeout

        tk.Label(
            frame,
            text="Timeout (seconds):",
            font=("Arial", 11)
        ).grid(row=5, column=0, padx=15, pady=8, sticky="w")

        tk.Entry(
            frame,
            textvariable=self.timeout,
            width=25
        ).grid(row=5, column=1, sticky="w", padx=5)

        # Packet loss

        tk.Label(
            frame,
            text="Simulated packet loss (%):",
            font=("Arial", 11)
        ).grid(row=6, column=0, padx=15, pady=8, sticky="w")

        tk.Entry(
            frame,
            textvariable=self.packet_loss,
            width=25
        ).grid(row=6, column=1, sticky="w", padx=5)

        # Buttons

        button_frame = tk.Frame(frame)
        button_frame.grid(
            row=7,
            column=0,
            columnspan=3,
            sticky="w",
            padx=15,
            pady=12
        )

        tk.Button(
            button_frame,
            text="Start Transfer",
            command=self.start_transfer,
            width=15
        ).pack(side="left", padx=5)

        tk.Button(
            button_frame,
            text="Clear Log",
            command=self.clear_sender_log,
            width=12
        ).pack(side="left", padx=5)

        # Progress bar

        self.sender_progress = ttk.Progressbar(
            frame,
            orient="horizontal",
            mode="determinate",
            maximum=100
        )

        self.sender_progress.grid(
            row=8,
            column=0,
            columnspan=3,
            sticky="ew",
            padx=15,
            pady=10
        )

        self.sender_progress_label = tk.Label(
            frame,
            text="Ready",
            font=("Arial", 10)
        )

        self.sender_progress_label.grid(
            row=9,
            column=0,
            columnspan=3,
            sticky="w",
            padx=15
        )

        # Log

        self.sender_log = tk.Text(
            frame,
            height=18,
            width=120,
            font=("Consolas", 10)
        )

        self.sender_log.grid(
            row=10,
            column=0,
            columnspan=3,
            sticky="nsew",
            padx=15,
            pady=10
        )

        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(10, weight=1)

    # ========================================================
    # RECEIVER GUI
    # ========================================================

    def create_receiver_tab(self, frame):

        # Listen port

        tk.Label(
            frame,
            text="Listen Port:",
            font=("Arial", 11)
        ).grid(
            row=0,
            column=0,
            padx=15,
            pady=15,
            sticky="w"
        )

        tk.Entry(
            frame,
            textvariable=self.listen_port,
            width=25
        ).grid(
            row=0,
            column=1,
            sticky="w"
        )

        # Save folder

        tk.Label(
            frame,
            text="Save folder:",
            font=("Arial", 11)
        ).grid(
            row=1,
            column=0,
            padx=15,
            pady=10,
            sticky="w"
        )

        tk.Entry(
            frame,
            textvariable=self.save_folder,
            width=90
        ).grid(
            row=1,
            column=1,
            padx=5,
            sticky="ew"
        )

        tk.Button(
            frame,
            text="Choose",
            command=self.choose_folder
        ).grid(
            row=1,
            column=2,
            padx=10
        )

        # Buttons

        button_frame = tk.Frame(frame)

        button_frame.grid(
            row=2,
            column=0,
            columnspan=3,
            sticky="w",
            padx=15,
            pady=12
        )

        tk.Button(
            button_frame,
            text="Start Receiver",
            command=self.start_receiver,
            width=15
        ).pack(side="left", padx=5)

        tk.Button(
            button_frame,
            text="Stop Receiver",
            command=self.stop_receiver,
            width=15
        ).pack(side="left", padx=5)

        tk.Button(
            button_frame,
            text="Clear Log",
            command=self.clear_receiver_log,
            width=12
        ).pack(side="left", padx=5)

        # Progress

        self.receiver_progress = ttk.Progressbar(
            frame,
            orient="horizontal",
            mode="determinate",
            maximum=100
        )

        self.receiver_progress.grid(
            row=3,
            column=0,
            columnspan=3,
            sticky="ew",
            padx=15,
            pady=10
        )

        self.receiver_progress_label = tk.Label(
            frame,
            text="No transfer yet.",
            font=("Arial", 10)
        )

        self.receiver_progress_label.grid(
            row=4,
            column=0,
            columnspan=3,
            sticky="w",
            padx=15
        )

        # Log

        self.receiver_log = tk.Text(
            frame,
            height=22,
            width=120,
            font=("Consolas", 10)
        )

        self.receiver_log.grid(
            row=5,
            column=0,
            columnspan=3,
            sticky="nsew",
            padx=15,
            pady=10
        )

        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(5, weight=1)

    # ========================================================
    # FILE BROWSER
    # ========================================================

    def browse_file(self):

        path = filedialog.askopenfilename()

        if path:
            self.file_path.set(path)

    # ========================================================

    def choose_folder(self):

        folder = filedialog.askdirectory()

        if folder:
            self.save_folder.set(folder)

    # ========================================================
    # LOG FUNCTIONS
    # ========================================================

    def sender_print(self, text):

        self.root.after(
            0,
            lambda: self.sender_log.insert(
                tk.END,
                text + "\n"
            )
        )

        self.root.after(
            0,
            lambda: self.sender_log.see(tk.END)
        )

    # ========================================================

    def receiver_print(self, text):

        self.root.after(
            0,
            lambda: self.receiver_log.insert(
                tk.END,
                text + "\n"
            )
        )

        self.root.after(
            0,
            lambda: self.receiver_log.see(tk.END)
        )

    # ========================================================

    def clear_sender_log(self):

        self.sender_log.delete("1.0", tk.END)

    # ========================================================

    def clear_receiver_log(self):

        self.receiver_log.delete("1.0", tk.END)

    # ========================================================
    # START RECEIVER
    # ========================================================

    def start_receiver(self):

        if self.receiver_running:
            self.receiver_print("[SERVER] Receiver is already running.")
            return

        try:
            port = int(self.listen_port.get())

        except ValueError:
            messagebox.showerror(
                "Error",
                "Invalid port number."
            )
            return

        folder = self.save_folder.get()

        os.makedirs(folder, exist_ok=True)

        self.receiver_running = True

        thread = threading.Thread(
            target=self.receiver_loop,
            args=(port, folder),
            daemon=True
        )

        thread.start()

    # ========================================================

    def stop_receiver(self):

        self.receiver_running = False

        if self.receiver_socket:

            try:
                self.receiver_socket.close()
            except:
                pass

            self.receiver_socket = None

        self.receiver_print("[SERVER] Receiver stopped.")

    # ========================================================
    # RECEIVER LOOP
    # ========================================================

    def receiver_loop(self, port, folder):

        sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM
        )

        self.receiver_socket = sock

        try:

            sock.setsockopt(
                socket.SOL_SOCKET,
                socket.SO_REUSEADDR,
                1
            )

            sock.bind(
                ("127.0.0.1", port)
            )

            sock.settimeout(1)

            self.receiver_print(
                f"[SERVER] Listening on UDP port {port}"
            )

            while self.receiver_running:

                try:

                    data, address = sock.recvfrom(65535)

                except socket.timeout:
                    continue

                except OSError:
                    break

                try:

                    message = data.decode()

                    # --------------------------------------
                    # START MESSAGE
                    # --------------------------------------

                    if message.startswith("START|"):

                        parts = message.split("|", 2)

                        total_packets = int(parts[1])
                        filename = parts[2]

                        self.receiver_print(
                            f"[META] Receiving: {filename} | "
                            f"packets={total_packets}"
                        )

                        received_packets = {}
                        start_time = time.time()

                        while len(received_packets) < total_packets:

                            try:

                                packet_data, packet_address = sock.recvfrom(
                                    65535
                                )

                            except socket.timeout:
                                continue

                            packet_text = packet_data.decode()

                            packet_parts = packet_text.split("|", 3)

                            if len(packet_parts) != 4:
                                continue

                            packet_type = packet_parts[0]

                            if packet_type != "DATA":
                                continue

                            packet_number = int(packet_parts[1])

                            received_crc = int(packet_parts[2])

                            encoded_message = packet_parts[3]

                            try:

                                chunk = base64.b64decode(
                                    encoded_message.encode()
                                )

                            except:
                                continue

                            # ----------------------------------
                            # CRC CHECK
                            # ----------------------------------

                            calculated_crc = zlib.crc32(chunk)

                            if calculated_crc != received_crc:

                                self.receiver_print(
                                    f"[CRC ERROR] Packet "
                                    f"{packet_number} discarded"
                                )

                                continue

                            self.receiver_print(
                                f"[RECV] Packet "
                                f"{packet_number + 1}/{total_packets}"
                            )

                            # ----------------------------------
                            # DUPLICATE CHECK
                            # ----------------------------------

                            if packet_number not in received_packets:

                                received_packets[
                                    packet_number
                                ] = chunk

                            else:

                                self.receiver_print(
                                    f"[DUPLICATE] Packet "
                                    f"{packet_number}"
                                )

                            # ----------------------------------
                            # SEND ACK
                            # ----------------------------------

                            ack = f"ACK|{packet_number}"

                            sock.sendto(
                                ack.encode(),
                                packet_address
                            )

                            self.receiver_print(
                                f"[ACK] Packet {packet_number}"
                            )

                            # Progress

                            progress = (
                                len(received_packets)
                                / total_packets
                            ) * 100

                            self.root.after(
                                0,
                                lambda p=progress: self.update_receiver_progress(
                                    p,
                                    len(received_packets),
                                    total_packets
                                )
                            )

                        # --------------------------------------
                        # RECONSTRUCT FILE
                        # --------------------------------------

                        output_path = os.path.join(
                            folder,
                            "received_" + filename
                        )

                        with open(
                            output_path,
                            "wb"
                        ) as output_file:

                            for i in range(total_packets):

                                output_file.write(
                                    received_packets[i]
                                )

                        elapsed = time.time() - start_time

                        file_size = os.path.getsize(
                            output_path
                        )

                        speed = 0

                        if elapsed > 0:
                            speed = (
                                file_size / 1024
                            ) / elapsed

                        self.receiver_print(
                            f"[SUCCESS] File reconstructed: "
                            f"{output_path}"
                        )

                        self.receiver_print(
                            f"[STATS] {file_size} bytes | "
                            f"{elapsed:.2f}s | "
                            f"{speed:.1f} KB/s"
                        )

                        self.root.after(
                            0,
                            lambda: self.update_receiver_progress(
                                100,
                                total_packets,
                                total_packets
                            )
                        )

                except Exception as e:

                    self.receiver_print(
                        f"[ERROR] {e}"
                    )

        finally:

            try:
                sock.close()
            except:
                pass

            self.receiver_socket = None

    # ========================================================
    # RECEIVER PROGRESS
    # ========================================================

    def update_receiver_progress(
        self,
        progress,
        received,
        total
    ):

        self.receiver_progress["value"] = progress

        self.receiver_progress_label.config(
            text=f"Packets received: {received}/{total}"
        )

    # ========================================================
    # START TRANSFER
    # ========================================================

    def start_transfer(self):

        path = self.file_path.get()

        if not path:

            messagebox.showerror(
                "Error",
                "Please select a file."
            )

            return

        if not os.path.exists(path):

            messagebox.showerror(
                "Error",
                "Selected file does not exist."
            )

            return

        thread = threading.Thread(
            target=self.sender_loop,
            args=(path,),
            daemon=True
        )

        thread.start()

    # ========================================================
    # SENDER LOOP
    # ========================================================

    def sender_loop(self, path):

        try:

            ip = self.receiver_ip.get()

            port = int(self.port.get())

            packet_size = int(
                self.packet_size.get()
            )

            timeout = float(
                self.timeout.get()
            )

            loss_percentage = float(
                self.packet_loss.get()
            )

            # ----------------------------------------------
            # READ FILE
            # ----------------------------------------------

            with open(path, "rb") as file:

                file_data = file.read()

            filename = os.path.basename(path)

            # ----------------------------------------------
            # SPLIT FILE INTO PACKETS
            # ----------------------------------------------

            chunks = []

            for i in range(
                0,
                len(file_data),
                packet_size
            ):

                chunks.append(
                    file_data[
                        i:i + packet_size
                    ]
                )

            total_packets = len(chunks)

            self.sender_print(
                f"[META] File: {filename}"
            )

            self.sender_print(
                f"[META] Size: {len(file_data)} bytes"
            )

            self.sender_print(
                f"[META] Packets: {total_packets}"
            )

            # ----------------------------------------------
            # CREATE UDP SOCKET
            # ----------------------------------------------

            sender = socket.socket(
                socket.AF_INET,
                socket.SOCK_DGRAM
            )

            sender.settimeout(timeout)

            # ----------------------------------------------
            # START MESSAGE
            # ----------------------------------------------

            start_message = (
                "START|"
                + str(total_packets)
                + "|"
                + filename
            )

            sender.sendto(
                start_message.encode(),
                (ip, port)
            )

            self.sender_print(
                f"[START] {start_message}"
            )

            start_time = time.time()

            retransmissions = 0

            # ----------------------------------------------
            # SEND EACH PACKET
            # ----------------------------------------------

            for packet_number, chunk in enumerate(chunks):

                crc = zlib.crc32(chunk)

                encoded_chunk = base64.b64encode(
                    chunk
                ).decode()

                packet = (
                    "DATA|"
                    + str(packet_number)
                    + "|"
                    + str(crc)
                    + "|"
                    + encoded_chunk
                )

                while True:

                    # --------------------------------------
                    # SIMULATE PACKET LOSS
                    # --------------------------------------

                    lost = (
                        random.random()
                        < loss_percentage / 100
                    )

                    if lost:

                        self.sender_print(
                            f"[SIMULATED LOSS] "
                            f"Packet {packet_number}"
                        )

                    else:

                        sender.sendto(
                            packet.encode(),
                            (ip, port)
                        )

                        self.sender_print(
                            f"[SEND] Packet "
                            f"{packet_number + 1}/"
                            f"{total_packets}"
                        )

                    # --------------------------------------
                    # WAIT FOR ACK
                    # --------------------------------------

                    try:

                        ack_data, address = sender.recvfrom(
                            1024
                        )

                        ack = ack_data.decode()

                        expected_ack = (
                            "ACK|"
                            + str(packet_number)
                        )

                        if ack == expected_ack:

                            self.sender_print(
                                f"[ACK] Packet "
                                f"{packet_number}"
                            )

                            break

                    except socket.timeout:

                        retransmissions += 1

                        self.sender_print(
                            f"[TIMEOUT] Packet "
                            f"{packet_number}"
                        )

                        self.sender_print(
                            f"[RETRANSMIT] Packet "
                            f"{packet_number}"
                        )

                    except ConnectionResetError:

                        retransmissions += 1

                        self.sender_print(
                            f"[CONNECTION RESET] "
                            f"Retransmitting packet "
                            f"{packet_number}"
                        )

                    # --------------------------------------
                    # UPDATE PROGRESS
                    # --------------------------------------

                    progress = (
                        packet_number
                        / total_packets
                    ) * 100

                    self.root.after(
                        0,
                        lambda p=progress,
                        n=packet_number,
                        t=total_packets:
                        self.update_sender_progress(
                            p,
                            n,
                            t
                        )
                    )

                # Update after successful ACK

                progress = (
                    (packet_number + 1)
                    / total_packets
                ) * 100

                self.root.after(
                    0,
                    lambda p=progress,
                    n=packet_number + 1,
                    t=total_packets:
                    self.update_sender_progress(
                        p,
                        n,
                        t
                    )
                )

            # ----------------------------------------------
            # FINISHED
            # ----------------------------------------------

            elapsed = time.time() - start_time

            speed = 0

            if elapsed > 0:

                speed = (
                    len(file_data) / 1024
                ) / elapsed

            self.sender_print(
                "[SUCCESS] Transfer completed"
            )

            self.sender_print(
                f"[STATS] Packets={total_packets} | "
                f"Retransmissions={retransmissions} | "
                f"Time={elapsed:.2f}s | "
                f"Speed={speed:.1f} KB/s"
            )

            self.root.after(
                0,
                lambda: self.update_sender_progress(
                    100,
                    total_packets,
                    total_packets
                )
            )

            sender.close()

        except Exception as e:

            self.sender_print(
                f"[ERROR] {e}"
            )

    # ========================================================
    # SENDER PROGRESS
    # ========================================================

    def update_sender_progress(
        self,
        progress,
        sent,
        total
    ):

        self.sender_progress["value"] = progress

        self.sender_progress_label.config(
            text=f"Packets sent: {sent}/{total}"
        )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    root = tk.Tk()

    app = ReliableUDPApp(root)

    root.mainloop()