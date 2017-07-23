#!/usr/bin/env python

from char import *

ALL = False
ALWAYS = 'str,dex,con,int,wis,cha,melee,ranged,hp_max'

c = Pathfinder()

def show(c):
  print ''
  for stat in c.stats.values():
    if ALL or stat.root or stat.name in ALWAYS:
      print stat

def show_hp(c):
  print ''
  for name in ('constitution','con','hp_max','hp'):
    stat = c.get_stat(name)
    print '%s = %s / %s' % (name,stat.value,stat.normal)

def test_basic():
  show(c)
  c.bonus('cats_grace',4,'dexterity')
  show(c)
  c.set_stat('strength','20')
  show(c)
  c.bonus('mage_armor',4,'ac_armor')
  show(c)
  c.off('cats_grace')
  show(c)

def test_bonus_types():
  show(c)
  c.bonus('item_armor',2,'ac_armor',typ='armor')
  show(c)
  c.bonus('mage_armor',4,'ac_armor',typ='armor')
  show(c)
  c.bonus('feat_dodge',1,'ac_dex',typ='dodge')
  show(c)
  c.bonus('fight_def',4,'ac_dex',typ='dodge')
  show(c)
  c.off('mage_armor')
  show(c)

def test_set_stat():
  show(c)
  c.set_stat('hp_max',formula='10')
  show(c)
  c.bonus('bears_endurance',4,'constitution',typ='enhancement')
  show(c)
  c.bonus('poison',-12,'constitution',typ='penalty')
  show(c)
  c.off('bears_endurance')
  show(c)

def test_normal():
  show_hp(c)
  c.set_stat('hp_max',formula='10')
  show_hp(c)
  c.bonus('bears_endurance',4,'constitution',typ='enhancement')
  show_hp(c)
  c.set_stat('level','3')
  show_hp(c)

test_set_stat()
