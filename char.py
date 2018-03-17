##### COMMANDS #####

# get (stat|bonus|text) NAME[,NAME...]
# add stat NAME [FORMULA] [TEXT] [UPDATED]
# add bonus NAME VALUE STAT[,STAT...] [TYP] [COND] [TEXT] [ACTIVE]
# add text NAME TEXT
# set stat NAME [FORMULA] [TEXT] [UPDATED] [FORCE]
# set bonus NAME VALUE
# set text NAME TEXT
# del (stat|bonus|text) NAME
# all (stat|bonus|text) NAME
# search TERM
# on BONUS
# off BONUS
# revert BONUS

# dmg HPLOST
# heal HPHEALED
# skill (info|list)
# skill (class|unclass) NAME
# skill rank NAME RANKS
# wiz (all|abilities|class|class_skill|level|race|size|skill)

##### ALIASES #####

#    get : g     add : a    set : s      del : d    all : l
# search : ?      on : +    off : -   revert : r
#   stat : s   bonus : b   text : t

##### EXAMPLES #####

# TRY THE SETUP (WIZ)ARD FUNCTIONS!
# >>> wiz all

# >>> get stat ac
# r-  10 ac (b:0/0 ?:0/0)

# >>> get stat ac,ac_ff,ac_touch
# r-  10 ac (b:0/0 ?:0/0)
# r-  10 ac_touch (b:0/0 ?:0/0)
# r-  10 ac_ff (b:0/0 ?:0/0)

# >>> help add bonus
# (add bonus) name value stats [typ] [cond] [text] [active]

# >>> add bonus mage_armor +4 ac armor
# >>> ? ac_touch
# s | r-  10 ac_touch (b:0/0 ?:0/0)

# >>> all stat ac
#   value | 14
# formula | 10+$_ac_armor+$_ac_shield+$_ac_dex+$size+$_ac_nat+$_ac_deflect+$_ac_misc
#   bonus | <_ac_armor> [+] mage_armor +4 (armor)
#  normal | 10
#    uses | _ac_armor,_ac_deflect,_ac_dex,_ac_misc,_ac_nat,_ac_shield,size
# used by |
#    text |

# [TODO] disallow setting backend stats without additional flag
# [TODO] set should raise exception not return a boolean
# [TODO] conditional bonuses
# [TODO] consider another way for set_stat() to interact with plug/unplug?
# [TODO] decide what goes in here and what goes in the CLI
# [TODO] Bonus subclasses Stat but only allows root nodes? allows formulas
# [TODO] stat classes for setting (and getting?) e.g. abilities, skills
# [TODO] mark skills that can only be used if trained somehow?
# [TODO] common effect library for importing: feats, spells, conditions
# [TODO] pre-made/custom views (e.g. show all abilities)
# [TODO] regex searching
# [TODO] quote blocking
# [TODO] keyword acceptance e.g. "set stat text=blah"
# [TODO] strip tabs/newlines from input
# [TODO] report modification to the cli somehow (add,set,upgrade...) decorator?
# [TODO] incrementing? at least for skill ranks?
# [TODO] swap meaning of root and leaf
# [TODO] move Pathfinder to its own file
# [TODO] experience
# [TODO] limit skill ranks
# [TODO] reset bonus original values dynamically to account for leveling up
# [TODO] make durations mathy
# [TODO] include effect name when printing bonuses or stats

# [TODO] finish Effects (duration tracking, etc.)
# [TODO] Item
# [TODO] Weapon
# [TODO] Armor
# [TODO] Ability
# [TODO] Spell
# [TODO] Event

# Stat
#   PathfinderSkill
# Bonus
# Effect
# Duration
# Item
#   Weapon
#   Armor
# Dice
# Ability
#   Spell
# Event
# Text

import time,inspect
from collections import OrderedDict

from dice import Dice
from functools import reduce

###############################################################################
# Custom exceptions
###############################################################################

class CharError(Exception):
  pass

class DuplicateError(CharError):
  pass

class DependencyError(CharError):
  pass

class FormulaError(CharError):
  pass

class ProtectedError(CharError):
  pass

class UserQuitException(CharError):
  pass

class UserSkipException(CharError):
  pass

# the universe contains everything
class Universe(dict):
  def __contains__(self,obj):
    return True
  def __getitem__(self,x):
    return 'GALAXY'
  def get(self,x,d):
    return 'GALAXY'

###############################################################################
# Character class
###############################################################################

class Character(object):

  # these are used to pre-populate a new character
  STATS = OrderedDict()
  BONUSES = OrderedDict()
  EFFECTS = OrderedDict()
  ITEMS = OrderedDict()
  ABILITIES = OrderedDict()
  EVENTS = OrderedDict()
  TEXTS = OrderedDict([('name','UNNAMED')])

  # this makes logic in _setup() easier later
  BONUSS = BONUSES
  ABILITYS = ABILITIES

  # all bonuses stack
  BONUS_STACK = Universe()

  # load a character from file
  # @param name (str) file path
  # @return (Character)
  @staticmethod
  def load(name):

    with open(name,'r') as f:
      lines = [x.strip('\n') for x in f.readlines()]

    errors = []
    chars = {k:v for (k,v) in globals().items()
        if inspect.isclass(v) and issubclass(v,Character)}
    fields = {k:v for (k,v) in globals().items()
        if inspect.isclass(v) and issubclass(v,Field)}

    char = None
    for (i,line) in enumerate(lines):
      if not line:
        continue
      if not char:
        if line not in chars:
          return ['line %s | unknown character type "%s"' % (i+1,line[0])]
        char = chars[line](setup=False)
      else:
        line = line.split('\t')
        if line[0] not in fields:
          errors.append('line %s | unknown object type "%s"' % (i+1,line[0]))
          continue
        try:
          obj = fields[line[0]].load(line[1:])
          if not errors:
            char._get_add_method(obj.__class__)(obj)
        except Exception as e:
          errors.append('line %s |   %s' % (i,' / '.join(line)))
          errors.append('*** %s: %s' % (e.__class__.__name__,e.args[0]))

    # add any new stats added since the character was saved
    if not errors:
      char._setup(ignore_dupes=True)

    return (char,errors)

  # @param setup (bool) [True] pre-populate character
  # @param name (str) [None] character name (set to 'UNNAMED' if setup=True)
  def __init__(self,setup=True,name=None):

    self.name = name
    self.stat = OrderedDict(); self.stats = self.stat
    self.bonus = OrderedDict(); self.bonuses = self.bonus
    self.effect = OrderedDict(); self.effects = self.effect
    self.item = OrderedDict(); self.items = self.item
    self.ability = OrderedDict(); self.abilities = self.ability
    self.event = OrderedDict(); self.events = self.event
    self.text = OrderedDict(); self.texts = self.text

    # aliases for objects
    self.letters = OrderedDict([
      ('s','stat'),
      ('b','bonus'),
      ('e','effect'),
      ('i','item'),
      ('a','ability'),
      ('v','event'),
      ('t','text')])

    # register commands
    self.export = ['search','on','off','revert','get','all']
    # register commands that have sub commands
    self.export_prefix = ['add','set','del']
    # register aliases
    self.export_alias = {
      '?':'search','+':'on','-':'off','r':'revert','g':'get','l':'all',
      'a':'add','s':'set','d':'del'
    }
    # register sub command aliases
    # [TODO] improve and include more objects
    self.export_sub_alias = {a:b for (a,b) in self.letters.items() if a in 'sbt'}

    # this doesn't execute when loading from a file to prevent conflicts
    if setup:
      self._setup()

  # pre-populate the character with the fields in STATS, BONUSES, etc.
  # @param ignore_dupes (bool) [False] skip duplicates instead of crashing
  # @raise DuplicateError if dupes encountered and ignore_dupes=False
  def _setup(self,ignore_dupes=False):

    for typ in self.letters.values():
      for (name,s) in getattr(self,typ.upper()+'S').items():
        try:
          getattr(self,'add_'+typ)(name,str(s))
        except DuplicateError:
          if ignore_dupes:
            pass
          else:
            raise

    if self.name:
      self.set_text('name',self.name)

  # @return a command line prompt
  def _get_prompt(self):

    s = len(self.stats)
    b = len(self.bonuses)
    a = len([x for x in self.bonuses.values() if x.active])
    return '[ S:%s B:%s/%s ] ' % (s,a,b)

  # @return our character name
  def _get_name(self):
    return self.texts['name'].text

  # @param cls (class) a sub-class of Field
  # @return (func) the relevant "add" method for adding Fields during file load
  # @raise KeyError
  def _get_add_method(self,cls):

    if cls.__name__.lower() in self.letters.values():
      return getattr(self,'_add_'+cls.__name__.lower())

    # handle sub classes
    if cls.__bases__:
      return self._get_add_method(cls.__bases__[0])

    raise KeyError('failed to get add method')

  # @param typ (str) the bonus type
  # @return (bool) if bonuses of that type stack
  def _stacks(self,typ):
    return not self.BONUS_STACK or typ in self.BONUS_STACK

###############################################################################
# User input functions
# [TODO] consider moving to char_cli somehow?
###############################################################################

  # get input from the user
  # @param msg (str) prompt to print
  # @param lower (bool) [True] lowercase user input
  # @param parse (func) [None] parse function (e.g. int)
  #   ValueError will be caught, others will crash
  # @param valid (func) [None] validation function
  #   accepts one parameter, returns True/False
  # @param repeat (bool) [True] keep asking for input until parse/valid succeed
  # @param blank (bool) [True] allow use to press enter without typing anything
  #   this returns the empty string
  # @return (object) the parsed & validated input
  # @raise UserSkipException if user enters 'skip' or 'next'
  # @raise UserQuitException if user enters 'quit' or 'exit'
  # @raise ValueError if parsing raises an exception and repeat=False
  def _input(self,msg,lower=True,parse=None,valid=None,repeat=True,blank=True):

    count = 0
    while count==0 or repeat:
      count += 1

      s = input(msg+': ').strip()
      if lower:
        s = s.lower()

      if s in ('quit','exit'):
        raise UserQuitException

      if s in ('skip','next'):
        raise UserSkipException

      if s=='' and blank:
        break

      if parse is not None:
        try:
          s = parse(s)
        except ValueError as e:
          print('*** %s: %s' % (e.__class__.__name__,e.args[0]))
          if repeat:
            continue
          else:
            raise

      if valid is None or valid(s):
        break
      else:
        print('*** Invalid entry')

    return s

  # get and act on a bunch of user input
  # @param actions (list of 3-tuple) actions to perform
  #   #0 prompt (str) the prompt to display
  #   #1 key (object) input to pass to the action
  #   #2 action (func,None) function to execute, receives (key,USERINPUT)
  # @param kwargs (dict) passed to _input()
  # @raise UserQuitException if generated by _input()
  def _inputs(self,actions,**kwargs):

    for (prompt,key,action) in actions:
      try:
        x = self._input(prompt,**kwargs)
      except (ValueError,UserSkipException):
        break
      if x=='' and kwargs.get('blank',True):
        continue
      if action is not None:
        action(key,x)

  # get a yes/no response from the user
  # @param prompt (str) the prompt to display
  # @param default (bool) [True] the default option
  # @param blank (bool) [True] whether to accept a blank line
  #   this returns the default
  # @return (bool)
  # @raise UserSkipException if user enters 'skip' or 'next'
  # @raise UserQuitException if user enters 'quit' or 'exit'
  def _yn(self,prompt,default=True,blank=True):

    yes = ('y','yes','ok')
    no = ('n','no','cancel')
    choices = 'Y/n' if default else 'N/y'
    response = self._input(
        '%s? (%s)' % (prompt,choices),
        valid = lambda x: x.lower() in yes+no,
        blank = blank
    )

    if response=='':
      return default

    return response in yes

  # get many yes/no responses and act on them
  # @param actions (list of 3-tuple) actions to perform
  #   #0 prompt (str) the prompt to display
  #   #1 key (object) input to pass to the action
  #   #2 action (func,None) function to execute, receives (key,USERINPUT)
  # @param kwargs (dict) passed to _yn()
  # @raise UserQuitException if generated by _yn()
  def _yns(self,actions,**kwargs):

    for (prompt,key,action) in actions:
      try:
        x = self._yn(prompt,**kwargs)
      except UserSkipException:
        break
      if action is not None:
        action(key,x)

###############################################################################
# User commands
###############################################################################

  # save this character
  # @param name (str) file path
  def save(self,name):

    s = self.__class__.__name__+'\n'
    for typ in self.letters.values():
      for obj in getattr(self,typ).values():
        s += ('%s\t' % obj.__class__.__name__)+'\t'.join(obj.save())+'\n'

    with open(name,'w') as f:
      f.write(s)

  def search(self,name,ignore='_'):
    """
    search all objects for one with a matching name
      - name (string) the search term
      - [ignore = '_'] (string) exclude results starting with this string
    """

    matches = []
    for (l,d) in self.letters.items():
      for (n,obj) in getattr(self,d).items():
        if name in n and (ignore=='*' or not n.startswith(ignore)):
          matches.append('%s | %s' % (l,obj.str_search()))
    return '\n'.join(matches)

  # @raise KeyError if typ does not exist
  def get(self,typ,name):
    """
    show a summary of the requested field(s)
      - typ (string) field type
      - name (string,list) the field name(s)
    """

    typ = typ if typ not in self.letters else self.letters[typ]
    if typ not in self.letters.values():
      raise KeyError('unknown type "%s"' % typ)

    if name=='*':
      name = sorted(getattr(self,typ).keys())
    elif not isinstance(name,list):
      name = [name]

    results = []
    for n in name:
      try:
        results.append(str(getattr(self,typ)[n]))
      except AttributeError:
        results.append('unknown %s "%s"' % (typ,n))
    return '\n'.join(results)

  # @raise KeyError if typ or name do not exist
  def all(self,typ,name):
    """
    show detailed information about the requested field(s)
      - typ (string) field type
      - name (string,list) the field name(s)
    """

    typ = typ if typ not in self.letters else self.letters[typ]
    if typ not in self.letters.values():
      raise KeyError('unknown type "%s"' % typ)

    try:
      return getattr(self,typ)[name].str_all()
    except AttributeError:
      raise KeyError('unknown %s "%s"' % (typ,name))

  # @param stat (Stat) the Stat to add
  # @raise DuplicateError if the name already exists
  def _add_stat(self,stat):

    if stat.name in self.stats:
      raise DuplicateError('stat "%s" already exists' % stat.name)
    stat.plug(self)
    self.stats[stat.name] = stat

  # @raise DuplicateError if name already exists
  def add_stat(self,name,formula='0',text='',updated=None):
    """
    add a new Stat
      - name (string)
      - [formula = '0'] (string) the formula for calculating its value
        - reference other stats with '$' (e.g. '$strength')
        - same as above but ignore any Bonuses with '#' (e.g. '#stength')
        - anything legal in eval() is legal here
      - [text = ''] (string)
      - [updated = NOW] (int) time the stat was last updated (unix epoch)
    """

    stat = Stat(name,formula,text,updated)
    self._add_stat(stat)

  # @raise KeyError if name does not exist
  # @raise DependencyError if delete would break hierarchy
  def del_stat(self,name):
    """
    delete a Stat
      - name (string)
    """

    try:
      stat = self.stats[name]
      stat.unplug()
      del self.stats[name]
    except KeyError:
      raise KeyError('unknown stat "%s"' % name)

  # @raise KeyError if name does not exist
  # @raise FormulaError if formula contains errors
  def set_stat(self,name,formula=None,text=None,updated=None,force=False):
    """
    modify an existing Stat
      - name (string)
      - formula (string) see 'help add stat'
      - [text = None] (string)
      - [updated = None] (int)
      - [force = False] (bool) ignore protected stats and force the update
    """

    try:
      old = self.stats[name]
    except KeyError:
      raise KeyError('unknown stat "%s"' % name)

    if not force:
      if old.protected:
        raise ProtectedError('stat "%s" is protected (use force)' % name)
      if old.uses:
        raise ProtectedError('stat "%s" is not a root (use force)' % name)

    # to preserve atomicity, copy the existing stat, modify it, then replug
    new = old.copy(text=text,formula=formula,updated=updated)
    new.usedby = set(old.usedby)
    if new.usedby:
      new.root = False
    old.unplug(force=True)
    try:
      self.stats[name] = new
      new.plug(self)
    except FormulaError as e:
      old.formula = old.original
      old.plug(self)
      self.stats[name] = old
      raise e

  # @param bonus (Bonus) the Bonus to add
  # @raise DuplicateError if the name already exists
  def _add_bonus(self,bonus):

    if bonus.name in self.bonuses:
      raise DuplicateError('bonus "%s" already exists' % bonus.name)
    bonus.plug(self)
    self.bonuses[bonus.name] = bonus

  # @raise DuplicateError if name already exists
  def add_bonus(self,name,value,stats,typ=None,cond=None,text=None,active=True):
    """
    add a new Bonus
      - name (string)
      - value (int,Dice) the number/Dice to add to our stat(s)
      - stats (string,list) the stat(s) this Bonus modifies
      - [typ = 'none'] (string) the bonus type (e.g. 'armor')
      - [cond = ''] (string) when this bonus applies if not all the time
      - [text = ''] (string)
      - [active = True] (bool)
    """

    bonus = Bonus(name,Dice(value),stats,typ,cond,text,active)
    self._add_bonus(bonus)

  # @raise KeyError if name does not exist
  def set_bonus(self,name,value):
    """
    modify an existing Bonus
      - name (string)
      - value (int,Dice) the number/Dice to add to our stat(s)
    """

    try:
      bonus = self.bonuses[name]
    except KeyError:
      raise KeyError('unknown bonus "%s"' % name)

    bonus.value = Dice(value)
    bonus.calc()

  # @raise KeyError if name does not exist
  def del_bonus(self,name):
    """
    delete a Bonus
      - name (string)
    """

    try:
      self.bonuses[name].unplug()
    except KeyError:
      raise KeyError('unknown bonus "%s"' % name)

    del self.bonuses[name]

  # @param effect (Effect) the Effect to add
  # @raise DuplicateError if the name already exists
  def _add_effect(self,effect):

    if effect.name in self.effects:
      raise DuplicateError('effect "%s" already exists' % effect.name)
    effect.plug(self)
    self.effects[effect.name] = effect

  # @raise DuplicateError if name already exists
  def add_effect(self,name,bonuses,duration=None,text=None,active=None):
    """
    add a new Effect
      - name (string)
      - bonuses (string,list) the bonuses created by this Effect
      - [duration = None] (string) valid units: rd,min,hr,day (None = infinite)
      - text (string) [None]
      - [active = None] (bool) if not None, (de)activate all our bonuses
    """

    effect = Effect(name,bonuses,Duration(duration,self),text,active)
    self._add_effect(effect)

  # @raise KeyError if name does not exist
  def set_effect(self,name,bonuses=None,duration=None):
    """
    modify an existing Effect
      - name (string)
      - [bonuses = None] (string,list)
      - [duration = None] (string) see 'help add effect'
        - None means don't update it, so use 'inf' to set an infinite duration
    """

    effect = self.effects[name]
    bonuses = bonuses or effect.bonuses
    duration = duration or effect.rounds
    try:
      effect.unplug()
      del self.effects[name]
      self.add_effect(name,bonuses,duration,effect.text,effect.active)
    except Exception as e:
      effect.plug(self)
      self.effects[name] = effect
      raise e

  # @param text (Text) the Text to add
  # @raise DuplicateError if the name already exists
  def _add_text(self,text):

    if text.name in self.texts:
      raise DuplicateError('text "%s" already exists' % text.name)
    self.texts[text.name] = text

  # @raise DuplicateError if name already exists
  def add_text(self,name,text):
    """
    add a new Text blurb
      - name (string)
      - text (string)
    """

    text = Text(name,text)
    self._add_text(text)

  # @raise KeyError if name does not exist
  def set_text(self,name,text):
    """
    modify an existing Text
      - name (string)
      - text (string)
    """

    try:
      t = self.texts[name]
    except KeyError:
      raise KeyError('unknown text "%s"' % name)

    t.set(text)

  # @raise KeyError if name does not exist
  def del_text(self,name):
    """
    delete a Text blurb
      - name (string)
    """

    try:
      del self.texts[name]
    except KeyError:
      raise KeyError('unknown text "%s"' % name)

  # @raise KeyError if name does not exist
  def on(self,name):
    """
    activate a Bonus
      - name (string)
    """

    try:
      self.bonuses[name].on()
    except KeyError:
      raise KeyError('unknwown bonus "%s"' % name)

  # @raise KeyError if name does not exist
  def off(self,name):
    """
    deactivate a Bonus
      - name (string)
    """

    try:
      self.bonuses[name].off()
    except KeyError:
      raise KeyError('unknwown bonus "%s"' % name)

  # @raise KeyError if name does not exist
  def revert(self,name):
    """
    revert a bonus to its last state
      - name (string)
    """

    try:
      self.bonuses[name].revert()
    except KeyError:
      raise KeyError('unknwown bonus "%s"' % name)

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
  def load(cls,fields):

    parsed = []
    i = 0
    for typ in cls.FIELDS.values():
      val = None
      if typ is not None:
        if typ is list:
          val = fields[i].split(',')
        elif typ is bool:
          val = fields[i]=='True'
        else:
          val = typ(fields[i])
        i += 1
      parsed.append(val)
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
  def plug(self,char):
    pass

  # try to remove ourself from the Character, checking for dependency issues
  # @raise DependencyError if other Fields depend on us
  def unplug(self):
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

###############################################################################
# Stat class
#   - stat tracking and calculation via string formulas and eval()
#   - stats are considered "root" nodes if their formula is static
#   - or "leaf" nodes if no other stat depends on it
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
          self.leaf = False
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
      stat.root = False

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
        stat.root = True
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

  # looks like: rl
  #   r (root) our formula has no dependencies
  #   l (leaf) no other stat depends on us
  # @return (str)
  def _str_flags(self):

    root = '-r'[self.root]
    leaf = '-l'[self.leaf]
    return '%s%s' % (root,leaf)

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

###############################################################################
# Bonus class
#   - bonuses add a number (or Dice) to a stat or item
#   - they can be turned on and off
#   - they can be conditional
#   - stats are considered "root" nodes if their formula is static
#   - or "leaf" nodes if no other stat depends on it
#   - stats whose name begins with '_' are protected by default
#   - stats can have Bonuses that affect their value
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
    if force or not reduce(lambda a,b:a or b.is_active(),self.usedby,False):
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
    self.active = self.last
    self.calc()

  # looks like: [+] NAME VALUE STATS (type)
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
    cond = '' if not self.condition else ' ? %s' % self.condition
    return '[%s]%s %s%s%s (%s)%s' % (act,n,sign,self.get_value(),s,self.typ,cond)

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
    l.append('conditn | %s' % self.condition)
    l.append('   text | %s' % self.text)
    return '\n'.join(l)

###############################################################################
# Duration class
#   - tracks a duration e.g. 1 round, 2 hours, 5 days
#   - can also be infinite
#   - can be based on $level or $caster_level e.g. 1/CL 1mi/2CL
###############################################################################

class Duration(object):

  INF = -1
  INF_NAMES = (None,'inf','infinity','infinite','perm','permanent','forever')

  UNITS = {
      ('','r','rd','rds','rnd','rnds','round','rounds') : 1,
      ('m','mi','min','mins','minute','minutes') : 10,
      ('h','hr','hrs','hour','hours') : 600,
      ('d','day','days') : 14400,
      ('y','yr','yrs','year','years') : 5259600,
      ('l','lvl','level') : '$level',
      ('cl','clvl','caster','casterlvl','casterlevel') : '$caster_level'
  }

  NAMES = [(5259600,'yr'),(14400,'day'),(600,'hr'),(10,'min'),(1,'rd')]

  # @param s (str)
  # @return (bool) whether the input string is an int
  @staticmethod
  def is_int(s):

    try:
      int(s)
      return True
    except:
      return False

  # @param s (str) unit name
  # @return (int) the corresponding multiplier for conversion to rounds
  @staticmethod
  def get_mult(s):

    for (names,mult) in Duration.UNITS.items():
      if s in names:
        return mult

    raise KeyError('unknown unit "%s"' % s)

  # @param s (str) one duration text
  # @return (2-tuple)
  #   #0 (str) the number
  #   #1 (str) unit
  @staticmethod
  def split_unit(s):

    i = 0
    while i<len(s) and Duration.is_int(s[i]):
      i += 1
    return (s[:i] or '1',s[i:])

  # @param s (str) full duration e.g. 1+1/CL
  # @return (str) input converted to valid python expression to be eval()
  @staticmethod
  def to_rds(s):

    if isinstance(s,int):
      return str(s)

    if isinstance(s,str):
      s = s.lower().replace(' ','').replace('_','')
    if s in Duration.INF_NAMES:
      return str(Duration.INF)

    durs = s.split('+')

    rds = []
    for dur in durs:

      if dur.count('/')>1:
        raise ValueError('too many / in "%s"' % dur)

      dur = dur.split('/')
      (num,unit) = Duration.split_unit(dur[0])
      s = '%s*%s' % (num,Duration.get_mult(unit))

      if len(dur)>1:
        (num,stat) = Duration.split_unit(dur[1])
        s += '*max(1,int(%s/%s))' % (Duration.get_mult(stat),num)

      rds.append(s)

    return '+'.join(rds)

  # @param s (str) text to parse
  # @param char (Character)
  # @return (int) number of rounds
  # @raise ValueError if we need a Character but don't have one
  @staticmethod
  def parse(s,char):

    s = Duration.to_rds(s)

    # expand $level and $caster_level
    for unit in Duration.UNITS.values():
      if isinstance(unit,str) and unit.startswith('$'):
        s = s.replace(unit,'char.stats["%s"].value' % unit[1:])
    if 'char.stats' in s and not char:
      raise ValueError('string references Stats but missing Character')

    return (s,eval(s))

  # @param dur (str) [None] the duration text to parse (None = infinite)
  # @param char (Character) [None]
  def __init__(self,dur=None,char=None):

    (self.raw,self.original) = Duration.parse(dur,char)
    self.rounds = self.original

  # @param dur (int,Duration) [1] value to subtract from remaining time
  # @return (bool) True if this Duration has expired
  # @raise TypeErrpr on dur
  def advance(self,dur=1):

    if isinstance(dur,Duration):
      dur = dur.rounds
    elif not isinstance(dur,int):
      raise TypeError('invalid type "%s"' % dur.__class__.__name__)

    if self.rounds==Duration.INF:
      return False
    self.rounds = max(0,self.rounds-dur)
    return self.expired()

  # @return (bool) if we're expired
  def expired(self):

    return self.rounds==0

  def reset(self):

    self.rounds = self.original

  # decompose into sum of years, days, hours, minutes, rounds
  # @return (str)
  def __str__(self):

    if self.rounds==Duration.INF:
      return 'infinite'

    s = []
    x = self.rounds
    for (num,name) in Duration.NAMES:
      if num<x:
        s.append('%s%s' % (x/num,name))
        x = x%num
    return '+'.join(s)

###############################################################################
# Effect class
#   - links a Duration to one or more bonuses
#   - the same Bonus object can be used by multiple Effects
#   - turning an Effect on/off intelligently turns on/off its Bonuses
###############################################################################

class Effect(Field):

  # @param name (str)
  # @param bonuses (str,list of str) bonuses conferred by this Effect
  # @param duration (Duration) [None] defaults to infinite
  # @param text (str) [None]
  # @param active (None,bool) whether this Effect is active
  #   if bool, our bonuses will get toggled; if None they won't
  #
  # @rase TypeError on duration
  def __init__(self,name,bonuses,duration=None,text=None,active=None):

    self.name = name
    self.bonuses = bonuses if isinstance(bonuses,list) else [bonuses]
    self.duration = duration or Duration()
    self.text = text
    self.active = active

    self.last = active
    self.char = None

    if not isinstance(self.duration,Duration):
      raise TypeError('duration must be Duration not "%s"'
          % self.duration.__class__.__name__)

  # @param char (Character)
  def plug(self,char):

    for name in self.bonuses:
      bonus = char.bonuses[name]
      bonus.usedby.add(self.name)
      if self.active is not None:
        if self.active:
          bonus.on()
        else:
          bonus.off()
    self.char = char

  # @raise RuntimeError if plug() wasn't called first
  def unplug(self):

    if not self.char:
      raise RuntimeError('plug() must be called before unplug()')

    for name in self.bonuses:
      bonus = char.bonuses[name]
      bonus.usedby.remove(self.name)
      bonus.off()
    self.char = None

  # @return (bool) if not manually set, tracks duration
  def is_active(self):

    if self.active is not None:
      return self.active
    return not self.duration.expired()

  def on(self):
    self.toggle(True)

  def off(self):
    self.toggle(False)

  # @param new (bool)
  def toggle(self,new):

    self.last = self.active
    self.active = new
    for name in self.bonuses:
      self.char.bonuses[name].toggle(new)

  # see Bonus.revert()
  def revert(self):

    self.active = self.last
    for name in self.bonuses:
      self.char.bonuses[name].revert()

  # looks like: {+} NAME DURATION BONUSES
  # can also start with {-} or {?}
  # @return (str)
  def __str__(self):

    actives = [b.active for b in self.bonuses]
    if all(actives):
      act = '+'
    elif any(actives):
      act = '?'
    else:
      act = '-'
    names = [b.name for b in self.bonuses]
    return '{%s} %s %s (%s)' % (act,self.name,self.duration,','.join(names))

  # @return (str)
  def str_all(self):

    l =      ['duration | %s' % self.duration]
    l.extend([' bonuses | %s' % b for b in self.bonuses])
    l.append( '  active | %s/%s (init: %s)' % (
        len([b for b in self.bonuses if b.active]),
        len(self.bonuses),
        {True:'+',False:'-',None:'='}[self.active]
    ))
    l.append( '    text | '+self.text)
    return '\n'.join(l)

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

###############################################################################
# Event class
#   - WIP
###############################################################################

class Event(object):

  # hp<=0, nonlethal>=hp

  def __init__(self):
    raise NotImplementedError

###############################################################################
# Pathfinder character class
#   - includes a setup wizard via the "wiz" command
#   - new class PathfinderSkill subclasses Stat
###############################################################################

class Pathfinder(Character):

  STATS = Character.STATS.copy()
  STATS.update([

  ('level',1),('hd','$level'),('caster_level','$level'),

  ('size',0),('legs',2),
  ('_size_index','4 if $size not in [8,4,2,1,0,-1,-2,-4,-8] else [8,4,2,1,0,-1,-2,-4,-8].index($size)'),

  ('strength',10),('dexterity',10),('constitution',10),
  ('intelligence',10),('wisdom',10),('charisma',10),
  ('str','int(($strength-10)/2)'),
  ('dex','int(($dexterity-10)/2)'),
  ('con','int(($constitution-10)/2)'),
  ('int','int(($intelligence-10)/2)'),
  ('wis','int(($wisdom-10)/2)'),
  ('cha','int(($charisma-10)/2)'),

  ('hp_max',0),('hp','$hp_max+$hd*($con-#con)'),('nonlethal',0),
  ('initiative','$dex'),('dr',0),('speed',30),

  ('armor_check',0),('_max_dex',99),('spell_fail',0),

  ('_ac_armor',0),('_ac_shield',0),('_ac_dex','min($dex,$_max_dex)'),
  ('_ac_nat',0),('_ac_deflect',0),('_ac_misc',0),
  ('ac','10+$_ac_armor+$_ac_shield+$_ac_dex+$size+$_ac_nat+$_ac_deflect+$_ac_misc'),
  ('ac_touch','10+$_ac_dex+$size+$_ac_deflect+$_ac_misc'),
  ('ac_ff','10+$_ac_armor+$_ac_shield+$size+$_ac_nat+$_ac_deflect+$_ac_misc'),

  ('fortitude','$con'),('reflex','$dex'),('will','$wis'),

  ('bab',0),('sr',0),('melee','$bab+$size+$str'),('ranged','$bab+$size+$dex'),

  ('cmb','$melee-2*$size'),
  ('cmd','10+$bab+$str+$_ac_dex+$_ac_deflect+$_ac_misc-$size'),

  ('acp','0'),

  ('_carry_size','([0.125,0.25,0.5,0.75,1,2,4,8,16] if $legs==2 else [0.25,0.5,0.75,1,1.5,3,6,12,24])[$_size_index]'),
  ('carry_heavy','$_carry_size*(10*$strength if $strength<11 else 2**int(($strength-11)/5)*[200,115,130,150,175][$strength%5])'),
  ('carry_light','int($carry_heavy/3)'),
  ('carry_medium','int(2*$carry_heavy/3)'),
  ('carry_lift_head','$carry_heavy'),
  ('carry_lift_ground','2*$carry_heavy'),
  ('carry_drag','5*$carry_heavy'),

  ('spell_mod',0),('spells_mod',0),('spell_dc','10+$spell_mod'),
  ('concentration','$caster_level+$spell_mod')

  ])

  SKILLS = OrderedDict([

  ('acrobatics','$dex'),('appraise','$int'),('bluff','$cha'),('climb','$str'),
  ('craft','$int'),('diplomacy','$cha'),('disable_device','$dex'),
  ('disguise','$cha'),('escape_artist','$dex'),('fly','$dex'),
  ('handle_animal','$cha'),('heal','$wis'),('intimidate','$cha'),

  ('knowledge_arcana','$int'),('knowledge_dungeoneering','$int'),
  ('knowledge_engineering','$int'),('knowledge_geography','$int'),
  ('knowledge_history','$int'),('knowledge_local','$int'),
  ('knowledge_nature','$int'),('knowledge_nobility','$int'),
  ('knowledge_planes','$int'),('knowledge_religion','$int'),

  ('linguisitics','$int'),('perception','$wis'),('perform','$cha'),
  ('profession','$wis'),('ride','$dex'),('sense_motive','$wis'),
  ('sleight_of_hand','$dex'),('spellcraft','$int'),('stealth','$dex'),
  ('survival','$wis'),('swim','$str'),('use_magic_device','$cha')

  ])

  SKILLS_TRAINED_ONLY = ['disable_device','handle_animal','knowledge',
      'linguisitics','profession','sleight_of_hand','spellcraft',
      'use_magic_device']

  TEXTS = Character.TEXTS.copy()
  TEXTS.update({'race':'','class':'','race_traits':''})

  BONUS_TYPES = ('alchemical','armor','circumstance','competence','deflection',
      'dodge','enhancement','inherent','insight','luck','morale',
      'natural_armor','profane','racial','resistance','sacred','shield',
      'size','trait','penalty','none')
  BONUS_STACK = ('none','dodge','circumstance','racial','penalty')
  BONUS_PERM = ('inherent','racial','trait')

  AC_BONUS = {'armor':'_ac_armor','deflection':'_ac_deflect','dodge':'_ac_dex',
      'natural_armor':'_ac_nat','shield':'_ac_shield','size':'_ac_size'}

  ABILITIES = ['strength','dexterity','constitution',
      'intelligence','wisdom','charisma']
  SAVES = ['fortitude','reflex','will']

  SIZE_NAMES = OrderedDict([
      ('f','fine'),
      ('d','diminutive'),
      ('t','tiny'),
      ('s','small'),
      ('m','medium'),
      ('l','large'),
      ('h','huge'),
      ('g','gargantuan'),
      ('c','colossal')
  ])
  SIZES = [8,4,2,1,0,-1,-2,-4,-8]

  RACE_INDEX = ['size','speed','abilities','bonuses','traits','manual']
  RACE_INFO = {
      'dwarf':['m',20,'245',
          [   ['defensive_training',4,'ac','dodge','vs subtype(giant)'],
              ['hardy',2,SAVES,'vs poison,spells,spell-like-abilities'],
              ['stability',4,'cmd','vs bull-rush,trip while standing on ground'],
              ['greed',2,'appraise','on non-magical items containing gems/metals'],
              ['stonecunning',2,'perception','none','to notice unusual stonework'],
              ['hatred',1,['melee','ranged'],'vs subtype(orc,goblinoid)']
          ],
          [   'darkvision 60ft',
              'weapons: battleaxe,heavy_pick,warhammer',
              'auto perception check within 10ft of unusual stonework'
          ],
          ['speed never reduced by armor/encumbrance']
      ],
      'elf':['m',30,'132',
          [   ['immunities',2,SAVES,'vs enchantment spells/effects'],
              ['keen_senses',2,'perception'],
              ['magic',2,'caster_level','to overcome spell resistance'],
              ['magic_items',2,'spellcraft','to identify magic items']
          ],
          [   'immune to magic sleep',
              'low-light-vision',
              'weapons: longbow,longsword,rapier,shortbow'
          ],
          []
      ],
      'gnome':['s',20,'250',
          [   ['defensive_training',4,'ac','dodge','vs subtype(giant)'],
              ['illusion_resistance',2,SAVES,'vs illusion spells/effects'],
              ['keen_senses',2,'perception'],
              ['magic',1,'spell_dc','none','for illusion spells'],
              ['hatred',1,['melee','ranged'],'none','vs subtype(reptilian,goblinoid)']
          ],
          ['low-light-vision'],
          ['+2 on 1 craft or profession','gnome_magic']
      ],
      'halfelf': ['m',30, None,
          [   ['immunities',2,SAVES,'vs enchantment spells/effects'],
              ['keen_senses',2,'perception'],
          ],
          [   'immune to magic sleep',
              'low-light-vision',
              'count as both elves and humans',
              'choose 2 favored classes'
          ],
          ['skill focus at 1st level']
      ],
      'halforc': ['m',30, None,
          [['intimidating',2,'intimidate']],
          ['darkvision 60ft','count as both orcs and humans'],
          ['ferocity 1/day for 1 round']
      ],
      'halfling': ['s',20,'150',
          [   ['fearless',2,SAVES,'vs fear'],
              ['luck',1,SAVES],
              ['sure_footed',2,['acrobatics','climb']],
              ['keen_senses',2,'perception']
          ],
          ['weapons: sling'],
          []
      ],
      'human':    ['m',30, None,
          [],
          ['+1 skill rank per level'],
          ['bonus feat at 1st level']
      ]
  }

  CLASS_INDEX = ['skills','bab','saves','cast_mod']
  CLASS_INFO = {
      'barbarian': ['10011000001010000001000010010000110','1.00','100',None],
      'bard':      ['11111101100011111111111111101111001','0.75','011','cha'],
      'cleric':    ['01001100000101000100111100101010000','0.75','101','wis'],
      'druid':     ['00011000011100001001000010110010110','0.75','101','wis'],
      'fighter':   ['00011000001010110000000000110000110','1.00','100',None],
      'monk':      ['10011000100010000100001011111001010','0.75','111',None],
      'paladin':   ['00001100001100000000101000111010000','1.00','101','cha'],
      'ranger':    ['00011000001110101001000010110011110','1.00','110','wis'],
      'rogue':     ['11111111100010100010000111101101011','0.75','010',None],
      'sorcerer':  ['01101000010011000000000000100010001','0.50','001','cha'],
      'wizard':    ['01001000010001111111111100100010000','0.50','001','int'],

      'alchemist':   ['01000010010101000001000010100110101','0.75','110','int'],
      'cavalier':    ['00111100001010000000000000111000010','1.00','100',None],
      'gunslinger':  ['10111000001110010010000010110100110','1.00','110',None],
      'inquisitor':  ['00111101000111100001011010111011110','0.75','101','wis'],
      'magus':       ['00011000010011100000010000110010011','0.75','101','int'],
      'oracle':      ['00001100000100000100011000101010000','0.75','001','cha'],
      'summoner':    ['00001000011000000000000100110010001','0.75','001','cha'],
      'vigilante':   ['11111111100010110010000011111101111','0.75','011',None],
      'witch':       ['00001000010111000101010000100010001','0.50','011','int'],

      'arcane archer':         ['00000000000000000000000010010001100','1.00','332',None],
      'arcane trickster':      ['11110111100001111111111010001111010','0.50','233',None],
      'assassin':              ['10110111100010000000000110001101011','0.75','232',None],
      'dragon disciple':       ['00000100110001111111111010000010000','1.00','323',None],
      'duelist':               ['10100000100000000000000011001000000','1.00','232',None],
      'eldritch knight':       ['00010000000001000000100100011010010','1.00','322',None],
      'loremaster':            ['01000100001101111111111101000010001','0.50','223',None],
      'mystic theurge':        ['00000000000001000000001000001010000','0.50','223',None],
      'pathfinder chronicler': ['01100101100011111111111111011100101','0.75','233',None],
      'shadowdancer':          ['10100101100000000000000011000101000','0.75','232',None]
  }

  CLASS_SAVES = ['int(x/3)','2+int(x/2)','int((x+1)/3)','1+int((x-1)/2)']

  # [TODO] conditional jump modifier based on move speed
  # [TODO] craft, profession, perform
  # [TODO] class skills
  # [TODO] max_dex
  # [TODO] consider using _base_reflex etc.

  # @param args (list) passed to Character
  # @param kwargs (dict) passed to Character
  def __init__(self,*args,**kwargs):

    super(Pathfinder,self).__init__(*args,**kwargs)
    self.export += ['dmg','heal','skill','wiz']

  # include skills in the setup method
  # see Character._setup()
  def _setup(self,ignore_dupes=False):

    super(Pathfinder,self)._setup(ignore_dupes)
    for (name,formula) in self.SKILLS.items():
      skill = PathfinderSkill(name,formula)
      try:
        self._add_stat(skill)
      except DuplicateError:
        if ignore_dupes:
          pass
        else:
          raise

  # include hp, status, ac
  # @return (str)
  def _get_prompt(self):
    return ('[ %s   %s   AC/To/FF: %s/%s/%s ]\n \___ ' % (
        self._get_name(),
        self._health(),
        self.stats['ac'].value,
        self.stats['ac_touch'].value,
        self.stats['ac_ff'].value
    ))

  # @return (int) our maximum hp (including bonuses except for _damage)
  def _max_hp(self):

    hp = self.stats['hp'].value
    if '_damage' not in self.bonuses:
      return hp
    return hp-self.bonuses['_damage'].value

  # @return (5-tuple)
  #   #0 (int) current hp
  #   #1 (int) max hp
  #   #2 (int) nonlethal damage
  #   #3 (int) the hp value when we die
  #   #4 (str) one of: up,DEAD,DYING,STAGGERED,UNCON
  def _get_status(self):

    current = self.stats['hp'].value
    max_hp = self._max_hp()
    nonlethal = self.stats['nonlethal'].value
    death = -self.stats['constitution'].value

    status = 'up'
    if current<=death:
      status = 'DEAD'
    elif current<0:
      status = 'DYING'
    elif current==0:
      status = 'STAGGERED'
    elif nonlethal>=current:
      status = 'UNCON'

    return (current,max_hp,nonlethal,death,status)

  # @return (str) hp and status info
  def _health(self):

    (current,max_hp,nonlethal,death,status) = self._get_status()
    non = '' if nonlethal==0 else '   Nonlethal: %s' % nonlethal
    death = '' if current>0 else '   Death: %s' % death
    status = '' if status=='up' else '   %s' % status
    return 'HP: %s/%s%s%s%s' % (current,max_hp,non,death,status)

  # set our size modifier and text
  # @param size (str) first letter or whole word of the standard sizes:
  #   fine,diminutive,tiny,small,medium,large,huge,gargantuan,colossal
  def _set_size(self,size):

    size = size[0].lower()
    i = list(self.SIZE_NAMES.keys()).index(size)
    self.set_stat('size',self.SIZES[i],self.SIZE_NAMES[size])

###############################################################################
# User commands
###############################################################################

  # [TODO] consider making massive damage an Event for consistency
  def dmg(self,damage,nonlethal=False):
    """
    take damage and update HP
      - damage (int) amount of damage to take (positive)
      - [nonlethal = False] (bool)
    """

    damage = int(damage)
    if damage<=0:
      raise ValueError('damage must be > 0')

    if nonlethal:
      self.set_stat('nonlethal',self.stats['nonlethal'].value+damage)
    else:
      if '_damage' in self.bonuses:
        self.set_bonus('_damage',self.bonuses['_damage'].value-damage)
      else:
        self.add_bonus('_damage',-damage,'hp')
      if damage>=50 and damage>=int(self._max_hp()/2):
        print('!!! Massive damage')

  def heal(self,damage):
    """
    heal damage and update HP
      - damage (int) amount of damage to heal (positive)
    """

    damage = int(damage)
    if damage<=0:
      raise ValueError('healing must be > 0')

    nonlethal = min(damage,self.stats['nonlethal'].value)
    try:
      current = -self.bonuses['_damage'].value
    except KeyError:
      current = 0
    damage = min(damage,current)

    if '_damage' in self.bonuses and damage:
      self.set_bonus('_damage',self.bonuses['_damage'].value+damage)
      if self.bonuses['_damage'].value==0:
        self.del_bonus('_damage')
    if nonlethal:
      self.set_stat('nonlethal',self.stats['nonlethal'].value-nonlethal)

  def skill(self,action='info',name=None,value=0):
    """
    manage skills
      - action (string) see below
      - [name = None] (string,list) the skill(s) to modify
        - leaving this field blank acts on all skills
      - [value = 0] (object)

    actions:
      - info [value = UNUSED] give some quick stats
      - list [value = None] show summary text
      - rank [value = 0] set skill ranks
      - class [value = UNUSED] set as class skills
      - unclass [value = UNUSED] set as not class skills
    """

    actions = ['info','list','rank','class','unclass']
    if action not in actions:
      raise ValueError('invalid sub-command "%s"' % action)

    name = name or list(self.SKILLS.keys())
    if not isinstance(name,list):
      name = [name]
    if action=='info':
      name = ['info']

    if action=='info':
      def func(name):
        skills = [x for x in self.stats.values()
            if isinstance(x,PathfinderSkill)]
        clas = reduce(lambda a,b: a+b.class_skill,skills,0)
        ranks = reduce(lambda a,b: a+b.ranks,skills,0)
        return '%s class skills\n%s ranks' % (clas,ranks)

    elif action=='list':
      func = lambda name: self.stats[name]

    elif action=='rank':
      func = lambda name: self.stats[name].set_ranks(int(value))

    elif action=='class':
      func = lambda name: self.stats[name].set_cskill()

    elif action=='unclass':
      func = lambda name: self.stats[name].set_cskill(False)

    for n in name:
      try:
        result = func(n)
      except Exception as e:
        result = '*** %s (%s) %s' % (e.__class__.__name__,n,e.args[0])
      if result:
        print(result)

###############################################################################
# Overrides
###############################################################################

  def add_bonus(self,name,value,stats,typ=None,cond=None,text=None,active=True):

    if isinstance(stats,str) and stats.lower()=='ac':
      stats = self.AC_BONUS.get(typ,'_ac_misc')
    super(Pathfinder,self).add_bonus(name,value,stats,typ,cond,text,active)

###############################################################################
# Setup wizard
###############################################################################

  def wiz(self,action='help'):
    """
    character setup wizard for some automation
      - action (string) see below

    actions:
      - all [N/A] execute each [ALL] action below in order
      - level [ALL] set character level
      - race [ALL] set race and add racial bonuses
      - class [ALL] set class, some stats, and class skills
      - abilities [ALL] set ability scores and racial adjustments
      - skill [ALL] set skill ranks
      - size [ONE] set size (e.g. medium)
      - class_skill [ONE] set class skills

    special inputs:
      - skip - for the 'all' action, skip the current sub-action
      - quit - exit the wizard making no further changes
    """

    actions = ['level','race','class','abilities','skill']
    standalone = ['size','class_skill']
    if action not in actions+standalone and action not in ('help','all'):
      raise ValueError('invalid sub-command "%s"' % action)

    if action=='help':
      print('(wiz) [all] (%s)' % ('|'.join(sorted(actions+standalone))))

    else:
      actions = actions if action=='all' else [action]
      try:
        for action in actions:
          action = getattr(self,'_wiz_'+action)
          if len(actions)>1:
            print('\n=== %s' % action.__doc__)
          try:
            action()
          except UserSkipException:
            continue
      except UserQuitException:
        pass

  def _wiz_level(self):
    """Character level"""

    level = self._input(
        'Enter level',
        parse = int,
        valid = lambda x: x>0
    )
    self.set_stat('level',level)

  def _wiz_race(self):
    """Race"""

    if self.texts['race'].text:
      print("+++ WARNING: if you've already run this command don't re-run it")

    race = self._input(
        'Enter race name',
        parse = lambda x: x.replace('-','').replace('_',''),
        valid = lambda x: x in self.RACE_INFO,
        blank = False
    )
    self.set_text('race',race)
    info = self.RACE_INFO[race]

    size = info[self.RACE_INDEX.index('size')]
    self._set_size(size)

    speed = info[self.RACE_INDEX.index('speed')]
    self.set_stat('speed',speed)

    bonuses = info[self.RACE_INDEX.index('bonuses')]
    if len(bonuses):
      print('--- racial bonuses')
    for bonus in bonuses:
      args = bonus[:3]+['racial']
      args[0] = '%s_%s' % (race,args[0])
      while len(bonus)>3:
        s = bonus.pop()
        if s in self.BONUS_TYPES:
          args[3] = s
        else:
          args += [s]
      self.add_bonus(*args)
      print('  %s' % self.bonuses[args[0]]._str())

    traits = info[self.RACE_INDEX.index('traits')]
    if traits:
      self.set_text('race_traits','\n'.join(traits))
      print('--- all text race_traits')
      for t in traits:
        print('  %s' % t)

    manual = info[self.RACE_INDEX.index('manual')]
    for s in manual:
      print('+++ NOTE: %s' % s)

  def _wiz_class(self):
    """Class skills, BAB, Saves"""

    if self.texts['class'].text:
      print("+++ WARNING: if you've already run this command don't re-run it")

    clas = self._input(
        'Enter class name',
        valid = lambda x: x in self.CLASS_INFO,
        blank = False
    )
    self.set_text('class',clas)
    info = self.CLASS_INFO[clas]

    names = list(self.SKILLS.keys())
    one_hot = info[self.CLASS_INDEX.index('skills')]
    skills = []
    for (i,x) in enumerate(one_hot):
      if x=='1':
        skill = names[i]
        skills.append(skill)
        self.stat[skill].set_cskill()
    print('class skills: %s' % ','.join(skills))

    prog = info[self.CLASS_INDEX.index('bab')]
    self.set_stat('bab','int(%s*$level)' % prog)
    print('bab progression: %s' % prog)

    mods = ('con','dex','wis')
    progs = info[self.CLASS_INDEX.index('saves')]
    good = []
    for (save,mod,prog) in zip(self.SAVES,mods,progs):
      prog = int(prog)
      if prog in (1,3):
        good.append(save)
      base = self.CLASS_SAVES[prog].replace('x','$level')
      new = '$%s+%s' % (mod,base)
      self.set_stat(save,new,force=True)
    print('good saves: %s' % ','.join(good))

    mod = info[self.CLASS_INDEX.index('cast_mod')]
    if mod:
      self.set_stat('spell_mod','$'+mod)
      self.set_stat('spells_mod','#'+mod)
      print('casting mod: %s' % mod)

  def _wiz_abilities(self):
    """Ability scores"""

    self._inputs(
        [(  '%s (%s)' % (a,self.stats[a].normal),
            a,
            lambda k,v:self.set_stat(k,str(v))
        ) for a in self.ABILITIES],
        parse = int,
        valid = lambda x: x>=0
    )

    race = self.texts['race'].text
    if race and self._yn('Adjust for %s' % race):
      info = self.RACE_INFO[race]
      abilities = info[self.RACE_INDEX.index('abilities')]
      for (i,a) in enumerate(abilities):
        a = self.ABILITIES[int(a)]
        adjust = (-2 if i==2 else 2)
        new = self.stats[a].value+adjust
        self.set_stat(a,new)
        print(('+' if adjust>0 else '')+' '+a)

  def _wiz_skill(self):
    """Skill ranks"""

    print('+++ Max ranks: %s' % self.stats['level'].value)
    self._inputs(
        [(  '%s (%s)' % (s,self.stats[s].ranks),
            s,
            lambda k,v:self.stats[k].set_ranks(v)
        ) for s in self.SKILLS],
        parse = int,
        valid = lambda x: x>=0 and x<=self.stats['level'].value
    )

  def _wiz_size(self):
    """Size"""

    size = self._input(
        'Enter size',
        valid = lambda x: x[0] in self.SIZE_NAMES.keys()
    )
    self._set_size(size)

  def _wiz_class_skill(self):
    """Class skills"""

    self._yns(
        [(  '%s (%s)' % (s,'ny'[self.stats[s].class_skill]),
            s,
            lambda k,v:self.stats[k].set_cskill(v)
        ) for s in self.SKILLS]
    )

###############################################################################
# PathfinderSkill class
#   - subclasses Stat
###############################################################################

class PathfinderSkill(Stat):

  FIELDS = OrderedDict(
      [(k,v) for (k,v) in Stat.FIELDS.items()] +
      [('ranks',int),('class_skill',bool)]
  )

  # the first 6 args get passed to Stat
  # @param ranks (int) [0] skill ranks
  # @param class_skill (bool) [False]
  def __init__(self,*args,**kwargs):

    mine = list(args)[6:]
    if mine:
      self.ranks = mine.pop(0)
    else:
      self.ranks = kwargs.pop('ranks',0)
    if mine:
      self.class_skill = mine.pop(0)
    else:
      self.class_skill = kwargs.pop('clas',False)

    # Stat.__init__() with correct args
    super(PathfinderSkill,self).__init__(*args[:6],**kwargs)

    f = '+@ranks+(3 if @class_skill and @ranks else 0)'
    if '$dex' in self.original or '$str' in self.original:
      f += '+${acp}'

    # we need a check here so we don't double up on the +3 class skills when
    # loading from a file
    # [TODO] consider a cleaner way of controlling this
    if f not in self.formula:
      self.set_formula(self.formula+f)

    self.trained_only = False

    # needed for Stat.copy()
    self.COPY += ['ranks','class_skill']

  # @param new (bool) [True]
  def set_cskill(self,new=True):

    self.class_skill = new
    self.calc()

  # @param value (int)
  # @raise TypeError on value
  # @raise ValueError if value<0 or value>level
  def set_ranks(self,value):

    if not isinstance(value,int):
      raise TypeError('parameter "value" must be int')

    if value<0:
      raise ValueError('ranks must be >= 0')

    level = self.char.stats['level'].value
    if value>level:
      raise ValueError('ranks must be <= level=%s' % level)

    self.ranks = value
    self.calc()

  # @param char (Character)
  def plug(self,char):

    super(PathfinderSkill,self).plug(char)

    # determine if we're trained only or not
    for skill in self.char.SKILLS_TRAINED_ONLY:
      if self.name.startswith(skill):
        self.trained_only = True
        break

  # looks like: c!
  #   c (class_skill)
  #   ! OR t (trained_only) based on ranks>0
  # @return (str)
  def _str_flags(self):

    cs = '-c'[self.class_skill]
    tr = ['-!'[self.trained_only],'t'][self.ranks>0]
    return '%s%s' % (cs,tr)

  # @return (str)
  def str_all(self):

    s = super(PathfinderSkill,self).str_all()

    l = ['  ranks | %s' % self.ranks]
    l.append(' cskill | %s' % self.class_skill)
    l.append('trained | %s' % ['anyone','only'][self.trained_only])

    return s+'\n'+'\n'.join(l)
