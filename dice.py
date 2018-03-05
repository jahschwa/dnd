#!/usr/bin/env python

import random
from functools import total_ordering

@total_ordering
class Dice(object):

  @staticmethod
  def parse(s):

    s = str(s)

    if not reduce(lambda a,b: a and (b.isdigit() or b in 'd+-'),s,True):
      raise ValueError('invalid Dice string "%s"' % s)

    s = s.lower().replace('-','+-')
    fields = [x.strip() for x in s.split('+')]
    dice = {}
    bonus = 0
    for field in fields:
      if not field:
        continue
      if 'd' in field:
        (num,sides) = field.split('d')
        num = int(num or 1) or 1
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
    elif isinstance(obj,Dice):
      return self.__add_dice(obj.neg())

  def __rsub__(self,obj):

    if isinstance(obj,int):
      return self.neg().__add_int(obj)
    else:
      return NotImplemented

  def __eq__(self,other):

    if isinstance(other,Dice):
      return self.avg()==other.avg()
    elif isinstance(other,int):
      return self.avg()==other

  def __lt__(self,other):

    if isinstance(other,Dice):
      return self.avg()<other.avg()
    elif isinstance(other,int):
      return self.avg()<other

  def neg(self):

    new = self.copy()
    new.bonus *= -1
    for sides in new.dice:
      new.dice[sides] *= -1
    return new

  def same(self,other):

    if not isinstance(other,Dice):
      raise TypeError('invalid type %s for Dice.same()'
          % other.__class__.__name__)

    return str(self)==str(other)

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
      neg = [1,-1][num<0]
      for i in range(0,num,neg):
        total += random.randint(1,sides)*neg
    return Dice.intify(total+self.bonus)

  def min(self):

    pos = [n for n in self.dice.values() if n>0]
    neg = [n*s for (s,n) in self.dice.items() if n<0]
    return sum(pos)+sum(neg)+self.bonus

  def avg(self):

    avg = 0
    for (sides,num) in self.dice.items():
      avg += num*(sides+1)/2.0
    return Dice.intify(avg+self.bonus)

  def max(self):

    pos = [n*s for (s,n) in self.dice.items() if n>0]
    neg = [n for n in self.dice.values() if n<0]
    return sum(pos)+sum(neg)+self.bonus

  def stats(self):

    return self.__str__()+' = %s/%s/%s' % (self.min(),self.avg(),self.max())

  def __str__(self):

    sides = sorted(self.dice.items(),key=lambda x:x[1]*(x[0]+1)/2.0,reverse=True)
    s = '+'.join(['%sd%s' % (n,s) for (s,n) in sides]).replace('+-','-')
    if self.bonus:
      s += '%s%s' % ('+' if self.bonus>0 else '',self.bonus)
    if s.startswith('+'):
      return s[1:]
    return s

  __repr__ = __str__
