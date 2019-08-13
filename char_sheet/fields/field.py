# Field hierarchy:
#   Stat
#     PathfinderSkill
#   Bonus
#   Effect
#   Duration
#   Item
#     Weapon
#     Armor
#   Dice
#   Ability
#     Spell
#   Event
#   Text

# [TODO] add a "Function" class? for stats?
# [TODO] Item
# [TODO] Weapon
# [TODO] Armor
# [TODO] Ability
# [TODO] Spell
# [TODO] Event

import inspect
import time
from collections import OrderedDict
from functools import reduce

from dnd.duration import Duration
from dnd.char_sheet.errors import *

###############################################################################
# Field class
#   - parent class for objects used by Characters
#   - setting the FIELDS dict enables saving and loading in child classes
#   - child classes should consider overriding everything except load/save
###############################################################################

class Field(object):

  # this should be an OrderedDict of name:type where typ is one of:
  #   str - no action taken
  #   None - we will always pass None ignoring actual content
  #   list - splits on commas
  #   bool - compares against the string 'True'
  FIELDS = {}

  # parse an argument list into a (sub-classed) Field object
  # @param fields (list of str) arguments to pass to the object __init__
  # @return (object) an instance a Field sub-class
  @classmethod
  def load(cls, fields):

    sig = inspect.getfullargspec(cls.__init__)
    required = len(sig.args) - 1 - len(sig.defaults or [])
    if len(fields) < required:
      raise ValueError('need %s args for %s but got %s' % (required, cls.__name__, len(fields)))

    i = 0
    parsed = []
    for typ in cls.FIELDS.values():
      result = None
      if typ is not None:
        val = fields[i]
        if typ is list:
          result = val.split(',')
        elif typ is bool:
          result = val=='True'
        else:
          result = typ(val)
        i += 1
      parsed.append(result)
      if i >= len(fields):
        break
    return cls(*parsed)

  # calls str() on each field (or on each item if the field is a list)
  # @return (list of str) fields to save
  def save(self):

    result = []
    for (field,typ) in self.FIELDS.items():
      if typ is None:
        continue
      val = getattr(self,field)
      if isinstance(val,list):
        result.append(','.join([str(x) for x in val]))
      else:
        result.append(str(val))
    return result

  # create variables and establish dependencies in a Character
  # @param (Character) the character to plug into
  def plug(self, char, *args, **kwargs):

    char.debug('PLUG %s.%s' % (self.__class__.__name__, self.name))
    self.char = char
    try:
      self._plug(*args, **kwargs)
    except:
      self.char = None
      raise

  # to be overriden in children
  def _plug(self):
    pass

  # try to remove ourself from the Character, checking for dependency issues
  # @raise DependencyError if other Fields depend on us
  def unplug(self, *args, **kwargs):

    self.char.debug('UNPLUG %s.%s' % (self.__class__.__name__, self.name))

    if not self.char:
      raise RuntimeError('plug() must be called before unplug()')

    self._unplug(*args, **kwargs)
    self.char = None

  # to be overriden in children
  def _unplug(self):
    pass

  # recalculate our value
  def calc(self):
    pass

  # what to print for the "search" command
  def str_search(self):
    return str(self)

  # what to print for the "all" command
  def str_all(self):
    return str(self)

  # what to print in other cases, including the "get" command
  def __str__(self):
    return repr(self)

  # this gets called in the interpreter, and for when in a collection
  def __repr__(self):
    return '<%s %s>' % (self.__class__.__name__,self.name)
