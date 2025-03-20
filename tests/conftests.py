# tests/conftest.py
import pytest
import sys
import os

# Ajout du chemin du projet pour les imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))