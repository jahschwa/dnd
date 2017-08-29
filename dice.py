#!/usr/bin/env python

import random

class Dice(object):

  @staticmethod
  def parse(s):

    if not reduce(lambda a,b: a and (b.isdigit() or b in 'd+-'),s,True):
      raise ValueError('Invalid characters in "%s"' % s)

    s = s.lower().replace('-','+-')
    fields = [x.strip() for x in s.split('+')]
    dice = {}
    bonus = 0
    for field in fields:
      if not field:
        continue
      if 'd' in field:
        (num,sides) = field.split('d')
        num = int(num) or 1
        sides = int(sides)
        Dice.dict_add(dice,sides,num)
      else:
        bonus += int(field)
    return (dice,bonus)

  @staticmethod
  def dict_add(d,k,v):

    if k in d:
      d[k] += v
    else:
      d[k] = v

  @staticmethod
  def intify(x):
    if x==int(x):
      return int(x)
    else:
      return x

  def __init__(self,s=''):

    (self.dice,self.bonus) = Dice.parse(s)

  def __add__(self,obj):

    if isinstance(obj,int):
      return self.__add_int(obj)
    elif isinstance(obj,Dice):
      return self.__add_dice(obj)
    else:
      return NotImplemented

  def __radd__(self,obj):

    if isinstance(obj,int):
      return self.__add_int(obj)
    else:
      return NotImplemented

  def __sub__(self,obj):

    if isinstance(obj,int):
      return self.__add_int(-obj)
    else:
      return NotImplemented

  def copy(self):

    dice = Dice()
    dice.dice = self.dice.copy()
    dice.bonus = self.bonus
    return dice

  def __add_int(self,i):

    dice = self.copy()
    dice.bonus += i
    return dice

  def __add_dice(self,d):

    dice = self.copy()
    for (sides,num) in d.dice.items():
      Dice.dict_add(dice.dice,sides,num)
    dice.bonus += d.bonus
    return dice

  def roll(self):

    total = 0
    for (sides,num) in self.dice.items():
      for i in range(0,num):
        total += random.randint(1,sides)
    return Dice.intify(total+self.bonus)

  def min(self):

    return sum(self.dice.values())+self.bonus

  def avg(self):

    avg = 0
    for (sides,num) in self.dice.items():
      avg += num*(sides+1)/2.0
    return Dice.intify(avg+self.bonus)

  def max(self):

    return sum([sides*num for (sides,num) in self.dice.items()])+self.bonus

  def stats(self):

    return self__str__()+' = %s/%s/%s' % (self.min(),self.avg(),self.max())

  def __str__(self):

    s = '+'.join(['%sd%s'%(self.dice[k],k) for k in sorted(self.dice.keys())])
    if self.bonus:
      s += '%s%s' % ('+' if self.bonus>0 else '',self.bonus)
    return s
