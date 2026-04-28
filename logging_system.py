import logging
from datetime import date
import os

# Ensure directories exist so FileHandler doesn't crash
os.makedirs('logs/client', exist_ok=True)
os.makedirs('logs/server', exist_ok=True)

today = date.today()
log_format = logging.Formatter('%(name)s - %(levelname)s - %(message)s')

# --- CLIENT LOGGER ---
logger = logging.getLogger("clientLogger")
logger.propagate = False
logger.setLevel(logging.DEBUG)

client_console = logging.StreamHandler()
client_file = logging.FileHandler(f'logs/client/{today}.log')

client_console.setLevel(logging.WARNING)
client_file.setLevel(logging.DEBUG)

client_console.setFormatter(log_format)
client_file.setFormatter(log_format)

logger.addHandler(client_console)
logger.addHandler(client_file)

# --- SERVER LOGGER (Added) ---
server_logger = logging.getLogger("serverLogger")
server_logger.propagate = False
server_logger.setLevel(logging.DEBUG)

# Separate handlers for the server
server_console = logging.StreamHandler()
server_file = logging.FileHandler(f'logs/server/{today}.log')

server_console.setLevel(logging.INFO) # Server usually wants INFO+ in console
server_file.setLevel(logging.DEBUG)

server_console.setFormatter(log_format)
server_file.setFormatter(log_format)

server_logger.addHandler(server_console)
server_logger.addHandler(server_file)

# --- USAGE ---
logger.info("Client: Processing request...")
server_logger.info("Server: MCP Connection established.")
server_logger.error("Server: Failed to reach tool provider.")