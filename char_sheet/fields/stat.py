import time
from collections import OrderedDict

from dnd.char_sheet.fields import Field

###############################################################################
# Stat class
#   - stat tracking and calculation via string formulas and eval()
#   - stats are considered "root" nodes if their formula is static
#   - or "leaf" nodes if no other stat depends on it
#   - Example: dexterity > dex > _ac_dex > ac
#     - roots: dexterity
#     - leaves: ac
#     - neither: dex, _ac_dex
#   - stats whose name begins with '_' are protected by default
#   - stats can have Bonuses that affect their value
###############################################################################

class Stat(Field):

  FIELDS = OrderedDict([
      ('name',str),
      ('original',str),
      ('text',str),
      ('bonuses',None),
      ('protected',bool),
      ('updated',float)
  ])

  VARS = {'$':'self.char.stats["%s"].value',
      '#':'self.char.stats["%s"].normal',
  }

  # @param name (str)
  # @param formula (str) ['0'] will get passed to eval()
  #   using $NAME refers to the value of the Stat by that name
  #   using #NAME refers to the normal (no bonuses) value
  #   using @NAME refers to an attribute of this Stat object
  #   these can be wrapped in braces to prevent conflicts e.g. ${NAME}
  # @param text (str) ['']
  # @param bonuses (Bonus,list of Bonus) [None] bonuses affecting this stat
  # @param protected (bool) [name.startswith('_')] if this stat is protected
  # @param updated (float) [time.time()] when this Stat was updated
  def __init__(self,name,formula='0',text='',bonuses=None,protected=None,
      updated=None):

    self.char = None
    self.name = name
    self.text = text

    # during plug() in self.formula we replace aliases with valid python code
    # when displaying to the user or creating a new Stat we need the original
    self.formula = str(formula)
    self.original = self.formula

    # this is a dict of type:list where the elements of the list are Bonus
    # e.g. {"armor":[<Bonus mage_armor>,<Bonus shield>]}
    self.bonuses = bonuses or {}
    self.protected = name.startswith('_') if protected is None else protected
    self.updated = time.time() if updated is None else updated

    self.uses = set()
    self.usedby = set()
    self.normal = None
    self.value = None
    self.root = True
    self.leaf = True

    # overridden in sub-classes to specify additional fields to copy()
    self.COPY = []

  # @raise FormulaError
  def plug(self,char):

    self.char = char

    # iterate over each stat in the character and replace matching #/$ aliases
    s = self.formula
    usedby = set()
    for name in char.stats:
      for (var,expand) in self.VARS.items():
        orig = s
        s = s.replace(var+name,expand % name)
        s = s.replace('%s{%s}' % (var,name),expand % name)
        if s!=orig:
          self.uses.add(name)
          self.root = False
          usedby.add(char.stats[name])

    # iterate over our attributes and replace matching @ aliases
    for name in dir(self):
      s = s.replace('@'+name,'self.'+name)
      s = s.replace('@{'+name+'}','self.'+name)

    # if any aliases were invalid or misspelled, we'll have "#NAME" left which
    # will throw an exception in the eval()
    # of course can also throw syntax errors if something else is wrong
    try:
      eval(s)
    except Exception as e:
      raise FormulaError('%s in "%s"' % (e.__class__.__name__,s))

    # add ourselves as a dependant to stats that are in our formula
    for stat in usedby:
      stat.usedby.add(self.name)
      stat.leaf = False

    self.formula = s
    self.calc()

  # remove this stat from its character if possible
  # @param force (bool) [False] ignore dependency issues for this stat
  # @param recursive (bool) [False] remove all our dependants as well
  # @raise RuntimeError if we don't have a character
  # @raise DependencyError
  def unplug(self,force=False,recursive=False):

    if not self.char:
      raise RuntimeError('plug() must be called before unplug()')

    if self.usedby and not force and not recursive:
      raise DependencyError('still usedby: '+','.join(self.usedby))

    # unplug our dependants if requested
    if recursive:
      for name in self.usedby:
        stat = self.char.stats[name]
        stat.unplug(recursive=recursive)
    self.usedby = set()

    self.formula = self.original

    for name in self.uses:
      stat = self.char.stats[name]
      stat.usedby.remove(self.name)
      if not stat.usedby:
        stat.leaf = True
    self.uses = set()

    self.root = True
    self.leaf = True
    self.char = None

  # convenience method that sets self.formula and self.original
  # @param s (str) formula
  # @raise RuntimeError if we're already plugged in to a character
  def set_formula(self,s):

    if self.char:
      raise RuntimeError('set_formula() must be called before plug()')

    self.formula = s
    self.original = s

  # @raise RuntimeError if we don't have a character
  def calc(self):

    if not self.char:
      raise RuntimeError('plug() must be called before calc()')

    # evaluate our formula without bonuses
    old_v = self.value
    old_n = self.normal
    self.normal = eval(self.formula.replace('.value','.normal'))

    # evaluate our formula with bonuses
    self.value = eval(self.formula)
    for (typ,bonuses) in self.bonuses.items():
      bonuses = [b.get_value() for b in bonuses if b.active]
      if not bonuses:
        continue
      if self.char._stacks(typ):
        self.value += sum(bonuses)
      else:
        self.value += max(bonuses)

    # if we changed, bubble the calc() up through our dependants
    if old_v!=self.value or old_n!=self.normal:
      for stat in self.usedby:
        stat = self.char.stats[stat]
        stat.calc()

  # add a bonus to this stat that will affect its value
  # @param bonus (Bonus) the Bonus to add
  def add_bonus(self,bonus):

    typ = bonus.typ
    if typ in self.bonuses:
      self.bonuses[typ].append(bonus)
    else:
      self.bonuses[typ] = [bonus]

  # remove a bonus from this stat
  # @param bonus (Bonus) the Bonus to remove
  # [TODO] raise a KeyError or return a bool?
  def del_bonus(self,bonus):

    typ = bonus.typ
    self.bonuses[typ] = [b for b in self.bonuses[typ] if b is not bonus]
    if not self.bonuses[typ]:
      del self.bonuses[typ]

  # return all bonuses that can affect this stat, including from dependencies
  # @return (2-tuple)
  #   #0 (list of Bonus) permanent bonuses
  #   #1 (list of Bonus) conditional bonuses
  def get_bonuses(self):

    bonuses = []
    conds = []
    for typ in self.bonuses.values():
      for b in typ:
        if b.condition:
          conds.append((self.name,b))
        else:
          bonuses.append((self.name,b))

    # recurse over dependencies
    for stat in self.uses:
      (b,c) = self.char.stats[stat].get_bonuses()
      bonuses += b
      conds += c

    return (bonuses,conds)

  # copy this Stat into a new object with specified changes
  # @param kwargs (dict) fields to update
  # @return (Stat) the copy
  def copy(self,**kwargs):

    a = []
    for var in ('name','text','bonuses','updated'):
      a.append(kwargs.get(var,getattr(self,var)))
    formula = kwargs.get('formula',self.original)
    a.insert(1,formula)

    # sub-classes of Stat can specify additional fields to copy
    k = {}
    for var in self.COPY:
      k[var] = kwargs.get(var,getattr(self,var))

    return self.__class__(*a,**k)

  # looks like: -rl
  #   - (type) should be overridden in child classes
  #   r (root) our formula has no dependencies
  #   l (leaf) no other stat depends on us
  # @return (str)
  def _str_flags(self):

    root = '-r'[self.root]
    leaf = '-l'[self.leaf]
    return '-%s%s' % (root,leaf)

  # looks like: rl 999 NAME (b:5/10 ?:0/5)
  # followed by conditional bonuses indented on new lines
  # @param cond_bonuses (bool) [False] whether to print conditional bonuses
  # @return (str)
  def _str(self,cond_bonuses=False):

    flags = self._str_flags()
    (bonuses,conds) = self.get_bonuses()
    (total_b,total_c,active_b,active_c) = (len(bonuses),len(conds),0,0)
    for (stat,b) in bonuses:
      if b.active:
        active_b += 1
    for (stat,b) in conds:
      if b.active:
        active_c += 1
    stats = 'b:%s/%s ?:%s/%s' % (active_b,total_b,active_c,total_c)
    bons = ''
    if cond_bonuses:
      bons = ''.join(['\n  %s'%b[1]._str(stat=False) for b in conds])
    return '%s %3s %s (%s)%s' % (flags,self.value,self.name,stats,bons)

  # don't print conditional bonuses
  # @return (str)
  def str_search(self):
    return self._str()

  # do print conditional bonuses
  # @return (str)
  def __str__(self):
    return self._str(True)

  # @return (str)
  def str_all(self):

    l =     ['  value | %s' % self.value]
    l.append('formula | %s' % self.original)
    x = []

    # each bonus gets its own line
    # if the bonus is on one of our dependencies, include its name
    (bonuses,conds) = self.get_bonuses()
    for (stat,bonus) in bonuses:
      name = '' if stat==self.name else '<%s> ' % stat
      x +=  ['  bonus | %s%s' % (name,bonus._str(stat=False))]
    l.extend(sorted(x))
    x = []
    for (stat,bonus) in conds:
      name = '' if stat==self.name else '<%s> ' % stat
      x +=  [' bonus? | %s%s' % (name,bonus._str(stat=False))]
    l.extend(sorted(x))

    l.append(' normal | %s' % self.normal)
    l.append('   uses | %s' % ','.join(sorted(self.uses)))
    l.append('used by | %s' % ','.join(sorted(self.usedby)))
    l.append('   text | %s' % self.text)
    return '\n'.join(l)
