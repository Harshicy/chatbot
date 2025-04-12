#!/bin/bash
pip install -r requirements.txt
python -c "import nltk; nltk.download('punkt', download_dir='./nltk_data'); nltk.download('wordnet', download_dir='./nltk_data')"