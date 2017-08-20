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

# TODO: change backend stats to start with "_"
# TODO: set should raise exception not return a boolean
# TODO: conditional bonuses
# TODO: consider another way for set_stat() to interact with plug/unplug?
# TODO: decide what goes in here and what goes in the CLI

# Stat
# Bonus
# Effect
# Item
#   Weapon
#   Armor
# Dice
# Ability
# Event
# Text

import time
from collections import OrderedDict

class DependencyError(Exception):
  pass

class Character(object):

  STATS = {}

  def __init__(self):

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

    self.setup()

  def search(self,name):
    matches = []
    for (l,d) in self.letters.items():
      for (n,obj) in getattr(self,d).items():
        if name in n:
          matches.append('%s | %s' % (l,obj))
    return '\n'.join(matches)

  def get(self,typ,name):
    typ = typ if typ not in self.letters else self.letters[typ]
    if not isinstance(name,list):
      name = [name]
    return '\n'.join([str(getattr(self,typ)[n]) for n in name])

  def all(self,typ,name):
    typ = typ if typ not in self.letters else self.letters[typ]
    return getattr(self,typ)[name].str_all()

  def _add_stat(self,stat):
    if stat.name in self.stats:
      raise ValueError('Stat "%s" already exists' % stat.name)
    self.stats[stat.name] = stat

  def add_stat(self,name,formula='0',text='',updated=None):
    stat = Stat(name,formula,text,updated)
    stat.plug(self)
    self._add_stat(stat)

  def del_stat(self,name):
    stat = self.stats[name]
    try:
      stat.unplug()
    except DependencyError:
      return False
    return True

  def set_stat(self,name,formula=None,text=None,updated=None):
    old = self.stats[name]
    new = old.copy(text=text,formula=formula,updated=updated)
    new.usedby = set(old.usedby)
    if new.usedby:
      new.root = False
    old.unplug(force=True)
    try:
      self.stats[name] = new
      new.plug(self)
    except KeyError:
      old.formula = old.original
      old.plug(self)
      self.stats[name] = old
      return False
    return True

  def _add_bonus(self,bonus):
    if bonus.name in self.bonuses:
      raise ValueError('Bonus "%s" already exists' % bonus.name)
    self.bonuses[bonus.name] = bonus

  def add_bonus(self,name,value,stats,typ=None,text=None,active=True):
    bonus = Bonus(name,int(value),stats,typ,text,active)
    self._add_bonus(bonus)
    bonus.plug(self)

  def set_bonus(self,name,value):
    bonus = self.bonuses[name]
    bonus.value = value
    bonus.calc()

  def del_bonus(self,name):
    self.bonuses[name].unplug()
    del self.bonuses[name]

  def on(self,name):
    self.bonuses[name].on()

  def off(self,name):
    self.bonuses[name].off()

  def revert(self,name):
    self.bonuses[name].revert()

  def setup(self):
    for (name,formula) in self.STATS.items():
      self.add_stat(name,str(formula))

class Stat(object):

  VARS = {'$':'self.char.stats["%s"].value',
      '#':'self.char.stats["%s"].normal'
  }

  def __init__(self,name,formula='0',text='',bonuses=None,updated=None):

    self.char = None
    self.name = name
    self.text = text
    self.formula = str(formula)
    self.original = self.formula
    self.bonuses = bonuses or {}
    self.updated = time.time() if updated is None else updated

    self.uses = set()
    self.usedby = set()
    self.normal = None
    self.value = None
    self.root = True
    self.leaf = True

  def plug(self,char):

    self.char = char

    s = self.formula
    usedby = set()
    for name in char.stats:
      for (var,expand) in self.VARS.items():
        if var+name in s:
          s = s.replace(var+name,expand % name)
          self.uses.add(name)
          self.leaf = False
          usedby.add(char.stats[name])

    try:
      eval(s)
    except Exception as e:
      raise KeyError

    for stat in usedby:
      stat.usedby.add(self.name)
      stat.root = False

    self.formula = s
    self.calc()

  def unplug(self,force=False,recursive=False):

    if not self.char:
      return

    if self.usedby and not force and not recursive:
      raise DependencyError(str(self.usedby))

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

  def calc(self):

    if not self.char:
      raise RuntimeError('plug() must be called before calc()')

    old_v = self.value
    old_n = self.normal
    self.normal = eval(self.formula.replace('.value','.normal'))
    self.value = eval(self.formula)
    for (typ,bonuses) in self.bonuses.items():
      bonuses = [b.value for b in bonuses if b.active]
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

    self.bonuses[typ] = [b for b in self.bonuses[typ] if b is not bonus]
    if not self.bonuses[typ]:
      del self.bonuses[typ]

  def copy(self,name=None,text=None,formula=None,bonuses=None,updated=None):

    for var in ('name','text','bonuses','updated'):
      exec('%s = %s or self.%s' % ((var,)*3))
    formula = formula or self.original
    return Stat(name,formula,text,bonuses,updated)

  def __str__(self):
    return '%s = %s' % (self.name,self.value)

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

class Bonus(object):

  TYPES = ('alchemical','armor','circumstance','competence','defelction',
      'dodge','enhancement','inherent','insight','luck','morale',
      'natural_armor','profane','racial','resistance','sacred','shield',
      'size','trait','penalty','none')

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
    if self.typ not in Bonus.TYPES:
      raise ValueError('Invalid bonus type "%s"' % self.typ)

    self.char = None
    self.last = active

  def plug(self,char):

    for name in self.stats:
      stat = char.stats[name]
      stat.add_bonus(self)
      stat.calc()
    self.char = char

  def unplug(self):

    if not self.char:
      return

    for name in self.stats:
      stat = self.char.stats[name]
      stat.del_bonus(self)
      stat.calc()
    self.char = None

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
    return '%s %s %s%s (%s)' % (act,self.name,sign,self.value,self.typ)

  def str_all(self):

    l =     ['  value | %s' % self.value]
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

  ('strength',10), ('dexterity',10), ('constitution',10),
  ('intelligence',10), ('wisdom',10), ('charisma',10),
  ('str','int(($strength-10)/2)'),
  ('dex','int(($dexterity-10)/2)'),
  ('con','int(($constitution-10)/2)'),
  ('int','int(($intelligence-10)/2)'),
  ('wis','int(($wisdom-10)/2)'),
  ('cha','int(($charisma-10)/2)'),

  ('hp_max',0),('hp','$hp_max+$hd*($con-#con)'),('nonlethal',0),
  ('initiative','$dex'),('dr',0),('speed',30),

  ('armor_check',0),('max_dex',99),('spell_fail',0),

  ('ac_armor',0),('ac_shield',0),('ac_dex','min($dex,$max_dex)'),('ac_size','0'),
  ('ac_nat',0),('ac_deflect',0),('ac_misc',0),
  ('ac','10+$ac_armor+$ac_shield+$ac_dex+$ac_size+$ac_nat+$ac_deflect+$ac_misc'),
  ('touch','10+$ac_dex+$ac_size+$ac_deflect+$ac_misc'),
  ('ff','10+$ac_armor+$ac_shield+$ac_size+$ac_nat+$ac_deflect+$ac_misc'),

  ('fortitude','$con'),('reflex','$dex'),('will','$wis'),

  ('bab',0),('sr',0),('melee','$bab+$str'),('ranged','$bab+$dex'),

  ('cmb','$melee-$ac_size'),('cmd','10+$bab+$str+$ac_dex+$ac_deflect+$ac_misc'),

  ('acrobatics','$dex'),('appraise','$int'),('bluff','$cha'),('climb','$str'),
  ('diplomacy','$cha'),('disable_device','$dex'),('disguise','$cha'),
  ('escape_artist','$dex'),('fly','$dex'),('handle_animal','$cha'),
  ('heal','$wis'),('intimidate','$cha'),

  ('knowledge_arcana','$int'),('knowledge_dungeoneering','$int'),
  ('knowledge_engineering','$int'),('knowledge_geography','$int'),
  ('knowledge_history','$int'),('knowledge_local','$int'),
  ('knowledge_nature','$int'),('knowledge_nobility','$int'),
  ('knowledge_planes','$int'),('knowledge_religion','$int'),

  ('linguisitics','$int'),('perception','$wis'),('ride','$dex'),
  ('sense_motive','$wis'),('sleight_of_hand','$dex'),('spellcraft','$int'),
  ('stealth','$dex'),('survival','$wis'),('swim','$str'),
  ('use_magic_device','$cha'),

  ])

  # TODO: conditional jump modifier based on move speed
  # TODO: craft, profession, perform
  # TODO: class skills
  # TODO: max_dex

  def damage(self,dmg,nonlethal=False):
    raise NotImplementedError

  def ranks(self):
    raise NotImplementedError

  def bonus_ac(self,name,value,typ,text=None,active=True):
    raise NotImplementedError

###############################################################################

if __name__=='__main__':
  main()
