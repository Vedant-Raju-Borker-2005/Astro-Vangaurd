import sys

try:
    import main
    print("Imports completely successful!")
except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)
sys.exit(0)
