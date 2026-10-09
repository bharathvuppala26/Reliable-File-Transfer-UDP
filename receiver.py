import socket
import zlib

receiver = socket.socket(
    socket.AF_INET,
    socket.SOCK_DGRAM
)

receiver.bind(("127.0.0.1", 9000))

print("Receiver waiting...")


# Receive START message

data, address = receiver.recvfrom(1024)

start_message = data.decode()

print("Received:", start_message)

parts = start_message.split("|")

total_packets = int(parts[1])

filename = parts[2]

print("Total packets:", total_packets)
print("Filename:", filename)


received_packets = set()

received_data = {}

# Used only for our packet-loss demonstration
packet_5_dropped = False


while len(received_packets) < total_packets:

    data, address = receiver.recvfrom(1024)

    packet = data.decode()

    packet_number, received_crc, message = packet.split("|", 2)

    packet_number = int(packet_number)

    print(
        "Received Packet",
        packet_number,
        ":",
        message
    )


    # --------------------------------
    # INTENTIONAL PACKET LOSS
    # --------------------------------

    if packet_number == 5 and packet_5_dropped == False:

        print("!!! INTENTIONALLY DROPPING PACKET 5 !!!")

        packet_5_dropped = True

        continue


    # --------------------------------
    # CRC CHECK
    # --------------------------------

    calculated_crc = zlib.crc32(message.encode())

    if calculated_crc == int(received_crc):

        print("CRC OK")


        # --------------------------------
        # DUPLICATE CHECK
        # --------------------------------

        if packet_number not in received_packets:

            received_packets.add(packet_number)

            received_data[packet_number] = message

            print("New packet accepted")

        else:

            print("Duplicate packet")


        # --------------------------------
        # SEND ACK
        # --------------------------------

        ack = f"ACK|{packet_number}"

        receiver.sendto(
            ack.encode(),
            address
        )

        print("Sent:", ack)


    else:

        print("CRC ERROR - Packet discarded")


print("All packets received!")


# --------------------------------
# CREATE RECEIVED FILE
# --------------------------------

file = open("received_" + filename, "w")

for i in range(total_packets):

    file.write(received_data[i])

file.close()

print("File received successfully!")

receiver.close()