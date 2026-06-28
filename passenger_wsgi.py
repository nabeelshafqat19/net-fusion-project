import os
import sys

# Ensure the application directory is on the Python path for cPanel/Passenger.
sys.path.insert(0, os.path.dirname(__file__))

from main import app as application
