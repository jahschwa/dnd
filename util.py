# @param s (str)
# @param chunk (int) [3] number of characters per group
# @param sep (str) [','] the character to place between groups
# @param left (bool) [False] start counting from the left instead of the right
def group(s,chunk=3,sep=',',left=False):
  """group a string; by default, does thousands-separation"""

  s = str(s)
  new = ''
  i = 0
  offset = 0 if left else (chunk-len(s)%chunk)%chunk
  while i<len(s):
    if (i+offset)%chunk==0:
      new += sep
    new += s[i]
    i += 1
  return new.strip(sep)