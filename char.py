#!/usr/bin/env python

#def stat ac_dex 3
#def stat ac_armor 0
#def stat ff 10+ac_armor
#def stat touch 10+ac_dex
#def stat ac 10+ac_dex+ac_armor
#get ac
#> 13
#def bonus mage_armor ac_armor +4
#get ac,ff,touch
#> 13,10,13
#get ac,ff,touch with mage_armor
#> 17,14,13
#active mage_armor
#get ac,ff,touch
#> 17,14,13

# TODO: disallow setting backend stats without additional flag
# TODO: set should raise exception not return a boolean
# TODO: conditional bonuses
# TODO: consider another way for set_stat() to interact with plug/unplug?
# TODO: decide what goes in here and what goes in the CLI
# TODO: Bonus subclasses Stat but only allows root nodes? allows formulas
# TODO: stat classes for setting (and getting?) e.g. abilities, skills
# TODO: mark skills that can only be used if trained somehow?
# TODO: common effect library for importing: feats, spells, conditions

# Stat
#   PathfinderSkill
# Bonus
# Effect
# Item
#   Weapon
#   Armor
# Dice
# Ability
# Event
# Text

import time,inspect
from collections import OrderedDict

class DuplicateError(Exception):
  pass

class DependencyError(Exception):
  pass

class FormulaError(Exception):
  pass

class ProtectedError(Exception):
  pass

class Universe(object):
  def __contains__(self,obj):
    return True

class Character(object):

  STATS = {}
  BONUSES = Universe()

  def __init__(self,setup=True):

    self.stat = OrderedDict(); self.stats = self.stat
    self.bonus = OrderedDict(); self.bonuses = self.bonus
    self.effect = OrderedDict(); self.effects = self.effect
    self.item = OrderedDict(); self.items = self.item
    self.ability = OrderedDict(); self.abilities = self.ability
    self.event = OrderedDict(); self.events = self.event
    self.note = OrderedDict(); self.notes = self.note

    self.letters = OrderedDict([
      ('s','stat'),
      ('b','bonus'),
      ('e','effect'),
      ('i','item'),
      ('a','ability'),
      ('v','event'),
      ('n','note')])

    self.export = ['search','on','off','revert','get','all']
    self.export_prefix = ['add','set','del']
    self.export_alias = {
      '?':'search','+':'on','-':'off','r':'revert','g':'get','l':'all',
      'a':'add','s':'set','d':'del'
    }
    self.export_sub_alias = {a:b for (a,b) in self.letters.items() if a in 'sb'} # TODO

    if setup:
      self.setup()

  def save(self,name):

    s = self.__class__.__name__+'\n'
    for typ in self.letters.values():
      for obj in getattr(self,typ).values():
        s += ('%s\t' % obj.__class__.__name__)+'\t'.join(obj.save())+'\n'

    with open(name,'w') as f:
      f.write(s)

  @staticmethod
  def load(name):

    with open(name,'r') as f:
      lines = [x.strip() for x in f.readlines()]

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
          errors.append('*** %s: %s' % (e.__class__.__name__,e.message))

    return (char,errors)

  def _get_add_method(self,cls):

    if cls.__name__.lower() in self.letters.values():
      return getattr(self,'_add_'+cls.__name__.lower())
    if cls.__bases__:
      return self._get_add_method(cls.__bases__[0])
    raise KeyError('failed to get add method')

  def search(self,name,ignore='_'):

    matches = []
    for (l,d) in self.letters.items():
      for (n,obj) in getattr(self,d).items():
        if name in n and (ignore=='*' or not n.startswith(ignore)):
          matches.append('%s | %s' % (l,obj))
    return '\n'.join(matches)

  # @raise KeyError if typ does not exist
  def get(self,typ,name):

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

  # @raise KeyError if typ does not exist
  # @raise KeyError if name does not exist
  def all(self,typ,name):

    typ = typ if typ not in self.letters else self.letters[typ]
    if typ not in self.letters.values():
      raise KeyError('unknown type "%s"' % typ)

    try:
      return getattr(self,typ)[name].str_all()
    except AttributeError:
      raise KeyError('unknown %s "%s"' % (typ,name))

  # @raise ValueError if name already exists
  def _add_stat(self,stat):

    if stat.name in self.stats:
      raise DuplicateError('stat "%s" already exists' % stat.name)
    stat.plug(self)
    self.stats[stat.name] = stat

  # @raise ValueError if name already exists
  def add_stat(self,name,formula='0',text='',updated=None):

    stat = Stat(name,formula,text,updated)
    self._add_stat(stat)

  # @raise KeyError if name does not exist
  # @raise DependencyError if delete would break hierarchy
  def del_stat(self,name):

    try:
      stat = self.stats[name]
      stat.unplug()
    except KeyError:
      raise KeyError('unknown stat "%s"' % name)

  # @raise KeyError if name does not exist
  # @raise FormulaError if formula contains errors
  def set_stat(self,name,formula=None,text=None,updated=None,force=False):

    try:
      old = self.stats[name]
    except KeyError:
      raise KeyError('unknown stat "%s"' % name)

    if not force:
      if old.protected:
        raise ProtectedError('stat "%s" is protected (use force)' % name)
      if old.uses:
        raise ProtectedError('stat "%s" is not a root (use force)' % name)

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

  # @raise ValueError if name already exists
  def _add_bonus(self,bonus):

    if bonus.name in self.bonuses:
      raise ValueError('bonus "%s" already exists' % bonus.name)
    bonus.plug(self)
    self.bonuses[bonus.name] = bonus

  # @raise ValueError if name already exists
  def add_bonus(self,name,value,stats,typ=None,text=None,active=True):

    bonus = Bonus(name,int(value),stats,typ,text,active)
    self._add_bonus(bonus)

  # @raise KeyError if name does not exist
  def set_bonus(self,name,value):

    try:
      bonus = self.bonuses[name]
    except KeyError:
      raise KeyError('unknown bonus "%s"' % name)

    bonus.value = value
    bonus.calc()

  # @raise KeyError if name does not exist
  def del_bonus(self,name):

    try:
      self.bonuses[name].unplug()
    except KeyError:
      raise KeyError('unknown bonus "%s"' % name)

    del self.bonuses[name]

  # @raise KeyError if name does not exist
  def on(self,name):

    try:
      self.bonuses[name].on()
    except KeyError:
      raise KeyError('unknwown bonus "%s"' % name)

  # @raise KeyError if name does not exist
  def off(self,name):

    try:
      self.bonuses[name].off()
    except KeyError:
      raise KeyError('unknwown bonus "%s"' % name)

  # @raise KeyError if name does not exist
  def revert(self,name):

    try:
      self.bonuses[name].revert()
    except KeyError:
      raise KeyError('unknwown bonus "%s"' % name)

  def setup(self):

    for (name,formula) in self.STATS.items():
      self.add_stat(name,str(formula))

class Field(object):

  FIELDS = {}

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

class Stat(Field):

  FIELDS = OrderedDict([('name',str),('original',str),('text',str),
      ('bonuses',None),('protected',bool),('updated',float)])

  VARS = {'$':'self.char.stats["%s"].value',
      '#':'self.char.stats["%s"].normal',
  }

  def __init__(self,name,formula='0',text='',bonuses=None,protected=None,
      updated=None):

    self.char = None
    self.name = name
    self.text = text
    self.formula = str(formula)
    self.original = self.formula
    self.bonuses = bonuses or {}
    self.protected = name.startswith('_') if protected is None else protected
    self.updated = time.time() if updated is None else updated

    self.uses = set()
    self.usedby = set()
    self.normal = None
    self.value = None
    self.root = True
    self.leaf = True

    self.COPY = []

  def plug(self,char):

    self.char = char

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

    for name in dir(self):
      s = s.replace('@'+name,'self.'+name)
      s = s.replace('@{'+name+'}','self.'+name)

    try:
      eval(s)
    except Exception as e:
      raise FormulaError('%s (%s)' % (e.message,e.__class__.__name__))

    for stat in usedby:
      stat.usedby.add(self.name)
      stat.root = False

    self.formula = s
    self.calc()

  def unplug(self,force=False,recursive=False):

    if not self.char:
      raise RuntimeError('plug() must be called before unplug()')

    if self.usedby and not force and not recursive:
      raise DependencyError('still usedby: '+','.join(self.usedby))

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

  def set_formula(self,s):

    if self.char:
      raise RuntimeError('set_formula() must be called before plug()')

    self.formula = s
    self.original = s

  def calc(self):

    if not self.char:
      raise RuntimeError('plug() must be called before calc()')

    old_v = self.value
    old_n = self.normal
    self.normal = eval(self.formula.replace('.value','.normal'))
    self.value = eval(self.formula)
    for (typ,bonuses) in self.bonuses.items():
      bonuses = [b.get_value() for b in bonuses if b.active]
      if not bonuses:
        continue
      if Bonus.stacks(typ):
        self.value += sum(bonuses)
      else:
        self.value += max(bonuses)
    if old_v!=self.value or old_n!=self.normal:
      for stat in self.usedby:
        stat = self.char.stats[stat]
        stat.calc()

  def add_bonus(self,bonus):

    typ = bonus.typ
    if typ in self.bonuses:
      self.bonuses[typ].append(bonus)
    else:
      self.bonuses[typ] = [bonus]

  def del_bonus(self,bonus):

    typ = bonus.typ
    self.bonuses[typ] = [b for b in self.bonuses[typ] if b is not bonus]
    if not self.bonuses[typ]:
      del self.bonuses[typ]

  def copy(self,**kwargs):

    for var in ('name','bonuses','text','updated'):
      exec('%s = kwargs.get("%s",self.%s)' % ((var,)*3))
    formula = kwargs.get('formula',self.original)

    k = {}
    for var in self.COPY:
      k[var] = kwargs.get(var,getattr(self,var))

    return self.__class__(name,formula,text,bonuses,updated,**k)

  def __str__(self):

    root = '-r'[self.root]
    leaf = '-l'[self.leaf]
    return '%s%s %3s %s' % (root,leaf,self.value,self.name)

  def __repr__(self):
    return '<%s %s>' % (self.__class__.__name__,self.name)

  def str_all(self):

    l =     ['  value | %s' % self.value]
    l.append('formula | '+self.original)
    x = []
    for typ in self.bonuses.values():
      x +=  ['  bonus | %s' % b for b in typ]
    l.extend(sorted(x))
    l.append(' normal | %s' % self.normal)
    l.append('   uses | '+','.join(sorted(self.uses)))
    l.append('used by | '+','.join(sorted(self.usedby)))
    l.append('   text | '+self.text)
    return '\n'.join(l)

class Bonus(Field):

  FIELDS = OrderedDict([('name',str),('value',int),('stats',list),
      ('typ',str),('text',str),('active',bool)])

  @staticmethod
  def stacks(typ):

    return typ in ('none','dodge','circumstance','racial','penalty')

  def __init__(self,name,value,stats,typ=None,text=None,active=True):

    self.name = name
    self.value = value
    self.stats = stats if isinstance(stats,list) else [stats]
    self.text = text or ''
    self.active = active
    self.typ = (typ or 'none').lower()

    self.char = None
    self.last = active

  def plug(self,char):

    if self.typ not in char.BONUSES:
      raise ValueError('invalid bonus type "%s"' % self.typ)

    for name in self.stats:
      stat = char.stats[name]
      stat.add_bonus(self)
      stat.calc()
    self.char = char

  def unplug(self):

    if not self.char:
      raise RuntimeError('plug() must be called before unplug()')

    for name in self.stats:
      stat = self.char.stats[name]
      stat.del_bonus(self)
      stat.calc()
    self.char = None

  def get_value(self):
    return self.value

  def calc(self):

    for name in self.stats:
      self.char.stats[name].calc()

  def on(self):
    self.toggle(True)

  def off(self):
    self.toggle(False)

  def toggle(self,new):

    self.last = self.active
    self.active = new
    self.calc()

  def revert(self):

    if self.active==self.last:
      return
    self.active = self.last
    self.calc()

  def __str__(self):

    act = '-+'[self.active]
    sign = '+' if self.value>=0 else ''
    return '%s %s %s%s (%s)' % (act,self.name,sign,self.get_value(),self.typ)

  def str_all(self):

    l =     ['  value | %s' % self.get_value()]
    l.append(' active | %s' % self.active)
    l.append('   type | '+self.typ)
    l.append(' revert | '+('change','same')[self.last==self.active])
    l.append('  stats | '+','.join(sorted(self.stats)))
    l.append('   text | '+self.text)
    return '\n'.join(l)

class Effect(object):

  def __init__(self):
    raise NotImplementedError

class Text(object):

  def __init__(self):
    raise NotImplementedError

class Event(object):

  # hp<=0, nonlethal>=hp

  def __init__(self):
    raise NotImplementedError

###############################################################################

class Pathfinder(Character):

  STATS = OrderedDict([

  ('level',1),('hd','$level'),

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
  ('_ac_size','0'),('_ac_nat',0),('_ac_deflect',0),('_ac_misc',0),
  ('ac','10+$_ac_armor+$_ac_shield+$_ac_dex+$_ac_size+$_ac_nat+$_ac_deflect+$_ac_misc'),
  ('touch','10+$_ac_dex+$_ac_size+$_ac_deflect+$_ac_misc'),
  ('ff','10+$_ac_armor+$_ac_shield+$_ac_size+$_ac_nat+$_ac_deflect+$_ac_misc'),

  ('fortitude','$con'),('reflex','$dex'),('will','$wis'),

  ('bab',0),('sr',0),('melee','$bab+$str'),('ranged','$bab+$dex'),

  ('cmb','$melee-$_ac_size'),
  ('cmd','10+$bab+$str+$_ac_dex+$_ac_deflect+$_ac_misc-$_ac_size'),

  ('acp','0')

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

  BONUSES = ('alchemical','armor','circumstance','competence','deflection',
      'dodge','enhancement','inherent','insight','luck','morale',
      'natural_armor','profane','racial','resistance','sacred','shield',
      'size','trait','penalty','none')

  AC_BONUS = {'armor':'_ac_armor','deflection':'_ac_deflect','dodge':'_ac_dex',
      'natural_armor':'_ac_nat','shield':'_ac_shield','size':'_ac_size'}

  CLASS_SKILLS = {
      'barbarian': '10011000001010000001000010010000110',
      'bard':      '11111101100011111111111111101111001',
      'cleric':    '01001100000101000100111100101010000',
      'druid':     '00011000011100001001000010110010110',
      'fighter':   '00011000001010110000000000110000110',
      'monk':      '10011000100010000100001011111001010',
      'paladin':   '00001100001100000000101000111010000',
      'ranger':    '00011000001110101001000010110011110',
      'rogue':     '11111111100010100010000111101101011',
      'sorcerer':  '01101000010011000000000000100010001',
      'wizard':    '01001000010001111111111100100010000',

      'gunslinger':  '10111000001110010010000010110100110',
      'inquisitor':  '00111101000111100001011010111011110',
      'alchemist':   '01000010010101000001000010100110101',
      'cavalier':    '00111100001010000000000000111000010',
      'magus':       '00011000010011100000010000110010011',
      'oracle':      '00001100000100000100011000101010000',
      'summoner':    '00001000011000000000000100110010001',
      'vigilante':   '11111111100010110010000011111101111',
      'witch':       '00001000010111000101010000100010001',

      'arcane archer':         '00000000000000000000000010010001100',
      'arcane trickster':      '11110111100001111111111010001111010',
      'assassin':              '10110111100010000000000110001101011',
      'dragon disciple':       '00000100110001111111111010000010000',
      'duelist':               '10100000100000000000000011001000000',
      'eldritch knight':       '00010000000001000000100100011010010',
      'loremaster':            '01000100001101111111111101000010001',
      'mystic theurge':        '00000000000001000000001000001010000',
      'pathfinder chronicler': '01100101100011111111111111011100101',
      'shadowdancer':          '10100101100000000000000011000101000'
  }

  # TODO: conditional jump modifier based on move speed
  # TODO: craft, profession, perform
  # TODO: class skills
  # TODO: max_dex

  def __init__(self,*args,**kwargs):

    super(Pathfinder,self).__init__(*args,**kwargs)
    self.export += ['dmg','heal','health','skill','wizard']

  def setup(self):

    super(Pathfinder,self).setup()
    for (name,formula) in self.SKILLS.items():
      skill = PathfinderSkill(name,formula)
      self._add_stat(skill)

  def dmg(self,damage,nonlethal=False):

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
        print '!!! Massive damage'

    self.health()

  def heal(self,damage):

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

    self.health()

  def health(self):

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

    print ('HP: %s/%s   Nonlethal: %s   Death: %s   Status: %s'
        % (current,max_hp,nonlethal,death,status))

  def _max_hp(self):

    hp = self.stats['hp'].value
    if '_damage' not in self.bonuses:
      return hp
    return hp-self.bonuses['_damage'].value

  def skill(self,action='info',name=None,value=0):

    actions = ['info','list','rank','class','unclass']
    if action not in actions:
      raise ValueError('invalid sub-command "%s"' % action)

    name = name or self.SKILLS.keys()
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
        result = '*** %s (%s) %s' % (e.__class__.__name__,n,e.message)
      if result:
        print result

  ##### OVERRIDES #####

  def add_bonus(self,name,value,stats,typ=None,text=None,active=True):

    if stats.lower()=='ac':
      stats = self.AC_BONUS.get(typ,'_ac_misc')
    super(Pathfinder,self).add_bonus(name,value,stats,typ,text,active)

  ##### WIZARD #####

  def wizard(self,action='help'):

    actions = ['class_skill','skill']
    if action not in actions and action not in ('help','all'):
      raise ValueError('invalid sub-command "%s"' % action)

    if action=='help':
      print 'usage: wizard [all] (%s)' % ('|'.join(sorted(actions)))

    else:
      actions = actions if action=='all' else [action]
      for action in actions:
        getattr(self,'wiz_'+action)()

  def wiz_class_skill(self):

    clas = raw_input('Enter class name: ').lower()
    if clas not in self.CLASS_SKILLS:
      raise KeyError('unknown class "%s"' % clas)

    names = self.SKILLS.keys()
    for (i,x) in enumerate(self.CLASS_SKILLS[clas]):
      if x=='1':
        self.stat[names[i]].set_cskill()

  def wiz_skill(self):

    done = False
    for skill in self.SKILLS:
      success = False
      while not success:
        try:
          value = raw_input('%s ranks = ' % skill)
          if value=='':
            value = 0
          elif value=='exit':
            done = True
            break
          else:
            value = int(value)
          self.stats[skill].set_ranks(value)
          success = True
        except Exception as e:
          print '*** %s: %s' % (e.__class__.__name__,e.message)
      if done:
        break

  def wiz_race(self):

    raise NotImplementedError

  ##### SKILL CLASS #####

class PathfinderSkill(Stat):

  def __init__(self,*args,**kwargs):

    self.class_skill = kwargs.pop('clas',False)
    self.ranks = kwargs.pop('ranks',0)
    super(PathfinderSkill,self).__init__(*args,**kwargs)

    f = '+@ranks+(3 if @class_skill and @ranks else 0)'
    if '$dex' in self.original or '$str' in self.original:
      f += '+${acp}'
    self.set_formula(self.formula+f)

    self.COPY += ['ranks','class_skill']

  def set_cskill(self,new=True):

    self.class_skill = new
    self.calc()

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

  def __str__(self):

    cs = '-c'[self.class_skill]
    tr = '-t'[self.ranks>0]
    return '%s%s %3s %s' % (cs,tr,self.value,self.name)

  def str_all(self):

    s = super(PathfinderSkill,self).str_all()

    l = ['  ranks | %s' % self.ranks]
    l.append(' cskill | %s' % self.class_skill)

    return s+'\n'+'\n'.join(l)
