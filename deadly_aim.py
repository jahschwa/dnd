#!/usr/bin/env python

#-------------------------
# Andin normal

#~ AC = 20
#~ DR = 0

#~ BONUS = 17
#~ F_BONUS = BONUS-1

#~ BAB = 11
#~ FLURRY = 1
#~ EXTRA = 0

#~ DICE = '1d8'
#~ DMG = 7
#~ DEADLY = 1+BAB/4

#-------------------------
# Andin buffed

AC = 32
DR = 0

BONUS = 20
F_BONUS = BONUS-1

BAB = 12
FLURRY = 1
EXTRA = 2

DICE = '4d6'
DMG = 10
DEADLY = 1+BAB/4

#-------------------------
# Andin uber

#~ AC = [15,30]
#~ DR = 0

#~ BONUS = 22
#~ F_BONUS = BONUS-1

#~ BAB = 11
#~ FLURRY = 1
#~ EXTRA = 1

#~ DICE = '3d6'
#~ DMG = 13
#~ DEADLY = 1+BAB/4

#-------------------------
# Andin mazda

#~ AC = 19
#~ DR = 0

#~ BONUS = 16
#~ F_BONUS = BONUS-1

#~ BAB = 11
#~ FLURRY = 0
#~ EXTRA = 0

#~ DICE = '1d8+2d6'
#~ DMG = 7
#~ DEADLY = -10

#-------------------------
# Err normal

#~ AC = 20
#~ DR = 0

#~ BONUS = 17
#~ F_BONUS = BONUS-1

#~ BAB = 9
#~ FLURRY = 0
#~ EXTRA = 2

#~ DICE = '1d4'
#~ DMG = 5
#~ DEADLY = -10

from collections import OrderedDict as odict

def main(ac):

  print '\n Hit AC %s / DR %s with +%s (%s+%s) and DA -%s/+%s' % (ac,DR,BONUS,DICE,DMG,DEADLY,2*DEADLY)

  if isinstance(ac,int):
    (rolls,dmgs,best) = calc_one(ac)
    print '\n'+'-'*32
    print 'One       : %s' % rolls['one']
    print 'One+DA    : %s' % rolls['one_da']
    print 'Full      : %s' % rolls['full']
    print 'Full+DA   : %s' % rolls['full_da']
    print 'Flurry    : %s' % rolls['flu']
    print 'Flurry+DA : %s' % rolls['flu_da']
    print ''+'-'*32
    print 'One       : %s' % dmgs['one']
    print 'One+DA    : %s' % dmgs['one_da']
    print 'Full      : %s' % dmgs['full']
    print 'Full+DA   : %s' % dmgs['full_da']
    print 'Flurry    : %s' % dmgs['flu']
    print 'Flurry+DA : %s' % dmgs['flu_da']
    print '-'*32+'\n'
    print ' Best: %s = %s dmg' % (best[0],best[1])
  else:
    results = calc_many(ac)
    print ''
    for (ac,name,dmg,rolls) in results:
      print '%-2s: %-9s = %-3s (%s)' % (ac,name,dmg,rolls)

def get_vals(ac):

  dice = get_dice(DICE)
  dmg = dice+DMG
  dmg_da = dmg+2*DEADLY
  return (dice,max(dmg-DR,0),max(dmg_da-DR,0))

def get_full(ac,bonus,dmg,use_flu=True):

  rolls = ''
  dmgs = 0
  atts = 1+(BAB-1)/5

  flu_atts = FLURRY if use_flu else 0

  for i in range(0,EXTRA):
    (r,d) = get_dmg(ac,bonus,dmg)
    rolls += '%-2s '%r
    dmgs += d
  for i in range(0,atts):
    (r,d) = get_dmg(ac,bonus-5*i,dmg)
    for j in range(0,1+(i<flu_atts)):
      rolls += '%-2s '%r
      dmgs += d

  return (rolls,dmgs)

def calc_one(ac):

  (dice,dmg,dmg_da) = get_vals(ac)
  rolls = {}
  dmgs = {}

  (rolls['one'],dmgs['one']) = get_dmg(ac,BONUS,dmg)
  (rolls['one_da'],dmgs['one_da']) = get_dmg(ac,BONUS-DEADLY,dmg_da)
  (rolls['full'],dmgs['full']) = get_full(ac,BONUS,dmg,False)
  (rolls['full_da'],dmgs['full_da']) = get_full(ac,BONUS-DEADLY,dmg_da,False)
  (rolls['flu'],dmgs['flu']) = get_full(ac,F_BONUS,dmg)
  (rolls['flu_da'],dmgs['flu_da']) = get_full(ac,F_BONUS-DEADLY,dmg_da)

  dmg = odict([('one',dmgs['one']),
                ('one_da',dmgs['one_da']),
                ('full',dmgs['full']),
                ('full_da',dmgs['full_da']),
                ('flu',dmgs['flu']),
                ('flu_da',dmgs['flu_da'])])
  names = {'one':'One',
            'one_da':'One+DA',
            'full':'Full',
            'full_da':'Full+DA',
            'flu':'Flurry',
            'flu_da':'Flurry+DA'}
  n = ''
  m = 0
  value = ['flu_da','flu','full_da','full','one_da','one']
  if FLURRY==0:
    value = value[2:]+value[:2]
  for (k,v) in dmg.items():
    if n=='' or v>m or (v==m and (value.index(k)<value.index(n))):
      n = k
      m = v
  best = (names[n],int(m),rolls[n])

  return (rolls,dmgs,best)

def calc_many(ac):

  results = []
  for i in range(ac[0],ac[1]+1):
    (rolls,dmgs,best) = calc_one(i)
    results.append((i,best[0],best[1],best[2]))
  return results

def get_dmg(ac,bonus,dmg):

  need = max([2,min([20,ac-bonus])])
  dmg = dmg*(20-need+1)/20.0
  return (need,dmg)

def get_dice(s):

  s.replace(' ','')
  dice = s.split('+')
  total = 0
  for die in dice:
    (n,d) = die.split('d')
    if len(n):
      n = int(n)
    else:
      n = 1
    d = int(d)
    total += n*(d+1)/2.0
  return total

if __name__=='__main__':
  main(AC)
