import sys
sys.path.insert(0, r"D:\AI_Girlfriend\skills\shared")
from waitress import serve
from embedding_server import app
serve(app, host="127.0.0.1", port=9999, threads=2)
