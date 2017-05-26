#!/usr/bin/env python

# assume: aoe 2, mass 3, channel 2, saves 50%, touch hits 75%

# valid levels: 1,5,10,15
LEVEL = 15

FIGHT_DEF = True
DEAD_AIM = True
HASTE = False
KI_POINT = False

AC = 28

# global controls/overrides (OVERRIDE ignores ADD)
ADD_ATT = 0
ADD_DMG = 0
OVERRIDE_ATT = []
OVERRIDE_DMG = 0

def main():

  (atts,dmg,spell,low_spell,heal,low_heal,chan) = stats(LEVEL,FIGHT_DEF,DEAD_AIM,HASTE,KI_POINT)
  atts = OVERRIDE_ATT if OVERRIDE_ATT else [x+ADD_ATT for x in atts]
  dms = OVERRIDE_DMG if OVERRIDE_DMG else dmg+ADD_DMG
  prob_norm = [p20(AC-x) for x in atts]
  prob_luck = [pluck(AC-x) for x in atts]
  dmg_norm = reduce(lambda a,b: a+b*dmg,prob_norm,0)
  dmg_luck = reduce(lambda a,b: a+b*dmg,prob_luck,0)
  diff = dmg_luck-dmg_norm

  print 'Level %s / AC %s' % (LEVEL,AC)
  print 'FD/DA/Ha/Ki : %s/%s/%s/%s' % (FIGHT_DEF,DEAD_AIM,HASTE,KI_POINT)
  print ''
  print 'Attacks : %s' % ' / '.join(['%3s'%('+%s'%x) for x in atts])
  print 'Probs   : %s' % ' / '.join(['%2.d%%'%(100*x) for x in prob_norm])
  print ' + Luck : %s' % ' / '.join(['%2.d%%'%(100*x) for x in prob_luck])
  print 'Dmg per : %.1f' % dmg
  print 'Expect  : %.1f' % dmg_norm
  print ' + Luck : %.1f' % dmg_luck
  print ''
  print 'Mult    : %.d%%' % (100*dmg_luck/dmg_norm)
  print 'Differ  : %.1f' % diff
  print ''
  print 'Spell   : %-5.1f : %s' % (spell,SPELLS[LEVEL][0])
  print 'Spell-2 : %-5.1f : %s' % (low_spell,SPELLS[LEVEL][1])
  print 'Heal    : %-5.1f : %s' % (heal,HEALS[LEVEL][0])
  print 'Heal-2  : %-5.1f : %s' % (low_heal,HEALS[LEVEL][1])
  print 'Chan x2 : %-5.1f : %sd6' % (2*chan,LEVEL/2+1)

def p20(n):
  """probability of rolling this number or higher"""
  n = min(20,max(2,n))
  return 5.0*(20-n+1)/100

def pluck(n):
  n = min(20,max(2,n))
  return [100,99.74,98.99,97.73,96.0,93.73,90.96,87.73,83.96,79.71,74.96,69.72,
      63.97,57.73,50.96,43.72,35.93,27.73,19.0,9.77][n-1]/100

def stats(lvl,fd=False,da=False,haste=False,ki=False):
  """returns: ([bonuses],dmg,spelldmg,spell-2dmg,heal,heal-2,chan)"""
  return {1:one,5:five,10:ten,15:fifteen,20:twenty}[lvl](fd,da,haste,ki)

def mod(lvl,attacks,fd,da,haste,ki):
  (atts,dmg) = attacks
  if haste and lvl>=5:
    atts.insert(0,atts[0])
    atts = [x+1 for x in atts]
  if ki and lvl>=5:
    atts.insert(0,atts[0])
  if fd:
    atts = [x-(4 if lvl<15 else 2) for x in atts]
  if da and lvl>=5:
    bonus = 1+lvl/4
    atts = [x-bonus for x in atts]
    dmg += 2*bonus
  return [atts,dmg]

def one(*args):
  # MW LB, Dex16, BAB1; pbshot
  # summon eagle, bleed; CLW, virtue; chan1d6
  attacks = [[6],5.5] # 1d8+1
  spells = [7.5/2,1] # 3d4, 1
  heals = [5.5,1,3.5] # 1d8+1, 1, 1d6
  attacks = mod(1,attacks,*args)
  return attacks+spells+heals

def five(*args):
  # MW LB+4, Dex16/Str18, BAB3, flurry 2; pbshot, da, wfocus
  # searing light, summon eagle; CSW, CLW; chan3d6
  attacks = [[8,8],9.5] # 1d8+5
  spells = [9.0/1.5,7.5/2] # 2d8, 3d4
  heals = [18.5,9.5,10.5] # 3d8+5, 1d8+5, 3d6
  attacks = mod(5,attacks,*args)
  return attacks+spells+heals

def ten(*args):
  # +1 LB+4, Dex18/Str18, BAB8, flurry 7; pbshot, da, wfocus, elemental
  # flame strike, searing light; MCLW, CSW; chan5d6
  attacks = [[14,14,9],14] # 1d8+1d6+6
  spells = [2/2*35,22.5/1.5] # 10d6, 5d8
  heals = [3*14.5,23.5,17.5] # 1d8+10, 3d8+10, 5d6
  attacks = mod(10,attacks,*args)
  return attacks+spells+heals

def fifteen(*args):
  # +2 LB+4, Dex18/Str18, BAB13, flurry 12; pbshot, da, wfocus, elemental, crane
  # destruction, flame strike; MCCW, heal; chan8d6
  attacks = [[20,20,15,10],15] # 1d8+1d6+7
  spells = [(150+35.0)/2,2/2*52.5] # 150/10d6, 15d6
  heals = [3*33,150,28] # 4d8+15, 150, 8d6
  attacks = mod(15,attacks,*args)
  return attacks+spells+heals

def twenty(*args):
  raise NotImplementedError

SPELLS = {
  1  : ('Summon Monster I (eagle)','Bleed'),
  5  : ('Searing Light','Summon Monster I (eagle)'),
  10 : ('Flame Strike','Searing Light'),
  15 : ('Destruction','Flame Strike'),
  20 : ('','')}

HEALS = {
  1  : ('Cure Light Wounds','Virtue'),
  5  : ('Cure Serious Wounds','Cure Light Wounds'),
  10 : ('Mass Cure Light Wounds','Cure Serious Wounds'),
  15 : ('Mass Cure Critical Wounds','Heal'),
  20 : ('','')}

if __name__=='__main__':
  main()
