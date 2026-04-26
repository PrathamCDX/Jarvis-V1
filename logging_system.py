import logging
from datetime import date

# Get the current local date
today = date.today()
# 1. Create a custom logger
logger = logging.getLogger("clientLogger")
logger.setLevel(logging.DEBUG)  # Capture everything

# 2. Create handlers
console_handler = logging.StreamHandler()
file_handler = logging.FileHandler('logs/client/'+ str(today )+ '.log')

# 3. Set levels for handlers
console_handler.setLevel(logging.WARNING) # Only show warnings+ in console
file_handler.setLevel(logging.DEBUG)      # Save everything to file

# 4. Create a format and add it to handlers
log_format = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(log_format)
file_handler.setFormatter(log_format)

# 5. Add handlers to the logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Usage
logger.info("This is an info message (saved to file)")