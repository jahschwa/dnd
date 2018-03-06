#!/usr/bin/env python3

from char import *
from dice import Dice

ALL = False
ALWAYS = 'str,dex,con,int,wis,cha,melee,ranged,hp_max'

c = Pathfinder()

def main():
  test_duration()

def show(c):
  print('')
  for stat in c.stats.values():
    if ALL or stat.root or stat.name in ALWAYS:
      print(stat)

def show_hp(c):
  print('')
  for name in ('constitution','con','hp_max','hp'):
    stat = c.get_stat(name)
    print('%s = %s / %s' % (name,stat.value,stat.normal))

class MockStat(object):
  def __init__(self,value):
    self.value = value

class MockCharacter(object):
  def __init__(self):
    self.stats = {'level':MockStat(5),'caster_level':MockStat(7)}

def test_duration():
  char = MockCharacter()
  for dur in ['5rds','10minutes','5h','10min/CL','rd/2lvl']:
    print('%s = %s' % (dur,Duration(dur,char)))

def test_dice_sort():
  print(sorted([5,Dice('1d5'),Dice('1d5-4'),12,Dice('1d5+4'),Dice('3d5+10'),50,20,7,Dice('30')]))

def test_basic():
  show(c)
  c.new_bonus('cats_grace',4,'dexterity')
  show(c)
  c.set_stat('strength','20')
  show(c)
  c.new_bonus('mage_armor',4,'ac_armor')
  show(c)
  c.off('cats_grace')
  show(c)

def test_bonus_types():
  show(c)
  c.new_bonus('item_armor',2,'ac_armor',typ='armor')
  show(c)
  c.new_bonus('mage_armor',4,'ac_armor',typ='armor')
  show(c)
  c.new_bonus('feat_dodge',1,'ac_dex',typ='dodge')
  show(c)
  c.new_bonus('fight_def',4,'ac_dex',typ='dodge')
  show(c)
  c.off('mage_armor')
  show(c)

def test_set_stat():
  show(c)
  c.set_stat('hp_max',formula='10')
  show(c)
  c.new_bonus('bears_endurance',4,'constitution',typ='enhancement')
  show(c)
  c.new_bonus('poison',-12,'constitution',typ='penalty')
  show(c)
  c.off('bears_endurance')
  show(c)

def test_normal():
  show_hp(c)
  c.set_stat('hp_max',formula='10')
  show_hp(c)
  c.new_bonus('bears_endurance',4,'constitution',typ='enhancement')
  show_hp(c)
  c.set_stat('level','3')
  show_hp(c)

if __name__=='__main__':
  main()
