import socket
import zlib
import math

sender = socket.socket(
    socket.AF_INET,
    socket.SOCK_DGRAM
)

sender.settimeout(1)

file = open("sample.txt", "r")

message = file.read()

file.close()

packet_size = 5

total_packets = math.ceil(len(message) / packet_size)

start_message = "START|" + str(total_packets) + "|sample.txt"

sender.sendto(
    start_message.encode(),
    ("127.0.0.1", 9000)
)

print("Sent:", start_message)


for i in range(0, len(message), packet_size):

    packet = message[i:i + packet_size]

    packet_number = str(i // packet_size)

    crc = zlib.crc32(packet.encode())

    packet_data = packet_number + "|" + str(crc) + "|" + packet


    while True:

        sender.sendto(
            packet_data.encode(),
            ("127.0.0.1", 9000)
        )

        print("Sent:", packet_data)

        try:

            ack_data, address = sender.recvfrom(1024)

            ack = ack_data.decode()

            print("Received:", ack)

            if ack == "ACK|" + str(i // packet_size):
                break

        except socket.timeout:

            print(
                "Timeout! Retransmitting packet",
                i // packet_size
            )


sender.close()

print("File sent successfully!")