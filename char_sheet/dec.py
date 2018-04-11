# decorator used for commands that accept an arbitrary number of arguments
def arbargs(func):
  
  func._arbargs = True
  return func