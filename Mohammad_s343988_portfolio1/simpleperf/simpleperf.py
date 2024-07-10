# Import necessary modules
import argparse
import socket
import time
import threading
from concurrent.futures import ThreadPoolExecutor

'''
create_arg_parser()

Description: Creates an ArgumentParser object for parsing command line arguments.
Arguments: None
Returns: The ArgumentParser object.
'''
# Create argument parser function
def create_arg_parser():
    #Instantiate the ArgumentParser object
    parser = argparse.ArgumentParser(description="Simpleperf client and server mode.")
    #Add arguments to the parser
    parser.add_argument('-s', '--server', action='store_true', help='Enable server mode')
    parser.add_argument('-b', '--bind', type=str, default='127.0.0.1', help='IP address for server binding')
    parser.add_argument('-p', '--port', type=int, default=8080, help='Port number used by both server and client')
    parser.add_argument('-f', '--format', type=str, default='MB', help='Output summary format (B, KB, MB) for server and client')
    parser.add_argument('-c', '--client', action='store_true', help='Activate client mode')
    parser.add_argument('-I', '--serverip', type=str, default='127.0.0.1', help='IP address of the target server')
    parser.add_argument('-t', '--time', type=validate_positive, default=None, help='Time duration for data transmission in seconds')
    parser.add_argument('-n', '--num', type=parse_data_size, default=None, help='Amount of data to send (B, KB, MB)')
    parser.add_argument('-i', '--interval', type=validate_positive, default=None, help='Interval for printing statistics (x seconds, x > 0)')
    parser.add_argument('-P', '--connections', type=validate_positive, default=1, help='Number of parallel connections')
    # Return the parser object
    return parser
    

'''
server_mode(bind_ip, port, format)

Description: Runs the program in server mode. Listens for incoming client connections and processes the received data.
Arguments:
bind_ip (str): The IP address to bind the server to.
port (int): The port number to listen for incoming connections.
format (str): The output summary format ('B', 'KB', or 'MB').
Returns: None
'''
# Define the server_mode function
def server_mode(bind_ip, port, format):
    #Define the process_client function
    def process_client(connection, client_addr, format):
        #Get the local IP and port of the connection
        local_ip, local_port = connection.getsockname()
        #Print the connection details
        print(f"A simpleperf client with {client_addr[0]}:{client_addr[1]} is connected with {local_ip}:{local_port}")

        #Record the start time
        start_time = time.time()
        #Initialize the total received data counter
        total_received = 0

        # Continuously process incoming data
        while True:
            #Receive a data chunk (up to 1000 bytes)
            data_chunk = connection.recv(1000)
            #Add the length of the received data chunk to the total_received counter
            total_received += len(data_chunk)
            #Check if the received data is "BYE" (indicating the end of transmission)
            if data_chunk == b'BYE':
                #Send an acknowledgment to the client
                connection.sendall(b'ACK: BYE')
                #Break out of the loop
                break

        # Calculate the elapsed time and the data rate
        elapsed_time = time.time() - start_time
        data_rate = total_received / elapsed_time

        #Convert the total_received data to the desired format
        if format == 'KB':
            total_received /= 1000
        elif format == 'MB':
            total_received /= (1000 * 1000)

        #Calculate the data rate in Mbps
        data_rate_mbps = (data_rate * 8) / (1000 * 1000)
        # Print the results
        print(f"ID\t\t\tInterval\tReceived\tRate")
        print(f"{client_addr}\t0.0 - {elapsed_time:.1f}\t{total_received:.1f} {format}\t{data_rate_mbps:.1f} Mbps")
        print("-------------------------------------------------")

    # Define the accept_client function
    def accept_client(server_socket, format):
        #Continuously accept new clients
        while True:
            #Accept a new client connection
            connection, client_addr = server_socket.accept()
            #Create a new thread to handle the client
            client_handler = threading.Thread(target=process_client, args=(connection, client_addr, format))
            #Start the client handler thread
            client_handler.start()

    #Create the server socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        #Bind the server socket to the specified IP and port
        server_socket.bind((bind_ip, port))
        #Start listening for incoming connections
        server_socket.listen()
        #Print the server status
        print("-------------------------------------------------")
        print(f"A simpleperf server is listening on port {port}")
        print("-------------------------------------------------")

        #Accept and  process clients
        accept_client(server_socket, format)


'''
client_mode(server_ip, port, num_bytes, duration, format, interval, connection_id)

Description: Runs the program in client mode. Connects to the server and sends data.
Arguments:
server_ip (str): The IP address of the target server.
port (int): The port number of the target server.
num_bytes (int): The amount of data to send in bytes, or None for unlimited data.
duration (int): The time duration for data transmission in seconds, or None for unlimited duration.
format (str): The output summary format ('B', 'KB', or 'MB').
interval (int): The interval for printing statistics in seconds, or None for no interval printing.
connection_id (int): The ID of the connection for multi-connection mode.
Returns: None
'''
     
# Function to run the client mode
def client_mode(server_ip, port, num_bytes, duration, format, interval, connection_id):
    #Function to send data from  the client to the server
    def send_data(client_socket, num_bytes, end_time, total_sent, prev_total_sent):
        #Initialize the last print time
        last_print_time = time.time()
        # Continue sending data until the requested number of bytes is sent or the specified duration is reached
        while (num_bytes is not None and total_sent < num_bytes) or (end_time is not None and time.time() < end_time):
            #Calculate the number of bytes to send  in this iteration
            bytes_to_send = min(1000, num_bytes - total_sent) if num_bytes is not None else 1000
            # Send the data to the server
            client_socket.sendall(b'0' * bytes_to_send)
            # Update the total number of bytes sent
            total_sent += bytes_to_send
            #If interval is set and enough time has  passed, display interval statistics
            if interval is not None and time.time() - last_print_time >= interval:
                display_interval_stats(connection_id, local_ip, local_port, start_time, prev_total_sent, format, interval, total_sent)
                # Update the last print time and previous total sent
                last_print_time = time.time()
                prev_total_sent = total_sent
        return total_sent, prev_total_sent

    #Create a socket for  the client
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        try:
            #Print information about the client and  the server it is connecting to
            print("-------------------------------------------------")
            print(f"A simpleperf client ({connection_id}) connecting to server {server_ip}, port {port}")
            print("-------------------------------------------------")
            #Connect to the server
            client_socket.connect((server_ip, port))
        except socket.error as e:
            #Print an error message if unable to connect to the server
            print(f"Error: Unable to connect to server {server_ip}:{port}. Check the server address and port number.")
            return

        #Get the local IP and port for the client
        local_ip, local_port = client_socket.getsockname()
        #Print connection information
        print(f"Client ({connection_id}) connected with {server_ip} port {port}")

        #Initialize various variables for sending data
        start_time = time.time()
        if interval is not None:
            last_print_time = start_time

        total_sent, prev_total_sent = 0, 0
        #Send a start message to the server
        start_msg = f"START {start_time}\n"
        client_socket.sendall(start_msg.encode())

        #Send data to the server
        total_sent, prev_total_sent = send_data(client_socket, num_bytes, start_time + duration if duration is not None else None, total_sent, prev_total_sent)

        #Wait for 0.5 second and send aBYE message to the server
        #This short delay can help ensure that the server has enough time to process thepreviously sent data before receiving the "BYE" message .
        time.sleep(0.5)
        client_socket.sendall(b'BYE')
        # Receive a response from the server
        response = client_socket.recv(1000)
        # If the server acknowledges the BYE message, print final statistics
        if response == b'ACK: BYE':
            elapsed_time = time.time() - start_time
            data_rate = total_sent / elapsed_time

            #Convert the total_sent to the appropriate format (KB or MB)
            if format == 'KB':
                total_sent /= 1000
            elif format == 'MB':
                total_sent /= 1000000
                
            #Calculate the data rate in Mbps
            data_rate_mbps = (data_rate * 8) / (1000 * 1000)              
            #Print the final statistics
            print("-------------------------------------------------")
            print(f"ID\t\tInterval\tTransfer\tBandwidth")
            print(f"{local_ip}:{local_port}\t0.0-{elapsed_time:.1f}s\t{total_sent:.1f} {format}\t{data_rate_mbps:.1f} Mbps")
            print("-------------------------------------------------")
    
'''
display_interval_stats(connection_id, local_ip, local_port, start_time, prev_total_sent, format, interval, total_sent)

Description: Displays the interval statistics for data transmission during client mode.
Arguments:
connection_id (int): The ID of the connection for multi-connection mode.
local_ip (str): The local IP address of the client.
local_port (int): The local port  number of the client.
start_time (float): The time when the data transmission started.
prev_total_sent (int): The total amount of data sent before the current interval. 
format (str ):The output summary format (B,KB, or MB).
interval (int): The interval for printing statistics in seconds.
total_sent (int): The total amount of data sent so far.
Returns:None
'''    
# Function to display interval statistics
def display_interval_stats(connection_id, local_ip, local_port, start_time, prev_total_sent, format, interval, total_sent):
    #Calculate the elapsed time since the start of the transfer
    elapsed_time = time.time() - start_time
    #Calculate the amount of data sent in this interval
    interval_sent = total_sent - prev_total_sent
    #Calculate the data transfer rate for this interval
    interval_data_rate = interval_sent / interval

    #Convert interval_sent to the correct format (KB or MB)
    if format == 'KB':
        interval_sent /= 1000
    elif format == 'MB':
        interval_sent /= 1000000
        
    # Calculate the data transfer rate in Mbps
    data_rate_mbps = (interval_data_rate * 8) / (1000 * 1000)
    # Print the statistics for this interval
    print(f"{local_ip}:{local_port}\t{elapsed_time - interval:.1f}-{elapsed_time:.1f}s\t{interval_sent:.1f} {format}\t{data_rate_mbps:.1f} Mbps") 

'''
parse_data_size(value)

Description: Parses the data size from a string and returns it as an integer in bytes.
Arguments:
value (str): A string  representing the data size.
Returns: The data size as an integer in bytes.
Raises:ValueError if the input format is incorrect.
'''    
# Function to parse data size
def parse_data_size(value):
    # Define units for KB and MB
    units = {'KB': 1000, 'MB': 1000000}
    
    # Check if the last two characters of the value are in the units dictionary
    if value[-2:] in units:
        # Convert the value to an integer and multiply by the appropriate unit
        return int(value[:-2]) * units[value[-2:]]
    
    #check if the last character of the value is "B"
    elif value[-1:] == "B":
        #Convert the value to an integer (removing the "B" character)
        return int(value[:-1])
    
    #Raise an error if the format is invalid
    else:
        raise ValueError("Invalid format for --num. Use B, KB, or MB.")

'''
validate_positive(value)

Description: Validates that the input value is a positive integer.
Arguments:
value ( str):A string representing an integer value.
Returns: The input value as an integer.
Raises: ValueError if the input value is not a positive integer. 
'''
# Function to validate positive values
def validate_positive(value):
    #Convert the value to an integer
    int_value = int(value)
    
    #Check if the integer value is less than or equal to 0
    if int_value <= 0:
        # Raise an error if the value is not a valid positive value
        raise ValueError(f"{value} is not a valid positive value")
    
    #Return the integer value if it's a valid positive value
    return int_value


'''
simpleperf_main(args)

Description: The main function of the simpleperf program. Runs the program in either server or client mode based on the input arguments.
Arguments:
args ( Namespace): A Namespace object containing  the parsed command line arguments.
Returns: None
Raises: ValueError if neither server nor client mode is specified.
'''
# Main function that runs simpleperf
def simpleperf_main(args):
    #Check if neither  server nor client mode is specified
    if not args.server and not args.client:
        print("Error: You need to operate in either server or client mode.")
        return

    #If server mode is specified
    if args.server:
        server_mode(args.bind, args.port, args.format)
    #If client mode is specified
    elif args.client:
        #If neither num_bytes nor duration is specified, set default duration.
        if args.num is None and args.time is None:
            args.time = 25
        #If both num_bytes and duration are specified, raise error
        elif args.num is not None and args.time is not None:
            print('Error: you cannot use both --num and --time at the same time.')
            return

        #Create a ThreadPoolExecutor to manage multiple connections .
        with ThreadPoolExecutor(max_workers=args.connections) as executor:
            #Submit client mode  tasks to the executor
            futures = [executor.submit(client_mode, args.serverip, args.port, args.num, args.time, args.format, args.interval, i + 1) for i in range(args.connections)]

            #Wait for all tasks to complete.
            for future in futures:
                future.result()
    else:
        raise ValueError("Must specify either --server or --client mode")
  
'''
run_simpleperf()

Description: The entry point of the simpleperf program. Creates the argument parser, 
parses the command line arguments  and calls the main function.
Arguments: None
Returns: None
'''  
#Function to run simpleperf
def run_simpleperf():
    #Create argument parser
    parser = create_arg_parser()
    #parse command line arguments
    args = parser.parse_args()
    #Run the main simpleperf function
    simpleperf_main(args)

#If this script is run as the main program  execute the run_simpleperf function.
if __name__ == "__main__":
    run_simpleperf()
        
 
 