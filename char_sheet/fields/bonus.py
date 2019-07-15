from collections import OrderedDict

from dnd.char_sheet.fields.field import Field

###############################################################################
# Bonus class
#   - bonuses add a number (or Dice) to a stat or item
#   - they can be turned on and off
#   - they can be conditional
###############################################################################

class Bonus(Field):

  FIELDS = OrderedDict([
      ('name',str),
      ('value',int),
      ('stats',list),
      ('typ',str),
      ('condition',str),
      ('text',str),
      ('active',bool)
  ])

  # @param name (str)
  # @param value (int,Dice) the value to add to our stats
  # @param stats (str,list of str) names of stats that we affect
  # @param typ (str) ['none'] our type e.g. armor, dodge, morale
  # @param cond (str) [''] when this bonus applies if not all the time
  # @param text (str) ['']
  # @param active (bool) [not cond] whether we're "on" and modifying stats
  def __init__(self,name,value,stats,typ=None,cond=None,text=None,active=True):

    self.name = name
    self.value = value
    self.stats = stats if isinstance(stats,list) else [stats]
    self.text = text or ''
    self.active = False if cond else active
    self.typ = (typ or 'none').lower()
    self.condition = cond or ''

    self.char = None
    self.usedby = set() # this will contain Effects
    self.last = active # remember the state we're in before a toggle

  # @param char (Character)
  # @raise ValueError if our type isn't in our Character
  def plug(self,char):

    # I'd rather have this in __init__ but we don't have a char at that point
    if char.BONUS_TYPES and self.typ not in char.BONUS_TYPES:
      raise ValueError('invalid bonus type "%s"' % self.typ)

    for name in self.stats:
      stat = char.stats[name]
      stat.add_bonus(self)
      stat.calc()
    self.char = char

    # some bonuses should never be turned off
    if not self.condition and self.typ in self.char.BONUS_PERM:
      self.active = True

  def unplug(self):

    if not self.char:
      raise RuntimeError('plug() must be called before unplug()')

    for name in self.stats:
      stat = self.char.stats[name]
      stat.del_bonus(self)
      stat.calc()
    self.char = None

  # @return (int) the value of this bonus
  def get_value(self):
    return self.value

  def calc(self):

    for name in self.stats:
      self.char.stats[name].calc()

  def on(self):
    self.toggle(True)

  # @param force (bool) [False] turn off even if we belong to an active Effect
  def off(self,force=False):

    # if we belong to an Effect and it is active, we should stay on
    if force:
      self.toggle(False)
    else:
      for e in self.usedby:
        if self.char.effects[e].is_active():
          return
      self.toggle(False)

  # @param new (bool) the new state; could be the same as our old state
  def toggle(self,new):

    # some bonuses should never be turned off
    if not self.condition and self.typ in self.char.BONUS_PERM:
      return
    self.last = self.active
    self.active = new
    self.calc()

  # this is planned to be used for the "with" conditional which hasn't been
  # implemented yet e.g. "get ac with mage_armor" / "get ac without mage_armor"
  def revert(self):

    if self.active==self.last:
      return
    (self.active,self.last) = (self.last,self.active)
    self.calc()

  # looks like: [+] NAME VALUE STATS (type)
  # belongs to effects: [+] NAME VALUE STATS (type) {effect}
  # conditional: [-] NAME VALUE STATS (type) ? CONDITION
  # @param name (bool) [True] print our name
  # @param stat (bool) [True] print the stats we affect
  # @return (str)
  def _str(self,name=True,stat=True):

    (n,s) = ('','')
    if name:
      n = ' %s' % self.name
    if stat:
      s = ' %s' % ','.join(self.stats)
    act = '-+'[self.active]
    sign = '+' if self.value>=0 else ''
    eff = '' if not self.usedby else '{%s}'%','.join(sorted(self.usedby))
    cond = '' if not self.condition else ' ? %s' % self.condition
    return '[%s]%s%s %s%s%s (%s)%s' % (act,n,eff,sign,self.get_value(),s,self.typ,cond)

  # @return (str)
  def __str__(self):
    return self._str()

  # @return (str)
  def str_all(self):

    l =     ['  value | %s' % self.get_value()]
    l.append(' active | %s' % self.active)
    l.append('   type | %s' % self.typ)
    l.append(' revert | %s' % ('change','same')[self.last==self.active])
    l.append('  stats | %s' % ','.join(sorted(self.stats)))
    l.append(' usedby | %s' % ','.join(sorted(self.usedby)))
    l.append('conditn | %s' % self.condition)
    l.append('   text | %s' % self.text)
    return '\n'.join(l)
