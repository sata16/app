import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'very_hard_secret_key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql://postgres:12345@localhost/parking_management'
    SQLALCHEMY_TRACK_MODIFICATIONS = False