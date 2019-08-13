from collections import OrderedDict

from dnd.char_sheet.fields.stat import Stat

###############################################################################
# Bonus class
#   - bonuses add a number (or Dice) to a stat or item
#   - they can be turned on and off
#   - they can be conditional
###############################################################################

class Bonus(Stat):

  FIELDS = OrderedDict([
    ('name', str),
    ('original', str),
    ('stats', list),
    ('typ', str),
    ('condition', str),
    ('text', str),
    ('active', bool),
    ('updated', float),
  ])

  COPY_ARGS = [
    'name',
    ('formula', 'original'),
    'stats',
  ]
  COPY_KWARGS = [
    'typ',
    ('cond', 'condition'),
    'text',
    'active',
    'updated'
  ]
  COPY_VARS = [
    'usedby',
    'effects'
  ]

  # @param name (str)
  # @param formula (str) will get passed to eval()
  #   using $NAME refers to the value of the Stat by that name
  #   using #NAME refers to the normal (no bonuses) value
  #   using @NAME refers to an attribute of this Bonus object
  #   these can be wrapped in braces to prevent conflicts e.g. ${NAME}
  # @param stats (str,list of str) names of stats that we affect
  # @param typ (str) ['none'] our type e.g. armor, dodge, morale
  # @param cond (str) [''] when this bonus applies if not all the time
  # @param text (str) ['']
  # @param active (bool) [not cond] whether we're "on" and modifying stats
  # @param updated (float) [time.time()] when this Bonus was updated
  def __init__(self, name, formula, stats,
      typ=None, cond=None, text=None, active=True, updated=None):

    super().__init__(name, formula, text=text, updated=updated)

    self.stats = stats if isinstance(stats,list) else [stats]
    self.typ = (typ or 'none').lower()
    self.condition = cond or ''
    self.active = False if cond else active

    self.effects = set()
    self.last = active # remember the state we're in before a toggle

  # @raise ValueError if our type isn't in our Character
  def _plug(self):

    # I'd rather have this in __init__ but we don't have a char at that point
    if self.char.BONUS_TYPES and self.typ not in self.char.BONUS_TYPES:
      raise ValueError('%s.%s: invalid bonus type "%s"'
          % (self.__class__.__name__, self.name, self.typ))

    super()._plug()

    for name in self.stats:
      stat = self.char.stats[name]
      stat.add_bonus(self)
      stat.calc(self)

    # some bonuses should never be turned off
    if not self.condition and self.typ in self.char.BONUS_PERM:
      self.active = True

  def _unplug(self, force=False):

    for name in self.stats:
      stat = self.char.stats[name]
      stat.del_bonus(self)
      stat.calc(self)

    super()._unplug(force=force)

  # @return (int) the value of this bonus
  def get_value(self):
    return self.value

  def calc(self, caller=None):

    if not super().calc(caller):
      for name in self.stats:
        self.char.stats[name].calc(caller or self)

  def on(self):
    self.toggle(True)

  # @param force (bool) [False] turn off even if we belong to an active Effect
  def off(self,force=False):

    # if we belong to an Effect and it is active, we should stay on
    if force:
      self.toggle(False)
    else:
      for e in self.effects:
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
    eff = '' if not self.effects else '{%s}'%','.join(sorted(self.effects))
    cond = '' if not self.condition else ' ? %s' % self.condition
    return '[%s]%s%s %s%s%s (%s)%s' % (act,n,eff,sign,self.get_value(),s,self.typ,cond)

  # @return (str)
  def __str__(self):
    return self._str()

  # @return (str)
  def str_all(self):

    l =     ['  value | %s' % self.get_value()]
    l.append('formula | %s' % self.original)
    l.append('   uses | %s' % ','.join(sorted(self.uses)))
    l.append(' active | %s' % self.active)
    l.append('   type | %s' % self.typ)
    l.append(' revert | %s' % ('change','same')[self.last==self.active])
    l.append('  stats | %s' % ','.join(sorted(self.stats)))
    l.append('effects | %s' % ','.join(sorted(self.effects)))
    l.append('conditn | %s' % self.condition)
    l.append('   text | %s' % self.text)
    return '\n'.join(l)

  # @return (str)
  def str_search(self):
    return str(self)

  @property
  def add_bonus(self):
    raise AttributeError("'Bonus' object has no attribute 'add_bonus'")
  @property
  def del_bonus(self):
    raise AttributeError("'Bonus' object has no attribute 'del_bonus'")
