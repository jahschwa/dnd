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

class Character(object):

  def __init__(self):

    self.stats = []
    self.bonuses = []
    self.events = []

  def setup_pathfinder(self):
    """create objects for default pathfinder char"""

    raise NotImplementedError

class Stat(object):

  def __init__(self):

    uses = []
    usedby = []
    formula = []

class Bonus(object):

  def __init__(self,val,name):

    self.val = val
    self.name = name

class Event(object):

  def __init__(self):

    raise NotImplementedError
