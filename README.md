ValueVista Mini

ValueVista Mini is a simple product-comparison website made with Flask and MongoDB.

Features

Browse electronic products

Filter and sort products

View product details and specifications

Compare prices from different stores

Compare up to three products

Register and log in

Technology

Python and Flask

MongoDB and PyMongo

HTML, CSS, JavaScript, and Jinja

Run the project

git clone https://github.com/yashsantoshchougule/mongodb-assignment.git
cd mongodb-assignment
py -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
py -m pip install -r requirements.txt
Copy-Item .env.example .env
py seed_data.py
py app.py

Open http://127.0.0.1:5000 in your browser.

Make sure MongoDB is running before starting the project.

Database

Database name: valuevista_mini

Collections:

products

categories

platforms

users

The project uses manually prepared demonstration data, not live ecommerce data.
