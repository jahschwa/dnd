import os,sys

current = os.path.abspath(os.path.dirname(__file__))
char_sheet = os.path.dirname(current)
dnd = os.path.dirname(char_sheet)
sys.path.insert(0,dnd)
