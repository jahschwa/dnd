from functools import reduce, total_ordering
import random
import sys

@total_ordering
class Dice:

  @staticmethod
  def parse(s):

    s = str(s).replace(' ', '')

    if not reduce(lambda a, b: a and (b.isdigit() or b in 'd+-'), s, True):
      raise ValueError('invalid Dice string "%s"' % s)

    s = s.lower().replace('-', '+-')
    fields = [x.strip() for x in s.split('+')]
    dice = {}
    bonus = 0
    for field in fields:
      if not field:
        continue
      if 'd' in field:
        (num, sides) = field.split('d')
        if num == '-':
          num = -1
        num = int(num or 1)
        sides = int(sides)
        Dice.dict_add(dice, sides, num)
      else:
        bonus += int(field)
    return (dice, bonus)

  @staticmethod
  def dict_add(d, k, v):

    if v == 0:
      return

    if k in d:
      d[k] += v
    else:
      d[k] = v

    if d[k] == 0:
      del d[k]

  @staticmethod
  def intify(x):
    """cast floats to ints if they're whole numbers"""

    if abs(x - int(x)) < sys.float_info.epsilon:
      return int(x)
    else:
      return x

  def __init__(self, s=''):
    (self.dice, self.bonus) = Dice.parse(s)

########## Numeric functions ##########

  def __add__(self, obj):

    if isinstance(obj, int):
      return self.__add_int(obj)
    elif isinstance(obj, Dice):
      return self.__add_dice(obj)
    else:
      return NotImplemented

  def __radd__(self, obj):

    if isinstance(obj, int):
      return self.__add_int(obj)
    else:
      return NotImplemented

  def __sub__(self, obj):

    if isinstance(obj, int):
      return self.__add_int(-obj)
    elif isinstance(obj, Dice):
      return self.__add_dice(-obj)

  def __rsub__(self, obj):

    if isinstance(obj, int):
      return (-self).__add_int(obj)
    else:
      return NotImplemented

  def __mul__(self, obj):

    if isinstance(obj, Dice):
      obj = obj.as_int(ignore=False)
    if isinstance(obj, int):
      new = self.copy()
      for d in new.dice:
        new.dice[d] *= obj
      new.bonus *= obj
      return new
    else:
      return NotImplemented

  def __rmul__(self, obj):
    return self * obj

  def __truediv__(self, obj):

    if self.dice:
      raise ValueError("this Dice isn't just an integer bonus")
    if isinstance(obj, Dice):
      obj = obj.as_int(ignore=False)
    if isinstance(obj, int):
      return self.bonus / obj
    else:
      return NotImplemented

  def __rtruediv__(self, obj):

    if self.dice:
      raise ValueError("this Dice isn't just an integer bonus")
    if isinstance(obj, int):
      return obj / self.bonus
    else:
      return NotImplemented

  def __neg__(self):

    new = self.copy()
    new.bonus *= -1
    for sides in new.dice:
      new.dice[sides] *= -1
    return new

  def __int__(self):
    return self.as_int(ignore=False)

  def __float__(self):
    return float(int(self))

  def __eq__(self, other):

    if isinstance(other, Dice):
      return self.avg() == other.avg()
    elif isinstance(other, int):
      return self.avg() == other
    return NotImplemented

  def __lt__(self, other):

    if isinstance(other, Dice):
      return self.avg() < other.avg()
    elif isinstance(other, int):
      return self.avg() < other
    return NotImplemented

########## Helper functions ##########

  def __add_int(self, i):

    dice = self.copy()
    dice.bonus += i
    return dice

  def __add_dice(self, d):

    dice = self.copy()
    for (sides, num) in d.dice.items():
      Dice.dict_add(dice.dice, sides, num)
    dice.bonus += d.bonus
    return dice

########## Methods ##########

  def same(self, other):

    if not isinstance(other, Dice):
      raise TypeError(
        'invalid type %s for Dice.same()' % other.__class__.__name__
      )

    return str(self) == str(other)

  def copy(self):

    dice = Dice()
    dice.dice = self.dice.copy()
    dice.bonus = self.bonus
    return dice

  def as_int(self, ignore=True):

    if not ignore and self.dice:
      raise ValueError("this Dice isn't just an integer bonus")

    return self.bonus

  def as_dice(self, ignore=True):

    if not ignore and self.bonus != 0:
      raise ValueError("this Dice has a numerical bonus")

    return self.copy()

  def roll(self):

    total = 0
    for (sides, num) in self.dice.items():
      neg = [1, -1][num < 0]
      for i in range(0, num, neg):
        total += random.randint(1, sides) * neg
    return Dice.intify(total + self.bonus)

  def min(self):

    pos = [n for n in self.dice.values() if n > 0]
    neg = [n * s for (s, n) in self.dice.items() if n < 0]
    return sum(pos) + sum(neg) + self.bonus

  def avg(self):

    avg = 0
    for (sides, num) in self.dice.items():
      avg += num * (sides + 1) / 2.0
    return Dice.intify(avg + self.bonus)

  def max(self):

    pos = [n * s for (s, n) in self.dice.items() if n > 0]
    neg = [n for n in self.dice.values() if n < 0]
    return sum(pos) + sum(neg) + self.bonus

  def stats(self):
    return self.__str__() + ' = %s/%s/%s' % (self.min(), self.avg(), self.max())

  def __str__(self):

    sides = sorted(
      self.dice.items(),
      key=lambda x: x[1] * (x[0] + 1) / 2.0,
      reverse=True,
    )
    s = '+'.join(['%sd%s' % (n, s) for (s, n) in sides]).replace('+-', '-')
    if self.bonus or not self.dice:
      s += '%s%s' % ('+' if self.bonus > 0 else '', self.bonus)
    if s.startswith('+'):
      return s[1:]
    return s

  def __repr__(self):
    return '<Dice %s>' % str(self)
