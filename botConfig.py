
import os

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Set the current working directory to the script's directory
os.chdir(script_dir)

# Set sandbox_mode to True for Sandbox/Demo, and False for Live
sandbox_mode = True

# Demo mode API key and secret
demo_apiKey = 'mj3qywcgs0aLlspJ8NrdYf72mtGqhrfqkg9UuybjruvA0CdrhwHEyntcU3MHQFlv'
demo_secret = 'P6HRA89M5yTidrLGS8dNp7Ko61WDMhuLHovVQY22HF3m4aHPOsm6diDMsqCoIOnn'

# Live mode API key and secret
live_apiKey = 'omar'
live_secret = 'abbas'

if sandbox_mode:
    mode = 'Sandbox/Demo'
else:
    mode = 'Live'

