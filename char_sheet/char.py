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

# ===== backend =====
# [TODO] experience
# [TODO] raise warning / limit skill ranks? _total_ranks stat?
# [TODO] reset bonus original values dynamically to account for leveling up
# [TODO] save bonus raw to file
# [TODO] make durations mathy

# ===== ui =====
# [TODO] pre-made/custom views (e.g. show all abilities)
# [TODO] regex searching
# [TODO] strip tabs/newlines from input
# [TODO] report modification to the cli somehow (add,set,upgrade...) decorator?
# [TODO] incrementing? at least for skill ranks?
# [TODO] include effect name when printing bonuses or stats
# [TODO] check if you can actually set "active" from the CLI
# [TODO] make more commands accept lists ("all" command specifically)

import os,time,inspect,importlib
from collections import OrderedDict
from functools import reduce

from dnd.dice import Dice
from dnd.char_sheet.fields import *
from dnd.char_sheet.errors import *

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

  # @return (dict) name:class pairs for each system we know about
  #   @key (str) name of the file/class
  #   @value (class) the class itself for instantiation
  @staticmethod
  def get_systems():

    path = os.path.abspath(os.path.dirname(__file__))
    path = os.path.join(path,'systems')

    systems = {'character':Character}
    for fname in os.listdir(path):
      if fname.startswith('_'):
        continue
      name = fname.split('.')[0]
      loc = os.path.join(path,fname)
      spec = importlib.util.spec_from_file_location(name,loc)
      mod = importlib.util.module_from_spec(spec)
      spec.loader.exec_module(mod)
      for (name,cls) in inspect.getmembers(mod,inspect.isclass):
        if issubclass(cls,Character) and cls!=Character:
          systems[name.lower()] = cls

    return systems

  # create a new character
  # @param name (None,str) [None] name of the class (defaults to Character)
  # @param args (list) passed to the Character
  # @param kwargs (dict) passed to the Character
  # @return (Character)
  @staticmethod
  def new(name=None,*args,**kwargs):

    name = name or 'character'
    return Character.get_systems()[name.lower()](*args,**kwargs)

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
    except Exception:
      effect.plug(self)
      self.effects[name] = effect
      raise

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
