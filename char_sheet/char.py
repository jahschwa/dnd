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

#    get : g     add : a    set : s      del : d        all : l      reset : r
# search : ?      on : +    off : -   revert : v    advance : ++    create : c
#   roll : !
#   stat : s   bonus : b   text : t   effect : e

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

# ===== high-level / large-scale =====
# [TODO] consider another way for set_stat() to interact with plug/unplug?
# [TODO] decide what goes in here and what goes in the CLI
# [TODO] Bonus subclasses Stat but only allows root nodes? allows formulas
# [TODO] stat classes for setting (and getting?) e.g. abilities, skills
# [TODO] common effect library for importing: feats, spells, conditions
# [TODO] consolidate / move to fields.py add/set/del commands
# [TODO] consider moving wizard framework from Pathfinder to Character
# [TODO] abstract output into functions in cli somehow

# ===== backend =====
# [TODO] reset bonus original values dynamically to account for leveling up
# [TODO] save bonus raw to file

# ===== ui =====
# [TODO] strip tabs/newlines from input
# [TODO] report modification to the cli somehow (add,set,upgrade...) decorator?
# [TODO] incrementing? at least for skill ranks?
# [TODO] include effect name when printing bonuses or stats
# [TODO] check if you can actually set "active" from the CLI
# [TODO] make more commands accept lists ("all" command specifically)
# [TODO] ability to rename things
# [TODO] tutorial help text

import os,re,time,inspect,importlib
from collections import OrderedDict
from functools import reduce

from dnd.dice import Dice
from dnd.duration import Duration
from dnd.char_sheet.fields import *
from dnd.char_sheet.errors import *
from dnd.char_sheet.dec import arbargs

###############################################################################
# Universe class
###############################################################################

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

  # @return (dict) name:class (str:class) pairs for each Field we know about
  @staticmethod
  def _get_fields():

    return {k:v for (k,v) in globals().items()
        if inspect.isclass(v) and issubclass(v,Field) and v!=Field}

  # @return (dict) name:class (str:class) pairs for each System we know about
  @staticmethod
  def _get_systems(lower=False):

    path = os.path.abspath(os.path.dirname(__file__))
    path = os.path.join(path,'systems')

    systems = {'%sharacter'%('Cc'[lower]) : Character}
    fields = {}
    for fname in os.listdir(path):
      if fname.startswith('_'):
        continue
      name = fname.split('.')[0]
      loc = os.path.join(path,fname)
      spec = importlib.util.spec_from_file_location(name,loc)
      mod = importlib.util.module_from_spec(spec)
      spec.loader.exec_module(mod)
      for (name,cls) in inspect.getmembers(mod,inspect.isclass):
        if issubclass(cls,Character):
          systems[name.lower() if lower else name] = cls
        if issubclass(cls,Field):
          fields[name.lower() if lower else name] = cls

    fields.update(Character._get_fields())
    return (systems,fields)

  # create a new character
  # @param name (None,str) [None] name of the class (defaults to Character)
  # @param args (list) passed to the Character
  # @param kwargs (dict) passed to the Character
  # @return (Character)
  @staticmethod
  def new(name=None,*args,**kwargs):

    name = name or 'character'
    (chars,_) = Character._get_systems(lower=True)
    return chars[name.lower()](*args,**kwargs)

  # load a character from file
  # @param name (str) file path
  # @return (Character)
  @staticmethod
  def load(name):

    with open(name,'r') as f:
      lines = [x.strip('\n') for x in f.readlines()]

    errors = []
    (chars,fields) = Character._get_systems()

    char = None
    for (i,line) in enumerate(lines):
      if not line:
        continue
      if not char:
        if line not in chars:
          errors.append('line %.4d | unknown character system "%s"'
              % (i+1,line))
          break
        char = chars[line](setup=False)
      else:
        line = line.split('\t')
        if line[0] not in fields:
          errors.append('line %.4d | unknown object type "%s"' % (i+1,line[0]))
          continue
        try:
          obj = fields[line[0]].load(line[1:])
          if not errors:
            char._get_add_method(obj.__class__)(obj)
        except Exception as e:
          errors.append('line %.4d |   %s' % (i+1,' / '.join(line)))
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
      ('t','text'),
    ])

    # register commands
    self.export = [
      'search',
      'on',
      'off',
      'revert',
      'get',
      'all',
      'advance',
      'reset',
      'roll',
    ]

    # register commands that have sub commands
    self.export_prefix = ['add', 'set', 'del', 'create']

    # register aliases
    self.export_alias = {
      '?' : 'search',
      '+' : 'on',
      '-' : 'off',
      'v' : 'revert',
      'g' : 'get',
      'l' : 'all',
      'a' : 'add',
      's' : 'set',
      'd' : 'del',
      '++': 'advance',
      'r' : 'reset',
      'c' : 'create',
      '!' : 'roll',
    }

    # register sub command aliases
    # [TODO] improve and include more objects
    self.export_sub_alias = {a:b for (a,b) in self.letters.items() if a in 'sbet'}

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

  # save this character
  # @param name (str) file path
  def save(self,name):

    s = self.__class__.__name__+'\n'
    for typ in self.letters.values():
      for obj in getattr(self,typ).values():
        s += ('%s\t' % obj.__class__.__name__)+'\t'.join(obj.save())+'\n'

    with open(name,'w') as f:
      f.write(s)

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

  @arbargs
  def roll(self,*args,**kwargs):
    """
    roll some dice; if the first argument is a valid stat or list:
      - stat (string,list) the stat(s) to roll
    otherwisethe args are a dice string and we roll that:
      - dice (string) e.g. "d20" "4d6" "3d6+1d4+2"
    """

    stats = None
    if isinstance(args[0],list):
      stats = args[0]
    elif args[0] in self.stats:
      stats = [args[0]]
    else:
      return NotImplemented

    pad = len(max(stats,key=len))
    for name in stats:
      s = ('%%-%ss ' % pad) % name
      stat = self.stats[name]
      try:
        s += str(stat.roll())
      except KeyError:
        s += 'KeyError'
      except AttributeError:
        s += str(Dice('d20').roll()+stat.value)
      print(s)

  @arbargs
  def search(self,name='.*',fields=None,exclude='_',ignore_case=True,
      include_missing=False,**kwargs):
    """
    search all objects for one with a matching name
      - [name = ".*"] (string) the search term, supports python regex
        - defaults to matching everything
      - [fields = ALL] (string,list) the Fields to include in the results
      - [exclude = "_"] (string) exclude results that start with this
        - specify "*" to include everything
      - [ignore_case = True] (bool) ignore upper/lower case
      - [include_missing = False] (bool) show fields missing kwargs (see below)

    any additional keyword arguments are matched against instance variables:
      - casts the field to a string, then does regex matching
        - search root=True
        - search fields=stat value=^[^0]
      - functions starting with "is_" are automatically called
        - search fields=effect is_active=True
      - can perform custom evaluations where @ is the value of the variable
        - search fields=stat value="@ != 0"
        - search fields=effect duration="@ > 5"
        - search fields=bonus usedby="not @"
    """

    case = re.IGNORECASE if ignore_case else 0

    fields = fields or list(self.letters.values())
    if not isinstance(fields,list):
      fields = [fields]
    for field in fields:
      if field not in self.letters.values():
        raise ValueError('unknown field type "%s"' % field)

    attrs = {
        attr: (s if '@' in s else re.compile(s,case))
        for (attr,s) in kwargs.items()
    }

    r = re.compile(name,case)
    matches = []
    for (l,d) in self.letters.items():
      if d not in fields:
        continue
      for (n,obj) in getattr(self,d).items():
        if r.search(n) and (exclude=='*' or not n.startswith(exclude)):
          match = True
          for (name,key) in attrs.items():
            if hasattr(obj,name):
              attr = getattr(obj,name)
              if callable(attr) and name.startswith('is_'):
                attr = attr()
              if isinstance(key,str):
                if not eval(key.replace('@','attr')):
                  match=False
                  break
              elif not key.search(str(attr)):
                match=False
                break
            elif not include_missing:
              match = False
              break
          if match:
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

  def advance(self,duration=1,effects='*'):
    """
    advance Effects and check for their expiry
      - [duration = 1rd] (Duration) amount of time to move forward
        - bare integers are interpreted as rounds
        - valid units (e.g. 5min):
          - rd  = rounds
          - min = minutes (10 rounds)
          - hr  = hours
          - day = days
          - yr  = years
        - units can be combined with a plus sign (e.g. 1min+5rd)
        - passing "inf" will expire all Effects that aren't permanent
      - [effects = *] (string,list) effect(s) to advance (defaults to all)
    """

    if effects=='*':
      effects = self.effects.keys()
    elif not isinstance(effects,list):
      effects = [effects]

    for name in effects:
      try:
        effect = self.effects[name]
      except KeyError:
        raise KeyError('unknown effect "%s"' % name)
      if effect.is_active() and effect.advance(duration):
        print('!!! Effect expired: %s (%s)' % (name,','.join(effect.bonuses)))

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
    except FormulaError:
      old.formula = old.original
      old.plug(self)
      self.stats[name] = old
      raise

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
  def add_effect(self,name,bonuses,duration=None,text=None,active=True):
    """
    add a new Effect
      - name (string)
      - bonuses (string,list) the bonuses created by this Effect
      - [duration = None] (string) see "help advance" (None = infinite)
      - [text = None] (string)
      - [active = True] (bool) turn on/off all our bonuses
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
    """

    effect = self.effects[name]
    bonuses = bonuses or effect.bonuses
    duration = duration or effect.rounds
    try:
      effect.unplug()
      del self.effects[name]
      self.add_effect(name,bonuses,duration,effect.text,effect.is_active())
    except Exception:
      effect.plug(self)
      self.effects[name] = effect
      raise

  # @raise KeyError if name does not exist
  def del_effect(self,name):
    """
    delete an Effect
      - name (string)
    """

    try:
      self.effects[name].unplug()
    except KeyError:
      raise KeyError('unknown effect "%s"' % name)

    del self.effects[name]

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
    revert a bonus or effect to its last state
      - name (string)
    """

    if name in self.bonuses:
      self.bonuses[name].revert()
    elif name in self.effects:
      self.effects[name].revert()
    else:
      raise KeyError('unknwown bonus/effect "%s"' % name)

  # @raise KeyError if name does not exist
  def reset(self,names):
    """
    reset the duration of (and activate) effect(s)
      - name (string,list) effect(s) to reset
    """

    if not isinstance(names,list):
      names = [names]

    try:
      for name in names:
        self.effects[name].reset()
    except KeyError:
      raise KeyError('unknown effect "%s"' % name)

###############################################################################
# Setup wizard-esque commands
###############################################################################

  def create_stat(self):
    raise NotImplementedError

  def create_bonus(self):
    raise NotImplementedError

  def create_effect(self,name=None,duration=None,text=None,active=True):
    """
    create an Effect and its bonuses
      - name (string)
      - [duration = None] (string) see "help advance" (None = infinite)
      - [text = None] (string)
      - [active = True] (bool) turn on/off all our bonuses
    """

    name = name or self._input(
        'Effect name',
        blank=False,
        valid=lambda x:x not in self.effects
    )

    duration = duration or self._input(
        'Effect duration (infinite)',
        parse=Duration
    ) or None

    bonuses = []

    print('\nType "skip" at any prompt to finish entering bonuses\n')
    try:
      while True:

        n = (len(bonuses)+1)
        b_name = '_%s_%s' % (name,n)
        b_name = self._input(
            'Bonus#%s name (%s)' % (n,b_name),
            valid=lambda x:x not in self.bonuses
        ) or b_name

        b_value = self._input(
            'Bonus#%s value' % n,
            blank=False,
            parse=int
        )

        b_stats = self._input(
            'Bonus#%s stats' % n,
            blank=False,
            parse=lambda x:x.split(','),
            valid=lambda x:reduce(lambda a,b:a and (b in self.stats),x,True)
        )

        b_typ = self._input(
            'Bonus#%s type (none)' % n,
            valid=lambda x:x in self.BONUS_TYPES
        ) or None

        bonuses.append(Bonus(b_name,b_value,b_stats,b_typ))
        print('')

    except UserSkipException:
      print('\r')

    for bonus in bonuses:
      self._add_bonus(bonus)
    
    self.add_effect(name,[b.name for b in bonuses],duration,text)
    print(self.effects[name])
  
  def create_text(self):
    raise NotImplementedError
