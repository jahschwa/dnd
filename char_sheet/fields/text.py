from collections import OrderedDict

from dnd.char_sheet.fields import Field

###############################################################################
# Text class
#   - supports newlines via the 2 literal characters '\n'
###############################################################################

class Text(Field):

  FIELDS = OrderedDict([
      ('name',str),
      ('text',str),
  ])

  # @param name (str)
  # @param text (str)
  def __init__(self,name,text):

    self.name = name
    self.set(text)

  # @param text (str)
  def set(self,text):

    # we store newlines internally as '\' + 'n' for ease of saving
    text = text or ''
    self.text = text.strip().replace('\n','\\n')

  # @return (str) truncated to 50 characters and replacing newlines with '|'
  def __str__(self):

    text = '[BLANK]' if not self.text else self.text.replace('\\n',' | ')
    ellip = ''
    if len(text)>50:
      (text,ellip) = (text[:50],'...')
    return '%s: %s%s' % (self.name,text,ellip)

  # @return (str) full text with real newlines
  def str_all(self):

    text = '[BLANK]' if not self.text else self.text
    return '--- %s\n%s' % (self.name,text.replace('\\n','\n'))
