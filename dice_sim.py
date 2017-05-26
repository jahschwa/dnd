#!/usr/bin/env python
# encoding: utf8

import random,time
from collections import OrderedDict

DICE = '1d20'
REROLL = []
DROP = 0
SIMS = 1000000

def main():

  random.seed(time.time())
  t = time.time()
  result = simulate()
  t = time.time()-t
  cum_sum = list(cumsum(result.values()[::-1]))[::-1]
  print '%s R(%s) D%s took %s sec\n' % (DICE,','.join(map(str,REROLL)),DROP,t)
  print '\n'.join(['%3d = %7.4f %6.2f %s' % (t,p,c,'█'*int(round(2*p))) for ((t,p),c) in zip(result.items(),cum_sum)])
  print '\nAverage: %s' % (reduce(lambda a,b: a+b[0]*b[1],result.items(),0)/100.0)

def cumsum(lis):

    total = 0
    for x in lis:
        total += x
        yield total

def simulate():

  fields = DICE.split('+')
  ops = []
  for field in fields:
    if 'd' in field:
      (a,b) = field.split('d')
      ops.append((int(a),int(b)))
    else:
      ops.append(int(field))

  mi = 0
  ma = 0
  for o in ops:
    if isinstance(o,tuple):
      mi += o[0]-abs(DROP)
      ma += (o[0]-abs(DROP))*o[1]
    else:
      mi += o
      ma += o
  result = OrderedDict([(x,0) for x in range(mi,ma+1)])

  for i in xrange(0,SIMS):
    total = 0
    for o in ops:
      if isinstance(o,tuple):
        rolls = []
        for n in range(0,o[0]):
          roll = random.randint(1,o[1])
          if REROLL and roll in REROLL:
            roll = random.randint(1,o[1])
          rolls.append(roll)
        total += sum(sorted(rolls,reverse=(DROP<0))[abs(DROP):])
      else:
        total += o
    result[total] += 1

  return {a:100.0*b/SIMS for (a,b) in result.items()}

if __name__ == '__main__':
  main()
