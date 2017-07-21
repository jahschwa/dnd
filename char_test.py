#!/usr/bin/env python

from char import *

ALL = True

c = Character()
c.setup('pathfinder')

def show(c):
  print ''
  for stat in c.stats.values():
    if ALL or len(stat.name)==3:
      print stat

show(c)

Bonus(c,'cats_grace',4,'dexterity')

show(c)

c.set_stat('strength','20')

show(c)

Bonus(c,'mage_armor',4,'ac_armor')

show(c)
