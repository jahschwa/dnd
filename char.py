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

# TODO: conditional bonuses

import time
from collections import OrderedDict

class Character(object):

  def __init__(self):

    self.stats = OrderedDict()
    self.bonuses = {}
    self.events = {}

  def add_stat(self,stat):
    self.stats[stat.name] = stat

  def new_stat(self,name,text='',formula='0',updated=None):
    self.add_stat(Stat(self,name,text,formula,updated))

  def set_stat(self,name,formula):
    stat = self.stats[name]
    stat.formula = formula
    stat.calc()

  def setup(self,name):
    """create objects for default char"""

    for (name,formula) in eval(name.upper()).items():
      self.new_stat(name,'',str(formula))

class Stat(object):

  def __init__(self,char,name,text='',formula='0',bonuses=None,updated=None):

    self.char = char
    self.name = name
    self.uses = []
    self.usedby = []
    self.value = None
    self.bonuses = bonuses or []
    self.updated = time.time() if updated is None else updated
    self.dirty = True
    self.root = True
    self.leaf = True
    self.parse(formula)

  def parse(self,s):

    for name in self.char.stats:
      if '$'+name in s:
        s = s.replace('$'+name,'self.char.stats["%s"].value' % name)
        self.uses.append(name)
        self.leaf = False
        stat = self.char.stats[name]
        stat.usedby.append(self.name)
        stat.root = False
    self.formula = s
    self.calc()

  def calc(self):

    self.dirty = False
    old = self.value
    self.value = eval(self.formula)
    for bonus in self.bonuses:
      if bonus.active:
        self.value += bonus.value
    if old!=self.value:
      for stat in self.usedby:
        stat = self.char.stats[stat]
        stat.dirty = True
        stat.calc()

  def __str__(self):
    return '%s = %s' % (self.name,self.value)

class Bonus(object):

  def __init__(self,char,name,value,stats,active=True,typ=None):

    self.char = char
    self.name = name
    self.value = value
    self.active = active
    self.typ = typ
    self.plug(stats if isinstance(stats,list) else [stats])

  def plug(self,stats):

    for name in stats:
      stat = self.char.stats[name]
      stat.bonuses.append(self)
      stat.calc()

class Effect(object):

  def __init__(self,char):

    self.char = char

class Event(object):

  def __init__(self,char):

    self.char = char

###############################################################################

PATHFINDER = OrderedDict([

('strength',10), ('dexterity',10), ('constitution',10),
('intelligence',10), ('wisdom',10), ('charisma',10),
('str','int(($strength-10)/2)'),
('dex','int(($dexterity-10)/2)'),
('con','int(($constitution-10)/2)'),
('int','int(($intelligence-10)/2)'),
('wis','int(($wisdom-10)/2)'),
('cha','int(($charisma-10)/2)'),

('ac_armor',0),('ac_shield',0),('ac_dex','$dex'),('ac_size','0'),
('ac_nat',0),('ac_deflect',0),('ac_misc',0),
('ac','10+$ac_armor+$ac_shield+$ac_dex+$ac_size+$ac_nat+$ac_deflect+$ac_misc'),
('touch','10+$ac_dex+$ac_size+$ac_deflect+$ac_misc'),
('ff','10+$ac_armor+$ac_shield+$ac_size+$ac_nat+$ac_deflect+$ac_misc'),

('bab',0),('melee','$bab+$str'),('ranged','$bab+$dex'),

('cmb','$melee-$ac_size'),('cmd','10+$bab+$str+$ac_dex+$ac_deflect+$ac_misc'),
])

###############################################################################

if __name__=='__main__':
  main()
