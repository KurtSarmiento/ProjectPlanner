import os
from dotenv import load_dotenv
from app import create_app
from flask_wtf.csrf import CSRFProtect

# Load environment variables from .env file
load_dotenv()

app = create_app()

# Set the secret key from an environment variable
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')
print("Secret Key:", app.config['SECRET_KEY'])

# Check if secret key is set
if not app.config['SECRET_KEY']:
    raise ValueError("No FLASK_SECRET_KEY set. Please set the FLASK_SECRET_KEY environment variable or add it to .env file.")

csrf = CSRFProtect(app)

if __name__ == '__main__':
    app.run(debug=True)